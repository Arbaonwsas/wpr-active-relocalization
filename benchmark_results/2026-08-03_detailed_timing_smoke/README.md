# Global relocalization timing benchmark

- Started: 2026-08-03T18:38:40.183242+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 1.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| map_center | 1 | success | 15.549 | 16.900 | 0.504 | 0.019 | 10.800 | 0.804 | 0.000 | 1.004 | 0.003 | 1.003 | 1 | 0.0611 |

## Recovery summary

- Success rate: 1/1.
- Successful service wall time: mean 15.55 s, P50 15.55 s, P95 15.55 s, max 15.55 s.
- Successful position error: mean 0.061 m, max 0.061 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 0/0 | - | - | - | - |
| map_center | 1/1 | 15.549 | 15.549 | 15.549 | 15.549 |
| bottom_right_area | 0/0 | - | - | - | - |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.504 | 0.504 | 0.504 | 0.504 | 3.2% |
| INITIALIZING | 0.019 | 0.019 | 0.019 | 0.019 | 0.1% |
| SCANNING | 10.800 | 10.800 | 10.800 | 10.800 | 69.5% |
| CONFIRMING | 0.804 | 0.804 | 0.804 | 0.804 | 5.2% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 1.004 | 1.004 | 1.004 | 1.004 | 6.5% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 1.003 | 1.003 | 1.003 | 1.003 | 6.5% |
| SERVICE/CLI_UNACCOUNTED | 1.411 | 1.411 | 1.411 | 1.411 | 9.1% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.420 | 2.420 | 2.420 | 2.420 |
| Pause physics | 0.325 | 0.325 | 0.325 | 0.325 |
| Teleport | 0.315 | 0.315 | 0.315 | 0.315 |
| Verify Gazebo pose | 0.541 | 0.541 | 0.541 | 0.541 |
| Unpause physics | 1.322 | 1.322 | 1.322 | 1.322 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.359 | 1.359 | 1.359 | 1.359 |
| Post-test stop | 1.894 | 1.894 | 1.894 | 1.894 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 1.351 | 1.351 | 1.351 | 1.351 |
| Capture AMCL pose | 0.883 | 0.883 | 0.883 | 0.883 |
| Capture quality | 0.870 | 0.870 | 0.870 | 0.870 |
| Capture velocity | 1.249 | 1.249 | 1.249 | 1.249 |
| Cleanup unpause | 0.332 | 0.332 | 0.332 | 0.332 |
| Cleanup stop | 1.892 | 1.892 | 1.892 | 1.892 |
| Whole test case | 34.314 | 34.314 | 34.314 | 34.314 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
