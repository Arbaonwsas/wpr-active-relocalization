"""Exercise the node's motion guards without starting ROS or a robot."""

import importlib.util
import math
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

from action_msgs.msg import GoalStatus
from action_msgs.srv import CancelGoal
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / 'src' / 'active_global_relocalization.py'
SPEC = importlib.util.spec_from_file_location('relocalization_safety_node', SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
NODE = MODULE.ActiveGlobalRelocalization


def make_node():
    node = NODE.__new__(NODE)
    node._data_lock = threading.RLock()
    node._navigation_status = {}
    node._active_hypotheses = False
    node._laser_transform = (0.0, 0.0, 0.0)
    node._translation_sector_half_angle = 0.52
    node._translation_robot_radius = 0.22
    node._score_maximum_range = 8.0
    node._sensor_timeout = 0.5
    node._latest_scan = object()
    node._latest_odom_position = (0.0, 0.0)
    node._latest_scan_wall_time = time.monotonic()
    node._latest_odom_wall_time = time.monotonic()
    node._control_frequency = 20.0
    node._service_timeout = 0.2
    node._cmd_pub = Mock()
    node._stop_robot = Mock()
    return node


def scan(ranges, angle_min=-0.5, angle_increment=0.01):
    return SimpleNamespace(
        ranges=ranges, angle_min=angle_min, angle_increment=angle_increment,
        range_min=0.1, range_max=10.0,
    )


def test_thin_obstacle_in_front_is_not_discarded():
    node = make_node()
    ranges = [5.0] * 101
    ranges[50] = 0.25
    assert node._sector_clearance(scan(ranges), 0.0) == pytest.approx(0.03)


def test_obstacle_outside_sector_but_inside_footprint_blocks_motion():
    node = make_node()
    # 0.2 m forward, 0.2 m to the side: outside the 30 degree sector.
    ranges = [math.inf] * 101 + [math.hypot(0.2, 0.2)]
    message = scan(ranges, angle_min=-math.pi / 4, angle_increment=math.pi / 404)
    # Last endpoint is at pi/4; the sector itself contains free observations.
    message.angle_increment = (math.pi / 2) / 101
    assert node._sector_clearance(message, 0.0) < 0.2


def test_offset_and_rotated_laser_uses_base_footprint():
    node = make_node()
    node._laser_transform = (0.1, 0.0, math.pi)
    message = scan([0.3], angle_min=math.pi, angle_increment=0.0)
    assert node._sector_clearance(message, -math.pi) == pytest.approx(0.18)


def test_rear_obstacle_blocks_reverse_motion():
    node = make_node()
    message = scan([0.25], angle_min=math.pi, angle_increment=0.0)
    assert node._sector_clearance(message, math.pi) == pytest.approx(0.03)


@pytest.mark.parametrize('ranges', [[], [math.nan], [0.01], [-math.inf]])
def test_unknown_forward_clearance_is_blocked(ranges):
    node = make_node()
    assert node._sector_clearance(scan(ranges, 0.0, 0.0), 0.0) == 0.0


@pytest.mark.parametrize('sensor', ['scan', 'odom'])
def test_stale_sensor_prevents_motion(sensor):
    node = make_node()
    setattr(node, f'_latest_{sensor}_wall_time', time.monotonic() - 1.0)
    assert not node._motion_inputs_ready()


def test_new_navigation_goal_prevents_recovery_motion():
    node = make_node()
    assert node._motion_inputs_ready()
    node._navigation_status['navigate_through_poses'] = {b'goal': GoalStatus.STATUS_EXECUTING}
    assert not node._motion_inputs_ready()


@pytest.mark.parametrize('response', [None, CancelGoal.Response(return_code=1)])
def test_cancel_failure_is_not_treated_as_success(response):
    node = make_node()
    node._cancel_clients = {'navigate_to_pose': object()}
    node._call_service = Mock(return_value=response)
    node.get_logger = Mock(return_value=Mock())
    assert not node._cancel_navigation()
    node._stop_robot.assert_called_once()


def test_cancel_waits_for_terminal_status(monkeypatch):
    node = make_node()
    goal = MODULE.CancelGoal.Request().goal_info
    goal.goal_id.uuid = list(range(16))
    goal_id = bytes(goal.goal_id.uuid)
    node._navigation_status['navigate_to_pose'] = {goal_id: GoalStatus.STATUS_CANCELING}
    node._cancel_clients = {'navigate_to_pose': object()}
    node._call_service = Mock(return_value=CancelGoal.Response(goals_canceling=[goal]))
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)
    observed = []

    def finish(_):
        observed.append(True)
        node._navigation_status['navigate_to_pose'][goal_id] = GoalStatus.STATUS_CANCELED

    monkeypatch.setattr(MODULE.time, 'sleep', finish)
    assert node._cancel_navigation()
    assert observed
    node._cmd_pub.publish.assert_called_once()


