from unittest.mock import MagicMock, patch


with patch.dict(
    "os.environ",
    {"GEMINI_API_KEY": "fake-key-for-tests"},
):
    from app.services.coaching_service import (
        CoachingService
    )


def _service():
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "fake-key-for-tests"},
    ):
        return CoachingService()


def test_build_coaching_data_includes_posture_signals():
    service = _service()

    analysis_result = {
        "transcript": "hello",
        "posture": {"windows": [{"window_index": 0}]},
    }

    data = service._build_coaching_data(analysis_result)

    assert data["posture_signals"] == {
        "windows": [{"window_index": 0}]
    }


def test_build_coaching_data_defaults_posture_signals_when_missing():
    service = _service()

    data = service._build_coaching_data({"transcript": "hello"})

    assert data["posture_signals"] == {}


def test_build_coaching_data_strips_avatar_state_from_posture_signals():
    service = _service()

    analysis_result = {
        "transcript": "hello",
        "posture": {
            "windows": [
                {
                    "window_index": 0,
                    "avatar_state": "bored",
                    "reasons": ["어깨 기울어짐 80% 구간"],
                }
            ]
        },
    }

    data = service._build_coaching_data(analysis_result)

    window = data["posture_signals"]["windows"][0]

    assert "avatar_state" not in window
    assert window["window_index"] == 0
    assert window["reasons"] == ["어깨 기울어짐 80% 구간"]


def test_build_prompt_includes_posture_rules_section():
    service = _service()

    coaching_data = service._build_coaching_data(
        {"transcript": "hello"}
    )

    prompt = service._build_prompt(coaching_data)

    assert "[자세]" in prompt
    assert "posture_signals" in prompt
    assert "torso_signal_sufficient" in prompt
    assert "open_posture_level" in prompt
    assert "power_zone_level" in prompt
    assert "head_alignment_level" in prompt
    assert "앞으로 기울어진" in prompt
