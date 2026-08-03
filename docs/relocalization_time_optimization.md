# 全局重定位时间优化

## 基线

2026-08-03 的三位置基准全部恢复成功，但墙钟恢复时间为
95.243～250.910 秒，平均 186.49 秒。完整原始数据见
[`benchmark_results/2026-08-03_baseline`](../benchmark_results/2026-08-03_baseline/README.md)。

## Agent Reach 调研结果

本次使用 Agent Reach 的 Exa 技术搜索和 GitHub 信息检索，重点比较了以下方案：

| 方案 | 证据 | 与本项目的关系 |
|---|---|---|
| [Nav2 AMCL](https://docs.nav2.org/configuration/packages/configuring-amcl.html) | ROS 2/Nav2 官方成熟实现；支持 KLD 采样、全局粒子初始化和随机粒子恢复 | 当前方案的稳定基础，保留作为最终跟踪器 |
| [MH-AMCL](https://github.com/fmrico/mh_amcl) | ROS 2/Nav2 多假设实现；论文报告平均恢复 6.501 秒、成功率 100%，对照 AMCL 为 13.714 秒、26.67% | 候选生成、多假设保留和基于扫描一致性的质量判定值得借鉴；仓库最近主要更新在 2023 年 |
| [CBGL](https://github.com/cbgl/cbgl) | IROS 2024 单扫描全局定位；真实数据平均 1.61 秒，99.1% 的结果位置误差小于 0.5 m | 很适合作为 AMCL 前置候选位姿生成器，但公开 ROS 包仍基于 ROS 1 Kinetic，需要移植 |
| [Cartographer FastCorrelativeScanMatcher2D](https://github.com/cartographer-project/cartographer/blob/master/cartographer/mapping/internal/2d/scan_matching/fast_correlative_scan_matcher_2d.h) | 成熟的多分辨率分支限界扫描匹配，提供全子图搜索 | 可作为后续粗到细全图候选搜索的算法基础，集成成本高于本轮接线修复 |
| [Beluga AMCL](https://github.com/Ekumen-OS/beluga) | 活跃、测试充分、接口兼容 Nav2 AMCL；公开基准显示精度和 CPU 与 Nav2 AMCL 相近 | 是现代化替代实现，但没有证据表明仅替换它就能显著缩短全局恢复时间 |

`recovery_alpha_fast=0.1` 和 `recovery_alpha_slow=0.001` 已经在本项目中启用。
它们适用于定位退化后的随机粒子注入，但不会消除显式全局均匀初始化的搜索成本。

## 本地根因与标定

重定位节点此前与 `velocity_smoother` 同时向 `/cmd_vel` 发布：

- 重定位节点以 20 Hz 请求 `0.35 rad/s`；
- `velocity_smoother` 也以 20 Hz 向 `/cmd_vel` 输出；
- Gazebo `base_controller` 是该话题唯一订阅者，因此该接法存在命令竞争风险。

Nav2 的标准数据路径是：

```text
motion producer -> /cmd_vel_nav -> velocity_smoother -> /cmd_vel -> base_controller
```

第一阶段因此把主动重定位输出改为 `/cmd_vel_nav`。导航目标会在重定位开始时先被
取消，平滑器继续负责限速、加减速和超时停车，从而消除发布竞争并保留安全边界。

接线修复后的受控标定还显示，Gazebo 模型的世界姿态响应明显低于速度消息：

- 持续请求 `0.35 rad/s` 时，世界姿态实测约为 `0.06～0.07 rad/s`；
- 持续请求 `1.0 rad/s` 五秒，世界姿态旋转约 `2.89 rad`，实测约为 `0.58 rad/s`；
- `velocity_smoother` 的角速度上限本来就是 `1.0 rad/s`，最大角加速度为
  `3.2 rad/s²`。

第二阶段将扫描请求设为 `1.0 rad/s`，其仿真实际速度仍处于温和范围。单次扫描上限
从 `7.2 rad` 增至 `7.6 rad`，用于在圈末为连续三个 AMCL 更新留出余量；扫描评分、
协方差和真实误差验证门限均不放宽。

## 第一轮优化结果

同一套三个绑架位置在 `angular_speed=1.0` 下全部恢复成功。原始日志和逐次状态见
[`benchmark_results/2026-08-03_speed_1_0`](../benchmark_results/2026-08-03_speed_1_0/README.md)。

| 位置 | 原始基线 (s) | 本轮 (s) | 缩短 | 位置误差 (m) | 朝向误差 (deg) |
|---|---:|---:|---:|---:|---:|
| 左上房间 | 250.910 | 30.541 | 87.8% | 0.072 | 6.301 |
| 地图中心 | 95.243 | 14.618 | 84.7% | 0.040 | 7.354 |
| 右下区域 | 213.331 | 29.938 | 86.0% | 0.085 | 8.090 |

- 成功率：`3/3`；每次结束时实测速度均为零；
- 平均墙钟时间：从 `186.49 s` 降至 `25.03 s`，本轮缩短 `86.6%`；
- 最慢恢复时间：`30.54 s`；
- 扫描评分、协方差及连续三次 AMCL 更新门限没有放宽；
- 左上和右下位置使用了第二次尝试及短距离平移，因此目前仍应保留两次尝试策略。

这些结果证明运动链路和扫描速度曾是主要时间瓶颈，但每个位置目前仅有一次优化后
样本，不能据此宣称稳定成功率。下一轮应固定随机种子记录方式，并按每个位置至少
10 次测量 P50、P95、成功率和误定位率。

## 分阶段方案

1. 修复速度话题接线，以同一三位置基准测量纯运动链路收益。
2. 对当前速度配置执行每位置至少 10 次重复试验，先建立可靠的 P50/P95 和失败率。
3. 在稳定性不下降的前提下，测试 AMCL 粒子数和激光束数量的性能边界。
4. 若 P95 仍不满足目标，引入粗到细的全图扫描匹配，输出多个候选位姿并局部初始化 AMCL。
5. 对重复结构保留候选间距、扫描一致性复核和主动短距离消歧，禁止仅凭协方差确认。
