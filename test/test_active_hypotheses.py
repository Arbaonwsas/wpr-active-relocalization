"""Check candidate ambiguity, odometry invariance and informative actions."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from wpr_relocalization.active_hypotheses import (
    Hypothesis, HypothesisSearch, advance_pose, relative_motion,
    scan_endpoints, unique_candidate,
)
from wpr_relocalization.relocalization_core import LikelihoodField


def make_search(cells, resolution=0.1):
    h, w = cells.shape
    field = LikelihoodField(w, h, resolution, 0.0, 0.0, cells.ravel())
    return HypothesisSearch(field, cells)


def room_map():
    cells = np.zeros((120, 120), dtype=int)
    cells[0, :] = cells[-1, :] = 100
    cells[:, 0] = cells[:, -1] = 100
    cells[20:60, 70] = 100
    cells[30, 20:50] = 100
    return cells


def endpoints(search, pose, max_range=8.0):
    ranges = search.predict_scan(pose, beams=360, max_range=max_range)
    scan = SimpleNamespace(ranges=ranges, angle_min=-math.pi,
                           angle_increment=2 * math.pi / 360,
                           range_min=0.1, range_max=max_range)
    return scan_endpoints(scan)


def test_global_search_keeps_the_true_mode_without_pose_prior():
    search = make_search(room_map())
    truth = (3.7, 6.2, 0.65)
    found = search.global_candidates(endpoints(search, truth), count=6)
    assert math.hypot(found[0].x - truth[0], found[0].y - truth[1]) < 0.15
    assert abs(found[0].yaw - truth[2]) < 0.08
    assert len(found) >= 2


def test_symmetric_candidates_cannot_report_unique_success():
    candidates = [Hypothesis(1, 2, 0, 0.96), Hypothesis(9, 8, math.pi, 0.95)]
    assert unique_candidate(candidates, [0.96, 0.95]) is None


def test_previous_confidence_cannot_override_current_contradiction():
    candidates = [Hypothesis(1, 2, 0, 0.65), Hypothesis(9, 8, math.pi, 0.95)]
    assert unique_candidate(candidates, [0.95, 0.65]) is None


def test_both_current_and_historical_evidence_can_select_a_winner():
    candidates = [Hypothesis(1, 2, 0, 0.96), Hypothesis(9, 8, math.pi, 0.70)]
    assert unique_candidate(candidates, [0.95, 0.72]) == 0


def test_relative_odometry_does_not_reveal_absolute_world_position():
    start = (12, -5, 1.0)
    motion = (0.6, -0.1, 0.4)
    end = advance_pose(start, motion)
    change_of_origin = (-100, 250, -0.8)
    assert relative_motion(start, end) == pytest.approx(motion)
    assert relative_motion(advance_pose(change_of_origin, start),
                           advance_pose(change_of_origin, end)) == pytest.approx(motion)


def test_exactly_repeated_rooms_have_no_informative_action():
    cells = np.zeros((120, 240), dtype=int)
    cells[0, :] = cells[-1, :] = 100
    cells[:, 0] = cells[:, 119] = cells[:, 120] = cells[:, -1] = 100
    search = make_search(cells)
    candidates = [Hypothesis(6, 6, 0, 1), Hypothesis(18, 6, 0, 1)]
    # Identical local scans and identical future scans remain ambiguous.
    assert search.choose_action(candidates, [(0, 0.8), (math.pi / 2, 0.8)],
                                max_range=4.0) is None


def test_exploration_selects_a_newly_visible_distinguishing_landmark():
    cells = np.zeros((120, 300), dtype=int)
    cells[0, :] = cells[-1, :] = 100
    cells[:, 0] = cells[:, -1] = 100
    # Both starts have no obstacle within 4 m. A forward move reveals a
    # landmark only under the first hypothesis.
    cells[40:80, 103] = 100
    search = make_search(cells)
    candidates = [Hypothesis(6, 6, 0, 1), Hypothesis(22, 6, 0, 1)]
    assert np.allclose(search.predict_scan(candidates[0].pose, max_range=4),
                       search.predict_scan(candidates[1].pose, max_range=4))
    action = search.choose_action(candidates, [(0, 0.8), (math.pi, 0.8)],
                                  max_range=4)
    assert action is not None
    assert action.heading == 0
    assert action.gain > 0.01


def test_path_in_unknown_space_is_not_a_safe_information_action():
    cells = room_map()
    cells[50:70, 45:65] = -1
    search = make_search(cells)
    assert not search.path_free((4, 6, 0), 0, 1)


def test_obstacle_on_any_candidate_path_rejects_the_action():
    cells = room_map()
    search = make_search(cells)
    candidates = [Hypothesis(6, 5, 0, 1), Hypothesis(4, 8, 0, 1)]
    assert search.choose_action(candidates, [(0, 1.5)]) is None


def test_too_few_laser_hits_cannot_initialize_a_pose():
    search = make_search(room_map())
    with pytest.raises(ValueError, match='25 finite'):
        search.global_candidates(np.ones((10, 2)))


def test_action_rewards_new_evidence_instead_of_existing_disagreement():
    search = make_search(room_map())
    search.path_free = lambda *args: True

    def prediction(pose, *args, **kwargs):
        if pose[0] < 10:
            return np.zeros(72)
        gain = 0.15 if pose[0] == 10 else (0.183 if pose[0] < 10.5 else 0.209)
        return np.full(72, math.sqrt(gain))

    search.predict_scan = prediction
    candidates = [Hypothesis(0, 0, 0, 1), Hypothesis(10, 0, 0, 1)]
    action = search.choose_action(candidates, [(0, 0.35), (0, 0.9)])
    assert action is not None
    assert action.distance == 0.9
