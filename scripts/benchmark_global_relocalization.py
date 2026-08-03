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
    return next((document for document in documents if document is not None), None)


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
    preparing = next(
        (index for index, event in enumerate(events)
         if event.get("state") == "PREPARING"),
        0,
    )
    events = events[preparing:]
    attempts = []
    for event in events:
        detail = str(event.get("detail", ""))
        match = re.search(r"attempt (\d+)", detail)
        if match:
            attempts.append(int(match.group(1)))
    return events, max(attempts, default=0)


def write_markdown(path, rows, started_at):
    successes = [row for row in rows if row["success"]]
    durations = [float(row["wall_sec"]) for row in successes]
    position_errors = [float(row["position_error_m"]) for row in successes]
    lines = [
        "# Global relocalization baseline benchmark",
        "",
        f"- Started: {started_at}",
        (
            "- Scenario: Gazebo is paused, `wpb_home` is teleported, "
            "Gazebo is resumed, then `/global_relocalization` is called."
        ),
        "- Each location is tested once in this baseline pass.",
        "",
        (
            "| Location | Kidnapped pose (x, y, yaw) | Result | "
            "Wall time (s) | Sim time (s) | Attempts | Translation | "
            "Position error (m) | Yaw error (deg) | Scan score | "
            "Covariance (x, y, yaw) |"
        ),
        "|---|---:|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for row in rows:
        if "wall_sec" not in row:
            lines.append(
                f"| {row['location']} | ({row['target_x']}, {row['target_y']}, "
                f"{row['target_yaw']}) | harness error | - | - | - | - | - | - | - | - |"
            )
            continue
        lines.append(
            "| {location} | ({target_x}, {target_y}, {target_yaw}) | {result} | "
            "{wall_sec} | {sim_sec} | {attempts} | {translation_used} | "
            "{position_error_m} | {yaw_error_deg} | {scan_score} | "
            "({x_variance}, {y_variance}, {yaw_variance}) |".format(
                result="success" if row["success"] else "failure", **row
            )
        )
    lines += ["", "## Summary", ""]
    lines.append(f"- Success rate: {len(successes)}/{len(rows)}.")
    if durations:
        lines.append(
            f"- Successful wall time: mean {sum(durations) / len(durations):.2f} s, "
            f"min {min(durations):.2f} s, max {max(durations):.2f} s."
        )
    if position_errors:
        lines.append(
            f"- Successful position error: mean "
            f"{sum(position_errors) / len(position_errors):.3f} m, "
            f"max {max(position_errors):.3f} m."
        )
    lines += [
        "- `status_*.log` contains every state transition and intermediate quality sample.",
        (
            "- This three-case pass is a baseline for timing work; "
            "repeat trials are needed before claiming a stability percentage."
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def benchmark_case(output_dir, location, target_x, target_y, target_yaw):
    status_path = output_dir / f"status_{location}.log"
    monitor_file = status_path.open("w", encoding="utf-8")
    monitor = None
    try:
        publish_stop()
        call_empty("/pause_physics")
        run(
            [
                "gz", "model", "-m", "wpb_home",
                "-x", str(target_x), "-y", str(target_y), "-z", "0.0",
                "-R", "0.0", "-P", "0.0", "-Y", str(target_yaw),
            ]
        )
        gazebo_pose = run(["gz", "model", "-m", "wpb_home", "-p"]).stdout.strip()
        call_empty("/unpause_physics")
        time.sleep(2.0)

        monitor = subprocess.Popen(
            [
                "ros2", "topic", "echo", "/global_relocalization/status",
                "--field", "data",
            ],
            text=True,
            stdout=monitor_file,
            stderr=subprocess.STDOUT,
        )
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
        sim_end = clock_seconds()
        publish_stop()
        time.sleep(0.5)
        odom_pose = capture_topic("/odom", "pose.pose")
        amcl = capture_topic("/amcl_pose")
        quality_data = capture_topic("/global_relocalization/quality", "data")
        quality = (
            quality_data
            if isinstance(quality_data, dict)
            else json.loads(quality_data)
        )
        twist = capture_topic("/odom", "twist.twist")
    finally:
        if monitor is not None:
            monitor.terminate()
            try:
                monitor.wait(timeout=5)
            except subprocess.TimeoutExpired:
                monitor.kill()
        monitor_file.close()
        try:
            call_empty("/unpause_physics")
        except Exception:
            pass
        try:
            publish_stop()
        except Exception:
            pass

    events, attempts = parse_status_log(status_path)
    translation_used = any(
        event.get("state") == "TRANSLATING" for event in events
    )
    success_match = re.search(r"success=(True|False)", response.stdout)
    message_match = re.search(r"message='(.*?)'\)", response.stdout, re.DOTALL)
    success = bool(success_match and success_match.group(1) == "True")
    message = message_match.group(1) if message_match else response.stdout.strip()

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
    (output_dir / f"service_{location}.log").write_text(
        response.stdout, encoding="utf-8"
    )
    return row


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
    args = parser.parse_args()
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
    for location, x, y, yaw in selected_poses:
        print(f"START {location}: ({x}, {y}, {yaw})", flush=True)
        try:
            row = benchmark_case(output_dir, location, x, y, yaw)
        except Exception as error:
            row = {
                "location": location,
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
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(output_dir / "README.md", rows, started.isoformat())
    print(f"RESULT_DIR {output_dir.resolve()}", flush=True)


if __name__ == "__main__":
    main()
