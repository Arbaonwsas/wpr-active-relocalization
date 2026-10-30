#!/usr/bin/env python3
"""Active, safety-oriented global relocalization for Nav2 AMCL."""

from dataclasses import dataclass
import json
import math
import threading
import time

from action_msgs.msg import GoalStatus, GoalStatusArray
from action_msgs.srv import CancelGoal
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist
from nav_msgs.msg import OccupancyGrid, Odometry
from nav2_msgs.srv import ClearEntireCostmap
import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rclpy.time import Time
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from std_srvs.srv import Empty, Trigger
from tf2_ros import Buffer, TransformException, TransformListener

from wpr_relocalization.active_hypotheses import (
    Hypothesis,
    HypothesisSearch,
    advance_pose,
    relative_motion,
    scan_endpoints,
    unique_candidate,
)
from wpr_relocalization.relocalization_core import (
    ConsecutiveMismatchDetector,
    LikelihoodField,
    OdometryDiscontinuityDetector,
    WindowedMismatchDetector,
    normalize_angle,
    quaternion_to_yaw,
)


@dataclass(frozen=True)
class LocalizationQuality:
    sequence: int
    pose_sequence: int
    scan_score: float
    beams_used: int
    in_map_fraction: float
    x_variance: float
    y_variance: float
    yaw_variance: float
    odom_position_error: float | None
    odom_yaw_error: float | None


