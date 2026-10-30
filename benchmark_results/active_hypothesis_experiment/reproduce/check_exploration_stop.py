"""Interrupt information-seeking motion by stopping the real simulator streams."""
import json
from pathlib import Path
import subprocess
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from std_srvs.srv import Empty, Trigger

rclpy.init()
n=Node('hypothesis_exploration_stop_test')
events=[]
commands=[]
odom=[]
qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
n.create_subscription(String,'/global_relocalization/status',lambda m:events.append(json.loads(m.data)),qos)
n.create_subscription(Twist,'/cmd_vel_nav',lambda m:commands.append((time.monotonic(),m.linear.x,m.angular.z)),10)
n.create_subscription(Odometry,'/odom',lambda m:odom.append(m),qos_profile_sensor_data)
pause=n.create_client(Empty,'/pause_physics')
unpause=n.create_client(Empty,'/unpause_physics')
trigger=n.create_client(Trigger,'/global_relocalization')
stop=n.create_publisher(Twist,'/cmd_vel_nav',10)


def until(condition,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        rclpy.spin_once(n,timeout_sec=.02)
        if condition(): return
    raise TimeoutError('test condition timeout')


def call(client,request):
    assert client.wait_for_service(timeout_sec=10)
    f=client.call_async(request)
    until(f.done,10)
    return f.result()


report={}
try:
    until(lambda:odom)
    call(pause,Empty.Request())
    subprocess.run(['gz','model','-m','wpb_home','-x','-3.5','-y','1.93','-z','0','-R','0','-P','0','-Y','-2.52'],check=True,capture_output=True,timeout=10)
    call(unpause,Empty.Request())
    epoch=len(odom)
    until(lambda:len(odom)>epoch+10)
    start=len(events)
    future=trigger.call_async(Trigger.Request())
    until(lambda:any(e['state']=='TURNING_FOR_INFORMATION' for e in events[start:]))
    call(pause,Empty.Request())
    paused=time.monotonic()
    until(future.done,8)
    result=future.result()
    late=[v for v in commands if v[0]>=paused+.6]
    report={'success':result.success,'message':result.message,'pause_to_response_sec':time.monotonic()-paused,'late_nonzero_commands':sum(abs(x)+abs(w)>1e-9 for _,x,w in late),'late_command_count':len(late)}
    assert not result.success and 'stale sensors' in result.message
    assert late and report['late_nonzero_commands']==0
    call(unpause,Empty.Request())
    for _ in range(12):
        stop.publish(Twist());rclpy.spin_once(n,timeout_sec=.05)
    v=odom[-1].twist.twist
    report['final_speed_norm']=max(abs(v.linear.x),abs(v.linear.y),abs(v.angular.z))
    assert report['final_speed_norm']<=.01
    report['passed']=True
finally:
    try: call(unpause,Empty.Request())
    except Exception: pass
    for _ in range(10):
        stop.publish(Twist());rclpy.spin_once(n,timeout_sec=.05)
    Path('outputs/active_hypothesis_isolated_revised/exploration_stop.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
    n.destroy_node();rclpy.shutdown()
