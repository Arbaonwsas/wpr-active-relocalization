#!/usr/bin/env python3

"""Dead-man keyboard teleoperation for the WPR robot."""

import math
import tkinter as tk

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class KeyboardHoldController(Node):
    """Publish velocity only while a movement key is held down."""

    MOVEMENT_KEYS = {"w", "s", "a", "d", "q", "e"}
    KEY_RELEASE_DEBOUNCE_MS = 120

    def __init__(self):
        super().__init__("keyboard_hold_ctrl")
        self.publisher = self.create_publisher(Twist, "/cmd_vel", 10)
        self.linear_speed = self.declare_parameter("linear_speed", 0.2).value
        self.angular_speed = self.declare_parameter("angular_speed", 0.4).value
        self.pressed_keys = set()
        self.release_jobs = {}

        self.root = tk.Tk()
        self.root.title("WPR 点动键盘控制")
        self.root.geometry("560x420")
        self.root.resizable(False, False)

        title = tk.Label(
            self.root,
            text="WPR 点动键盘控制",
            font=("Sans", 20, "bold"),
        )
        title.pack(pady=(18, 8))

        instructions = (
            "按住移动，松开立即停止\n\n"
            "W / S：前进 / 后退     A / D：左移 / 右移\n"
            "Q / E：左转 / 右转     Space：立即刹车"
        )
        tk.Label(self.root, text=instructions, font=("Sans", 13)).pack()

        speed_frame = tk.LabelFrame(
            self.root,
            text="速度设置",
            font=("Sans", 12, "bold"),
            padx=12,
            pady=8,
        )
        speed_frame.pack(pady=(16, 4))

        self.linear_speed_var = tk.StringVar(value=f"{self.linear_speed:.2f}")
        self.angular_speed_var = tk.StringVar(value=f"{self.angular_speed:.2f}")

        tk.Label(speed_frame, text="线速度 (m/s)：", font=("Sans", 11)).grid(
            row=0, column=0, padx=5, pady=4, sticky="e"
        )
        self.linear_speed_entry = tk.Entry(
            speed_frame,
            textvariable=self.linear_speed_var,
            width=9,
            justify="center",
            font=("Sans", 11),
        )
        self.linear_speed_entry.grid(row=0, column=1, padx=5, pady=4)

        tk.Label(speed_frame, text="角速度 (rad/s)：", font=("Sans", 11)).grid(
            row=1, column=0, padx=5, pady=4, sticky="e"
        )
        self.angular_speed_entry = tk.Entry(
            speed_frame,
            textvariable=self.angular_speed_var,
            width=9,
            justify="center",
            font=("Sans", 11),
        )
        self.angular_speed_entry.grid(row=1, column=1, padx=5, pady=4)

        tk.Button(
            speed_frame,
            text="应用速度",
            command=self.apply_speeds,
            font=("Sans", 11),
            width=10,
        ).grid(row=0, column=2, rowspan=2, padx=(12, 5), pady=4)

        self.speed_feedback = tk.Label(
            self.root,
            text="可用范围：线速度 0.01–1.00，角速度 0.01–2.00",
            font=("Sans", 10),
            fg="#555555",
        )
        self.speed_feedback.pack()

        self.status = tk.Label(
            self.root,
            text="状态：已停止",
            font=("Sans", 14, "bold"),
            fg="#b00020",
        )
        self.status.pack(pady=14)

        tk.Label(
            self.root,
            text="安全保护：窗口失去焦点或关闭时自动停车",
            font=("Sans", 11),
            fg="#555555",
        ).pack()

        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.bind("<KeyRelease>", self.on_key_release)
        self.root.bind("<FocusOut>", self.on_focus_out)
        self.linear_speed_entry.bind("<Return>", self.apply_speeds)
        self.angular_speed_entry.bind("<Return>", self.apply_speeds)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self.control_loop)
        self.root.after(200, self.root.focus_force)

    def on_key_press(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        key = event.keysym.lower()
        release_job = self.release_jobs.pop(key, None)
        if release_job is not None:
            self.root.after_cancel(release_job)
        if key == "space":
            self.pressed_keys.clear()
            self.publish_stop()
        elif key in self.MOVEMENT_KEYS:
            self.pressed_keys.add(key)

    def on_key_release(self, event):
        if isinstance(event.widget, tk.Entry):
            return
        key = event.keysym.lower()
        if key not in self.MOVEMENT_KEYS:
            return
        old_job = self.release_jobs.pop(key, None)
        if old_job is not None:
            self.root.after_cancel(old_job)
        self.release_jobs[key] = self.root.after(
            self.KEY_RELEASE_DEBOUNCE_MS,
            lambda released_key=key: self.finish_key_release(released_key),
        )

    def finish_key_release(self, key):
        self.release_jobs.pop(key, None)
        self.pressed_keys.discard(key)
        self.publish_command()

    def on_focus_out(self, _event):
        self.pressed_keys.clear()
        self.publish_stop()

    @staticmethod
    def parse_speeds(linear_text, angular_text):
        linear_speed = float(linear_text)
        angular_speed = float(angular_text)
        if not math.isfinite(linear_speed) or not math.isfinite(angular_speed):
            raise ValueError("速度必须是有限数值")
        if not 0.01 <= linear_speed <= 1.0:
            raise ValueError("线速度范围应为 0.01–1.00 m/s")
        if not 0.01 <= angular_speed <= 2.0:
            raise ValueError("角速度范围应为 0.01–2.00 rad/s")
        return linear_speed, angular_speed

    def apply_speeds(self, _event=None):
        try:
            linear_speed, angular_speed = self.parse_speeds(
                self.linear_speed_var.get(), self.angular_speed_var.get()
            )
        except ValueError as error:
            self.speed_feedback.configure(text=f"输入错误：{error}", fg="#b00020")
            return "break"

        self.linear_speed = linear_speed
        self.angular_speed = angular_speed
        self.linear_speed_var.set(f"{linear_speed:.2f}")
        self.angular_speed_var.set(f"{angular_speed:.2f}")
        self.speed_feedback.configure(
            text=(
                f"已应用：线速度 {linear_speed:.2f} m/s，"
                f"角速度 {angular_speed:.2f} rad/s"
            ),
            fg="#00701a",
        )
        self.pressed_keys.clear()
        self.publish_stop()
        self.root.focus_set()
        return "break"

    def command_from_keys(self):
        command = Twist()
        command.linear.x = self.linear_speed * (
            int("w" in self.pressed_keys) - int("s" in self.pressed_keys)
        )
        command.linear.y = self.linear_speed * (
            int("a" in self.pressed_keys) - int("d" in self.pressed_keys)
        )
        command.angular.z = self.angular_speed * (
            int("q" in self.pressed_keys) - int("e" in self.pressed_keys)
        )
        return command

    def publish_command(self):
        command = self.command_from_keys()
        self.publisher.publish(command)

        moving = any(
            (command.linear.x, command.linear.y, command.angular.z)
        )
        if moving:
            self.status.configure(
                text=(
                    "状态：运动中  "
                    f"x={command.linear.x:.1f}  "
                    f"y={command.linear.y:.1f}  "
                    f"yaw={command.angular.z:.1f}"
                ),
                fg="#00701a",
            )
        else:
            self.status.configure(text="状态：已停止", fg="#b00020")

    def publish_stop(self):
        self.publisher.publish(Twist())
        try:
            self.status.configure(text="状态：已停止", fg="#b00020")
        except tk.TclError:
            pass

    def control_loop(self):
        if not rclpy.ok():
            self.root.destroy()
            return
        rclpy.spin_once(self, timeout_sec=0.0)
        self.publish_command()
        self.root.after(50, self.control_loop)

    def on_close(self):
        self.pressed_keys.clear()
        self.publish_stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main(args=None):
    rclpy.init(args=args)
    controller = KeyboardHoldController()
    try:
        controller.run()
    finally:
        controller.publisher.publish(Twist())
        controller.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
