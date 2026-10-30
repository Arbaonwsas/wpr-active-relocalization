#!/usr/bin/env python3
"""Run repeatable Gazebo kidnapping benchmarks for global relocalization."""

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import re
import subprocess
import time

import yaml


TEST_POSES = (
    ("top_left_room", -3.5, 2.5, 0.0),
    ("map_center", 0.0, 0.0, math.pi / 2.0),
    ("bottom_right_area", 3.5, -1.5, -2.0944),
)

TERMINAL_STATES = {"SUCCEEDED", "FAILED"}
HYPOTHESIS_PHASES = (
    "SEARCHING_HYPOTHESES", "COMPARING_HYPOTHESES", "PLANNING_INFORMATION",
    "TURNING_FOR_INFORMATION", "SEEDING_AMCL",
)
REPORTED_PHASES = (
    "PREPARING",
    "INITIALIZING",
    "SCANNING",
    "CONFIRMING",
    "TRANSLATING",
    "TRANSLATION_SKIPPED",
    "STOPPING_ATTEMPT",
    "VERIFYING_STATIONARY",
    "CLEARING_COSTMAPS",
    "FINAL_STOPPING",
) + HYPOTHESIS_PHASES
RUN_TABLE_PHASES = tuple(
    state for state in REPORTED_PHASES
    if state != "TRANSLATION_SKIPPED" and state not in HYPOTHESIS_PHASES
)


def run(command, timeout=30, check=True):
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}"
        )
    return result


def first_yaml_document(output):
    documents = list(yaml.safe_load_all(output))
    return next(
        (document for document in documents if document is not None),
        None,
    )


def capture_topic(topic, field=None, timeout=10):
    command = ["ros2", "topic", "echo", topic, "--once"]
    if topic in ("/clock", "/odom"):
        command += ["--qos-reliability", "best_effort"]
    if field:
        command += ["--field", field]
    result = run(command, timeout=timeout)
    return first_yaml_document(result.stdout)


def clock_seconds():
    clock = capture_topic("/clock", "clock")
    return float(clock["sec"]) + float(clock["nanosec"]) * 1.0e-9


def publish_stop():
    run(
        [
            "ros2",
            "topic",
            "pub",
            "--rate",
            "20",
            "--times",
            "20",
            "/cmd_vel",
            "geometry_msgs/msg/Twist",
            "{}",
        ],
        timeout=8,
    )


def call_empty(service, attempts=3):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            run(
                [
                    "ros2", "service", "call", service,
                    "std_srvs/srv/Empty", "{}",
                ],
                timeout=15,
            )
            return
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(1.0)
    raise RuntimeError(
        f"{service} failed after {attempts} attempts: {last_error}"
    )


def yaw_from_orientation(orientation):
    x = float(orientation["x"])
    y = float(orientation["y"])
    z = float(orientation["z"])
    w = float(orientation["w"])
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )


def angle_error(first, second):
    return abs(math.atan2(math.sin(first - second), math.cos(first - second)))


