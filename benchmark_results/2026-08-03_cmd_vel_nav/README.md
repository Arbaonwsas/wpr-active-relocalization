# Global relocalization baseline benchmark

- Started: 2026-08-03T18:11:11.368303+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Each location is tested once in this baseline pass.

| Location | Kidnapped pose (x, y, yaw) | Result | Wall time (s) | Sim time (s) | Attempts | Translation | Position error (m) | Yaw error (deg) | Scan score | Covariance (x, y, yaw) |
|---|---:|---|---:|---:|---:|---|---:|---:|---:|---|
| top_left_room | (-3.500, 2.500, 0.0000) | failure | 255.349 | 256.000 | 2 | True | 0.0670 | 6.640 | 0.8533 | (0.0648, 0.0291, 0.0839) |
| map_center | (0.000, 0.000, 1.5708) | success | 90.527 | 92.000 | 1 | False | 0.0232 | 0.508 | 0.9802 | (0.0459, 0.0258, 0.0429) |
| bottom_right_area | (3.500, -1.500, -2.0944) | success | 94.627 | 95.900 | 1 | False | 0.0736 | 0.864 | 0.9728 | (0.2663, 0.0535, 0.0976) |

## Summary

- Success rate: 2/3.
- Successful wall time: mean 92.58 s, min 90.53 s, max 94.63 s.
- Successful position error: mean 0.048 m, max 0.074 m.
- `status_*.log` contains every state transition and intermediate quality sample.
- This three-case pass is a baseline for timing work; repeat trials are needed before claiming a stability percentage.
