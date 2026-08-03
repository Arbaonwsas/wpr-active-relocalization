# Global relocalization timing benchmark

- Started: 2026-08-03T18:59:51.582688+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 3.854 | 4.700 | 0.152 | 0.017 | 2.564 | 0.202 | 0.000 | 0.453 | 0.002 | 0.151 | 1 | 0.0611 |
| top_left_room | 2 | success | 9.316 | 10.500 | 0.152 | 0.017 | 6.943 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0570 |
| top_left_room | 3 | success | 4.123 | 5.300 | 0.153 | 0.016 | 2.510 | 0.201 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0595 |

## Recovery summary

- Success rate: 3/3.
- Successful service wall time: mean 5.76 s, P50 4.12 s, P95 8.80 s, max 9.32 s.
- Successful position error: mean 0.059 m, max 0.061 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 5.764 | 4.123 | 8.797 | 9.316 |
| map_center | 0/0 | - | - | - | - |
| bottom_right_area | 0/0 | - | - | - | - |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.153 | 0.153 | 2.6% |
| INITIALIZING | 0.017 | 0.017 | 0.017 | 0.017 | 0.3% |
| SCANNING | 4.006 | 2.564 | 6.505 | 6.943 | 69.5% |
| CONFIRMING | 0.201 | 0.201 | 0.202 | 0.202 | 3.5% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.452 | 0.452 | 0.453 | 0.453 | 7.8% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 2.6% |
| SERVICE/CLI_UNACCOUNTED | 0.782 | 0.637 | 1.320 | 1.396 | 13.6% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.054 | 1.883 | 2.352 | 2.404 |
| Pause physics | 1.020 | 1.365 | 1.383 | 1.385 |
| Teleport | 0.264 | 0.263 | 0.271 | 0.272 |
| Verify Gazebo pose | 0.418 | 0.387 | 0.497 | 0.509 |
| Unpause physics | 1.027 | 1.372 | 1.399 | 1.402 |
| Settle delay | 2.001 | 2.001 | 2.002 | 2.002 |
| Post-test clock | 1.077 | 1.183 | 1.195 | 1.196 |
| Post-test stop | 2.061 | 1.889 | 2.361 | 2.413 |
| Post-test settle | 0.500 | 0.500 | 0.501 | 0.501 |
| Capture odometry pose | 0.867 | 0.862 | 0.881 | 0.883 |
| Capture AMCL pose | 0.978 | 0.868 | 1.169 | 1.202 |
| Capture quality | 1.329 | 1.194 | 1.564 | 1.605 |
| Capture velocity | 1.264 | 1.246 | 1.336 | 1.346 |
| Cleanup unpause | 1.024 | 1.375 | 1.387 | 1.388 |
| Cleanup stop | 2.414 | 2.548 | 2.784 | 2.810 |
| Whole test case | 25.201 | 22.779 | 29.480 | 30.225 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
