"""
Laser-only pose candidates and bounded, informative recovery actions.

Absolute odometry and simulation truth are deliberately absent from this module.
All action offsets and odometry increments are expressed in the robot frame.
"""

from dataclasses import dataclass
import math

import numpy as np

from .relocalization_core import normalize_angle


@dataclass(frozen=True)
class Hypothesis:
    """A distinct map pose and its latest laser endpoint likelihood."""

    x: float
    y: float
    yaw: float
    score: float

    @property
    def pose(self):
        """Return the SE(2) pose without its observation score."""
        return (self.x, self.y, self.yaw)


@dataclass(frozen=True)
class InformativeAction:
    """A relative heading, translation, and additional predicted disagreement."""

    heading: float
    distance: float
    gain: float


def advance_pose(pose, delta):
    """Compose SE(2) poses; delta is a relative body-frame displacement."""
    x, y, yaw = pose
    dx, dy, dyaw = delta
    c, s = math.cos(yaw), math.sin(yaw)
    return (x + c * dx - s * dy, y + s * dx + c * dy,
            normalize_angle(yaw + dyaw))


def relative_motion(start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    c, s = math.cos(start[2]), math.sin(start[2])
    return (c * dx + s * dy, -s * dx + c * dy,
            normalize_angle(end[2] - start[2]))


def unique_candidate(hypotheses, mean_scores, margin=0.12):
    """Require both recent and accumulated observations to distinguish modes."""
    if len(hypotheses) < 2:
        return None
    order = np.argsort(mean_scores)[::-1]
    best, runner_up = int(order[0]), int(order[1])
    current = hypotheses[best].score
    competing = max(h.score for i, h in enumerate(hypotheses) if i != best)
    if (current >= 0.72 and current - competing >= margin * 2 / 3
            and mean_scores[best] - mean_scores[runner_up] >= margin):
        return best
    return None


class HypothesisSearch:
    """Coarse-to-fine global scan matching with distinct retained modes."""

    def __init__(self, field, cells, robot_radius=0.22):
        """Reuse an immutable likelihood field and retain known-free map cells."""
        self.field = field
        self.cells = np.asarray(cells).reshape(field.height, field.width)
        self.distances = np.asarray(field._distances).reshape(field.height, field.width)
        self.robot_radius = robot_radius

    def _indices(self, x, y):
        ix = np.floor((x - self.field.origin_x) / self.field.resolution).astype(int)
        iy = np.floor((y - self.field.origin_y) / self.field.resolution).astype(int)
        valid = ((ix >= 0) & (iy >= 0) & (ix < self.field.width)
                 & (iy < self.field.height))
        return ix.clip(0, self.field.width - 1), iy.clip(0, self.field.height - 1), valid

    def score_poses(self, poses, endpoints, sigma=0.15):
        """Score transformed laser endpoints with a Gaussian obstacle field."""
        poses = np.asarray(poses, dtype=float).reshape(-1, 3)
        endpoints = np.asarray(endpoints, dtype=float).reshape(-1, 2)
        if len(endpoints) < 25:
            raise ValueError('at least 25 finite laser endpoints are required')
        scores = np.empty(len(poses))
        # Bounded batches keep memory independent of the full global grid size.
        for begin in range(0, len(poses), 2048):
            block = poses[begin:begin + 2048]
            c, s = np.cos(block[:, 2:3]), np.sin(block[:, 2:3])
            x = block[:, 0:1] + c * endpoints[:, 0] - s * endpoints[:, 1]
            y = block[:, 1:2] + s * endpoints[:, 0] + c * endpoints[:, 1]
            ix, iy, valid = self._indices(x, y)
            likelihood = np.exp(-0.5 * (self.distances[iy, ix] / sigma) ** 2)
            scores[begin:begin + len(block)] = np.mean(likelihood * valid, axis=1)
        return scores

    def _modes(self, poses, scores, count, separation=0.45):
        selected = []
        for index in np.argsort(scores)[::-1]:
            pose = poses[index]
            if all(math.hypot(pose[0] - h.x, pose[1] - h.y) > separation
                   or abs(normalize_angle(pose[2] - h.yaw)) > 0.35
                   for h in selected):
                selected.append(Hypothesis(*map(float, pose), float(scores[index])))
                if len(selected) >= count:
                    break
        return selected

    def global_candidates(self, endpoints, count=8, grid_step=0.20):
        """Search known-free positions and all headings, then refine distinct modes."""
        stride = max(1, round(grid_step / self.field.resolution))
        gy, gx = np.mgrid[0:self.field.height:stride, 0:self.field.width:stride]
        free = ((self.cells[gy, gx] >= 0) & (self.cells[gy, gx] <= 25)
                & (self.distances[gy, gx] > self.robot_radius))
        xy = np.column_stack((
            self.field.origin_x + (gx[free] + 0.5) * self.field.resolution,
            self.field.origin_y + (gy[free] + 0.5) * self.field.resolution,
        ))
        if not len(xy):
            return []
        yaws = np.arange(-math.pi, math.pi, math.radians(5))
        poses = np.column_stack((np.repeat(xy, len(yaws), axis=0),
                                 np.tile(yaws, len(xy))))
        scores = self.score_poses(poses, endpoints)
        seeds = self._modes(poses, scores, count * 3)
        refined = self.refine(seeds, endpoints, xy_radius=grid_step, yaw_radius=0.10)
        poses = np.asarray([h.pose for h in refined])
        return self._modes(poses, np.asarray([h.score for h in refined]), count)

    def refine(self, hypotheses, endpoints, xy_radius=0.10, yaw_radius=0.06):
        """Locally align each retained mode without merging separated aliases."""
        if not hypotheses:
            return []
        offsets = np.asarray(np.meshgrid(
            np.arange(-xy_radius, xy_radius + 0.001, 0.025),
            np.arange(-xy_radius, xy_radius + 0.001, 0.025),
            np.arange(-yaw_radius, yaw_radius + 0.001, 0.02),
            indexing='ij',
        )).reshape(3, -1).T
        refined = []
        for h in hypotheses:
            poses = np.asarray(h.pose) + offsets
            ix, iy, valid = self._indices(poses[:, 0], poses[:, 1])
            valid &= ((self.cells[iy, ix] >= 0) & (self.cells[iy, ix] <= 25)
                      & (self.distances[iy, ix] > self.robot_radius))
            poses = poses[valid]
            if not len(poses):
                continue
            scores = self.score_poses(poses, endpoints)
            best = int(np.argmax(scores))
            refined.append(Hypothesis(*map(float, poses[best]), float(scores[best])))
        # Merge candidates that local refinement pulled into the same mode.
        if not refined:
            return []
        poses = np.asarray([h.pose for h in refined])
        return self._modes(poses, np.asarray([h.score for h in refined]), len(refined))

    def predict_scan(self, pose, laser=(0.0, 0.0, 0.0), beams=72, max_range=8.0):
        """Ray-cast a full scan; unknown/outside cells stop the predicted ray."""
        laser_pose = advance_pose(pose, laser)
        angles = laser_pose[2] + np.linspace(-math.pi, math.pi, beams, endpoint=False)
        ranges = np.arange(self.field.resolution, max_range, self.field.resolution)
        x = laser_pose[0] + np.cos(angles[:, None]) * ranges
        y = laser_pose[1] + np.sin(angles[:, None]) * ranges
        ix, iy, valid = self._indices(x, y)
        blocked = ~valid | (self.cells[iy, ix] < 0) | (self.cells[iy, ix] >= 65)
        hits = np.any(blocked, axis=1)
        first = np.argmax(blocked, axis=1)
        return np.where(hits, ranges[first], max_range)

    def path_free(self, pose, heading, distance):
        """Check the swept circular footprint against obstacles and unknown cells."""
        samples = np.arange(0, distance + 0.025, 0.025)
        yaw = pose[2] + heading
        x = pose[0] + samples * math.cos(yaw)
        y = pose[1] + samples * math.sin(yaw)
        ix, iy, valid = self._indices(x, y)
        return bool(np.all(valid & (self.cells[iy, ix] >= 0)
                           & (self.cells[iy, ix] <= 25)
                           & (self.distances[iy, ix] > self.robot_radius + 0.05)))

    def choose_action(self, hypotheses, actions, laser=(0.0, 0.0, 0.0),
                      max_range=8.0, minimum_gain=0.01):
        """Choose safe relative motion maximizing predicted scan disagreement."""
        if len(hypotheses) < 2:
            return None
        baseline = [self.predict_scan(h.pose, laser, max_range=max_range)
                    for h in hypotheses]
        baseline_gains = [
            float(np.mean(np.minimum(abs(a - b), 1.0) ** 2))
            for i, a in enumerate(baseline) for b in baseline[i + 1:]
        ]
        best = None
        for heading, distance in actions:
            if not all(self.path_free(h.pose, heading, distance) for h in hypotheses):
                continue
            predictions = []
            for h in hypotheses:
                future = advance_pose(h.pose, (distance * math.cos(heading),
                                               distance * math.sin(heading), heading))
                predictions.append(self.predict_scan(future, laser, max_range=max_range))
            # A small fraction of rays may distinguish a doorway or a thin wall.
            # Cap differences so a single long ray cannot dominate the decision.
            pair_gains = [
                float(np.mean(np.minimum(abs(a - b), 1.0) ** 2))
                for i, a in enumerate(predictions) for b in predictions[i + 1:]
            ]
            # Reward NEW evidence rather than disagreement already visible at
            # the current pose. Otherwise cheap, short moves can repeatedly win
            # without making the remaining ambiguity any easier to resolve.
            gain = min(future - current for future, current
                       in zip(pair_gains, baseline_gains))
            utility = gain / (1.0 + 0.25 * distance + 0.05 * abs(heading))
            if gain >= minimum_gain and (best is None or utility > best[0]):
                best = (utility, InformativeAction(heading, distance, gain))
        return None if best is None else best[1]


def scan_endpoints(scan, laser=(0.0, 0.0, 0.0), max_beams=180):
    """Return finite hit endpoints in the robot frame, with spatial beam sampling."""
    ranges = np.asarray(scan.ranges, dtype=float)
    indices = np.arange(0, len(ranges), max(1, math.ceil(len(ranges) / max_beams)))
    distances = ranges[indices]
    valid = (np.isfinite(distances) & (distances >= max(scan.range_min, 0.35))
             & (distances < min(scan.range_max, 8.0)))
    angles = scan.angle_min + indices[valid] * scan.angle_increment + laser[2]
    return np.column_stack((laser[0] + distances[valid] * np.cos(angles),
                            laser[1] + distances[valid] * np.sin(angles)))
