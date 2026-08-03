# Global relocalization timing benchmark

- Started: 2026-08-03T18:54:51.210183+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 8.111 | 9.600 | 0.152 | 0.019 | 5.728 | 0.202 | 0.000 | 0.453 | 0.003 | 0.151 | 1 | 0.0580 |
| top_left_room | 2 | success | 4.118 | 5.500 | 0.152 | 0.017 | 1.757 | 0.201 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0672 |
| top_left_room | 3 | success | 5.263 | 6.100 | 0.152 | 0.017 | 2.914 | 0.201 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0722 |

## Recovery summary

- Success rate: 3/3.
- Successful service wall time: mean 5.83 s, P50 5.26 s, P95 7.83 s, max 8.11 s.
- Successful position error: mean 0.066 m, max 0.072 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 5.831 | 5.263 | 7.826 | 8.111 |
| map_center | 0/0 | - | - | - | - |
| bottom_right_area | 0/0 | - | - | - | - |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 2.6% |
| INITIALIZING | 0.018 | 0.017 | 0.019 | 0.019 | 0.3% |
| SCANNING | 3.466 | 2.914 | 5.447 | 5.728 | 59.5% |
| CONFIRMING | 0.201 | 0.201 | 0.202 | 0.202 | 3.5% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.469 | 0.453 | 0.497 | 0.502 | 8.0% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 2.6% |
| SERVICE/CLI_UNACCOUNTED | 1.372 | 1.387 | 1.403 | 1.405 | 23.5% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.060 | 1.891 | 2.354 | 2.405 |
| Pause physics | 1.480 | 1.409 | 1.629 | 1.653 |
| Teleport | 0.307 | 0.298 | 0.356 | 0.362 |
| Verify Gazebo pose | 0.500 | 0.499 | 0.519 | 0.521 |
| Unpause physics | 1.360 | 1.380 | 2.284 | 2.384 |
| Settle delay | 2.001 | 2.001 | 2.002 | 2.002 |
| Post-test clock | 1.240 | 1.389 | 1.487 | 1.498 |
| Post-test stop | 2.125 | 1.885 | 2.536 | 2.608 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 1.020 | 0.887 | 1.269 | 1.311 |
| Capture AMCL pose | 1.311 | 1.205 | 1.506 | 1.539 |
| Capture quality | 1.177 | 1.219 | 1.392 | 1.411 |
| Capture velocity | 1.367 | 1.347 | 1.529 | 1.549 |
| Cleanup unpause | 1.028 | 1.381 | 1.383 | 1.383 |
| Cleanup stop | 1.882 | 1.881 | 1.886 | 1.887 |
| Whole test case | 26.360 | 26.102 | 28.719 | 29.010 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
