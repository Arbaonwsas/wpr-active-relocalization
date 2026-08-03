# Global relocalization baseline benchmark

- Started: 2026-08-03T18:23:46.028821+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Each location is tested once in this baseline pass.

| Location | Kidnapped pose (x, y, yaw) | Result | Wall time (s) | Sim time (s) | Attempts | Translation | Position error (m) | Yaw error (deg) | Scan score | Covariance (x, y, yaw) |
|---|---:|---|---:|---:|---:|---|---:|---:|---:|---|
| top_left_room | (-3.500, 2.500, 0.0000) | success | 30.541 | 31.700 | 2 | True | 0.0724 | 6.301 | 0.8549 | (0.0448, 0.0384, 0.0608) |
| map_center | (0.000, 0.000, 1.5708) | success | 14.618 | 16.000 | 1 | False | 0.0400 | 7.354 | 0.5684 | (0.0387, 0.0312, 0.0472) |
| bottom_right_area | (3.500, -1.500, -2.0944) | success | 29.938 | 30.800 | 2 | True | 0.0854 | 8.090 | 0.8134 | (0.0604, 0.0248, 0.0372) |

## Summary

- Success rate: 3/3.
- Successful wall time: mean 25.03 s, min 14.62 s, max 30.54 s.
- Successful position error: mean 0.066 m, max 0.085 m.
- `status_*.log` contains every state transition and intermediate quality sample.
- This three-case pass is a baseline for timing work; repeat trials are needed before claiming a stability percentage.
