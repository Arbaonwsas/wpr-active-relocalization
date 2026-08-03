# Global relocalization timing benchmark

- Started: 2026-08-03T18:43:32.118609+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 1.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 6.220 | 7.100 | 0.152 | 0.017 | 4.721 | 0.402 | 0.000 | 0.452 | 0.002 | 0.151 | 1 | 0.0836 |
| map_center | 1 | success | 16.588 | 17.500 | 0.152 | 0.018 | 8.891 | 0.503 | 5.538 | 1.005 | 0.002 | 0.151 | 2 | 0.0465 |
| bottom_right_area | 1 | success | 19.124 | 20.300 | 0.152 | 0.018 | 9.054 | 0.352 | 6.750 | 0.905 | 0.002 | 0.151 | 2 | 0.0954 |

## Recovery summary

- Success rate: 3/3.
- Successful service wall time: mean 13.98 s, P50 16.59 s, P95 18.87 s, max 19.12 s.
- Successful position error: mean 0.075 m, max 0.095 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 1/1 | 6.220 | 6.220 | 6.220 | 6.220 |
| map_center | 1/1 | 16.588 | 16.588 | 16.588 | 16.588 |
| bottom_right_area | 1/1 | 19.124 | 19.124 | 19.124 | 19.124 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 1.1% |
| INITIALIZING | 0.018 | 0.018 | 0.018 | 0.018 | 0.1% |
| SCANNING | 7.555 | 8.891 | 9.038 | 9.054 | 54.1% |
| CONFIRMING | 0.419 | 0.402 | 0.493 | 0.503 | 3.0% |
| TRANSLATING | 4.096 | 5.538 | 6.629 | 6.750 | 29.3% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.787 | 0.905 | 0.995 | 1.005 | 5.6% |
| CLEARING_COSTMAPS | 0.002 | 0.002 | 0.002 | 0.002 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 1.1% |
| SERVICE/CLI_UNACCOUNTED | 0.797 | 0.328 | 1.599 | 1.740 | 5.7% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 1.888 | 1.886 | 1.893 | 1.894 |
| Pause physics | 1.392 | 1.389 | 1.402 | 1.403 |
| Teleport | 0.322 | 0.272 | 0.411 | 0.427 |
| Verify Gazebo pose | 0.429 | 0.431 | 0.470 | 0.474 |
| Unpause physics | 0.990 | 1.318 | 1.326 | 1.327 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.006 | 0.933 | 1.171 | 1.198 |
| Post-test stop | 2.316 | 2.513 | 2.538 | 2.541 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 1.014 | 0.904 | 1.218 | 1.253 |
| Capture AMCL pose | 1.164 | 1.192 | 1.400 | 1.423 |
| Capture quality | 1.039 | 0.928 | 1.229 | 1.262 |
| Capture velocity | 0.898 | 0.899 | 0.900 | 0.900 |
| Cleanup unpause | 1.477 | 1.384 | 2.588 | 2.722 |
| Cleanup stop | 2.057 | 1.896 | 2.339 | 2.388 |
| Whole test case | 35.228 | 40.071 | 40.282 | 40.306 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
