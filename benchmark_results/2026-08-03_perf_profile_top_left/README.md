# Global relocalization timing benchmark

- Started: 2026-08-03T18:53:37.443004+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 1.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top_left_room | 1 | success | 14.725 | 15.600 | 0.152 | 0.017 | 9.446 | 0.403 | 3.275 | 0.954 | 0.003 | 0.151 | 2 | 0.0710 |

## Recovery summary

- Success rate: 1/1.
- Successful service wall time: mean 14.72 s, P50 14.72 s, P95 14.72 s, max 14.72 s.
- Successful position error: mean 0.071 m, max 0.071 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| top_left_room | 1/1 | 14.725 | 14.725 | 14.725 | 14.725 |
| map_center | 0/0 | - | - | - | - |
| bottom_right_area | 0/0 | - | - | - | - |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.152 | 0.152 | 0.152 | 0.152 | 1.0% |
| INITIALIZING | 0.017 | 0.017 | 0.017 | 0.017 | 0.1% |
| SCANNING | 9.446 | 9.446 | 9.446 | 9.446 | 64.1% |
| CONFIRMING | 0.403 | 0.403 | 0.403 | 0.403 | 2.7% |
| TRANSLATING | 3.275 | 3.275 | 3.275 | 3.275 | 22.2% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.954 | 0.954 | 0.954 | 0.954 | 6.5% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 1.0% |
| SERVICE/CLI_UNACCOUNTED | 0.325 | 0.325 | 0.325 | 0.325 | 2.2% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 1.889 | 1.889 | 1.889 | 1.889 |
| Pause physics | 1.321 | 1.321 | 1.321 | 1.321 |
| Teleport | 0.267 | 0.267 | 0.267 | 0.267 |
| Verify Gazebo pose | 0.438 | 0.438 | 0.438 | 0.438 |
| Unpause physics | 2.376 | 2.376 | 2.376 | 2.376 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 0.894 | 0.894 | 0.894 | 0.894 |
| Post-test stop | 2.542 | 2.542 | 2.542 | 2.542 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 0.902 | 0.902 | 0.902 | 0.902 |
| Capture AMCL pose | 0.868 | 0.868 | 0.868 | 0.868 |
| Capture quality | 0.887 | 0.887 | 0.887 | 0.887 |
| Capture velocity | 1.446 | 1.446 | 1.446 | 1.446 |
| Cleanup unpause | 1.386 | 1.386 | 1.386 | 1.386 |
| Cleanup stop | 1.887 | 1.887 | 1.887 | 1.887 |
| Whole test case | 35.656 | 35.656 | 35.656 | 35.656 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
