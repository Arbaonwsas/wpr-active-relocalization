# Global relocalization timing benchmark

- Started: 2026-08-03T19:37:27.194803+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 6.881 | 7.900 | 0.152 | 0.024 | 5.376 | 0.151 | 0.000 | 0.502 | 0.203 | 0.004 | 0.151 | 1 | 0.0605 |
| top_left_room | 2 | success | 4.325 | 5.200 | 0.152 | 0.018 | 2.864 | 0.101 | 0.000 | 0.502 | 0.203 | 0.004 | 0.151 | 1 | 0.0628 |
| top_left_room | 3 | success | 5.341 | 6.500 | 0.152 | 0.021 | 2.716 | 0.202 | 0.000 | 0.502 | 0.204 | 0.003 | 0.151 | 1 | 0.0600 |
| map_center | 1 | success | 3.880 | 5.400 | 0.152 | 0.022 | 2.414 | 0.101 | 0.000 | 0.502 | 0.203 | 0.004 | 0.151 | 1 | 0.0358 |
| map_center | 2 | success | 2.814 | 3.700 | 0.152 | 0.022 | 1.408 | 0.101 | 0.000 | 0.452 | 0.204 | 0.003 | 0.151 | 1 | 0.0465 |
| map_center | 3 | success | 3.465 | 4.300 | 0.152 | 0.018 | 2.010 | 0.101 | 0.000 | 0.502 | 0.204 | 0.002 | 0.151 | 1 | 0.0425 |
| bottom_right_area | 1 | success | 4.324 | 5.200 | 0.152 | 0.019 | 2.918 | 0.101 | 0.000 | 0.453 | 0.203 | 0.004 | 0.151 | 1 | 0.0620 |
| bottom_right_area | 2 | success | 3.870 | 4.700 | 0.152 | 0.017 | 1.356 | 0.101 | 0.000 | 0.502 | 0.203 | 0.002 | 0.151 | 1 | 0.0631 |
| bottom_right_area | 3 | success | 3.970 | 4.800 | 0.152 | 0.017 | 1.507 | 0.101 | 0.000 | 0.503 | 0.203 | 0.003 | 0.151 | 1 | 0.0551 |

## Recovery summary

- Success rate: 9/9.
- Successful service wall time: mean 4.32 s, P50 3.97 s, P95 6.26 s, max 6.88 s.
- Successful position error: mean 0.054 m, max 0.063 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 5.516 | 5.341 | 6.727 | 6.881 |
| map_center | 3/3 | 3.386 | 3.465 | 3.838 | 3.880 |
| bottom_right_area | 3/3 | 4.055 | 3.970 | 4.289 | 4.324 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 3.5% |
| INITIALIZING | 0.020 | 0.019 | 0.023 | 0.024 | 0.5% |
| SCANNING | 2.508 | 2.414 | 4.393 | 5.376 | 58.1% |
| CONFIRMING | 0.118 | 0.101 | 0.182 | 0.202 | 2.7% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.491 | 0.502 | 0.503 | 0.503 | 11.4% |
| VERIFYING_STATIONARY | 0.203 | 0.203 | 0.204 | 0.204 | 4.7% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.004 | 0.004 | 0.1% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 3.5% |
| SERVICE/CLI_UNACCOUNTED | 0.673 | 0.329 | 1.388 | 1.390 | 15.6% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.253 | 2.392 | 2.513 | 2.568 |
| Pause physics | 1.057 | 1.378 | 1.408 | 1.412 |
| Teleport | 0.310 | 0.290 | 0.364 | 0.367 |
| Verify Gazebo pose | 0.468 | 0.473 | 0.542 | 0.544 |
| Unpause physics | 1.246 | 1.379 | 1.399 | 1.410 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.020 | 0.877 | 1.453 | 1.526 |
| Post-test stop | 2.165 | 2.220 | 2.546 | 2.558 |
| Post-test settle | 0.500 | 0.500 | 0.501 | 0.501 |
| Capture odometry pose | 1.004 | 0.899 | 1.425 | 1.553 |
| Capture AMCL pose | 1.059 | 0.880 | 1.541 | 1.544 |
| Capture quality | 1.032 | 0.878 | 1.303 | 1.366 |
| Capture velocity | 1.229 | 1.200 | 1.553 | 1.554 |
| Cleanup unpause | 1.141 | 1.381 | 1.389 | 1.389 |
| Cleanup stop | 1.948 | 1.887 | 2.217 | 2.429 |
| Whole test case | 24.255 | 24.354 | 27.065 | 27.915 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
