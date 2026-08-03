"""Pure-Python helpers for active AMCL global relocalization."""

from collections import deque
from dataclasses import dataclass, field
import heapq
import math
from typing import Sequence


def normalize_angle(angle: float) -> float:
    """Return an angle in [-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Extract planar yaw from a quaternion."""
    return math.atan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )


@dataclass(frozen=True)
class ScanScore:
    likelihood: float
    beams_used: int
    in_map_fraction: float


@dataclass
class ConsecutiveMismatchDetector:
    """Require persistent scan mismatch before requesting recovery."""

    maximum_score: float
    minimum_in_map_fraction: float
    minimum_beams: int
    required_consecutive: int
    maximum_xy_variance: float = math.inf
    maximum_yaw_variance: float = math.inf
    consecutive: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.maximum_score <= 1.0:
            raise ValueError("maximum mismatch score must be in [0, 1]")
        if not 0.0 <= self.minimum_in_map_fraction <= 1.0:
            raise ValueError("minimum in-map fraction must be in [0, 1]")
        if self.minimum_beams < 1:
            raise ValueError("minimum beams must be positive")
        if self.required_consecutive < 1:
            raise ValueError("required consecutive scans must be positive")
        if self.maximum_xy_variance < 0.0:
            raise ValueError("maximum XY variance must be non-negative")
        if self.maximum_yaw_variance < 0.0:
            raise ValueError("maximum yaw variance must be non-negative")

    def reset(self) -> None:
        self.consecutive = 0

    def update(
        self,
        score: float,
        beams_used: int,
        in_map_fraction: float,
        x_variance: float = 0.0,
        y_variance: float = 0.0,
        yaw_variance: float = 0.0,
    ) -> bool:
        enough_beams = beams_used >= self.minimum_beams
        mismatched = enough_beams and (
            score < self.maximum_score
            or in_map_fraction < self.minimum_in_map_fraction
            or x_variance > self.maximum_xy_variance
            or y_variance > self.maximum_xy_variance
            or yaw_variance > self.maximum_yaw_variance
        )
        if not mismatched:
            self.reset()
            return False

        self.consecutive += 1
        if self.consecutive < self.required_consecutive:
            return False
        self.reset()
        return True


@dataclass
class WindowedMismatchDetector:
    """Detect a mostly persistent, moderate mismatch over a fixed window."""

    maximum_score: float
    minimum_beams: int
    window_size: int
    required_ratio: float
    samples: deque[bool] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not 0.0 <= self.maximum_score <= 1.0:
            raise ValueError("maximum mismatch score must be in [0, 1]")
        if self.minimum_beams < 1:
            raise ValueError("minimum beams must be positive")
        if self.window_size < 1:
            raise ValueError("window size must be positive")
        if not 0.0 < self.required_ratio <= 1.0:
            raise ValueError("required ratio must be in (0, 1]")
        self.samples = deque(maxlen=self.window_size)

    def reset(self) -> None:
        self.samples.clear()

    def update(self, score: float, beams_used: int) -> bool:
        # Missing or extremely sparse scans carry no evidence either way.
        if beams_used < self.minimum_beams:
            return False

        self.samples.append(score < self.maximum_score)
        if len(self.samples) < self.window_size:
            return False
        if sum(self.samples) / self.window_size < self.required_ratio:
            return False
        self.reset()
        return True


