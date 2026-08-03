# Global relocalization timing benchmark

- Started: 2026-08-03T19:43:00.561110+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 7.615 | 9.100 | 0.152 | 0.017 | 5.827 | 0.101 | 0.000 | 0.502 | 0.205 | 0.006 | 0.151 | 1 | 0.0580 |
| top_left_room | 2 | success | 4.123 | 5.700 | 0.152 | 0.014 | 2.008 | 0.101 | 0.000 | 0.502 | 0.203 | 0.002 | 0.151 | 1 | 0.0686 |
| top_left_room | 3 | success | 3.637 | 4.800 | 0.152 | 0.014 | 1.860 | 0.101 | 0.000 | 0.502 | 0.203 | 0.002 | 0.151 | 1 | 0.0708 |
| map_center | 1 | success | 3.112 | 4.600 | 0.152 | 0.014 | 1.708 | 0.103 | 0.000 | 0.451 | 0.203 | 0.002 | 0.151 | 1 | 0.0464 |
| map_center | 2 | success | 3.308 | 4.200 | 0.152 | 0.014 | 1.862 | 0.101 | 0.000 | 0.502 | 0.203 | 0.004 | 0.151 | 1 | 0.0326 |
| map_center | 3 | success | 4.365 | 5.200 | 0.152 | 0.014 | 2.668 | 0.406 | 0.000 | 0.451 | 0.203 | 0.003 | 0.151 | 1 | 0.0177 |
| bottom_right_area | 1 | success | 2.854 | 3.700 | 0.152 | 0.015 | 1.408 | 0.101 | 0.000 | 0.503 | 0.204 | 0.003 | 0.151 | 1 | 0.0635 |
| bottom_right_area | 2 | success | 3.711 | 4.600 | 0.152 | 0.014 | 2.315 | 0.101 | 0.000 | 0.451 | 0.203 | 0.002 | 0.151 | 1 | 0.0626 |
| bottom_right_area | 3 | success | 6.889 | 8.200 | 0.152 | 0.014 | 4.622 | 0.101 | 0.000 | 0.502 | 0.203 | 0.003 | 0.151 | 1 | 0.0605 |

## Recovery summary

- Success rate: 9/9.
- Successful service wall time: mean 4.40 s, P50 3.71 s, P95 7.32 s, max 7.62 s.
- Successful position error: mean 0.053 m, max 0.071 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 5.125 | 4.123 | 7.266 | 7.615 |
| map_center | 3/3 | 3.595 | 3.308 | 4.259 | 4.365 |
| bottom_right_area | 3/3 | 4.485 | 3.711 | 6.571 | 6.889 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 3.5% |
| INITIALIZING | 0.014 | 0.014 | 0.016 | 0.017 | 0.3% |
| SCANNING | 2.698 | 2.008 | 5.345 | 5.827 | 61.3% |
| CONFIRMING | 0.135 | 0.101 | 0.285 | 0.406 | 3.1% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.485 | 0.502 | 0.503 | 0.503 | 11.0% |
| VERIFYING_STATIONARY | 0.203 | 0.203 | 0.205 | 0.205 | 4.6% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.005 | 0.006 | 0.1% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 3.4% |
| SERVICE/CLI_UNACCOUNTED | 0.560 | 0.327 | 1.081 | 1.141 | 12.7% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.078 | 1.887 | 2.420 | 2.420 |
| Pause physics | 1.182 | 1.383 | 1.409 | 1.413 |
| Teleport | 0.278 | 0.265 | 0.322 | 0.327 |
| Verify Gazebo pose | 0.480 | 0.462 | 0.557 | 0.561 |
| Unpause physics | 1.165 | 1.378 | 1.987 | 2.377 |
| Settle delay | 2.001 | 2.001 | 2.002 | 2.002 |
| Post-test clock | 1.172 | 1.168 | 1.550 | 1.586 |
| Post-test stop | 2.129 | 2.214 | 2.488 | 2.530 |
| Post-test settle | 0.500 | 0.500 | 0.501 | 0.501 |
| Capture odometry pose | 1.211 | 1.218 | 1.681 | 1.685 |
| Capture AMCL pose | 1.267 | 1.217 | 1.648 | 1.720 |
| Capture quality | 1.125 | 0.914 | 1.530 | 1.537 |
| Capture velocity | 1.128 | 1.200 | 1.471 | 1.549 |
| Cleanup unpause | 1.196 | 1.381 | 1.391 | 1.393 |
| Cleanup stop | 2.084 | 1.974 | 2.414 | 2.418 |
| Whole test case | 24.903 | 23.883 | 30.265 | 30.978 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