class ActiveGlobalRelocalization(Node):
    """Expose a blocking Trigger service that actively relocalizes AMCL."""

    def __init__(self) -> None:
        super().__init__('active_global_relocalization')
        self._callback_group = ReentrantCallbackGroup()
        self._data_lock = threading.RLock()
        self._run_lock = threading.Lock()

        self.declare_parameter('angular_speed', 0.35)
        self.declare_parameter('rotation_radians', 7.20)
        self.declare_parameter('attempts', 2)
        self.declare_parameter('minimum_rotation_before_success', 1.20)
        self.declare_parameter('control_frequency', 20.0)
        self.declare_parameter('service_timeout', 15.0)
        self.declare_parameter('sensor_timeout', 0.5)
        self.declare_parameter('translation_robot_radius', 0.22)
        self.declare_parameter('active_hypothesis_relocalization', False)
        self.declare_parameter('hypothesis_score_margin', 0.15)
        self.declare_parameter('hypothesis_maximum_moves', 3)
        self.declare_parameter('hypothesis_maximum_travel', 1.8)
        self.declare_parameter('maximum_wall_duration', 360.0)
        self.declare_parameter('motion_stall_timeout', 15.0)
        self.declare_parameter('stop_speed_threshold', 0.01)
        self.declare_parameter('stop_consecutive_samples', 3)
        self.declare_parameter('stop_minimum_commands', 3)
        self.declare_parameter('stationary_good_scans', 2)
        self.declare_parameter('stationary_confirmation_timeout', 2.0)
        self.declare_parameter('automatic_relocalization', False)
        self.declare_parameter('automatic_mismatch_score', 0.35)
        self.declare_parameter('automatic_mismatch_in_map_fraction', 0.65)
        self.declare_parameter('automatic_mismatch_scans', 12)
        self.declare_parameter('automatic_suspect_score', 0.60)
        self.declare_parameter('automatic_suspect_window_scans', 40)
        self.declare_parameter('automatic_suspect_required_ratio', 0.90)
        self.declare_parameter('automatic_odom_jump_translation', 0.75)
        self.declare_parameter('automatic_odom_jump_yaw', 0.80)
        self.declare_parameter('simulation_odom_validation', False)
        self.declare_parameter('simulation_max_odom_position_error', 0.75)
        self.declare_parameter('simulation_max_odom_yaw_error', 0.60)
        self.declare_parameter('automatic_trigger_cooldown', 8.0)
        self.declare_parameter('translation_distance', 0.55)
        self.declare_parameter('translation_speed', 0.16)
        self.declare_parameter('translation_clearance', 0.45)
        self.declare_parameter('translation_sector_half_angle', 0.52)
        self.declare_parameter('consecutive_good_scans', 3)
        self.declare_parameter('max_xy_variance', 0.40)
        self.declare_parameter('max_yaw_variance', 0.12)
        self.declare_parameter('minimum_scan_score', 0.60)
        self.declare_parameter('minimum_in_map_fraction', 0.80)
        self.declare_parameter('minimum_score_beams', 25)
        self.declare_parameter('score_sigma', 0.20)
        self.declare_parameter('score_minimum_range', 0.35)
        self.declare_parameter('score_maximum_range', 8.0)
        self.declare_parameter('score_maximum_beams', 180)
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('odom_topic', '/odom')
        self.declare_parameter('amcl_pose_topic', '/amcl_pose')
        self.declare_parameter('map_topic', '/map')

        self._angular_speed = abs(self._double('angular_speed'))
        self._rotation_radians = abs(self._double('rotation_radians'))
        self._attempts = max(1, self._integer('attempts'))
        self._minimum_rotation = abs(
            self._double('minimum_rotation_before_success')
        )
        self._control_frequency = max(2.0, self._double('control_frequency'))
        self._service_timeout = max(1.0, self._double('service_timeout'))
        self._sensor_timeout = max(0.1, self._double('sensor_timeout'))
        self._translation_robot_radius = max(
            0.0, self._double('translation_robot_radius')
        )
        self._active_hypotheses = self._boolean('active_hypothesis_relocalization')
        self._hypothesis_score_margin = max(0.05, self._double('hypothesis_score_margin'))
        self._hypothesis_maximum_moves = max(0, self._integer('hypothesis_maximum_moves'))
        self._hypothesis_maximum_travel = max(0.0, self._double('hypothesis_maximum_travel'))
        self._maximum_wall_duration = max(
            30.0, self._double('maximum_wall_duration')
        )
        self._motion_stall_timeout = max(
            3.0, self._double('motion_stall_timeout')
        )
        self._stop_speed_threshold = max(
            0.0, self._double('stop_speed_threshold')
        )
        self._stop_consecutive_samples = max(
            1, self._integer('stop_consecutive_samples')
        )
        self._stop_minimum_commands = max(
            1, self._integer('stop_minimum_commands')
        )
        self._stationary_good_scans = max(
            1, self._integer('stationary_good_scans')
        )
        self._stationary_confirmation_timeout = max(
            0.5, self._double('stationary_confirmation_timeout')
        )
        self._automatic_relocalization = self._boolean(
            'automatic_relocalization'
        )
        self._automatic_trigger_cooldown = max(
            0.0, self._double('automatic_trigger_cooldown')
        )
        self._mismatch_detector = ConsecutiveMismatchDetector(
            maximum_score=self._double('automatic_mismatch_score'),
            minimum_in_map_fraction=self._double(
                'automatic_mismatch_in_map_fraction'
            ),
            minimum_beams=self._integer('minimum_score_beams'),
            required_consecutive=max(
                1, self._integer('automatic_mismatch_scans')
            ),
            maximum_xy_variance=self._double('max_xy_variance'),
            maximum_yaw_variance=self._double('max_yaw_variance'),
        )
        self._suspect_mismatch_detector = WindowedMismatchDetector(
            maximum_score=self._double('automatic_suspect_score'),
            minimum_beams=self._integer('minimum_score_beams'),
            window_size=max(
                1, self._integer('automatic_suspect_window_scans')
            ),
            required_ratio=self._double(
                'automatic_suspect_required_ratio'
            ),
        )
        self._odom_discontinuity_detector = OdometryDiscontinuityDetector(
            maximum_translation_jump=self._double(
                'automatic_odom_jump_translation'
            ),
            maximum_yaw_jump=self._double('automatic_odom_jump_yaw'),
        )
        self._simulation_odom_validation = self._boolean(
            'simulation_odom_validation'
        )
        self._simulation_max_odom_position_error = max(
            0.0, self._double('simulation_max_odom_position_error')
        )
        self._simulation_max_odom_yaw_error = max(
            0.0, self._double('simulation_max_odom_yaw_error')
        )
        self._translation_distance = max(
            0.0, self._double('translation_distance')
        )
        self._translation_speed = max(
            0.05, abs(self._double('translation_speed'))
        )
        self._translation_clearance = max(
            0.20, self._double('translation_clearance')
        )
        self._translation_sector_half_angle = max(
            0.10, self._double('translation_sector_half_angle')
        )
        self._required_good_scans = max(
            1, self._integer('consecutive_good_scans')
        )
        self._max_xy_variance = self._double('max_xy_variance')
        self._max_yaw_variance = self._double('max_yaw_variance')
        self._minimum_scan_score = self._double('minimum_scan_score')
        self._minimum_in_map_fraction = self._double(
            'minimum_in_map_fraction'
        )
        self._minimum_score_beams = self._integer('minimum_score_beams')
        self._score_sigma = self._double('score_sigma')
        self._score_minimum_range = self._double('score_minimum_range')
        self._score_maximum_range = self._double('score_maximum_range')
        self._score_maximum_beams = self._integer('score_maximum_beams')
        self._base_frame = self._string('base_frame')

        self._map_field: LikelihoodField | None = None
        self._hypothesis_search: HypothesisSearch | None = None
        self._latest_pose: PoseWithCovarianceStamped | None = None
        self._latest_odom_yaw: float | None = None
        self._latest_odom_position: tuple[float, float] | None = None
        self._latest_speed_norm: float | None = None
        self._odom_sequence = 0
        self._latest_odom_wall_time = 0.0
        self._latest_scan_wall_time = 0.0
        self._latest_scan: LaserScan | None = None
        self._latest_quality: LocalizationQuality | None = None
        self._quality_sequence = 0
        self._pose_sequence = 0
        self._laser_transform: tuple[float, float, float] | None = None
        self._laser_frame = ''
        self._run_sequence = 0
        self._active_run_id = 0
        self._event_sequence = 0
        self._run_start_wall: float | None = None
        self._run_start_sim: float | None = None
        self._phase_state = ''
        self._phase_start_wall: float | None = None
        self._phase_start_sim: float | None = None
        self._automatic_trigger_pending = False
        self._automatic_failure_latched = False
        self._pending_odom_jump: tuple[float, float] | None = None
        self._last_relocalization_end_wall = 0.0
        self._navigation_status = {}

        status_qos = QoSProfile(depth=1)
        status_qos.reliability = ReliabilityPolicy.RELIABLE
        status_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        self._cmd_pub = self.create_publisher(
            Twist, self._string('cmd_vel_topic'), 10
        )
        self._initial_pose_pub = self.create_publisher(
            PoseWithCovarianceStamped, '/initialpose', 10
        )
        self._status_pub = self.create_publisher(
            String, '/global_relocalization/status', status_qos
        )
        self._quality_pub = self.create_publisher(
            String, '/global_relocalization/quality', 10
        )
        self.create_subscription(
            OccupancyGrid,
            self._string('map_topic'),
            self._on_map,
            map_qos,
            callback_group=self._callback_group,
        )
        self.create_subscription(
            PoseWithCovarianceStamped,
            self._string('amcl_pose_topic'),
            self._on_pose,
            10,
            callback_group=self._callback_group,
        )
        self.create_subscription(
            Odometry,
            self._string('odom_topic'),
            self._on_odom,
            qos_profile_sensor_data,
            callback_group=self._callback_group,
        )
        self.create_subscription(
            LaserScan,
            self._string('scan_topic'),
            self._on_scan,
            qos_profile_sensor_data,
            callback_group=self._callback_group,
        )

        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)
        self._global_init_client = self.create_client(
            Empty,
            '/reinitialize_global_localization',
            callback_group=self._callback_group,
        )
        self._nomotion_update_client = self.create_client(
            Empty,
            '/request_nomotion_update',
            callback_group=self._callback_group,
        )
        self._cancel_clients = {}
        for action_name in ('navigate_to_pose', 'navigate_through_poses'):
            self._cancel_clients[action_name] = self.create_client(
                CancelGoal,
                f'/{action_name}/_action/cancel_goal',
                callback_group=self._callback_group,
            )
            self.create_subscription(
                GoalStatusArray,
                f'/{action_name}/_action/status',
                lambda message, name=action_name: self._on_navigation_status(
                    name, message
                ),
                status_qos,
                callback_group=self._callback_group,
            )
        self._clear_global_client = self.create_client(
            ClearEntireCostmap,
            '/global_costmap/clear_entirely_global_costmap',
            callback_group=self._callback_group,
        )
        self._clear_local_client = self.create_client(
            ClearEntireCostmap,
            '/local_costmap/clear_entirely_local_costmap',
            callback_group=self._callback_group,
        )
        self.create_service(
            Trigger,
            '/global_relocalization',
            self._on_trigger,
            callback_group=self._callback_group,
        )
        self._publish_status('IDLE', 'ready')
        self.get_logger().info(
            'Active global relocalization ready on /global_relocalization'
        )

    def _double(self, name: str) -> float:
        return float(self.get_parameter(name).value)

    def _integer(self, name: str) -> int:
        return int(self.get_parameter(name).value)

    def _boolean(self, name: str) -> bool:
        return bool(self.get_parameter(name).value)

    def _string(self, name: str) -> str:
        return str(self.get_parameter(name).value)

    def _on_map(self, message: OccupancyGrid) -> None:
        try:
            field = LikelihoodField(
                message.info.width,
                message.info.height,
                message.info.resolution,
                message.info.origin.position.x,
                message.info.origin.position.y,
                message.data,
            )
        except ValueError as error:
            self.get_logger().error(f'Cannot build likelihood field: {error}')
            return
        with self._data_lock:
            self._map_field = field
            self._hypothesis_search = HypothesisSearch(
                field, message.data, self._translation_robot_radius
            )
        self.get_logger().info(
            f'Likelihood field ready: {field.width}x{field.height}'
        )

    def _on_pose(self, message: PoseWithCovarianceStamped) -> None:
        with self._data_lock:
            self._latest_pose = message
            self._pose_sequence += 1

    def _on_odom(self, message: Odometry) -> None:
        orientation = message.pose.pose.orientation
        yaw = quaternion_to_yaw(
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        )
        position = (
            message.pose.pose.position.x,
            message.pose.pose.position.y,
        )
        with self._data_lock:
            discontinuous, translation, yaw_change = (
                self._odom_discontinuity_detector.update(position, yaw)
            )
            if (
                discontinuous
                and self._automatic_relocalization
                and not self._run_lock.locked()
            ):
                self._pending_odom_jump = (translation, yaw_change)
                self._automatic_failure_latched = False
            self._latest_odom_yaw = yaw
            self._latest_odom_position = position
            self._latest_speed_norm = max(
                abs(message.twist.twist.linear.x),
                abs(message.twist.twist.linear.y),
                abs(message.twist.twist.angular.z),
            )
            self._odom_sequence += 1
            self._latest_odom_wall_time = time.monotonic()

    def _on_scan(self, message: LaserScan) -> None:
        with self._data_lock:
            self._latest_scan_wall_time = time.monotonic()
            self._latest_scan = message
            field = self._map_field
            pose_message = self._latest_pose
            pose_sequence = self._pose_sequence
            odom_position = self._latest_odom_position
            odom_yaw = self._latest_odom_yaw
        laser_transform = self._lookup_laser_transform(message.header.frame_id)
        if field is None or pose_message is None or laser_transform is None:
            return

        pose = pose_message.pose.pose
        orientation = pose.orientation
        base_pose = (
            pose.position.x,
            pose.position.y,
            quaternion_to_yaw(
                orientation.x,
                orientation.y,
                orientation.z,
                orientation.w,
            ),
        )
        score = field.score_scan(
            base_pose,
            message.ranges,
            message.angle_min,
            message.angle_increment,
            message.range_min,
            message.range_max,
            laser_transform,
            sigma=self._score_sigma,
            min_usable_range=self._score_minimum_range,
            max_usable_range=self._score_maximum_range,
            max_beams=self._score_maximum_beams,
        )
        covariance = pose_message.pose.covariance
        odom_position_error = None
        odom_yaw_error = None
        if odom_position is not None and odom_yaw is not None:
            odom_position_error = math.hypot(
                base_pose[0] - odom_position[0],
                base_pose[1] - odom_position[1],
            )
            odom_yaw_error = abs(normalize_angle(base_pose[2] - odom_yaw))
        with self._data_lock:
            self._quality_sequence += 1
            quality = LocalizationQuality(
                sequence=self._quality_sequence,
                pose_sequence=pose_sequence,
                scan_score=score.likelihood,
                beams_used=score.beams_used,
                in_map_fraction=score.in_map_fraction,
                x_variance=max(0.0, covariance[0]),
                y_variance=max(0.0, covariance[7]),
                yaw_variance=max(0.0, covariance[35]),
                odom_position_error=odom_position_error,
                odom_yaw_error=odom_yaw_error,
            )
            self._latest_quality = quality
        self._quality_pub.publish(String(data=json.dumps(quality.__dict__)))
        self._consider_automatic_relocalization(quality)

    def _lookup_laser_transform(
        self, laser_frame: str
    ) -> tuple[float, float, float] | None:
        if not laser_frame:
            return None
        with self._data_lock:
            if self._laser_frame == laser_frame and self._laser_transform:
                return self._laser_transform
        try:
            transform = self._tf_buffer.lookup_transform(
                self._base_frame, laser_frame, Time()
            )
        except TransformException as error:
            self.get_logger().warning(
                f'Waiting for {self._base_frame} <- {laser_frame}: {error}',
                throttle_duration_sec=5.0,
            )
            return None
        translation = transform.transform.translation
        rotation = transform.transform.rotation
        result = (
            translation.x,
            translation.y,
            quaternion_to_yaw(
                rotation.x, rotation.y, rotation.z, rotation.w
            ),
        )
        with self._data_lock:
            self._laser_frame = laser_frame
            self._laser_transform = result
        return result

    def _sim_seconds(self) -> float:
        return self.get_clock().now().nanoseconds * 1.0e-9

    def _begin_run_telemetry(self) -> None:
        now_wall = time.monotonic()
        now_sim = self._sim_seconds()
        with self._data_lock:
            self._run_sequence += 1
            self._active_run_id = self._run_sequence
            self._event_sequence = 0
            self._run_start_wall = now_wall
            self._run_start_sim = now_sim
            self._phase_state = ''
            self._phase_start_wall = now_wall
            self._phase_start_sim = now_sim

    def _publish_status(
        self,
        state: str,
        detail: str,
        **extra: object,
    ) -> None:
        now_wall = time.monotonic()
        now_sim = self._sim_seconds()
        with self._data_lock:
            if state != self._phase_state:
                self._phase_state = state
                self._phase_start_wall = now_wall
                self._phase_start_sim = now_sim
            self._event_sequence += 1
            run_start_wall = self._run_start_wall
            run_start_sim = self._run_start_sim
            phase_start_wall = self._phase_start_wall
            phase_start_sim = self._phase_start_sim
            payload = {
                'schema_version': 2,
                'run_id': self._active_run_id,
                'event_index': self._event_sequence,
                'state': state,
                'detail': detail,
                'wall_elapsed_sec': round(
                    now_wall - run_start_wall
                    if run_start_wall is not None else 0.0,
                    6,
                ),
                'sim_elapsed_sec': round(
                    now_sim - run_start_sim
                    if run_start_sim is not None else 0.0,
                    6,
                ),
                'phase_wall_sec': round(
                    now_wall - phase_start_wall
                    if phase_start_wall is not None else 0.0,
                    6,
                ),
                'phase_sim_sec': round(
                    now_sim - phase_start_sim
                    if phase_start_sim is not None else 0.0,
                    6,
                ),
                **extra,
            }
        self._status_pub.publish(
            String(data=json.dumps(payload, ensure_ascii=False))
        )
        self.get_logger().info(f'{state}: {detail}')

    def _call_service(self, client, request, timeout: float):
        if not client.wait_for_service(timeout_sec=timeout):
            return None
        event = threading.Event()
        holder = {}
        future = client.call_async(request)

        def done_callback(done_future) -> None:
            try:
                holder['response'] = done_future.result()
            except Exception as error:  # rclpy propagates service failures here
                holder['error'] = error
            event.set()

        future.add_done_callback(done_callback)
        if not event.wait(timeout):
            future.cancel()
            return None
        if 'error' in holder:
            self.get_logger().error(f'Service call failed: {holder["error"]}')
            return None
        return holder.get('response')

    def _on_navigation_status(self, name, message: GoalStatusArray) -> None:
        with self._data_lock:
            self._navigation_status[name] = {
                bytes(item.goal_info.goal_id.uuid): item.status
                for item in message.status_list
            }

    def _navigation_is_active(self) -> bool:
        active = {
            GoalStatus.STATUS_ACCEPTED,
            GoalStatus.STATUS_EXECUTING,
            GoalStatus.STATUS_CANCELING,
        }
        with self._data_lock:
            return any(
                status in active
                for goals in self._navigation_status.values()
                for status in goals.values()
            )

    def _cancel_navigation(self) -> bool:
        # Send stop commands before any potentially blocking service discovery.
        self._stop_robot(10)
        pending = []
        for name, client in self._cancel_clients.items():
            response = self._call_service(
                client, CancelGoal.Request(), self._service_timeout
            )
            if response is None or response.return_code != CancelGoal.Response.ERROR_NONE:
                self.get_logger().error(f'Cannot confirm cancellation of {name}')
                return False
            pending.extend(
                (name, bytes(goal.goal_id.uuid))
                for goal in response.goals_canceling
            )

        terminal = {
            GoalStatus.STATUS_SUCCEEDED,
            GoalStatus.STATUS_CANCELED,
            GoalStatus.STATUS_ABORTED,
        }
        deadline = time.monotonic() + self._service_timeout
        while rclpy.ok() and time.monotonic() < deadline:
            with self._data_lock:
                finished = all(
                    self._navigation_status.get(name, {}).get(goal_id) in terminal
                    for name, goal_id in pending
                )
            if finished and not self._navigation_is_active():
                return True
            self._cmd_pub.publish(Twist())
            time.sleep(1.0 / self._control_frequency)
        return False

    def _motion_inputs_ready(self) -> bool:
        now = time.monotonic()
        with self._data_lock:
            fresh = (
                self._latest_scan is not None
                and self._latest_odom_position is not None
                and now - self._latest_scan_wall_time <= self._sensor_timeout
                and now - self._latest_odom_wall_time <= self._sensor_timeout
            )
        return fresh and not self._navigation_is_active()

    def _clear_costmaps(self) -> None:
        for client in (self._clear_global_client, self._clear_local_client):
            self._call_service(
                client, ClearEntireCostmap.Request(), self._service_timeout
            )

    def _stop_robot(self, repetitions: int = 20) -> None:
        zero = Twist()
        period = 1.0 / self._control_frequency
        stable_samples = 0
        with self._data_lock:
            last_odom_sequence = self._odom_sequence
        for command_index in range(repetitions):
            try:
                self._cmd_pub.publish(zero)
            except Exception:
                break
            time.sleep(period)
            with self._data_lock:
                odom_sequence = self._odom_sequence
                speed_norm = self._latest_speed_norm
            if odom_sequence == last_odom_sequence:
                continue
            last_odom_sequence = odom_sequence
            if (
                speed_norm is not None
                and speed_norm <= self._stop_speed_threshold
            ):
                stable_samples += 1
            else:
                stable_samples = 0
            if (
                command_index + 1 >= self._stop_minimum_commands
                and stable_samples >= self._stop_consecutive_samples
            ):
                return

    def _ready(self) -> tuple[bool, str]:
        with self._data_lock:
            missing = []
            if self._map_field is None:
                missing.append('/map')
            if self._latest_odom_yaw is None:
                missing.append('/odom')
            if time.monotonic() - self._latest_scan_wall_time > self._sensor_timeout:
                missing.append('/scan')
            if time.monotonic() - self._latest_odom_wall_time > self._sensor_timeout:
                missing.append('fresh /odom')
            if self._laser_transform is None:
                missing.append('laser TF')
        if missing:
            return False, 'missing: ' + ', '.join(missing)
        return True, 'ready'

    def _quality_is_good(self, quality: LocalizationQuality) -> bool:
        return (
            quality.beams_used >= self._minimum_score_beams
            and quality.in_map_fraction >= self._minimum_in_map_fraction
            and quality.scan_score >= self._minimum_scan_score
            and quality.x_variance <= self._max_xy_variance
            and quality.y_variance <= self._max_xy_variance
            and quality.yaw_variance <= self._max_yaw_variance
            and self._simulation_odom_is_consistent(quality)
        )

    def _simulation_odom_is_consistent(
        self,
        quality: LocalizationQuality,
    ) -> bool:
        if not self._simulation_odom_validation:
            return True
        return (
            quality.odom_position_error is not None
            and quality.odom_yaw_error is not None
            and quality.odom_position_error
            <= self._simulation_max_odom_position_error
            and quality.odom_yaw_error
            <= self._simulation_max_odom_yaw_error
        )

    def _consider_automatic_relocalization(
        self,
        quality: LocalizationQuality,
    ) -> None:
        if not self._automatic_relocalization:
            return
        if self._run_lock.locked():
            with self._data_lock:
                self._reset_mismatch_detectors()
            return

        now = time.monotonic()
        with self._data_lock:
            if self._automatic_failure_latched:
                if self._quality_is_good(quality):
                    self._automatic_failure_latched = False
                elif self._pending_odom_jump is None:
                    self._reset_mismatch_detectors()
                    return
            cooling_down = (
                now - self._last_relocalization_end_wall
                < self._automatic_trigger_cooldown
            )
            if self._automatic_trigger_pending or cooling_down:
                self._reset_mismatch_detectors()
                return
            odom_jump = self._pending_odom_jump
            hard_mismatch = False
            suspect_mismatch = False
            simulation_mismatch = (
                self._simulation_odom_validation
                and not self._simulation_odom_is_consistent(quality)
            )
            if odom_jump is None:
                hard_mismatch = self._mismatch_detector.update(
                    quality.scan_score,
                    quality.beams_used,
                    quality.in_map_fraction,
                    quality.x_variance,
                    quality.y_variance,
                    quality.yaw_variance,
                    forced_mismatch=simulation_mismatch,
                )
                suspect_mismatch = self._suspect_mismatch_detector.update(
                    quality.scan_score,
                    quality.beams_used,
                )
            if odom_jump is None and not hard_mismatch and not suspect_mismatch:
                return
            if odom_jump is not None:
                trigger_reason = (
                    'odometry discontinuity '
                    f'(translation={odom_jump[0]:.2f} m, '
                    f'yaw={odom_jump[1]:.2f} rad)'
                )
                self._pending_odom_jump = None
            elif hard_mismatch and simulation_mismatch:
                position_error = (
                    'unavailable'
                    if quality.odom_position_error is None
                    else f'{quality.odom_position_error:.2f} m'
                )
                yaw_error = (
                    'unavailable'
                    if quality.odom_yaw_error is None
                    else f'{quality.odom_yaw_error:.2f} rad'
                )
                trigger_reason = (
                    'simulation odometry disagreement '
                    f'(position={position_error}, yaw={yaw_error})'
                )
            elif hard_mismatch:
                trigger_reason = 'persistent hard mismatch'
            else:
                trigger_reason = 'windowed moderate mismatch'
            self._automatic_trigger_pending = True

        thread = threading.Thread(
            target=self._run_automatic_relocalization,
            args=(quality, trigger_reason),
            name='automatic_global_relocalization',
            daemon=True,
        )
        thread.start()

    def _run_automatic_relocalization(
        self,
        quality: LocalizationQuality,
        trigger_reason: str,
    ) -> None:
        self.get_logger().warning(
            f'{trigger_reason.capitalize()} detected; starting automatic '
            f'recovery (score={quality.scan_score:.3f}, '
            f'in_map={quality.in_map_fraction:.3f})'
        )
        response = Trigger.Response()
        try:
            self._execute_relocalization(response, trigger_source='automatic')
            result = f'Automatic relocalization result: {response.message}'
            if response.success:
                with self._data_lock:
                    self._automatic_failure_latched = False
                self.get_logger().info(result)
            else:
                with self._data_lock:
                    self._automatic_failure_latched = True
                self.get_logger().error(result)
        finally:
            with self._data_lock:
                self._automatic_trigger_pending = False

    def _reset_mismatch_detectors(self) -> None:
        self._mismatch_detector.reset()
        self._suspect_mismatch_detector.reset()

    def _confirm_stationary_quality(
        self,
        attempt: int,
        global_deadline: float,
    ) -> tuple[bool, str]:
        self._publish_status(
            'VERIFYING_STATIONARY',
            'requesting AMCL no-motion quality updates',
            attempt=attempt,
            required_good_scans=self._stationary_good_scans,
        )
        verification_deadline = min(
            global_deadline,
            time.monotonic() + self._stationary_confirmation_timeout,
        )
        with self._data_lock:
            last_pose_sequence = self._pose_sequence
            last_quality_sequence = self._quality_sequence

        good_scans = 0
        while rclpy.ok() and time.monotonic() < verification_deadline:
            remaining = verification_deadline - time.monotonic()
            response = self._call_service(
                self._nomotion_update_client,
                Empty.Request(),
                min(self._service_timeout, max(0.05, remaining)),
            )
            if response is None:
                return False, 'AMCL no-motion update service unavailable'

            while rclpy.ok() and time.monotonic() < verification_deadline:
                with self._data_lock:
                    quality = self._latest_quality
                if (
                    quality is not None
                    and quality.sequence > last_quality_sequence
                    and quality.pose_sequence > last_pose_sequence
                ):
                    last_quality_sequence = quality.sequence
                    last_pose_sequence = quality.pose_sequence
                    if not self._quality_is_good(quality):
                        return False, (
                            'stationary quality check failed; '
                            f'score={quality.scan_score:.3f}, '
                            f'variance=({quality.x_variance:.3f}, '
                            f'{quality.y_variance:.3f}, '
                            f'{quality.yaw_variance:.3f})'
                        )
                    good_scans += 1
                    if good_scans >= self._stationary_good_scans:
                        return True, (
                            'stationary quality confirmed; '
                            f'score={quality.scan_score:.3f}, '
                            f'variance=({quality.x_variance:.3f}, '
                            f'{quality.y_variance:.3f}, '
                            f'{quality.yaw_variance:.3f})'
                        )
                    break
                time.sleep(1.0 / self._control_frequency)

        return False, 'stationary quality confirmation timed out'

    def _sector_clearance(self, scan: LaserScan, center: float) -> float:
        # Check every endpoint in the swept footprint, including thin obstacles
        # and points outside the forward angular sector. The sector only proves
        # that the sensor actually observes the intended direction.
        transform = self._laser_transform
        if transform is None:
            return 0.0
        lx, ly, laser_yaw = transform
        direction = center + laser_yaw
        cos_dir, sin_dir = math.cos(direction), math.sin(direction)
        clearance = min(scan.range_max, self._score_maximum_range)
        observed = False
        for index, measured_range in enumerate(scan.ranges):
            angle = scan.angle_min + index * scan.angle_increment
            in_sector = (
                abs(normalize_angle(angle - center))
                <= self._translation_sector_half_angle
            )
            if math.isinf(measured_range) and measured_range > 0:
                observed = observed or in_sector
                continue
            if not math.isfinite(measured_range) or measured_range < scan.range_min:
                if in_sector:
                    return 0.0
                continue
            if measured_range > scan.range_max:
                if in_sector:
                    return 0.0
                continue
            observed = observed or in_sector
            x = lx + measured_range * math.cos(angle + laser_yaw)
            y = ly + measured_range * math.sin(angle + laser_yaw)
            along = x * cos_dir + y * sin_dir
            lateral = abs(-x * sin_dir + y * cos_dir)
            radius = self._translation_robot_radius
            if lateral <= radius:
                half_chord = math.sqrt(max(0.0, radius * radius - lateral * lateral))
                if along + half_chord >= 0.0:
                    clearance = min(clearance, max(0.0, along - half_chord))
        return clearance if observed else 0.0

    def _translate_for_disambiguation(
        self, global_deadline: float, distance: float | None = None,
        fixed_direction: float | None = None,
    ) -> bool:
        target_distance = self._translation_distance if distance is None else distance
        if target_distance <= 0.0:
            return False
        with self._data_lock:
            scan = self._latest_scan
            start = self._latest_odom_position
            laser_transform = self._laser_transform
        if scan is None or start is None or laser_transform is None:
            self._publish_status('TRANSLATION_SKIPPED', 'scan or odometry unavailable')
            return False

        laser_yaw = laser_transform[2]
        front_center = -laser_yaw
        rear_center = math.pi - laser_yaw
        front = self._sector_clearance(scan, front_center)
        rear = self._sector_clearance(scan, rear_center)
        required = target_distance + self._translation_clearance
        available = max(front, rear) if fixed_direction is None else (
            front if fixed_direction > 0 else rear
        )
        if available < required:
            self._publish_status(
                'TRANSLATION_SKIPPED',
                'insufficient local clearance',
                front=round(front, 2),
                rear=round(rear, 2),
                required=round(required, 2),
            )
            return False

        direction = fixed_direction if fixed_direction is not None else (
            1.0 if front >= rear else -1.0
        )
        self._publish_status(
            'TRANSLATING',
            'breaking symmetric localization hypotheses',
            direction='forward' if direction > 0.0 else 'backward',
            distance=target_distance,
            front_clearance=round(front, 2),
            rear_clearance=round(rear, 2),
        )
        period = 1.0 / self._control_frequency
        last_motion_time = time.monotonic()
        previous_distance = 0.0
        while rclpy.ok() and time.monotonic() < global_deadline:
            if not self._motion_inputs_ready():
                self._stop_robot(20)
                raise RuntimeError('Motion aborted: stale sensors or active navigation')
            with self._data_lock:
                position = self._latest_odom_position
                current_scan = self._latest_scan
            if position is None or current_scan is None:
                self._stop_robot(10)
                return False
            distance = math.hypot(position[0] - start[0], position[1] - start[1])
            if distance >= target_distance:
                self._stop_robot(20)
                return True
            if distance > previous_distance + 1.0e-4:
                previous_distance = distance
                last_motion_time = time.monotonic()
            if time.monotonic() - last_motion_time > self._motion_stall_timeout:
                self._stop_robot(20)
                self._publish_status('TRANSLATION_SKIPPED', 'translation stalled')
                return False

            center = front_center if direction > 0.0 else rear_center
            clearance = self._sector_clearance(current_scan, center)
            if clearance < self._translation_clearance:
                self._stop_robot(20)
                self._publish_status(
                    'TRANSLATION_SKIPPED',
                    'obstacle approached during translation',
                    clearance=round(clearance, 2),
                )
                return False

            command = Twist()
            command.linear.x = direction * self._translation_speed
            self._cmd_pub.publish(command)
            time.sleep(period)
        self._stop_robot(20)
        return False

    def _hypothesis_snapshot(self, deadline, previous_scan=None):
        while rclpy.ok() and time.monotonic() < deadline:
            if not self._motion_inputs_ready():
                raise RuntimeError('Hypothesis recovery aborted: stale sensors or navigation')
            with self._data_lock:
                scan = self._latest_scan
                odom = (*self._latest_odom_position, self._latest_odom_yaw)
                laser = self._laser_transform
            if scan is not previous_scan and laser is not None:
                return scan, odom, scan_endpoints(scan, laser)
            time.sleep(1.0 / self._control_frequency)
        raise RuntimeError('Hypothesis recovery timed out waiting for a fresh scan')

    def _turn_for_information(self, heading, deadline):
        if abs(heading) < 0.03:
            return True
        sign = 1.0 if heading > 0 else -1.0
        with self._data_lock:
            previous_yaw = self._latest_odom_yaw
        progress = 0.0
        last_motion = time.monotonic()
        self._publish_status('TURNING_FOR_INFORMATION', 'facing informative direction',
                             heading=heading)
        while rclpy.ok() and time.monotonic() < deadline:
            if not self._motion_inputs_ready():
                raise RuntimeError('Informative turn aborted: stale sensors or navigation')
            with self._data_lock:
                yaw = self._latest_odom_yaw
            delta = sign * normalize_angle(yaw - previous_yaw)
            previous_yaw = yaw
            progress += delta
            if delta > 0.0001:
                last_motion = time.monotonic()
            remaining = abs(heading) - progress
            if remaining <= 0.03:
                self._stop_robot(20)
                return True
            if time.monotonic() - last_motion > self._motion_stall_timeout:
                raise RuntimeError('Informative turn stalled')
            command = Twist()
            # The simulated planar base barely responds below 0.35 rad/s.
            # Keep a useful command down to the angle tolerance, then stop via
            # the velocity smoother rather than spending seconds creeping.
            command.angular.z = sign * min(self._angular_speed, max(0.5, 2 * remaining))
            self._cmd_pub.publish(command)
            time.sleep(1.0 / self._control_frequency)
        self._stop_robot(20)
        return False

    def _resolve_hypotheses(self, deadline):
        with self._data_lock:
            search = self._hypothesis_search
            laser = self._laser_transform
        if search is None:
            return False, 'hypothesis map unavailable'
        self._stop_robot(10)
        scan, previous_odom, endpoints = self._hypothesis_snapshot(deadline)
        self._publish_status('SEARCHING_HYPOTHESES', 'global laser-only candidate search')
        candidates = search.global_candidates(endpoints)
        if len(candidates) < 2:
            return False, 'insufficient global pose candidates'
        totals = [h.score for h in candidates]
        observations = 1
        travel = 0.0
        for move in range(self._hypothesis_maximum_moves + 1):
            if time.monotonic() >= deadline:
                return False, 'hypothesis recovery time budget exhausted'
            means = [value / observations for value in totals]
            winner = unique_candidate(candidates, means, self._hypothesis_score_margin)
            self._publish_status(
                'COMPARING_HYPOTHESES', 'checking distinct pose modes',
                move=move, observations=observations, travel=travel,
                hypotheses=[{'pose': h.pose, 'score': h.score, 'mean_score': mean}
                            for h, mean in zip(candidates, means)],
            )
            if winner is not None:
                # A second fresh scan must independently preserve the winner.
                fresh, current_odom, points = self._hypothesis_snapshot(deadline, scan)
                delta = relative_motion(previous_odom, current_odom)
                verified = []
                for h in candidates:
                    predicted = Hypothesis(*advance_pose(h.pose, delta), h.score)
                    refined = search.refine([predicted], points, 0.05, 0.04)
                    verified.append(refined[0] if refined else Hypothesis(
                        *predicted.pose, 0.0))
                totals = [old + h.score for old, h in zip(totals, verified)]
                observations += 1
                candidates = verified
                scan, previous_odom = fresh, current_odom
                means = [value / observations for value in totals]
                if unique_candidate(candidates, means, self._hypothesis_score_margin) == winner:
                    message = PoseWithCovarianceStamped()
                    message.header.frame_id = 'map'
                    message.header.stamp = self.get_clock().now().to_msg()
                    chosen = candidates[winner]
                    message.pose.pose.position.x = chosen.x
                    message.pose.pose.position.y = chosen.y
                    message.pose.pose.orientation.z = math.sin(chosen.yaw / 2)
                    message.pose.pose.orientation.w = math.cos(chosen.yaw / 2)
                    message.pose.covariance[0] = 0.01
                    message.pose.covariance[7] = 0.01
                    message.pose.covariance[35] = 0.01
                    self._publish_status(
                        'SEEDING_AMCL', 'distinct laser candidate initializes AMCL',
                        candidate_pose=chosen.pose, score=chosen.score,
                    )
                    with self._data_lock:
                        pose_epoch = self._pose_sequence
                    self._initial_pose_pub.publish(message)
                    # Wait for AMCL to consume the prior before requesting its
                    # stationary updates. No simulation position enters the prior.
                    seed_deadline = min(deadline, time.monotonic() + 5.0)
                    updated = False
                    while rclpy.ok() and time.monotonic() < seed_deadline:
                        if not self._motion_inputs_ready():
                            return False, 'sensor or navigation change during AMCL handoff'
                        self._call_service(self._nomotion_update_client, Empty.Request(), 1.0)
                        with self._data_lock:
                            updated = self._pose_sequence > pose_epoch
                        if updated:
                            break
                        time.sleep(0.05)
                    if not updated:
                        return False, 'AMCL did not acknowledge the laser candidate'
                    self._stop_robot(10)
                    confirmed, detail = self._confirm_stationary_quality(move + 1, deadline)
                    with self._data_lock:
                        pose = self._latest_pose.pose.pose
                    q = pose.orientation
                    yaw = quaternion_to_yaw(q.x, q.y, q.z, q.w)
                    if (math.hypot(pose.position.x - chosen.x, pose.position.y - chosen.y) > 0.3
                            or abs(normalize_angle(yaw - chosen.yaw)) > 0.2):
                        return False, 'AMCL diverged from the selected laser candidate'
                    return confirmed, detail

            if move >= self._hypothesis_maximum_moves:
                break
            remaining_travel = self._hypothesis_maximum_travel - travel
            with self._data_lock:
                live_scan = self._latest_scan
            actions = []
            for heading in (0.0, math.pi / 4, -math.pi / 4,
                            math.pi / 2, -math.pi / 2, math.pi):
                clearance = self._sector_clearance(live_scan, heading - laser[2])
                for distance in (0.35, 0.65, 0.90):
                    if (distance <= remaining_travel
                            and clearance >= distance + self._translation_clearance):
                        actions.append((heading, distance))
            best_mean = max(means)
            competing = [h for h, mean in zip(candidates, means)
                         if mean >= best_mean - 0.18][:3]
            action = search.choose_action(competing, actions, laser)
            if action is None:
                return False, 'pose ambiguity remains; no safe informative action available'
            self._publish_status(
                'PLANNING_INFORMATION', 'selecting motion by predicted scan disagreement',
                heading=action.heading, distance=action.distance, gain=action.gain,
            )
            if not self._turn_for_information(action.heading, deadline):
                return False, 'informative turn timed out'
            if not self._translate_for_disambiguation(deadline, action.distance, 1.0):
                return False, 'informative translation blocked or incomplete'
            fresh, current_odom, points = self._hypothesis_snapshot(deadline, scan)
            delta = relative_motion(previous_odom, current_odom)
            travel += math.hypot(delta[0], delta[1])
            updated = []
            for h in candidates:
                predicted = Hypothesis(*advance_pose(h.pose, delta), h.score)
                refined = search.refine([predicted], points)
                updated.append(refined[0] if refined else Hypothesis(*predicted.pose, 0.0))
            candidates = updated
            totals = [old + h.score for old, h in zip(totals, candidates)]
            observations += 1
            scan, previous_odom = fresh, current_odom
        return False, 'pose ambiguity remains after bounded informative exploration'

    def _run_attempt(
        self,
        attempt: int,
        direction: float,
        global_deadline: float,
        initialize_globally: bool,
    ) -> tuple[bool, str]:
        if initialize_globally:
            self._publish_status(
                'INITIALIZING',
                'requesting AMCL global particle initialization',
                attempt=attempt,
            )
            response = self._call_service(
                self._global_init_client, Empty.Request(), self._service_timeout
            )
            if response is None:
                return False, 'AMCL global initialization service unavailable'

        with self._data_lock:
            previous_yaw = self._latest_odom_yaw
            quality_epoch = self._quality_sequence
            initial_pose_sequence = self._pose_sequence
        if previous_yaw is None:
            return False, 'odometry unavailable'

        self._publish_status(
            'SCANNING',
            f'attempt {attempt}/{self._attempts}',
            attempt=attempt,
            direction=direction,
        )
        period = 1.0 / self._control_frequency
        rotation = 0.0
        good_scans = 0
        last_quality_sequence = quality_epoch
        last_pose_sequence = initial_pose_sequence
        last_motion_time = time.monotonic()
        last_report_rotation = 0.0

        while rclpy.ok() and time.monotonic() < global_deadline:
            if not self._motion_inputs_ready():
                self._stop_robot(20)
                raise RuntimeError('Motion aborted: stale sensors or active navigation')
            command = Twist()
            command.angular.z = direction * self._angular_speed
            self._cmd_pub.publish(command)
            time.sleep(period)

            with self._data_lock:
                yaw = self._latest_odom_yaw
                quality = self._latest_quality
            if yaw is not None:
                delta = normalize_angle(yaw - previous_yaw)
                previous_yaw = yaw
                if abs(delta) > 1.0e-4:
                    rotation += abs(delta)
                    last_motion_time = time.monotonic()

            if time.monotonic() - last_motion_time > self._motion_stall_timeout:
                return False, 'rotation stalled; possible collision or paused simulation'

            if quality and quality.sequence > last_quality_sequence:
                last_quality_sequence = quality.sequence
                if quality.pose_sequence > last_pose_sequence:
                    last_pose_sequence = quality.pose_sequence
                    if (
                        rotation >= self._minimum_rotation
                        and self._quality_is_good(quality)
                    ):
                        good_scans += 1
                        if good_scans == 1:
                            self._publish_status(
                                'CONFIRMING',
                                'first acceptable AMCL update',
                                attempt=attempt,
                                required_good_scans=(
                                    self._required_good_scans
                                ),
                            )
                    else:
                        if good_scans:
                            self._publish_status(
                                'SCANNING',
                                'quality confirmation reset',
                                attempt=attempt,
                            )
                        good_scans = 0
                    if good_scans >= self._required_good_scans:
                        return True, (
                            f'converged after {rotation:.2f} rad; '
                            f'score={quality.scan_score:.3f}, '
                            f'variance=({quality.x_variance:.3f}, '
                            f'{quality.y_variance:.3f}, '
                            f'{quality.yaw_variance:.3f})'
                        )

            if rotation - last_report_rotation >= 0.5:
                last_report_rotation = rotation
                if quality:
                    report_state = (
                        'CONFIRMING' if good_scans else 'SCANNING'
                    )
                    self._publish_status(
                        report_state,
                        f'attempt {attempt}, rotation {rotation:.2f} rad',
                        attempt=attempt,
                        score=round(quality.scan_score, 3),
                        beams=quality.beams_used,
                        in_map=round(quality.in_map_fraction, 3),
                        covariance=[
                            round(quality.x_variance, 3),
                            round(quality.y_variance, 3),
                            round(quality.yaw_variance, 3),
                        ],
                        good_scans=good_scans,
                    )
            if rotation >= self._rotation_radians:
                return False, f'attempt {attempt} completed without convergence'

        return False, 'global relocalization wall-time limit reached'

    def _on_trigger(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        del request
        return self._execute_relocalization(response, trigger_source='manual')

    def _execute_relocalization(
        self,
        response: Trigger.Response,
        trigger_source: str,
    ) -> Trigger.Response:
        if not self._run_lock.acquire(blocking=False):
            response.success = False
            response.message = 'global relocalization is already running'
            return response

        self._begin_run_telemetry()
        final_state = 'FAILED'
        final_detail = 'global relocalization did not complete'
        try:
            ready, detail = self._ready()
            if not ready:
                response.success = False
                response.message = detail
                final_detail = detail
                return response

            self._publish_status(
                'PREPARING',
                'canceling navigation and stopping robot',
                trigger_source=trigger_source,
            )
            if not self._cancel_navigation():
                response.success = False
                response.message = 'Navigation cancellation could not be confirmed'
                final_detail = response.message
                return response
            deadline = time.monotonic() + self._maximum_wall_duration
            if self._active_hypotheses:
                success, detail = self._resolve_hypotheses(deadline)
                response.success, response.message = success, detail
                final_state = 'SUCCEEDED' if success else 'FAILED'
                final_detail = detail
                if success:
                    self._publish_status('CLEARING_COSTMAPS', 'clearing after laser candidate')
                    self._clear_costmaps()
                return response
            last_detail = 'no attempt executed'
            for attempt in range(1, self._attempts + 1):
                direction = 1.0 if attempt % 2 else -1.0
                if attempt > 1:
                    self._translate_for_disambiguation(deadline)
                success, last_detail = self._run_attempt(
                    attempt,
                    direction,
                    deadline,
                    initialize_globally=(attempt == 1),
                )
                self._publish_status(
                    'STOPPING_ATTEMPT',
                    f'stopping after attempt {attempt}',
                    attempt=attempt,
                    attempt_success=success,
                )
                self._stop_robot(20)
                if success:
                    verified, verification_detail = (
                        self._confirm_stationary_quality(attempt, deadline)
                    )
                    if not verified:
                        success = False
                        last_detail = verification_detail
                if success:
                    self._publish_status(
                        'CLEARING_COSTMAPS',
                        'clearing global and local costmaps',
                    )
                    self._clear_costmaps()
                    response.success = True
                    response.message = f'{last_detail}; {verification_detail}'
                    final_state = 'SUCCEEDED'
                    final_detail = response.message
                    return response
                if time.monotonic() >= deadline:
                    break

            response.success = False
            response.message = last_detail
            final_detail = last_detail
            return response
        except Exception as error:  # Always stop the physical command path.
            self.get_logger().error(f'Global relocalization failed: {error}')
            response.success = False
            response.message = str(error)
            final_detail = str(error)
            return response
        finally:
            self._publish_status(
                'FINAL_STOPPING',
                'publishing final zero-velocity commands',
            )
            self._stop_robot(20)
            self._publish_status(final_state, final_detail)
            with self._data_lock:
                self._last_relocalization_end_wall = time.monotonic()
                self._reset_mismatch_detectors()
            self._run_lock.release()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = ActiveGlobalRelocalization()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node._stop_robot(20)
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
