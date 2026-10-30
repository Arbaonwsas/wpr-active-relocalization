"""Publish only the jump-free odometry transform on the isolated AMCL bus."""
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
rclpy.init()
n=Node('isolated_odometry_tf_fixture')
pub=n.create_publisher(TFMessage,'/hypothesis_tf',100)


def relay(message):
    tf=TransformStamped()
    tf.header=message.header
    tf.child_frame_id=message.child_frame_id
    p=message.pose.pose.position
    tf.transform.translation.x=p.x
    tf.transform.translation.y=p.y
    tf.transform.translation.z=p.z
    tf.transform.rotation=message.pose.pose.orientation
    pub.publish(TFMessage(transforms=[tf]))


n.create_subscription(Odometry,'/continuous_odom',relay,10)
try:
    rclpy.spin(n)
finally:
    n.destroy_node()
    rclpy.shutdown()
