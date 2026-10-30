"""Test fixture: hide Gazebo teleport jumps from the recovery algorithm."""
import copy
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from wpr_relocalization.active_hypotheses import advance_pose, relative_motion
from wpr_relocalization.relocalization_core import quaternion_to_yaw

rclpy.init()
node = Node('continuous_odometry_test_fixture')
pub = node.create_publisher(Odometry, '/continuous_odom', 10)
previous = None
continuous = (0.0, 0.0, 0.0)


def callback(message):
    global previous, continuous
    p = message.pose.pose.position
    q = message.pose.pose.orientation
    raw = (p.x, p.y, quaternion_to_yaw(q.x, q.y, q.z, q.w))
    if previous is not None:
        delta = relative_motion(previous, raw)
        if math.hypot(delta[0], delta[1]) > 0.3 or abs(delta[2]) > 0.4:
            print('Removed teleport jump:', delta, flush=True)
        else:
            continuous = advance_pose(continuous, delta)
    previous = raw
    adjusted = copy.deepcopy(message)
    adjusted.header.frame_id = 'continuous_odom'
    adjusted.pose.pose.position.x, adjusted.pose.pose.position.y = continuous[:2]
    adjusted.pose.pose.orientation.z = math.sin(continuous[2] / 2)
    adjusted.pose.pose.orientation.w = math.cos(continuous[2] / 2)
    pub.publish(adjusted)


node.create_subscription(Odometry, '/odom', callback, qos_profile_sensor_data)
try:
    rclpy.spin(node)
finally:
    node.destroy_node()
    rclpy.shutdown()
