#!/usr/bin/env python3
"""Active, safety-oriented global relocalization for Nav2 AMCL."""

from dataclasses import dataclass
import json
import math
import threading
import time

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

from wpr_relocalization.relocalization_core import (
    ConsecutiveMismatchDetector,
    LikelihoodField,
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
        self._last_relocalization_end_wall = 0.0

        status_qos = QoSProfile(depth=1)
        status_qos.reliability = ReliabilityPolicy.RELIABLE
        status_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
        map_qos = QoSProfile(depth=1)
        map_qos.reliability = ReliabilityPolicy.RELIABLE
        map_qos.durability = DurabilityPolicy.TRANSIENT_LOCAL

        self._cmd_pub = self.create_publisher(
            Twist, self._string('cmd_vel_topic'), 10
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
        self._cancel_client = self.create_client(
            CancelGoal,
            '/navigate_to_pose/_action/cancel_goal',
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
        with self._data_lock:
            self._latest_odom_yaw = yaw
            self._latest_odom_position = (
                message.pose.pose.position.x,
                message.pose.pose.position.y,
            )
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

    def _cancel_navigation(self) -> None:
        response = self._call_service(
            self._cancel_client, CancelGoal.Request(), self._service_timeout
        )
        if response is None:
            self.get_logger().warning(
                'NavigateToPose cancel service unavailable; continuing after stop command'
            )
        self._stop_robot(10)

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
            if time.monotonic() - self._latest_scan_wall_time > 5.0:
                missing.append('/scan')
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
            cooling_down = (
                now - self._last_relocalization_end_wall
                < self._automatic_trigger_cooldown
            )
            if self._automatic_trigger_pending or cooling_down:
                self._reset_mismatch_detectors()
                return
            hard_mismatch = self._mismatch_detector.update(
                quality.scan_score,
                quality.beams_used,
                quality.in_map_fraction,
                quality.x_variance,
                quality.y_variance,
                quality.yaw_variance,
            )
            suspect_mismatch = self._suspect_mismatch_detector.update(
                quality.scan_score,
                quality.beams_used,
            )
            if not hard_mismatch and not suspect_mismatch:
                return
            trigger_reason = (
                'persistent hard mismatch'
                if hard_mismatch
                else 'windowed moderate mismatch'
            )
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
            log = self.get_logger().info if response.success else self.get_logger().error
            log(f'Automatic relocalization result: {response.message}')
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
        samples = []
        for index, measured_range in enumerate(scan.ranges):
            angle = scan.angle_min + index * scan.angle_increment
            if abs(normalize_angle(angle - center)) > self._translation_sector_half_angle:
                continue
            if math.isinf(measured_range) and measured_range > 0.0:
                samples.append(min(scan.range_max, self._score_maximum_range))
            elif math.isfinite(measured_range) and measured_range >= scan.range_min:
                samples.append(float(measured_range))
        if not samples:
            return 0.0
        samples.sort()
        percentile_index = min(len(samples) - 1, int(0.20 * len(samples)))
        return samples[percentile_index]

    def _translate_for_disambiguation(self, global_deadline: float) -> bool:
        if self._translation_distance <= 0.0:
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
        required = self._translation_distance + self._translation_clearance
        if max(front, rear) < required:
            self._publish_status(
                'TRANSLATION_SKIPPED',
                'insufficient local clearance',
                front=round(front, 2),
                rear=round(rear, 2),
                required=round(required, 2),
            )
            return False

        direction = 1.0 if front >= rear else -1.0
        self._publish_status(
            'TRANSLATING',
            'breaking symmetric localization hypotheses',
            direction='forward' if direction > 0.0 else 'backward',
            distance=self._translation_distance,
            front_clearance=round(front, 2),
            rear_clearance=round(rear, 2),
        )
        period = 1.0 / self._control_frequency
        last_motion_time = time.monotonic()
        previous_distance = 0.0
        while rclpy.ok() and time.monotonic() < global_deadline:
            with self._data_lock:
                position = self._latest_odom_position
                current_scan = self._latest_scan
            if position is None or current_scan is None:
                self._stop_robot(10)
                return False
            distance = math.hypot(position[0] - start[0], position[1] - start[1])
            if distance >= self._translation_distance:
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
            self._cancel_navigation()
            deadline = time.monotonic() + self._maximum_wall_duration
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