class LikelihoodField:
    """
    Distance-to-obstacle field used to validate an AMCL pose.

    AMCL covariance alone is not a sufficient success criterion: a particle
    filter can be tightly concentrated around a wrong, symmetric hypothesis.
    This class independently projects laser endpoints into the occupancy map
    and scores how well they coincide with mapped obstacles.
    """

    _NEIGHBORS = (
        (-1, 0, 1.0),
        (1, 0, 1.0),
        (0, -1, 1.0),
        (0, 1, 1.0),
        (-1, -1, math.sqrt(2.0)),
        (-1, 1, math.sqrt(2.0)),
        (1, -1, math.sqrt(2.0)),
        (1, 1, math.sqrt(2.0)),
    )

    def __init__(
        self,
        width: int,
        height: int,
        resolution: float,
        origin_x: float,
        origin_y: float,
        cells: Sequence[int],
        occupied_threshold: int = 65,
        max_distance: float = 2.0,
    ) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("map dimensions must be positive")
        if resolution <= 0.0:
            raise ValueError("map resolution must be positive")
        if len(cells) != width * height:
            raise ValueError("occupancy data length does not match dimensions")

        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin_x = origin_x
        self.origin_y = origin_y
        self.max_distance = max_distance
        self._distances = self._build_distance_field(cells, occupied_threshold)

    def _build_distance_field(
        self, cells: Sequence[int], occupied_threshold: int
    ) -> list[float]:
        limit_cells = self.max_distance / self.resolution
        distances = [limit_cells] * (self.width * self.height)
        queue: list[tuple[float, int, int]] = []

        for index, value in enumerate(cells):
            if value >= occupied_threshold:
                x = index % self.width
                y = index // self.width
                distances[index] = 0.0
                heapq.heappush(queue, (0.0, x, y))

        while queue:
            distance, x, y = heapq.heappop(queue)
            index = y * self.width + x
            if distance != distances[index]:
                continue
            for dx, dy, step in self._NEIGHBORS:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.width and 0 <= ny < self.height):
                    continue
                candidate = distance + step
                neighbor = ny * self.width + nx
                if candidate < distances[neighbor] and candidate <= limit_cells:
                    distances[neighbor] = candidate
                    heapq.heappush(queue, (candidate, nx, ny))

        return [min(value * self.resolution, self.max_distance) for value in distances]

    def distance_at(self, map_x: float, map_y: float) -> float | None:
        cell_x = int(math.floor((map_x - self.origin_x) / self.resolution))
        cell_y = int(math.floor((map_y - self.origin_y) / self.resolution))
        if not (0 <= cell_x < self.width and 0 <= cell_y < self.height):
            return None
        return self._distances[cell_y * self.width + cell_x]

    def score_scan(
        self,
        base_pose: tuple[float, float, float],
        ranges: Sequence[float],
        angle_min: float,
        angle_increment: float,
        range_min: float,
        range_max: float,
        laser_in_base: tuple[float, float, float] = (0.0, 0.0, 0.0),
        *,
        sigma: float = 0.20,
        min_usable_range: float = 0.35,
        max_usable_range: float = 8.0,
        max_beams: int = 180,
    ) -> ScanScore:
        if sigma <= 0.0:
            raise ValueError("score sigma must be positive")
        if not ranges:
            return ScanScore(0.0, 0, 0.0)

        stride = max(1, math.ceil(len(ranges) / max(1, max_beams)))
        bx, by, base_yaw = base_pose
        lx, ly, laser_yaw = laser_in_base
        cos_base, sin_base = math.cos(base_yaw), math.sin(base_yaw)
        laser_map_x = bx + cos_base * lx - sin_base * ly
        laser_map_y = by + sin_base * lx + cos_base * ly
        beam_yaw_offset = base_yaw + laser_yaw
        usable_max = min(range_max, max_usable_range)

        likelihood_sum = 0.0
        beams_used = 0
        in_map = 0
        for index in range(0, len(ranges), stride):
            distance = float(ranges[index])
            if not math.isfinite(distance):
                continue
            if distance < max(range_min, min_usable_range) or distance >= usable_max:
                continue

            beam_yaw = beam_yaw_offset + angle_min + index * angle_increment
            endpoint_x = laser_map_x + distance * math.cos(beam_yaw)
            endpoint_y = laser_map_y + distance * math.sin(beam_yaw)
            obstacle_distance = self.distance_at(endpoint_x, endpoint_y)
            beams_used += 1
            if obstacle_distance is None:
                continue
            in_map += 1
            likelihood_sum += math.exp(
                -0.5 * (obstacle_distance / sigma) ** 2
            )

        if beams_used == 0:
            return ScanScore(0.0, 0, 0.0)
        return ScanScore(
            likelihood=likelihood_sum / beams_used,
            beams_used=beams_used,
            in_map_fraction=in_map / beams_used,
        )
