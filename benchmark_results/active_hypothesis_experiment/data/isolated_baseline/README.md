# Global relocalization timing benchmark

- Started: 2026-10-30T23:14:46.340213+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| isolated_ambiguous_room | 1 | success | 4.847 | 5.700 | 0.156 | 0.017 | 2.464 | 0.101 | 0.000 | 0.452 | 0.102 | 0.003 | 0.151 | 1 | 0.0555 |
| isolated_ambiguous_room | 2 | success | 3.817 | 5.000 | 0.154 | 0.018 | 1.456 | 0.101 | 0.000 | 0.453 | 0.102 | 0.002 | 0.151 | 1 | 0.0629 |
| isolated_ambiguous_room | 3 | success | 4.618 | 5.800 | 0.153 | 0.017 | 2.916 | 0.153 | 0.000 | 0.452 | 0.203 | 0.003 | 0.151 | 1 | 0.0634 |

## Recovery summary

- Success rate: 3/3.
- Successful service wall time: mean 4.43 s, P50 4.62 s, P95 4.82 s, max 4.85 s.
- Successful position error: mean 0.061 m, max 0.063 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| isolated_ambiguous_room | 3/3 | 4.427 | 4.618 | 4.824 | 4.847 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.154 | 0.154 | 0.156 | 0.156 | 3.5% |
| INITIALIZING | 0.017 | 0.017 | 0.018 | 0.018 | 0.4% |
| SCANNING | 2.279 | 2.464 | 2.871 | 2.916 | 51.5% |
| CONFIRMING | 0.118 | 0.101 | 0.148 | 0.153 | 2.7% |
| TRANSLATING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.452 | 0.452 | 0.453 | 0.453 | 10.2% |
| VERIFYING_STATIONARY | 0.136 | 0.102 | 0.193 | 0.203 | 3.1% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.1% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 3.4% |
| SEARCHING_HYPOTHESES | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| COMPARING_HYPOTHESES | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| PLANNING_INFORMATION | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TURNING_FOR_INFORMATION | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| SEEDING_AMCL | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| SERVICE/CLI_UNACCOUNTED | 1.117 | 1.381 | 1.399 | 1.401 | 25.2% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.445 | 2.405 | 2.524 | 2.537 |
| Pause physics | 0.680 | 0.326 | 1.287 | 1.394 |
| Teleport | 0.276 | 0.261 | 0.302 | 0.307 |
| Verify Gazebo pose | 0.397 | 0.396 | 0.405 | 0.406 |
| Unpause physics | 1.741 | 1.467 | 2.288 | 2.379 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.077 | 1.186 | 1.186 | 1.186 |
| Post-test stop | 2.770 | 2.537 | 3.287 | 3.370 |
| Post-test settle | 0.500 | 0.500 | 0.501 | 0.501 |
| Capture odometry pose | 0.987 | 0.886 | 1.173 | 1.205 |
| Capture AMCL pose | 1.197 | 1.189 | 1.489 | 1.522 |
| Capture quality | 1.294 | 1.177 | 1.501 | 1.537 |
| Capture velocity | 1.360 | 1.342 | 1.524 | 1.544 |
| Cleanup unpause | 1.012 | 1.332 | 1.377 | 1.382 |
| Cleanup stop | 2.439 | 2.390 | 2.523 | 2.538 |
| Whole test case | 26.022 | 25.345 | 28.007 | 28.303 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
