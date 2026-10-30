# 隔离实验复现

这些夹具仅用于专用 Gazebo 仿真。先启动项目原有地图、Gazebo 与 Nav2；停止原有重定位节点，避免多个节点同时发布恢复速度。每个新终端先执行：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
cd ~/ros2_ws/src/wpr_simulation2/benchmark_results/active_hypothesis_experiment/reproduce
```

分别在两个终端运行 `python3 continuous_odometry.py` 与 `python3 isolated_tf.py`。前者去除单帧大于 0.3 m 或 0.4 rad 的跳变，是理想连续里程计夹具，不是实机检测算法。然后启动隔离 AMCL：

```bash
ros2 run nav2_amcl amcl --ros-args -r __node:=amcl_isolated \
  --params-file isolated_amcl.yaml \
  -r /tf:=/hypothesis_tf \
  -r /amcl_pose:=/isolated_amcl_pose \
  -r /initialpose:=/isolated_initialpose \
  -r /request_nomotion_update:=/isolated/request_nomotion_update \
  -r /reinitialize_global_localization:=/isolated/reinitialize_global_localization
```

另一个终端配置、激活后启动恢复节点：

```bash
ros2 lifecycle set /amcl_isolated configure
ros2 lifecycle set /amcl_isolated activate
ros2 run wpr_simulation2 active_global_relocalization.py --ros-args \
  --params-file "$(ros2 pkg prefix --share wpr_simulation2)/config/nav2_params.yaml" \
  -p active_hypothesis_relocalization:=true \
  -p simulation_odom_validation:=false \
  -p automatic_relocalization:=false \
  -p odom_topic:=/continuous_odom \
  -p amcl_pose_topic:=/isolated_amcl_pose \
  -r /initialpose:=/isolated_initialpose \
  -r /request_nomotion_update:=/isolated/request_nomotion_update \
  -r /reinitialize_global_localization:=/isolated/reinitialize_global_localization
```

运行同点三次基准：

```bash
python3 benchmark_isolated.py --repetitions 3 --output-dir /tmp/relocalization_isolated_repeat
```

旧流程对照将恢复节点参数 `active_hypothesis_relocalization` 改为 `false`，其他隔离配置相同，使用另一个输出目录。基准会搬动机器人并调用恢复服务；原始 odom 仅用于外部评分。AMCL 未固定随机种子，因此重复结果不保证与本报告完全一致。

测试结束停止隔离恢复节点、AMCL 和两个夹具，再恢复原项目自动恢复节点。不要在现有运行节点旁直接启动第二个恢复节点。
