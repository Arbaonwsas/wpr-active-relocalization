# Global relocalization timing benchmark

- Started: 2026-08-03T18:46:04.257487+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 15.400 | 16.900 | 0.152 | 0.017 | 8.800 | 0.605 | 3.321 | 0.955 | 0.003 | 0.151 | 2 | 0.0795 |
| top_left_room | 2 | success | 16.099 | 17.300 | 0.152 | 0.020 | 10.761 | 0.403 | 3.321 | 0.955 | 0.003 | 0.151 | 2 | 0.0637 |
| top_left_room | 3 | success | 14.648 | 15.900 | 0.152 | 0.017 | 8.850 | 0.403 | 3.273 | 0.904 | 0.002 | 0.151 | 2 | 0.0628 |
| map_center | 1 | success | 6.930 | 8.300 | 0.152 | 0.021 | 5.427 | 0.402 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0306 |
| map_center | 2 | success | 7.789 | 9.300 | 0.152 | 0.018 | 4.976 | 0.604 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0266 |
| map_center | 3 | success | 5.727 | 6.600 | 0.152 | 0.017 | 4.223 | 0.403 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0478 |
| bottom_right_area | 1 | success | 9.469 | 10.700 | 0.153 | 0.017 | 6.583 | 0.403 | 0.000 | 0.502 | 0.002 | 0.151 | 1 | 0.0708 |
| bottom_right_area | 2 | success | 9.467 | 10.700 | 0.153 | 0.021 | 6.582 | 0.402 | 0.000 | 0.502 | 0.002 | 0.151 | 1 | 0.0799 |
| bottom_right_area | 3 | success | 8.294 | 9.800 | 0.152 | 0.021 | 6.734 | 0.403 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0957 |

## Recovery summary

- Success rate: 9/9.
- Successful service wall time: mean 10.42 s, P50 9.47 s, P95 15.82 s, max 16.10 s.
- Successful position error: mean 0.062 m, max 0.096 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 15.382 | 15.400 | 16.029 | 16.099 |
| map_center | 3/3 | 6.815 | 6.930 | 7.703 | 7.789 |
| bottom_right_area | 3/3 | 9.077 | 9.467 | 9.469 | 9.469 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.153 | 0.153 | 1.5% |
| INITIALIZING | 0.019 | 0.018 | 0.021 | 0.021 | 0.2% |
| SCANNING | 6.993 | 6.583 | 9.997 | 10.761 | 67.1% |
| CONFIRMING | 0.448 | 0.403 | 0.605 | 0.605 | 4.3% |
| TRANSLATING | 1.102 | 0.000 | 3.321 | 3.321 | 10.6% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.636 | 0.502 | 0.955 | 0.955 | 6.1% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 1.4% |
| SERVICE/CLI_UNACCOUNTED | 0.922 | 0.897 | 1.656 | 1.657 | 8.8% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.109 | 1.976 | 2.411 | 2.419 |
| Pause physics | 1.030 | 1.383 | 1.994 | 2.386 |
| Teleport | 0.287 | 0.264 | 0.365 | 0.372 |
| Verify Gazebo pose | 0.508 | 0.507 | 0.583 | 0.588 |
| Unpause physics | 1.015 | 1.320 | 1.983 | 2.379 |
| Settle delay | 2.001 | 2.001 | 2.002 | 2.002 |
| Post-test clock | 1.308 | 1.262 | 1.519 | 1.520 |
| Post-test stop | 2.170 | 2.217 | 2.598 | 2.712 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 1.020 | 0.911 | 1.293 | 1.337 |
| Capture AMCL pose | 1.131 | 1.197 | 1.518 | 1.531 |
| Capture quality | 1.014 | 0.929 | 1.235 | 1.261 |
| Capture velocity | 1.119 | 0.900 | 1.506 | 1.546 |
| Cleanup unpause | 0.735 | 0.571 | 1.390 | 1.394 |
| Cleanup stop | 2.018 | 1.893 | 2.322 | 2.387 |
| Whole test case | 29.565 | 28.256 | 33.464 | 33.518 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
