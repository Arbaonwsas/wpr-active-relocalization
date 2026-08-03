import math

import pytest

from wpr_relocalization.relocalization_core import (
    LikelihoodField,
    normalize_angle,
    quaternion_to_yaw,
)


def make_wall_field() -> LikelihoodField:
    width = 100
    height = 100
    cells = [0] * (width * height)
    for cell_y in range(height):
        cells[cell_y * width + 70] = 100
    return LikelihoodField(width, height, 0.1, -5.0, -5.0, cells)


def test_angle_helpers() -> None:
    assert normalize_angle(3.0 * math.pi) == pytest.approx(math.pi)
    yaw = 1.1
    assert quaternion_to_yaw(
        0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)
    ) == pytest.approx(yaw)


def test_likelihood_field_prefers_aligned_scan() -> None:
    field = make_wall_field()
    ranges = [2.0] * 21
    angle_min = -0.05
    angle_increment = 0.005

    aligned = field.score_scan(
        (0.0, 0.0, 0.0),
        ranges,
        angle_min,
        angle_increment,
        0.1,
        10.0,
    )
    shifted = field.score_scan(
        (-1.0, 0.0, 0.0),
        ranges,
        angle_min,
        angle_increment,
        0.1,
        10.0,
    )

    assert aligned.beams_used == 21
    assert aligned.in_map_fraction == pytest.approx(1.0)
    assert aligned.likelihood > 0.8
    assert shifted.likelihood < 0.01


def test_scan_filters_invalid_and_too_close_ranges() -> None:
    field = make_wall_field()
    score = field.score_scan(
        (0.0, 0.0, 0.0),
        [math.inf, math.nan, 0.2, 2.0],
        0.0,
        0.0,
        0.1,
        10.0,
        min_usable_range=0.35,
    )
    assert score.beams_used == 1


def test_rejects_bad_map_shape() -> None:
    with pytest.raises(ValueError):
        LikelihoodField(2, 2, 0.05, 0.0, 0.0, [0, 0])
