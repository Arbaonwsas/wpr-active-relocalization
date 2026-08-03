# Global relocalization timing benchmark

- Started: 2026-08-03T19:01:29.374491+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 6.883 | 8.200 | 0.152 | 0.026 | 5.428 | 0.302 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0639 |
| top_left_room | 2 | success | 6.234 | 7.100 | 0.152 | 0.026 | 4.425 | 0.201 | 0.000 | 0.452 | 0.004 | 0.151 | 1 | 0.0726 |
| top_left_room | 3 | success | 5.980 | 7.200 | 0.152 | 0.026 | 4.624 | 0.202 | 0.000 | 0.502 | 0.002 | 0.151 | 1 | 0.0665 |

## Recovery summary

- Success rate: 3/3.
- Successful service wall time: mean 6.37 s, P50 6.23 s, P95 6.82 s, max 6.88 s.
- Successful position error: mean 0.068 m, max 0.073 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 6.366 | 6.234 | 6.818 | 6.883 |
| map_center | 0/0 | - | - | - | - |
| bottom_right_area | 0/0 | - | - | - | - |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 2.4% |
| INITIALIZING | 0.026 | 0.026 | 0.026 | 0.026 | 0.4% |
| SCANNING | 4.826 | 4.624 | 5.348 | 5.428 | 75.8% |
| CONFIRMING | 0.235 | 0.202 | 0.292 | 0.302 | 3.7% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.485 | 0.502 | 0.502 | 0.502 | 7.6% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.004 | 0.004 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 2.4% |
| SERVICE/CLI_UNACCOUNTED | 0.488 | 0.322 | 0.774 | 0.824 | 7.7% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.057 | 1.892 | 2.346 | 2.397 |
| Pause physics | 1.024 | 1.374 | 1.382 | 1.383 |
| Teleport | 0.280 | 0.265 | 0.307 | 0.312 |
| Verify Gazebo pose | 0.464 | 0.450 | 0.516 | 0.523 |
| Unpause physics | 1.682 | 1.375 | 2.206 | 2.298 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.248 | 1.228 | 1.602 | 1.644 |
| Post-test stop | 3.097 | 3.399 | 3.502 | 3.514 |
| Post-test settle | 0.500 | 0.500 | 0.500 | 0.500 |
| Capture odometry pose | 1.467 | 1.200 | 2.221 | 2.334 |
| Capture AMCL pose | 1.310 | 1.201 | 1.501 | 1.534 |
| Capture quality | 1.196 | 1.208 | 1.222 | 1.224 |
| Capture velocity | 1.198 | 1.347 | 1.349 | 1.349 |
| Cleanup unpause | 0.669 | 0.316 | 1.275 | 1.382 |
| Cleanup stop | 2.299 | 2.410 | 2.591 | 2.611 |
| Whole test case | 28.078 | 27.800 | 29.687 | 29.897 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
