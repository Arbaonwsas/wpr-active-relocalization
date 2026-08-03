import math

import pytest

from wpr_relocalization.relocalization_core import (
    ConsecutiveMismatchDetector,
    LikelihoodField,
    OdometryDiscontinuityDetector,
    WindowedMismatchDetector,
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


def test_consecutive_mismatch_requires_persistence_and_resets() -> None:
    detector = ConsecutiveMismatchDetector(0.35, 0.65, 25, 3)

    assert not detector.update(0.20, 100, 1.0)
    assert not detector.update(0.20, 100, 1.0)
    assert not detector.update(0.80, 100, 1.0)
    assert detector.consecutive == 0
    assert not detector.update(0.20, 100, 1.0)
    assert not detector.update(0.20, 100, 1.0)
    assert detector.update(0.20, 100, 1.0)
    assert detector.consecutive == 0


def test_consecutive_mismatch_rejects_weak_scans_and_out_of_map() -> None:
    detector = ConsecutiveMismatchDetector(0.35, 0.65, 25, 2)

    assert not detector.update(0.10, 10, 0.1)
    assert detector.consecutive == 0
    assert not detector.update(0.90, 100, 0.5)
    assert detector.update(0.90, 100, 0.5)


def test_consecutive_mismatch_detects_lost_covariance() -> None:
    detector = ConsecutiveMismatchDetector(
        0.35,
        0.65,
        25,
        2,
        maximum_xy_variance=0.4,
        maximum_yaw_variance=0.12,
    )

    assert not detector.update(0.90, 100, 1.0, 6.0, 7.0, 6.0)
    assert detector.update(0.90, 100, 1.0, 6.0, 7.0, 6.0)


@pytest.mark.parametrize(
    "arguments",
    [(-0.1, 0.5, 10, 2), (0.5, 1.1, 10, 2), (0.5, 0.5, 0, 2),
     (0.5, 0.5, 10, 0)],
)
def test_consecutive_mismatch_validates_configuration(arguments) -> None:
    with pytest.raises(ValueError):
        ConsecutiveMismatchDetector(*arguments)


def test_windowed_mismatch_tolerates_occasional_good_scans() -> None:
    detector = WindowedMismatchDetector(0.60, 25, 10, 0.80)

    scores = [0.55, 0.54, 0.80, 0.56, 0.57, 0.58, 0.75, 0.59, 0.50]
    for score in scores:
        assert not detector.update(score, 100)
    assert detector.update(0.52, 100)
    assert len(detector.samples) == 0


def test_windowed_mismatch_rejects_healthy_window_and_sparse_scans() -> None:
    detector = WindowedMismatchDetector(0.60, 25, 4, 0.75)

    assert not detector.update(0.20, 10)
    assert len(detector.samples) == 0
    for score in [0.50, 0.80, 0.70, 0.55]:
        assert not detector.update(score, 100)


@pytest.mark.parametrize(
    "arguments",
    [
        (-0.1, 10, 4, 0.5),
        (0.5, 0, 4, 0.5),
        (0.5, 10, 0, 0.5),
        (0.5, 10, 4, 0.0),
    ],
)
def test_windowed_mismatch_validates_configuration(arguments) -> None:
    with pytest.raises(ValueError):
        WindowedMismatchDetector(*arguments)


def test_odometry_discontinuity_detects_translation_and_rotation_jumps() -> None:
    detector = OdometryDiscontinuityDetector(0.75, 0.80)

    assert detector.update((0.0, 0.0), 3.0) == (False, 0.0, 0.0)
    jump, distance, yaw_change = detector.update((0.1, 0.0), -3.0)
    assert not jump
    assert distance == pytest.approx(0.1)
    assert yaw_change == pytest.approx(2.0 * math.pi - 6.0)

    assert detector.update((1.0, 0.0), -3.0)[0]
    assert detector.update((1.0, 0.0), -1.5)[0]


@pytest.mark.parametrize("arguments", [(0.0, 0.5), (0.5, 0.0), (0.5, 3.2)])
def test_odometry_discontinuity_validates_configuration(arguments) -> None:
    with pytest.raises(ValueError):
        OdometryDiscontinuityDetector(*arguments)
