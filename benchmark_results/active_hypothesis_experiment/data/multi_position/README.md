# Global relocalization timing benchmark

- Started: 2026-10-30T23:04:29.230414+08:00
- Scenario: Gazebo is paused, `wpb_home` is teleported, Gazebo is resumed, then `/global_relocalization` is called.
- Requested repetitions per location: 3.

| Location | Trial | Result | Service wall (s) | Sim (s) | Prepare | Init | Scan | Confirm | Translate | Attempt stop | Stationary check | Clear maps | Final stop | Attempts | Pos. error (m) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ambiguous_room | 1 | success | 12.783 | 14.000 | 0.304 | 0.000 | 0.000 | 0.000 | 5.765 | 0.000 | 0.103 | 0.002 | 0.151 | 2 | 0.0489 |
| ambiguous_room | 2 | success | 11.826 | 13.000 | 0.303 | 0.000 | 0.000 | 0.000 | 5.863 | 0.000 | 0.103 | 0.002 | 0.151 | 2 | 0.0422 |
| ambiguous_room | 3 | success | 11.881 | 13.400 | 0.305 | 0.000 | 0.000 | 0.000 | 5.862 | 0.000 | 0.104 | 0.003 | 0.151 | 2 | 0.0416 |
| top_left_room | 1 | success | 1.934 | 2.800 | 0.304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.103 | 0.002 | 0.151 | 1 | 0.0454 |
| top_left_room | 2 | success | 2.997 | 4.500 | 0.303 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.102 | 0.002 | 0.151 | 1 | 0.0461 |
| top_left_room | 3 | success | 3.057 | 4.600 | 0.304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.154 | 0.003 | 0.152 | 1 | 0.0474 |
| map_center | 1 | success | 2.261 | 3.100 | 0.304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.204 | 0.003 | 0.151 | 1 | 0.0062 |
| map_center | 2 | success | 3.029 | 4.600 | 0.304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.153 | 0.002 | 0.151 | 1 | 0.0048 |
| map_center | 3 | success | 1.883 | 2.800 | 0.304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.103 | 0.002 | 0.151 | 1 | 0.0096 |
| bottom_right_area | 1 | success | 1.937 | 3.100 | 0.303 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.103 | 0.003 | 0.151 | 1 | 0.0224 |
| bottom_right_area | 2 | success | 1.886 | 3.100 | 0.303 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.103 | 0.003 | 0.151 | 1 | 0.0209 |
| bottom_right_area | 3 | success | 4.871 | 5.700 | 0.304 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.103 | 0.002 | 0.151 | 1 | 0.0201 |

## Recovery summary

- Success rate: 12/12.
- Successful service wall time: mean 5.03 s, P50 3.01 s, P95 12.29 s, max 12.78 s.
- Successful position error: mean 0.030 m, max 0.049 m.

### By location

| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|---:|
| ambiguous_room | 3/3 | 12.163 | 11.881 | 12.693 | 12.783 |
| top_left_room | 3/3 | 2.663 | 2.997 | 3.051 | 3.057 |
| map_center | 3/3 | 2.391 | 2.261 | 2.952 | 3.029 |
| bottom_right_area | 3/3 | 2.898 | 1.937 | 4.578 | 4.871 |

## Algorithm phase breakdown

| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | Mean share of service |
|---|---:|---:|---:|---:|---:|
| PREPARING | 0.304 | 0.304 | 0.304 | 0.305 | 6.0% |
| INITIALIZING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| SCANNING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| CONFIRMING | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TRANSLATING | 1.458 | 0.000 | 5.862 | 5.863 | 29.0% |
| TRANSLATION_SKIPPED | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| STOPPING_ATTEMPT | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| VERIFYING_STATIONARY | 0.120 | 0.103 | 0.176 | 0.204 | 2.4% |
| CLEARING_COSTMAPS | 0.002 | 0.002 | 0.003 | 0.003 | 0.0% |
| FINAL_STOPPING | 0.151 | 0.151 | 0.151 | 0.152 | 3.0% |
| SEARCHING_HYPOTHESES | 0.760 | 0.758 | 0.793 | 0.796 | 15.1% |
| COMPARING_HYPOTHESES | 0.019 | 0.004 | 0.063 | 0.064 | 0.4% |
| PLANNING_INFORMATION | 0.000 | 0.000 | 0.000 | 0.000 | 0.0% |
| TURNING_FOR_INFORMATION | 1.009 | 0.000 | 4.040 | 4.068 | 20.1% |
| SEEDING_AMCL | 0.257 | 0.258 | 0.259 | 0.260 | 5.1% |
| SERVICE/CLI_UNACCOUNTED | 0.950 | 0.447 | 2.274 | 3.331 | 18.9% |

## Harness overhead

| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |
|---|---:|---:|---:|---:|
| Pre-test stop | 2.002 | 1.886 | 2.413 | 2.422 |
| Pause physics | 1.139 | 1.390 | 2.399 | 2.414 |
| Teleport | 0.299 | 0.277 | 0.366 | 0.368 |
| Verify Gazebo pose | 0.455 | 0.438 | 0.542 | 0.558 |
| Unpause physics | 0.935 | 1.341 | 1.396 | 1.396 |
| Settle delay | 2.001 | 2.001 | 2.002 | 2.002 |
| Post-test clock | 1.201 | 1.202 | 1.560 | 1.576 |
| Post-test stop | 2.187 | 2.215 | 2.514 | 2.516 |
| Post-test settle | 0.501 | 0.501 | 0.501 | 0.501 |
| Capture odometry pose | 0.973 | 0.893 | 1.265 | 1.344 |
| Capture AMCL pose | 1.047 | 1.034 | 1.269 | 1.343 |
| Capture quality | 1.083 | 1.179 | 1.215 | 1.217 |
| Capture velocity | 1.148 | 1.195 | 1.433 | 1.542 |
| Cleanup unpause | 0.581 | 0.323 | 1.375 | 1.381 |
| Cleanup stop | 2.002 | 1.890 | 2.308 | 2.415 |
| Whole test case | 24.006 | 22.523 | 31.971 | 32.314 |

## Raw data

- `results.csv`: one wide row per trial, including phase totals.
- `phase_timings.csv`: one row per phase occurrence/attempt.
- `status_*.log`: timestamped state and intermediate quality events.
- `service_*.log`: raw Trigger service responses.
