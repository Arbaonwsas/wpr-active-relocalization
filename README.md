# WPR ROS 2 主动全局重定位

基于 WPR 机器人仿真与 Nav2 AMCL，在机器人被搬动、定位失效后自动尝试恢复全局位姿。重定位使用单线二维激光、已知栅格地图和轮式里程计，不要求增加传感器。支持普通 AMCL 主动扫描恢复，以及实验性的多候选搜索与主动移动消歧。

本项目基于 **6-robot/wpr_simulation2** 二次开发，保留原有机器人模型、导航、SLAM 和教学示例。上游课程与使用说明见 [原项目介绍](docs/upstream_usage.md)，来源与许可证见 [NOTICE](NOTICE.md)。

## 环境

- Ubuntu 22.04 / ROS 2 Humble
- Gazebo Classic 11 / Nav2 / Python 3 / NumPy
- 已验证本仓库自带的室内地图；尚未完成实机、大地图及动态人群验证。

## 安装与编译

将本仓库克隆或解压到 `~/ros2_ws/src/wpr_simulation2`。包名保持为 `wpr_simulation2`，不要与上游包重复放在同一工作空间。

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws/src/wpr_simulation2/scripts
bash install_for_humble.sh
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select wpr_simulation2
source install/setup.bash
```

依赖安装脚本会使用 sudo 安装软件，并复制 Gazebo 资源到 `~/.gazebo`。`rosdep` 首次使用前需完成系统级初始化与 `rosdep update`。

## 启动与体验

普通恢复模式（默认配置，包含仿真专用真值验收）：

```bash
ros2 launch wpr_simulation2 navigation.launch.py
```

多候选主动消歧模式（本轮人工验收使用的模式）：

```bash
ros2 launch wpr_simulation2 navigation.launch.py \
  active_hypothesis_relocalization:=true \
  automatic_relocalization:=true \
  simulation_odom_validation:=false
```

两条命令任选其一，启动 Gazebo、Nav2、RViz 和唯一一个重定位节点。请勿在现有仿真旁重复启动。

1. 等待地图、激光与导航就绪，确认机器人附近无碰撞。
2. 在 Gazebo 暂停物理，将 `wpb_home` 移到地图内其他空闲位置，再恢复物理。
3. 算法自动取消导航并尝试恢复；有歧义时可能短距离移动，无法确定时停车并返回失败。
4. 每轮结束等待至少 8 秒再进行下一次搬动。不要用 RViz 的 `2D Pose Estimate` 提供答案。

也可以手动调用服务并查看状态：

```bash
ros2 service call /global_relocalization std_srvs/srv/Trigger '{}'
ros2 topic echo /global_relocalization/status
ros2 topic echo /global_relocalization/quality
```

自动恢复失败会锁存，避免无限旋转；手动服务仍可重试。新一次搬动造成的里程计突跳也会解除锁存。恢复会取消当前导航任务；恢复后需重新发送导航目标。

## 算法与边界

普通模式重新散布 AMCL 粒子，主动旋转扫描，必要时短距离平移，再进行连续质量与静止复核。实验模式从激光与地图生成多个全局位姿候选，利用相对移动后的扫描持续评分，选择能增加候选区分度的安全动作，最终交给 AMCL 复核。

恢复保留传感器断流停车、底盘扫掠净空检查、导航取消确认和有限探索预算。默认圆形底盘半径为 0.22 m；适配其他机器人时必须同步调整地图与运动参数，并处理其他速度发布者的仲裁。

**仿真拖动会让原始 `/odom` 和 TF 同时跳变。** 默认 `simulation_odom_validation=true` 使用该信息拒绝错误解，只适用于本仿真。关闭它也不等于隔离了真值 TF；严格实验需使用 [隔离里程计与 TF 的复现夹具](benchmark_results/active_hypothesis_experiment/reproduce/README.md)。夹具模拟理想连续里程计，尚未覆盖真实噪声与滑移。

完全对称、且所有安全可达区域也对称的环境无法只靠现有激光与相对里程计唯一定位。分数差是工程判据，不是正确定位保证。实验模式默认关闭，当前证据不足以证明其总体优于普通模式。

详细流程、参数与接口见 [重定位说明](docs/relocalization.md)。

## 验证结果

隔离真值 TF、同一相似房间起点，各测试三次：

| 模式 | 正确恢复 | 平均服务时间 | 最大位置误差 |
|---|---:|---:|---:|
| 普通 AMCL 主动恢复 | 3/3 | 4.43 s | 6.34 cm |
| 多候选主动消歧 | 3/3 | 11.74 s | 5.60 cm |

新模式每次主动移动一次。样本较少，该起点用于调试且未固定共同随机种子，不能据此推断普遍成功率。早期版本的失败样本也保留在 [实验报告与原始数据](benchmark_results/active_hypothesis_experiment/README.md)。历史计时结果见 [优化记录](docs/relocalization_time_optimization.md)，不要将不同版本和实验条件混算。

相关四个单元测试套件共 61 项通过。复测：

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws/src/wpr_simulation2
PYTHONPATH="$PWD:$PYTHONPATH" python3 -m pytest -q \
  test/test_relocalization_core.py test/test_relocalization_benchmark.py \
  test/test_relocalization_safety.py test/test_active_hypotheses.py
```

单元测试不需要启动 Gazebo。专用仿真中的批量基准会主动搬动机器人：

```bash
python3 scripts/benchmark_global_relocalization.py \
  --repetitions 3 --output-dir /tmp/relocalization_benchmark
```

## 目录

- `src/active_global_relocalization.py`：ROS 节点、恢复与自动检测流程。
- `wpr_relocalization/`：扫描评分、运动保护与多候选算法。
- `config/nav2_params.yaml`：导航与恢复参数。
- `test/`：算法、保护和基准脚本测试。
- `benchmark_results/`：历史实验、原始记录和隔离复现夹具。
- `docs/`：详细说明及上游使用方式。

贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。
