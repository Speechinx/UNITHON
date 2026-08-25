import math

from app.services.posture_analyzer import (
    PostureAnalyzer,
)


def _landmark(x, y, visibility=1.0):
    return {"x": x, "y": y, "visibility": visibility}


def _frame(
    nose=(0.5, 0.2),
    left_ear=(0.42, 0.2),
    right_ear=(0.58, 0.2),
    left_shoulder=(0.4, 0.4),
    right_shoulder=(0.6, 0.4),
    left_wrist=(0.35, 0.6),
    right_wrist=(0.65, 0.6),
    left_hip=(0.45, 0.75),
    right_hip=(0.55, 0.75),
    left_elbow=(0.38, 0.55),
    right_elbow=(0.62, 0.55),
    visibility=1.0,
):
    return {
        "nose": _landmark(*nose, visibility),
        "left_ear": _landmark(*left_ear, visibility),
        "right_ear": _landmark(*right_ear, visibility),
        "left_shoulder": _landmark(*left_shoulder, visibility),
        "right_shoulder": _landmark(*right_shoulder, visibility),
        "left_wrist": _landmark(*left_wrist, visibility),
        "right_wrist": _landmark(*right_wrist, visibility),
        "left_hip": _landmark(*left_hip, visibility),
        "right_hip": _landmark(*right_hip, visibility),
        "left_elbow": _landmark(*left_elbow, visibility),
        "right_elbow": _landmark(*right_elbow, visibility),
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
        "avatar_state": "unknown",
    }


def test_analyze_window_empty_list_is_insufficient():
    analyzer = PostureAnalyzer()

    result = analyzer.analyze_window([])

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.0,
        "avatar_state": "unknown",
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


def test_analyze_window_avatar_state_engaged_when_no_reasons_and_default_engagement():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] == []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "normal"
    assert result["avatar_state"] == "engaged"


def test_analyze_window_avatar_state_confused_when_reasons_present_and_default_engagement():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] != []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "normal"
    assert result["avatar_state"] == "confused"


def test_analyze_window_avatar_state_focused_when_no_reasons_and_low_engagement():
    analyzer = PostureAnalyzer()

    closed_arm_frame = _frame(
        left_elbow=(0.44, 0.55),
        right_elbow=(0.56, 0.55),
    )

    frames = [closed_arm_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] == []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "closed"
    assert result["avatar_state"] == "focused"


def test_analyze_window_avatar_state_bored_when_reasons_present_and_low_engagement():
    analyzer = PostureAnalyzer()

    tilted_closed_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
        left_elbow=(0.44, 0.55),
        right_elbow=(0.56, 0.55),
    )

    frames = [tilted_closed_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] != []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "closed"
    assert result["avatar_state"] == "bored"


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


def test_torso_lean_deg_is_zero_when_shoulder_center_is_above_hip_center():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.4, 0.3),
        right_shoulder=(0.6, 0.3),
        left_hip=(0.4, 0.7),
        right_hip=(0.6, 0.7),
    )

    assert analyzer._torso_lean_deg(frame) == 0.0


def test_torso_lean_deg_for_45_degree_lean():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.5, 0.3),
        right_shoulder=(0.5, 0.3),
        left_hip=(0.7, 0.5),
        right_hip=(0.7, 0.5),
    )

    assert math.isclose(
        analyzer._torso_lean_deg(frame),
        45.0,
        abs_tol=0.01,
    )


def test_gaze_away_deg_is_zero_when_nose_centered_between_ears():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.5, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    assert analyzer._gaze_away_deg(frame) == 0.0


def test_gaze_away_deg_for_45_degree_turn():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.58, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    assert math.isclose(
        analyzer._gaze_away_deg(frame),
        45.0,
        abs_tol=0.01,
    )


def test_analyze_window_all_level_frames_reports_torso_lean_too():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["torso_signal_sufficient"] is True
    assert result["torso_lean_avg_deg"] == 0.0
    assert result["torso_lean_exceed_ratio"] == 0.0


def test_analyze_window_torso_insufficient_when_hips_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_hip"]["visibility"] = 0.1
    frame["right_hip"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["torso_signal_sufficient"] is False
    assert result["torso_lean_avg_deg"] == 0.0
    assert result["torso_lean_exceed_ratio"] == 0.0


def test_analyze_window_flags_torso_lean_reason_when_exceed_ratio_high():
    analyzer = PostureAnalyzer()

    leaned_frame = _frame(
        left_shoulder=(0.55, 0.3),
        right_shoulder=(0.55, 0.3),
        left_hip=(0.4, 0.7),
        right_hip=(0.4, 0.7),
    )

    frames = [leaned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_exceed_ratio"] == 0.8
    assert any(
        "상체" in reason
        for reason in result["reasons"]
    )


def test_analyze_window_result_is_compatible_with_posture_window_schema():
    from app.schemas.analysis_response import PostureWindow

    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)
    result["window_index"] = 0

    window = PostureWindow(**result)

    assert window.torso_signal_sufficient is True
    assert window.gaze_signal_sufficient is True
    assert window.avatar_state == "engaged"


def test_arm_openness_ratio_greater_than_one_when_elbows_wider_than_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.45, 0.4),
        right_shoulder=(0.55, 0.4),
        left_elbow=(0.2, 0.4),
        right_elbow=(0.8, 0.4),
    )

    assert math.isclose(
        analyzer._arm_openness_ratio(frame),
        6.0,
        rel_tol=1e-9,
    )


def test_arm_openness_level_closed_when_ratio_low():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([0.5, 0.6]) == "closed"


def test_arm_openness_level_open_when_ratio_high():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([1.5, 1.6]) == "open"


def test_arm_openness_level_normal_at_middle_ratio():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([1.0, 1.0]) == "normal"


def test_arm_openness_level_normal_at_low_boundary():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([0.8]) == "normal"


def test_arm_openness_level_normal_at_high_boundary():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([1.3]) == "normal"


def test_analyze_window_all_level_frames_has_normal_arm_openness():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["arm_openness_level"] == "normal"


def test_analyze_window_arm_openness_unknown_when_elbows_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_elbow"]["visibility"] = 0.1
    frame["right_elbow"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["arm_openness_level"] == "unknown"


def test_analyze_window_all_level_frames_reports_gaze_away_too():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["gaze_signal_sufficient"] is True
    assert result["gaze_away_avg_deg"] == 0.0
    assert result["gaze_away_exceed_ratio"] == 0.0


def test_analyze_window_gaze_insufficient_when_ears_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_ear"]["visibility"] = 0.1
    frame["right_ear"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["gaze_signal_sufficient"] is False
    assert result["gaze_away_avg_deg"] == 0.0
    assert result["gaze_away_exceed_ratio"] == 0.0


def test_analyze_window_flags_gaze_away_reason_when_exceed_ratio_high():
    analyzer = PostureAnalyzer()

    turned_frame = _frame(
        nose=(0.58, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    frames = [turned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["gaze_away_exceed_ratio"] == 0.8
    assert any(
        "시선" in reason
        for reason in result["reasons"]
    )
