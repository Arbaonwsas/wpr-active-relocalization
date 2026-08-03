# Global relocalization timing benchmark

- Started: 2026-08-03T18:56:42.137098+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| map_center | 1 | success | 3.717 | 4.600 | 0.152 | 0.019 | 2.112 | 0.504 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0273 |
| map_center | 2 | success | 3.354 | 4.200 | 0.152 | 0.018 | 2.009 | 0.201 | 0.000 | 0.502 | 0.003 | 0.151 | 1 | 0.0361 |
| map_center | 3 | success | 4.334 | 5.200 | 0.152 | 0.018 | 1.709 | 0.202 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0112 |
| bottom_right_area | 1 | success | 3.914 | 5.400 | 0.152 | 0.019 | 2.612 | 0.202 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0537 |
| bottom_right_area | 2 | success | 4.809 | 6.000 | 0.152 | 0.017 | 2.362 | 0.202 | 0.000 | 0.453 | 0.002 | 0.151 | 1 | 0.0553 |
| bottom_right_area | 3 | success | 4.506 | 7.200 | 0.152 | 0.017 | 2.968 | 0.202 | 0.000 | 0.452 | 0.003 | 0.151 | 1 | 0.0464 |

## Recovery summary

- Success rate: 6/6.
- Successful service wall time: mean 4.11 s, P50 4.12 s, P95 4.73 s, max 4.81 s.
- Successful position error: mean 0.038 m, max 0.055 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 0/0 | - | - | - | - |
| map_center | 3/3 | 3.802 | 3.717 | 4.272 | 4.334 |
| bottom_right_area | 3/3 | 4.410 | 4.506 | 4.779 | 4.809 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 3.7% |
| INITIALIZING | 0.018 | 0.018 | 0.019 | 0.019 | 0.4% |
| SCANNING | 2.295 | 2.237 | 2.879 | 2.968 | 55.9% |
| CONFIRMING | 0.252 | 0.202 | 0.428 | 0.504 | 6.1% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.460 | 0.452 | 0.490 | 0.502 | 11.2% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.1% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 3.7% |
| SERVICE/CLI_UNACCOUNTED | 0.774 | 0.444 | 1.602 | 1.646 | 18.9% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.062 | 1.883 | 2.445 | 2.466 |
| Pause physics | 1.242 | 1.393 | 2.200 | 2.384 |
| Teleport | 0.299 | 0.270 | 0.367 | 0.370 |
| Verify Gazebo pose | 0.457 | 0.443 | 0.534 | 0.552 |
| Unpause physics | 1.197 | 1.379 | 1.389 | 1.390 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.333 | 1.042 | 2.399 | 2.701 |
| Post-test stop | 2.049 | 1.893 | 2.460 | 2.544 |
| Post-test settle | 0.500 | 0.500 | 0.501 | 0.501 |
| Capture odometry pose | 1.145 | 1.204 | 1.347 | 1.352 |
| Capture AMCL pose | 1.138 | 1.189 | 1.445 | 1.525 |
| Capture quality | 1.145 | 1.083 | 1.500 | 1.533 |
| Capture velocity | 1.346 | 1.445 | 1.550 | 1.550 |
| Cleanup unpause | 3.571 | 1.069 | 13.335 | 17.341 |
| Cleanup stop | 2.022 | 1.889 | 2.337 | 2.378 |
| Whole test case | 26.741 | 24.718 | 36.400 | 39.813 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
