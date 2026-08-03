# Global relocalization baseline benchmark

- Started: 2026-08-03T17:37:49.771613+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Each location is tested once in this baseline pass.

| Location | Kidnapped pose (x, y, yaw) | Result | Wall time (s) | Sim time (s) | Attempts | Translation | Position error (m) | Yaw error (deg) | Scan score | Covariance (x, y, yaw) |
|---|---:|---|---:|---:|---:|---|---:|---:|---:|---|
| top_left_room | (-3.500, 2.500, 0.0000) | success | 250.910 | 251.500 | 2 | True | 0.0834 | 0.373 | 0.9650 | (0.0848, 0.0340, 0.1168) |
| map_center | (0.000, 0.000, 1.5708) | success | 95.243 | 96.300 | 1 | False | 0.0411 | 0.093 | 0.9693 | (0.0370, 0.0279, 0.0443) |
| bottom_right_area | (3.500, -1.500, -2.0944) | success | 213.331 | 214.300 | 2 | False (clearance insufficient) | 0.0868 | 2.758 | 0.9060 | (0.0340, 0.0189, 0.0279) |

## Summary

- Success rate: 3/3.
- Successful wall time: mean 186.49 s, min 95.24 s, max 250.91 s.
- Successful simulation time: mean 187.37 s, min 96.30 s, max 251.50 s.
- Successful position error: mean 0.070 m, max 0.087 m.
- Successful yaw error: mean 1.075 degrees, max 2.758 degrees.
- `status_*.log` contains every state transition and intermediate quality sample.
- This three-case pass is a baseline for timing work; repeat trials are needed before claiming a stability percentage.

## Observations for optimization

- The slowest case was the top-left room at 250.91 s. It used a full first scan, a 0.55 m backward translation, and almost a full second scan before convergence.
- The map center converged in the first scan at 95.24 s, showing that environment observability is currently the dominant timing factor.
- The bottom-right case needed a second scan. Translation was skipped safely because front/rear clearance was 0.91/0.98 m versus the required 1.00 m.
- Wall time and simulation time differ by at most 1.06 s, so the measured spread is algorithmic rather than a low Gazebo real-time factor.
- All final speed norms were zero, confirming that the robot stopped after every completed test.

## Reproduction

From a sourced ROS 2 workspace, run:

```bash
python3 scripts/benchmark_global_relocalization.py
```

Use `--location map_center` (or another table location) to run a targeted retry.
