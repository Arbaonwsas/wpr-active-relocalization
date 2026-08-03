# WPR系列机器人ROS2仿真工具

## 介绍课程
Bilibili: [机器人操作系统 ROS2 入门教材](https://www.bilibili.com/video/BV1oz421v7tB)  
Youtube: [机器人操作系统 ROS2 入门教材](https://www.youtube.com/watch?v=j0foOvBqQTc)

## 配套教材书籍
《机器人操作系统（ROS2）入门与实践》  
![视频课程](./media/book_1.jpg)
淘宝链接：[《机器人操作系统（ROS2）入门与实践》](https://world.taobao.com/item/820988259242.htm)

## 系统版本

- ROS2 Humble (Ubuntu 22.04)

## 使用说明

### 一、 启智ROS机器人
1. 获取源码:
```
cd ~/ros2_ws/src/
git clone https://github.com/6-robot/wpr_simulation2.git
```
2. 安装依赖项:  
ROS2 Humble (Ubuntu 22.04)
```
cd ~/ros2_ws/src/wpr_simulation2/scripts
./install_for_humble.sh
```
3. 编译
```
cd ~/ros2_ws
colcon build --symlink-install
```

简单场景:
```
ros2 launch wpr_simulation2 wpb_simple.launch.py 
```
![wpb_simple pic](./media/wpb_simple.png)

SLAM环境地图创建:
```
ros2 launch wpr_simulation2 slam.launch.py 
ros2 run rqt_robot_steering rqt_robot_steering 
```
![wpb_gmapping pic](./media/wpb_gmapping.png)

Navigation导航:
```
ros2 launch wpr_simulation2 navigation.launch.py 
```
![wpb_navigation pic](./media/wpb_navigation.png)

### 主动全局重定位

导航启动后，调用以下服务可执行完整的主动全局重定位：

```
ros2 service call /global_relocalization std_srvs/srv/Trigger "{}"
```

该过程会取消正在执行的导航目标、停止底盘、重新全局散布 AMCL
粒子并原地旋转扫描。若旋转后仍存在对称定位假设，系统会依据实时激光
净空选择安全方向短距离平移，再反向扫描。只有多个不同 AMCL 更新的
协方差和激光—地图一致性评分连续通过阈值时才返回成功；失败时机器人
会停车，不会在错误定位上继续导航。

可用下面两个话题监控过程：

```
ros2 topic echo /global_relocalization/status
ros2 topic echo /global_relocalization/quality
```

注意：本仿真模型使用 `libgazebo_ros_planar_move.so`，在 Gazebo 中直接
拖动模型会使 `/odom` 同时跳变，因此不属于严格的绑架机器人测试。

### 全局重定位基准测试

2026-08-03 的首轮三位置基准测试全部恢复成功，平均墙钟恢复时长为
186.49 秒。详细时长、真实位姿误差、原始状态日志和复测方法见
[基准测试记录](benchmark_results/2026-08-03_baseline/README.md)。

需要进行重复计时实验时，可在导航和 Gazebo 已启动后执行：

```
python3 scripts/benchmark_global_relocalization.py \
  --repetitions 10 \
  --output-dir benchmark_results/relocalization_repeat_10
```

可重复使用 `--location top_left_room`、`--location map_center` 或
`--location bottom_right_area` 只选择部分位置。每次运行会生成：

- `results.csv`：每次实验的总时间、各阶段累计时间、误差和成功状态；
- `phase_timings.csv`：每次尝试中初始化、扫描、确认、平移、停车和清图的
  起止墙钟/仿真时间；
- `README.md`：分位置成功率、P50、P95、最大恢复时间、阶段耗时占比和实验
夹具开销；
- `status_*.log`：带 `run_id` 和事件序号的原始状态事件，避免混入上一次
  瞬态持久消息。

算法阶段时间和暂停、传送、恢复 Gazebo、采集结果等实验夹具时间分开统计，
因此后续优化时不会把测试脚本本身的等待误认为重定位耗时。

当前正式 10 Hz 三位置三十次测试成功率为 `30/30`，平均服务墙钟时间 `4.94 s`、
P50 `4.36 s`、P95 `7.73 s`。停车后新增两次 AMCL 静止质量复核；仿真激光提高到
20 Hz 后，三位置九次初步对照仍为 `9/9`，节点内部平均恢复由 `4.68 s` 降至
`3.65 s`。完整参数 A/B、硬件利用率和下一阶段方向见
[重定位时间优化记录](docs/relocalization_time_optimization.md)。
