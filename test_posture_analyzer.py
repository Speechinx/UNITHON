import math

from app.services.posture_analyzer import (
    PostureAnalyzer,
)


def _landmark(x, y, visibility=1.0):
    return {"x": x, "y": y, "visibility": visibility}


def _frame(
    nose=(0.5, 0.2),
    left_shoulder=(0.4, 0.4),
    right_shoulder=(0.6, 0.4),
    left_wrist=(0.35, 0.6),
    right_wrist=(0.65, 0.6),
    visibility=1.0,
):
    return {
        "nose": _landmark(*nose, visibility),
        "left_shoulder": _landmark(*left_shoulder, visibility),
        "right_shoulder": _landmark(*right_shoulder, visibility),
        "left_wrist": _landmark(*left_wrist, visibility),
        "right_wrist": _landmark(*right_wrist, visibility),
    }


def test_is_valid_true_for_complete_high_visibility_frame():
    analyzer = PostureAnalyzer()

    assert analyzer._is_valid(_frame()) is True


def test_is_valid_false_for_none_frame():
    analyzer = PostureAnalyzer()

    assert analyzer._is_valid(None) is False


def test_is_valid_false_when_visibility_too_low():
    analyzer = PostureAnalyzer()

    frame = _frame(visibility=0.1)

    assert analyzer._is_valid(frame) is False


def test_shoulder_tilt_deg_is_zero_for_level_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.4, 0.4),
        right_shoulder=(0.6, 0.4),
    )

    assert analyzer._shoulder_tilt_deg(frame) == 0.0


def test_shoulder_tilt_deg_for_45_degree_tilt():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.4, 0.4),
        right_shoulder=(0.6, 0.6),
    )

    assert math.isclose(
        analyzer._shoulder_tilt_deg(frame),
        45.0,
        abs_tol=0.01,
    )


def test_head_down_deg_is_zero_when_nose_directly_above_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.5, 0.2),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    assert math.isclose(
        analyzer._head_down_deg(frame),
        0.0,
        abs_tol=0.01,
    )


def test_head_down_deg_is_90_when_nose_level_with_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.8, 0.5),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    assert math.isclose(
        analyzer._head_down_deg(frame),
        90.0,
        abs_tol=0.01,
    )
