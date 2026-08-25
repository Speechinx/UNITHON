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


def test_shoulder_tilt_deg_is_symmetric_when_shoulder_order_is_reversed():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.6, 0.4),
        right_shoulder=(0.4, 0.4),
    )

    assert analyzer._shoulder_tilt_deg(frame) == 0.0


def test_shoulder_tilt_deg_for_45_degree_tilt_with_reversed_shoulder_order():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.6, 0.4),
        right_shoulder=(0.4, 0.6),
    )

    assert math.isclose(
        analyzer._shoulder_tilt_deg(frame),
        45.0,
        abs_tol=0.01,
    )


def test_head_down_deg_is_unaffected_by_horizontal_nose_position():
    analyzer = PostureAnalyzer()

    centered = _frame(
        nose=(0.5, 0.3),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    off_to_the_side = _frame(
        nose=(0.7, 0.3),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    assert math.isclose(
        analyzer._head_down_deg(centered),
        analyzer._head_down_deg(off_to_the_side),
        abs_tol=0.001,
    )

    assert math.isclose(
        analyzer._head_down_deg(centered),
        45.0,
        abs_tol=0.01,
    )


def test_head_down_deg_increases_as_nose_approaches_shoulder_height():
    analyzer = PostureAnalyzer()

    upright = _frame(
        nose=(0.5, 0.1),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    hunched = _frame(
        nose=(0.5, 0.45),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    assert analyzer._head_down_deg(hunched) > analyzer._head_down_deg(upright)


def test_analyze_window_signal_insufficient_when_too_many_invalid_frames():
    analyzer = PostureAnalyzer()

    frames = [None, None, None, _frame()]

    result = analyzer.analyze_window(frames)

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.25,
    }


def test_analyze_window_empty_list_is_insufficient():
    analyzer = PostureAnalyzer()

    result = analyzer.analyze_window([])

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.0,
    }


def test_analyze_window_all_level_frames_has_zero_tilt_and_low_activity():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["valid_frame_ratio"] == 1.0
    assert result["shoulder_tilt_avg_deg"] == 0.0
    assert result["shoulder_tilt_exceed_ratio"] == 0.0
    assert result["gesture_activity_level"] == "low"
    assert result["reasons"] == []


def test_analyze_window_flags_shoulder_tilt_reason_when_exceed_ratio_high():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["shoulder_tilt_exceed_ratio"] == 0.8
    assert any(
        "어깨" in reason
        for reason in result["reasons"]
    )


def test_analyze_window_signal_sufficient_when_only_wrists_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_wrist"]["visibility"] = 0.1
    frame["right_wrist"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["valid_frame_ratio"] == 1.0
    assert result["gesture_activity_level"] == "unknown"


def test_analyze_window_detects_high_gesture_activity_from_moving_wrists():
    analyzer = PostureAnalyzer()

    frames = [
        _frame(left_wrist=(0.1, 0.6), right_wrist=(0.9, 0.6)),
        _frame(left_wrist=(0.5, 0.2), right_wrist=(0.5, 0.2)),
        _frame(left_wrist=(0.1, 0.6), right_wrist=(0.9, 0.6)),
    ]

    result = analyzer.analyze_window(frames)

    assert result["gesture_activity_level"] == "high"
