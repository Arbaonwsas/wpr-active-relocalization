# Global relocalization timing benchmark

- Started: 2026-08-03T19:21:48.764368+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 7.789 | 9.100 | 0.152 | 0.017 | 4.822 | 0.201 | 0.000 | 0.452 | 0.253 | 0.002 | 0.151 | 1 | 0.0651 |
| top_left_room | 2 | success | 7.583 | 8.900 | 0.152 | 0.018 | 4.972 | 0.201 | 0.000 | 0.502 | 0.203 | 0.002 | 0.151 | 1 | 0.0597 |
| top_left_room | 3 | success | 6.479 | 7.700 | 0.153 | 0.017 | 4.921 | 0.201 | 0.000 | 0.452 | 0.254 | 0.002 | 0.151 | 1 | 0.0614 |
| map_center | 1 | success | 3.672 | 4.600 | 0.152 | 0.021 | 2.010 | 0.302 | 0.000 | 0.502 | 0.203 | 0.002 | 0.151 | 1 | 0.0287 |
| map_center | 2 | success | 4.978 | 5.800 | 0.152 | 0.017 | 2.160 | 0.403 | 0.000 | 0.452 | 0.253 | 0.002 | 0.151 | 1 | 0.0220 |
| map_center | 3 | success | 4.393 | 5.600 | 0.152 | 0.017 | 1.760 | 0.202 | 0.000 | 0.502 | 0.203 | 0.003 | 0.151 | 1 | 0.0287 |
| bottom_right_area | 1 | success | 4.670 | 5.500 | 0.152 | 0.017 | 3.115 | 0.201 | 0.000 | 0.452 | 0.254 | 0.003 | 0.151 | 1 | 0.0608 |
| bottom_right_area | 2 | success | 7.284 | 8.200 | 0.152 | 0.017 | 3.669 | 0.202 | 0.000 | 0.503 | 0.204 | 0.003 | 0.151 | 1 | 0.0672 |
| bottom_right_area | 3 | success | 5.863 | 7.100 | 0.152 | 0.017 | 3.369 | 0.151 | 0.000 | 0.452 | 0.253 | 0.002 | 0.151 | 1 | 0.0641 |

## Recovery summary

- Success rate: 9/9.
- Successful service wall time: mean 5.86 s, P50 5.86 s, P95 7.71 s, max 7.79 s.
- Successful position error: mean 0.051 m, max 0.067 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 3/3 | 7.284 | 7.583 | 7.768 | 7.789 |
| map_center | 3/3 | 4.348 | 4.393 | 4.919 | 4.978 |
| bottom_right_area | 3/3 | 5.939 | 5.863 | 7.142 | 7.284 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.153 | 0.153 | 2.6% |
| INITIALIZING | 0.018 | 0.017 | 0.020 | 0.021 | 0.3% |
| SCANNING | 3.422 | 3.369 | 4.952 | 4.972 | 58.4% |
| CONFIRMING | 0.229 | 0.201 | 0.363 | 0.403 | 3.9% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.474 | 0.452 | 0.503 | 0.503 | 8.1% |
| VERIFYING_STATIONARY | 0.231 | 0.253 | 0.254 | 0.254 | 3.9% |
| CLEARING_COSTMAPS | 0.002 | 0.002 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 2.6% |
| SERVICE/CLI_UNACCOUNTED | 1.177 | 1.381 | 2.125 | 2.383 | 20.1% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.113 | 1.886 | 2.418 | 2.419 |
| Pause physics | 1.173 | 1.380 | 1.406 | 1.410 |
| Teleport | 0.301 | 0.303 | 0.364 | 0.367 |
| Verify Gazebo pose | 0.456 | 0.422 | 0.548 | 0.559 |
| Unpause physics | 1.480 | 1.377 | 2.383 | 2.383 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.095 | 1.211 | 1.325 | 1.325 |
| Post-test stop | 2.135 | 1.897 | 2.524 | 2.614 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 1.178 | 0.916 | 2.017 | 2.341 |
| Capture AMCL pose | 1.051 | 0.880 | 1.396 | 1.521 |
| Capture quality | 1.143 | 1.186 | 1.343 | 1.413 |
| Capture velocity | 1.140 | 1.195 | 1.424 | 1.544 |
| Cleanup unpause | 1.354 | 1.375 | 1.986 | 2.380 |
| Cleanup stop | 1.970 | 1.892 | 2.174 | 2.234 |
| Whole test case | 26.369 | 26.164 | 29.782 | 30.093 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