def test_canceling_goal_timeout_fails(monkeypatch):
    node = make_node()
    goal = MODULE.CancelGoal.Request().goal_info
    node._cancel_clients = {'navigate_to_pose': object()}
    node._call_service = Mock(return_value=CancelGoal.Response(goals_canceling=[goal]))
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)
    times = iter([0.0, 0.0, 1.0])
    monkeypatch.setattr(MODULE.time, 'monotonic', lambda: next(times))
    monkeypatch.setattr(MODULE.time, 'sleep', lambda _: None)
    assert not node._cancel_navigation()


@pytest.mark.parametrize('stage', ['rotation', 'translation'])
def test_stale_scan_stops_before_nonzero_command(stage, monkeypatch):
    node = make_node()
    node._latest_scan_wall_time -= 1.0
    node._latest_odom_yaw = 0.0
    node._quality_sequence = 0
    node._pose_sequence = 0
    node._attempts = 2
    node._translation_distance = 0.55
    node._translation_clearance = 0.45
    node._latest_scan = scan([math.inf] * 629, -math.pi, 0.01)
    node._publish_status = Mock()
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)
    with pytest.raises(RuntimeError, match='stale sensors'):
        if stage == 'rotation':
            node._run_attempt(1, 1.0, time.monotonic() + 1, False)
        else:
            node._translate_for_disambiguation(time.monotonic() + 1)
    node._stop_robot.assert_called_once()
    node._cmd_pub.publish.assert_not_called()


def test_both_navigation_actions_are_canceled(monkeypatch):
    node = make_node()
    node._cancel_clients = {
        'navigate_to_pose': object(), 'navigate_through_poses': object(),
    }
    node._call_service = Mock(return_value=CancelGoal.Response())
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)
    assert node._cancel_navigation()
    assert node._call_service.call_count == 2


def test_cancel_failure_exits_before_global_initialization():
    node = make_node()
    node._run_lock = threading.Lock()
    node._begin_run_telemetry = Mock()
    node._ready = Mock(return_value=(True, 'ready'))
    node._publish_status = Mock()
    node._cancel_navigation = Mock(return_value=False)
    node._run_attempt = Mock()
    node._reset_mismatch_detectors = Mock()
    response = MODULE.Trigger.Response()
    result = node._execute_relocalization(response, 'manual')
    assert not result.success
    node._run_attempt.assert_not_called()
    node._stop_robot.assert_called_once()
    assert not node._run_lock.locked()


@pytest.mark.parametrize('stage', ['rotation', 'translation'])
def test_sensor_loss_during_motion_stops_next_command(stage, monkeypatch):
    node = make_node()
    node._latest_odom_yaw = 0.0
    node._quality_sequence = 0
    node._pose_sequence = 0
    node._latest_quality = None
    node._attempts = 2
    node._angular_speed = 1.5
    node._minimum_rotation = 1.2
    node._motion_stall_timeout = 15.0
    node._rotation_radians = 7.6
    node._translation_distance = 0.55
    node._translation_clearance = 0.45
    node._translation_speed = 0.24
    node._latest_scan = scan([math.inf] * 629, -math.pi, 0.01)
    node._publish_status = Mock()
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)

    def disconnect(_):
        node._latest_scan_wall_time = time.monotonic() - 1.0

    monkeypatch.setattr(MODULE.time, 'sleep', disconnect)
    with pytest.raises(RuntimeError, match='stale sensors'):
        if stage == 'rotation':
            node._run_attempt(1, 1.0, time.monotonic() + 1, False)
        else:
            node._translate_for_disambiguation(time.monotonic() + 1)
    # One command before disconnect; the next command is prevented.
    node._cmd_pub.publish.assert_called_once()
    node._stop_robot.assert_called_once()


