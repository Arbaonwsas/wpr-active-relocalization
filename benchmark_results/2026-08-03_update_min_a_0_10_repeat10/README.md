# Global relocalization timing benchmark

- Started: 2026-08-03T19:03:24.549913+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 10.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 4.464 | 5.600 | 0.152 | 0.018 | 3.115 | 0.201 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0728 |
| top_left_room | 2 | success | 7.374 | 8.600 | 0.153 | 0.017 | 6.030 | 0.201 | 0.000 | 0.502 | 0.002 | 0.151 | 1 | 0.0601 |
| top_left_room | 3 | success | 7.309 | 8.800 | 0.152 | 0.017 | 5.481 | 0.402 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0610 |
| top_left_room | 4 | success | 4.310 | 5.500 | 0.152 | 0.017 | 2.762 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0677 |
| top_left_room | 5 | success | 8.701 | 9.600 | 0.152 | 0.018 | 5.982 | 0.504 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0626 |
| top_left_room | 6 | success | 4.314 | 5.700 | 0.152 | 0.018 | 3.014 | 0.201 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0646 |
| top_left_room | 7 | success | 5.318 | 6.200 | 0.152 | 0.018 | 4.018 | 0.201 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0753 |
| top_left_room | 8 | success | 6.429 | 7.300 | 0.152 | 0.016 | 4.874 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0544 |
| top_left_room | 9 | success | 7.181 | 8.000 | 0.000 | 0.018 | 5.836 | 0.202 | 0.000 | 0.503 | 0.003 | 0.151 | 1 | 0.0700 |
| top_left_room | 10 | success | 3.908 | 5.100 | 0.152 | 0.017 | 2.612 | 0.202 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0640 |
| map_center | 1 | success | 3.050 | 4.400 | 0.152 | 0.017 | 1.759 | 0.202 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0194 |
| map_center | 2 | success | 4.615 | 6.000 | 0.153 | 0.019 | 3.323 | 0.201 | 0.000 | 0.453 | 0.003 | 0.151 | 1 | 0.0331 |
| map_center | 3 | success | 3.310 | 4.500 | 0.152 | 0.018 | 2.009 | 0.201 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0272 |
| map_center | 4 | success | 4.146 | 5.300 | 0.152 | 0.018 | 1.509 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0386 |
| map_center | 5 | success | 4.221 | 5.100 | 0.152 | 0.018 | 2.713 | 0.403 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0225 |
| map_center | 6 | success | 3.822 | 5.300 | 0.152 | 0.017 | 1.457 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0044 |
| map_center | 7 | success | 5.283 | 6.500 | 0.153 | 0.017 | 2.866 | 0.201 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0482 |
| map_center | 8 | success | 4.518 | 5.400 | 0.153 | 0.019 | 2.311 | 0.201 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0332 |
| map_center | 9 | success | 4.359 | 5.200 | 0.152 | 0.019 | 2.009 | 0.201 | 0.000 | 0.502 | 0.002 | 0.151 | 1 | 0.0350 |
| map_center | 10 | success | 4.357 | 7.700 | 0.152 | 0.018 | 2.010 | 0.201 | 0.000 | 0.502 | 0.002 | 0.151 | 1 | 0.0396 |
| bottom_right_area | 1 | success | 4.184 | 5.400 | 0.152 | 0.017 | 2.514 | 0.201 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0820 |
| bottom_right_area | 2 | success | 4.293 | 5.600 | 0.152 | 0.018 | 2.614 | 0.202 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0736 |
| bottom_right_area | 3 | success | 4.181 | 5.400 | 0.154 | 0.018 | 2.263 | 0.202 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0729 |
| bottom_right_area | 4 | success | 3.711 | 5.100 | 0.153 | 0.017 | 2.412 | 0.201 | 0.000 | 0.451 | 0.002 | 0.151 | 1 | 0.0679 |
| bottom_right_area | 5 | success | 8.013 | 9.400 | 0.152 | 0.020 | 6.740 | 0.152 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0685 |
| bottom_right_area | 6 | success | 5.423 | 6.300 | 0.153 | 0.017 | 3.065 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0669 |
| bottom_right_area | 7 | success | 2.907 | 4.100 | 0.152 | 0.018 | 1.659 | 0.153 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0606 |
| bottom_right_area | 8 | success | 3.719 | 4.600 | 0.152 | 0.018 | 2.109 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0490 |
| bottom_right_area | 9 | success | 5.855 | 6.700 | 0.152 | 0.017 | 4.225 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0612 |
| bottom_right_area | 10 | success | 5.011 | 6.700 | 0.152 | 0.017 | 3.721 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0735 |

## Recovery summary

- Success rate: 30/30.
- Successful service wall time: mean 4.94 s, P50 4.36 s, P95 7.73 s, max 8.70 s.
- Successful position error: mean 0.054 m, max 0.082 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 10/10 | 5.931 | 5.873 | 8.104 | 8.701 |
| map_center | 10/10 | 4.168 | 4.289 | 4.982 | 5.283 |
| bottom_right_area | 10/10 | 4.730 | 4.239 | 7.042 | 8.013 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.147 | 0.152 | 0.153 | 0.154 | 3.0% |
| INITIALIZING | 0.018 | 0.018 | 0.019 | 0.020 | 0.4% |
| SCANNING | 3.234 | 2.737 | 6.008 | 6.740 | 65.4% |
| CONFIRMING | 0.221 | 0.201 | 0.403 | 0.504 | 4.5% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.469 | 0.452 | 0.502 | 0.503 | 9.5% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.1% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 3.1% |
| SERVICE/CLI_UNACCOUNTED | 0.696 | 0.576 | 1.391 | 1.661 | 14.1% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.189 | 2.216 | 2.484 | 2.536 |
| Pause physics | 1.678 | 1.379 | 2.233 | 17.394 |
| Teleport | 0.299 | 0.265 | 0.409 | 0.448 |
| Verify Gazebo pose | 0.470 | 0.463 | 0.549 | 0.652 |
| Unpause physics | 2.265 | 1.378 | 10.109 | 17.396 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.245 | 1.197 | 1.673 | 3.351 |
| Post-test stop | 2.361 | 2.400 | 3.113 | 3.415 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 1.144 | 1.055 | 1.615 | 2.332 |
| Capture AMCL pose | 1.159 | 0.874 | 1.917 | 2.333 |
| Capture quality | 1.135 | 1.060 | 1.560 | 1.796 |
| Capture velocity | 1.160 | 1.194 | 1.600 | 1.648 |
| Cleanup unpause | 1.020 | 1.372 | 1.404 | 2.394 |
| Cleanup stop | 2.123 | 2.140 | 2.525 | 2.538 |
| Whole test case | 26.909 | 24.959 | 39.786 | 42.453 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