def percentile(values, percentage):
    """Return a linearly interpolated percentile for a numeric sequence."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentage / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def extract_phase_records(events):
    """Convert timestamped state transitions into phase intervals."""
    timed_events = [
        event for event in events
        if "wall_elapsed_sec" in event and "sim_elapsed_sec" in event
    ]
    if not timed_events:
        return []

    groups = []
    for event in timed_events:
        state = str(event.get("state", "UNKNOWN"))
        if groups and groups[-1]["state"] == state:
            groups[-1]["events"].append(event)
        else:
            groups.append({"state": state, "events": [event]})

    occurrences = {}
    records = []
    for index, group in enumerate(groups):
        state = group["state"]
        if state in TERMINAL_STATES or index + 1 >= len(groups):
            continue
        start = group["events"][0]
        end = groups[index + 1]["events"][0]
        occurrences[state] = occurrences.get(state, 0) + 1
        records.append(
            {
                "phase": state,
                "occurrence": occurrences[state],
                "attempt": start.get("attempt", ""),
                "detail": start.get("detail", ""),
                "start_wall_sec": float(start["wall_elapsed_sec"]),
                "end_wall_sec": float(end["wall_elapsed_sec"]),
                "duration_wall_sec": round(
                    max(
                        0.0,
                        float(end["wall_elapsed_sec"])
                        - float(start["wall_elapsed_sec"]),
                    ),
                    6,
                ),
                "start_sim_sec": float(start["sim_elapsed_sec"]),
                "end_sim_sec": float(end["sim_elapsed_sec"]),
                "duration_sim_sec": round(
                    max(
                        0.0,
                        float(end["sim_elapsed_sec"])
                        - float(start["sim_elapsed_sec"]),
                    ),
                    6,
                ),
            }
        )
    return records


def parse_status_log(path):
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    preparing_events = [
        index for index, event in enumerate(events)
        if event.get("state") == "PREPARING"
    ]
    preparing = preparing_events[-1] if preparing_events else 0
    events = events[preparing:]
    if events and events[0].get("run_id") is not None:
        run_id = events[0]["run_id"]
        events = [event for event in events if event.get("run_id") == run_id]
    attempts = []
    for event in events:
        if event.get("attempt") is not None:
            attempts.append(int(event["attempt"]))
        detail = str(event.get("detail", ""))
        match = re.search(r"attempt (\d+)", detail)
        if match:
            attempts.append(int(match.group(1)))
    return events, max(attempts, default=0), extract_phase_records(events)


def numeric_summary(values):
    values = [float(value) for value in values]
    if not values:
        return None
    return {
        "mean": sum(values) / len(values),
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "max": max(values),
    }


def phase_field(state, clock="wall"):
    return f"phase_{state.lower()}_{clock}_sec"


def format_summary(summary):
    if summary is None:
        return ("-", "-", "-", "-")
    return tuple(
        f"{summary[key]:.3f}" for key in ("mean", "p50", "p95", "max")
    )


def write_markdown(path, rows, started_at, repetitions):
    successes = [row for row in rows if row["success"]]
    durations = [float(row["wall_sec"]) for row in successes]
    position_errors = [float(row["position_error_m"]) for row in successes]
    lines = [
        "# Global relocalization timing benchmark",
        "",
        f"- Started: {started_at}",
        (
            "- Scenario: Gazebo is paused, `wpb_home` is teleported, "
            "Gazebo is resumed, then `/global_relocalization` is called."
        ),
        f"- Requested repetitions per location: {repetitions}.",
        "",
        (
            "| Location | Trial | Result | Service wall (s) | Sim (s) | "
            "Prepare | Init | Scan | Confirm | Translate | Attempt stop | "
            "Stationary check | Clear maps | Final stop | Attempts | "
            "Pos. error (m) |"
        ),
        (
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"
            "---:|---:|---:|---:|---:|"
        ),
    ]
    for row in rows:
        if "wall_sec" not in row:
            lines.append(
                f"| {row['location']} | {row['trial']} | harness error | "
                "- | - | - | - | - | - | - | - | - | - | - | - | "
                "- |"
            )
            continue
        phase_values = [
            row.get(phase_field(state), "0.000")
            for state in RUN_TABLE_PHASES
        ]
        lines.append(
            f"| {row['location']} | {row['trial']} | "
            f"{'success' if row['success'] else 'failure'} | "
            f"{row['wall_sec']} | {row['sim_sec']} | "
            + " | ".join(phase_values)
            + f" | {row['attempts']} | {row['position_error_m']} |"
        )
    lines += ["", "## Recovery summary", ""]
    lines.append(f"- Success rate: {len(successes)}/{len(rows)}.")
    if durations:
        duration_summary = numeric_summary(durations)
        lines.append(
            "- Successful service wall time: mean "
            f"{duration_summary['mean']:.2f} s, "
            f"P50 {duration_summary['p50']:.2f} s, "
            f"P95 {duration_summary['p95']:.2f} s, "
            f"max {duration_summary['max']:.2f} s."
        )
    if position_errors:
        lines.append(
            f"- Successful position error: mean "
            f"{sum(position_errors) / len(position_errors):.3f} m, "
            f"max {max(position_errors):.3f} m."
        )
    lines += ["", "### By location", ""]
    lines += [
        "| Location | Success | Mean (s) | P50 (s) | P95 (s) | Max (s) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for location, *_ in TEST_POSES:
        location_rows = [row for row in rows if row["location"] == location]
        successful_rows = [row for row in location_rows if row["success"]]
        summary = numeric_summary(
            row["wall_sec"] for row in successful_rows
        )
        mean, p50, p95, maximum = format_summary(summary)
        lines.append(
            f"| {location} | {len(successful_rows)}/{len(location_rows)} | "
            f"{mean} | {p50} | {p95} | {maximum} |"
        )

    complete_rows = [row for row in rows if "wall_sec" in row]
    service_mean = numeric_summary(
        row["wall_sec"] for row in complete_rows
    )
    lines += ["", "## Algorithm phase breakdown", ""]
    lines += [
        "| Phase | Mean (s) | P50 (s) | P95 (s) | Max (s) | "
        "Mean share of service |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for state in REPORTED_PHASES:
        field = phase_field(state)
        summary = numeric_summary(
            row.get(field, 0.0) for row in complete_rows
        )
        mean, p50, p95, maximum = format_summary(summary)
        share = 0.0
        if summary and service_mean and service_mean["mean"] > 0.0:
            share = 100.0 * summary["mean"] / service_mean["mean"]
        lines.append(
            f"| {state} | {mean} | {p50} | {p95} | {maximum} | "
            f"{share:.1f}% |"
        )
    overhead_summary = numeric_summary(
        row.get("service_unaccounted_wall_sec", 0.0)
        for row in complete_rows
    )
    mean, p50, p95, maximum = format_summary(overhead_summary)
    overhead_share = 0.0
    if overhead_summary and service_mean and service_mean["mean"] > 0.0:
        overhead_share = (
            100.0 * overhead_summary["mean"] / service_mean["mean"]
        )
    lines.append(
        f"| SERVICE/CLI_UNACCOUNTED | {mean} | {p50} | {p95} | "
        f"{maximum} | {overhead_share:.1f}% |"
    )

    lines += ["", "## Harness overhead", ""]
    lines += [
        "| Operation | Mean (s) | P50 (s) | P95 (s) | Max (s) |",
        "|---|---:|---:|---:|---:|",
    ]
    harness_fields = (
        ("Pre-test stop", "harness_pre_stop_wall_sec"),
        ("Pause physics", "harness_pause_wall_sec"),
        ("Teleport", "harness_teleport_wall_sec"),
        ("Verify Gazebo pose", "harness_pose_verify_wall_sec"),
        ("Unpause physics", "harness_unpause_wall_sec"),
        ("Settle delay", "harness_settle_wall_sec"),
        ("Post-test clock", "harness_post_clock_wall_sec"),
        ("Post-test stop", "harness_post_stop_wall_sec"),
        ("Post-test settle", "harness_post_settle_wall_sec"),
        ("Capture odometry pose", "harness_capture_odom_wall_sec"),
        ("Capture AMCL pose", "harness_capture_amcl_wall_sec"),
        ("Capture quality", "harness_capture_quality_wall_sec"),
        ("Capture velocity", "harness_capture_twist_wall_sec"),
        ("Cleanup unpause", "harness_cleanup_unpause_wall_sec"),
        ("Cleanup stop", "harness_cleanup_stop_wall_sec"),
        ("Whole test case", "harness_total_wall_sec"),
    )
    for label, field in harness_fields:
        summary = numeric_summary(
            row[field] for row in complete_rows if field in row
        )
        mean, p50, p95, maximum = format_summary(summary)
        lines.append(
            f"| {label} | {mean} | {p50} | {p95} | {maximum} |"
        )

    failures = [row for row in complete_rows if not row["success"]]
    if failures:
        lines += ["", "## Failures", ""]
        for row in failures:
            lines.append(
                f"- {row['location']} trial {row['trial']}: "
                f"last phase `{row.get('last_phase', 'unknown')}`; "
                f"{row['message']}"
            )

    lines += [
        "",
        "## Raw data",
        "",
        "- `results.csv`: one wide row per trial, including phase totals.",
        "- `phase_timings.csv`: one row per phase occurrence/attempt.",
        "- `status_*.log`: timestamped state and intermediate quality events.",
        "- `service_*.log`: raw Trigger service responses.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def benchmark_case(
    output_dir,
    location,
    trial,
    target_x,
    target_y,
    target_yaw,
):
    suffix = f"{location}_trial_{trial:02d}"
    status_path = output_dir / f"status_{suffix}.log"
    monitor_file = status_path.open("w", encoding="utf-8")
    monitor = None
    harness = {}
    case_start = time.monotonic()
    try:
        stage_start = time.monotonic()
        publish_stop()
        harness["harness_pre_stop_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        call_empty("/pause_physics")
        harness["harness_pause_wall_sec"] = time.monotonic() - stage_start

        stage_start = time.monotonic()
        run(
            [
                "gz", "model", "-m", "wpb_home",
                "-x", str(target_x), "-y", str(target_y), "-z", "0.0",
                "-R", "0.0", "-P", "0.0", "-Y", str(target_yaw),
            ]
        )
        harness["harness_teleport_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        gazebo_pose = run(
            ["gz", "model", "-m", "wpb_home", "-p"]
        ).stdout.strip()
        harness["harness_pose_verify_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        call_empty("/unpause_physics")
        harness["harness_unpause_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        time.sleep(2.0)
        harness["harness_settle_wall_sec"] = (
            time.monotonic() - stage_start
        )

        monitor = subprocess.Popen(
            [
                "ros2", "topic", "echo", "/global_relocalization/status",
                "--field", "data",
            ],
            text=True,
            stdout=monitor_file,
            stderr=subprocess.STDOUT,
        )
        # Allow the CLI subscriber to match the transient-local publisher
        # before the fast recovery service emits PREPARING.
        time.sleep(0.2)
        sim_start = clock_seconds()
        wall_start = time.monotonic()
        response = run(
            [
                "ros2", "service", "call", "/global_relocalization",
                "std_srvs/srv/Trigger", "{}",
            ],
            timeout=390,
            check=False,
        )
        wall_duration = time.monotonic() - wall_start

        stage_start = time.monotonic()
        sim_end = clock_seconds()
        harness["harness_post_clock_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        publish_stop()
        harness["harness_post_stop_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        time.sleep(0.5)
        harness["harness_post_settle_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        odom_pose = capture_topic("/odom", "pose.pose")
        harness["harness_capture_odom_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        amcl = capture_topic("/amcl_pose")
        harness["harness_capture_amcl_wall_sec"] = (
            time.monotonic() - stage_start
        )

        stage_start = time.monotonic()
        quality_data = capture_topic("/global_relocalization/quality", "data")
        harness["harness_capture_quality_wall_sec"] = (
            time.monotonic() - stage_start
        )
        quality = (
            quality_data
            if isinstance(quality_data, dict)
            else json.loads(quality_data)
        )

        stage_start = time.monotonic()
        twist = capture_topic("/odom", "twist.twist")
        harness["harness_capture_twist_wall_sec"] = (
            time.monotonic() - stage_start
        )
    finally:
        if monitor is not None:
            monitor.terminate()
            try:
                monitor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                monitor.kill()
        monitor_file.close()
        try:
            stage_start = time.monotonic()
            call_empty("/unpause_physics")
            harness["harness_cleanup_unpause_wall_sec"] = (
                time.monotonic() - stage_start
            )
        except Exception:
            pass
        try:
            stage_start = time.monotonic()
            publish_stop()
            harness["harness_cleanup_stop_wall_sec"] = (
                time.monotonic() - stage_start
            )
        except Exception:
            pass

    harness["harness_total_wall_sec"] = time.monotonic() - case_start
    events, attempts, phase_records = parse_status_log(status_path)
    translation_used = any(
        event.get("state") == "TRANSLATING" for event in events
    )
    informative_moves = sum(
        event.get("state") == "PLANNING_INFORMATION" for event in events
    )
    success_match = re.search(r"success=(True|False)", response.stdout)
    message_match = re.search(
        r"message='(.*?)'\)",
        response.stdout,
        re.DOTALL,
    )
    success = bool(success_match and success_match.group(1) == "True")
    message = (
        message_match.group(1)
        if message_match
        else response.stdout.strip()
    )

    odom_position = odom_pose["position"]
    odom_yaw = yaw_from_orientation(odom_pose["orientation"])
    amcl_pose = amcl["pose"]["pose"]
    amcl_position = amcl_pose["position"]
    amcl_yaw = yaw_from_orientation(amcl_pose["orientation"])
    covariance = amcl["pose"]["covariance"]
    position_error = math.hypot(
        float(odom_position["x"]) - float(amcl_position["x"]),
        float(odom_position["y"]) - float(amcl_position["y"]),
    )
    yaw_error_deg = math.degrees(angle_error(odom_yaw, amcl_yaw))
    linear = twist["linear"]
    angular = twist["angular"]
    final_speed = math.sqrt(
        float(linear["x"]) ** 2
        + float(linear["y"]) ** 2
        + float(linear["z"]) ** 2
        + float(angular["x"]) ** 2
        + float(angular["y"]) ** 2
        + float(angular["z"]) ** 2
    )

    row = {
        "location": location,
        "trial": trial,
        "target_x": f"{target_x:.3f}",
        "target_y": f"{target_y:.3f}",
        "target_yaw": f"{target_yaw:.4f}",
        "gazebo_pose_after_teleport": gazebo_pose,
        "success": success,
        "message": message,
        "wall_sec": f"{wall_duration:.3f}",
        "sim_sec": f"{sim_end - sim_start:.3f}",
        "attempts": attempts,
        "translation_used": translation_used,
        "informative_moves": informative_moves,
        "odom_x": f"{float(odom_position['x']):.6f}",
        "odom_y": f"{float(odom_position['y']):.6f}",
        "odom_yaw": f"{odom_yaw:.6f}",
        "amcl_x": f"{float(amcl_position['x']):.6f}",
        "amcl_y": f"{float(amcl_position['y']):.6f}",
        "amcl_yaw": f"{amcl_yaw:.6f}",
        "position_error_m": f"{position_error:.4f}",
        "yaw_error_deg": f"{yaw_error_deg:.3f}",
        "scan_score": f"{float(quality['scan_score']):.4f}",
        "beams_used": quality["beams_used"],
        "in_map_fraction": f"{float(quality['in_map_fraction']):.4f}",
        "x_variance": f"{float(covariance[0]):.4f}",
        "y_variance": f"{float(covariance[7]):.4f}",
        "yaw_variance": f"{float(covariance[35]):.4f}",
        "final_speed_norm": f"{final_speed:.6f}",
    }
    for field, value in harness.items():
        row[field] = f"{value:.3f}"

    for state in REPORTED_PHASES:
        wall_total = sum(
            record["duration_wall_sec"]
            for record in phase_records
            if record["phase"] == state
        )
        sim_total = sum(
            record["duration_sim_sec"]
            for record in phase_records
            if record["phase"] == state
        )
        row[phase_field(state)] = f"{wall_total:.3f}"
        row[phase_field(state, 'sim')] = f"{sim_total:.3f}"

    terminal_events = [
        event for event in events
        if event.get("state") in TERMINAL_STATES
    ]
    reported_wall = (
        float(terminal_events[-1].get("wall_elapsed_sec", 0.0))
        if terminal_events else 0.0
    )
    reported_sim = (
        float(terminal_events[-1].get("sim_elapsed_sec", 0.0))
        if terminal_events else 0.0
    )
    row["node_reported_wall_sec"] = f"{reported_wall:.3f}"
    row["node_reported_sim_sec"] = f"{reported_sim:.3f}"
    row["service_unaccounted_wall_sec"] = (
        f"{max(0.0, wall_duration - reported_wall):.3f}"
    )
    row["last_phase"] = (
        phase_records[-1]["phase"] if phase_records else "unknown"
    )

    for record in phase_records:
        record["location"] = location
        record["trial"] = trial

    (output_dir / f"service_{suffix}.log").write_text(
        response.stdout, encoding="utf-8"
    )
    return row, phase_records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for CSV, Markdown, and raw logs",
    )
    parser.add_argument(
        "--location",
        action="append",
        choices=[pose[0] for pose in TEST_POSES],
        help="Run only this location; repeat the option to select several",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=1,
        help="Number of trials for every selected location (default: 1)",
    )
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    started = datetime.now().astimezone()
    output_dir = args.output_dir or (
        Path("benchmark_results") / started.strftime("%Y-%m-%d_%H-%M-%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    selected_poses = [
        pose for pose in TEST_POSES
        if not args.location or pose[0] in args.location
    ]
    rows = []
    phase_rows = []
    for location, x, y, yaw in selected_poses:
        for trial in range(1, args.repetitions + 1):
            print(
                f"START {location} trial {trial}/{args.repetitions}: "
                f"({x}, {y}, {yaw})",
                flush=True,
            )
            try:
                row, trial_phases = benchmark_case(
                    output_dir,
                    location,
                    trial,
                    x,
                    y,
                    yaw,
                )
                phase_rows.extend(trial_phases)
            except Exception as error:
                row = {
                    "location": location,
                    "trial": trial,
                    "target_x": f"{x:.3f}",
                    "target_y": f"{y:.3f}",
                    "target_yaw": f"{yaw:.4f}",
                    "success": False,
                    "message": f"benchmark harness error: {error}",
                }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

    fieldnames = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with (output_dir / "results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    phase_fieldnames = (
        "location",
        "trial",
        "phase",
        "occurrence",
        "attempt",
        "detail",
        "start_wall_sec",
        "end_wall_sec",
        "duration_wall_sec",
        "start_sim_sec",
        "end_sim_sec",
        "duration_sim_sec",
    )
    with (output_dir / "phase_timings.csv").open(
        "w", newline="", encoding="utf-8"
    ) as phase_file:
        writer = csv.DictWriter(
            phase_file,
            fieldnames=phase_fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(phase_rows)

    write_markdown(
        output_dir / "README.md",
        rows,
        started.isoformat(),
        args.repetitions,
    )
    print(f"RESULT_DIR {output_dir.resolve()}", flush=True)


if __name__ == "__main__":
    main()