def test_unresolved_hypotheses_never_seed_amcl_or_move():
    node = make_node()
    h = MODULE.Hypothesis
    node._hypothesis_search = Mock()
    node._hypothesis_search.global_candidates.return_value = [
        h(1, 2, 0, 0.95), h(9, 8, 3.14, 0.95),
    ]
    node._hypothesis_search.choose_action.return_value = None
    node._hypothesis_snapshot = Mock(return_value=(object(), (0, 0, 0), object()))
    node._hypothesis_maximum_moves = 3
    node._hypothesis_maximum_travel = 1.8
    node._hypothesis_score_margin = 0.15
    node._translation_clearance = 0.45
    node._sector_clearance = Mock(return_value=2.0)
    node._publish_status = Mock()
    node._initial_pose_pub = Mock()
    node._turn_for_information = Mock()
    result, detail = node._resolve_hypotheses(time.monotonic() + 10)
    assert not result and 'ambiguity remains' in detail
    node._initial_pose_pub.publish.assert_not_called()
    node._turn_for_information.assert_not_called()


def test_amcl_prior_comes_from_laser_candidate_not_odometry(monkeypatch):
    node = make_node()
    h = MODULE.Hypothesis
    candidates = [h(1, 2, 0.5, 0.98), h(9, 8, -2.64, 0.7)]
    node._hypothesis_search = Mock()
    node._hypothesis_search.global_candidates.return_value = candidates
    node._hypothesis_search.refine.side_effect = lambda hs, *args: hs
    # Arbitrary unrelated odometry origin must not enter the initialpose prior.
    node._hypothesis_snapshot = Mock(return_value=(object(), (1000, 2000, 1), object()))
    node._hypothesis_maximum_moves = 3
    node._hypothesis_maximum_travel = 1.8
    node._hypothesis_score_margin = 0.15
    node._publish_status = Mock()
    node._initial_pose_pub = Mock()
    node.get_clock = Mock(return_value=Mock())
    node.get_clock().now().to_msg.return_value = MODULE.Time().to_msg()
    node._pose_sequence = 0
    node._motion_inputs_ready = Mock(return_value=True)
    node._confirm_stationary_quality = Mock(return_value=(True, 'confirmed'))
    node._latest_pose = MODULE.PoseWithCovarianceStamped()
    pose = node._latest_pose.pose.pose
    pose.position.x, pose.position.y = 1.0, 2.0
    pose.orientation.z = math.sin(0.25)
    pose.orientation.w = math.cos(0.25)

    def update(*args):
        node._pose_sequence += 1
        return object()

    node._call_service = update
    node._nomotion_update_client = object()
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)
    assert node._resolve_hypotheses(time.monotonic() + 10)[0]
    prior = node._initial_pose_pub.publish.call_args.args[0]
    assert prior.pose.pose.position.x == 1.0
    assert prior.pose.pose.position.y == 2.0


def test_stale_sensors_prevent_informative_turn(monkeypatch):
    node = make_node()
    node._latest_odom_yaw = 0.0
    node._latest_scan_wall_time -= 1.0
    node._publish_status = Mock()
    monkeypatch.setattr(MODULE.rclpy, 'ok', lambda: True)
    with pytest.raises(RuntimeError, match='stale sensors'):
        node._turn_for_information(1.0, time.monotonic() + 10)
    node._cmd_pub.publish.assert_not_called()
