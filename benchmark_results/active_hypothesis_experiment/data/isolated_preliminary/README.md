# Global relocalization timing benchmark

- Started: 2026-10-30T23:10:04.888095+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| isolated_ambiguous_room | 1 | success | 17.228 | 18.100 | 0.305 | 0.000 | 0.000 | 0.000 | 10.067 | 0.000 | 0.204 | 0.003 | 0.152 | 3 | 0.0547 |
| isolated_ambiguous_room | 2 | failure | 16.880 | 17.700 | 0.305 | 0.000 | 0.000 | 0.000 | 6.861 | 0.000 | 0.000 | 0.000 | 0.151 | 0 | 1.4090 |
| isolated_ambiguous_room | 3 | success | 12.972 | 14.300 | 0.304 | 0.000 | 0.000 | 0.000 | 5.820 | 0.000 | 0.203 | 0.003 | 0.152 | 2 | 0.0461 |

## Recovery summary

- Success rate: 2/3.
- Successful service wall time: mean 15.10 s, P50 15.10 s, P95 17.02 s, max 17.23 s.
- Successful position error: mean 0.050 m, max 0.055 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| isolated_ambiguous_room | 2/3 | 15.100 | 15.100 | 17.015 | 17.228 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.305 | 0.305 | 0.305 | 0.305 | 1.9% |
| INITIALIZING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| SCANNING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| CONFIRMING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATING | 7.583 | 6.861 | 9.746 | 10.067 | 48.3% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| VERIFYING_STATIONARY | 0.136 | 0.203 | 0.204 | 0.204 | 0.9% |
| CLEARING_COSTMAPS | 0.002 | 0.003 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.152 | 0.152 | 0.152 | 0.152 | 1.0% |
| SEARCHING_HYPOTHESES | 0.760 | 0.760 | 0.761 | 0.761 | 4.8% |
| COMPARING_HYPOTHESES | 0.050 | 0.062 | 0.067 | 0.067 | 0.3% |
| PLANNING_INFORMATION | 0.001 | 0.001 | 0.001 | 0.001 | 0.0% |
| TURNING_FOR_INFORMATION | 5.171 | 4.066 | 7.049 | 7.380 | 32.9% |
| SEEDING_AMCL | 0.138 | 0.207 | 0.208 | 0.208 | 0.9% |
| SERVICE/CLI_UNACCOUNTED | 1.397 | 1.396 | 1.401 | 1.401 | 8.9% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.067 | 1.894 | 2.369 | 2.422 |
| Pause physics | 1.038 | 1.393 | 1.403 | 1.404 |
| Teleport | 0.259 | 0.261 | 0.264 | 0.264 |
| Verify Gazebo pose | 0.493 | 0.487 | 0.513 | 0.516 |
| Unpause physics | 1.363 | 1.391 | 2.279 | 2.378 |
| Settle delay | 2.002 | 2.002 | 2.002 | 2.002 |
| Post-test clock | 1.022 | 0.889 | 1.298 | 1.343 |
| Post-test stop | 2.098 | 1.901 | 2.447 | 2.508 |
| Post-test settle | 0.500 | 0.500 | 0.500 | 0.500 |
| Capture odometry pose | 1.006 | 0.904 | 1.187 | 1.218 |
| Capture AMCL pose | 1.376 | 1.407 | 1.515 | 1.527 |
| Capture quality | 0.867 | 0.865 | 0.878 | 0.880 |
| Capture velocity | 1.194 | 1.193 | 1.464 | 1.494 |
| Cleanup unpause | 1.029 | 1.381 | 1.385 | 1.386 |
| Cleanup stop | 2.331 | 2.402 | 2.675 | 2.705 |
| Whole test case | 35.841 | 37.047 | 37.706 | 37.779 |

## Failures

- isolated_ambiguous_room trial 2: last phase `FINAL_STOPPING`; pose ambiguity remains after bounded informative exploration

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
