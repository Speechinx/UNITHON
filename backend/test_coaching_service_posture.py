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


def test_build_prompt_includes_posture_rules_section():
    service = _service()

    coaching_data = service._build_coaching_data(
        {"transcript": "hello"}
    )

    prompt = service._build_prompt(coaching_data)

    assert "[자세]" in prompt
    assert "posture_signals" in prompt
