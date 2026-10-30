# Global relocalization timing benchmark

- Started: 2026-10-30T23:16:50.762376+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| isolated_ambiguous_room | 1 | success | 11.696 | 13.200 | 0.304 | 0.000 | 0.000 | 0.000 | 5.870 | 0.000 | 0.103 | 0.003 | 0.151 | 2 | 0.0560 |
| isolated_ambiguous_room | 2 | success | 11.691 | 13.000 | 0.304 | 0.000 | 0.000 | 0.000 | 5.866 | 0.000 | 0.103 | 0.003 | 0.151 | 2 | 0.0469 |
| isolated_ambiguous_room | 3 | success | 11.830 | 13.000 | 0.304 | 0.000 | 0.000 | 0.000 | 5.869 | 0.000 | 0.153 | 0.002 | 0.151 | 2 | 0.0527 |

## Recovery summary

- Success rate: 3/3.
- Successful service wall time: mean 11.74 s, P50 11.70 s, P95 11.82 s, max 11.83 s.
- Successful position error: mean 0.052 m, max 0.056 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| isolated_ambiguous_room | 3/3 | 11.739 | 11.696 | 11.817 | 11.830 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.304 | 0.304 | 0.304 | 0.304 | 2.6% |
| INITIALIZING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| SCANNING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| CONFIRMING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATING | 5.868 | 5.869 | 5.870 | 5.870 | 50.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| VERIFYING_STATIONARY | 0.120 | 0.103 | 0.148 | 0.153 | 1.0% |
| CLEARING_COSTMAPS | 0.003 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.151 | 1.3% |
| SEARCHING_HYPOTHESES | 0.738 | 0.746 | 0.753 | 0.754 | 6.3% |
| COMPARING_HYPOTHESES | 0.028 | 0.011 | 0.058 | 0.063 | 0.2% |
| PLANNING_INFORMATION | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TURNING_FOR_INFORMATION | 3.951 | 3.966 | 3.968 | 3.968 | 33.7% |
| SEEDING_AMCL | 0.256 | 0.256 | 0.256 | 0.256 | 2.2% |
| SERVICE/CLI_UNACCOUNTED | 0.321 | 0.320 | 0.325 | 0.325 | 2.7% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.174 | 2.227 | 2.393 | 2.411 |
| Pause physics | 1.028 | 1.381 | 1.385 | 1.386 |
| Teleport | 0.295 | 0.267 | 0.352 | 0.361 |
| Verify Gazebo pose | 0.478 | 0.454 | 0.520 | 0.527 |
| Unpause physics | 1.359 | 1.378 | 2.281 | 2.381 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.339 | 1.321 | 1.499 | 1.519 |
| Post-test stop | 2.325 | 2.379 | 2.391 | 2.392 |
| Post-test settle | 0.500 | 0.500 | 0.501 | 0.501 |
| Capture odometry pose | 0.896 | 0.901 | 0.910 | 0.911 |
| Capture AMCL pose | 1.405 | 1.496 | 1.522 | 1.525 |
| Capture quality | 1.187 | 1.184 | 1.208 | 1.211 |
| Capture velocity | 1.361 | 1.346 | 1.525 | 1.545 |
| Cleanup unpause | 1.386 | 1.385 | 1.391 | 1.392 |
| Cleanup stop | 2.499 | 2.538 | 2.541 | 2.541 |
| Whole test case | 33.431 | 33.678 | 35.169 | 35.335 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
