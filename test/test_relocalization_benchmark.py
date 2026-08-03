import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "benchmark_global_relocalization.py"
)
SPEC = importlib.util.spec_from_file_location(
    "benchmark_global_relocalization",
    SCRIPT_PATH,
)
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)


def event(run_id, index, state, wall, sim, **extra):
    return {
        "schema_version": 2,
        "run_id": run_id,
        "event_index": index,
        "state": state,
        "detail": state.lower(),
        "wall_elapsed_sec": wall,
        "sim_elapsed_sec": sim,
        **extra,
    }


def test_percentile_uses_linear_interpolation():
    assert BENCHMARK.percentile([10, 20, 30], 50) == 20
    assert BENCHMARK.percentile([10, 20], 95) == 19.5
    assert BENCHMARK.percentile([], 50) is None


def test_extract_phase_records_groups_progress_events():
    events = [
        event(4, 1, "PREPARING", 0.0, 0.0),
        event(4, 2, "INITIALIZING", 1.0, 1.1, attempt=1),
        event(4, 3, "SCANNING", 1.4, 1.5, attempt=1),
        event(4, 4, "SCANNING", 2.0, 2.2, attempt=1),
        event(4, 5, "CONFIRMING", 3.0, 3.3, attempt=1),
        event(4, 6, "STOPPING_ATTEMPT", 3.2, 3.5, attempt=1),
        event(4, 7, "FINAL_STOPPING", 4.2, 4.6),
        event(4, 8, "SUCCEEDED", 5.2, 5.7),
    ]

    phases = BENCHMARK.extract_phase_records(events)

    assert [phase["phase"] for phase in phases] == [
        "PREPARING",
        "INITIALIZING",
        "SCANNING",
        "CONFIRMING",
        "STOPPING_ATTEMPT",
        "FINAL_STOPPING",
    ]
    scanning = next(
        phase for phase in phases if phase["phase"] == "SCANNING"
    )
    assert scanning["duration_wall_sec"] == 1.6
    assert scanning["attempt"] == 1


def test_parse_status_log_ignores_latched_previous_run(tmp_path):
    events = [
        event(8, 20, "SUCCEEDED", 12.0, 12.5),
        event(9, 1, "PREPARING", 0.0, 0.0),
        event(9, 2, "SCANNING", 1.0, 1.1, attempt=1),
        event(9, 3, "FAILED", 3.0, 3.2),
    ]
    path = tmp_path / "status.log"
    path.write_text(
        "\n---\n".join(json.dumps(item) for item in events),
        encoding="utf-8",
    )

    parsed, attempts, phases = BENCHMARK.parse_status_log(path)

    assert {item["run_id"] for item in parsed} == {9}
    assert attempts == 1
    assert [phase["phase"] for phase in phases] == [
        "PREPARING",
        "SCANNING",
    ]
