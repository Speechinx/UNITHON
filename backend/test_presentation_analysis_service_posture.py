from unittest.mock import MagicMock

from app.services.presentation_analysis_service import (
    PresentationAnalysisService
)


def test_analyze_includes_empty_posture_when_none_given():
    service = PresentationAnalysisService.__new__(
        PresentationAnalysisService
    )

    service.analysis_service = MagicMock()
    service.analysis_service.analyze.return_value = {
        "transcript": "hello",
    }

    service.coaching_service = MagicMock()
    service.coaching_service.generate.return_value = {}

    result = service.analyze("fake.wav")

    assert result["posture"] == {"windows": []}


def test_analyze_passes_posture_windows_into_coaching_data():
    service = PresentationAnalysisService.__new__(
        PresentationAnalysisService
    )

    service.analysis_service = MagicMock()
    service.analysis_service.analyze.return_value = {
        "transcript": "hello",
    }

    service.coaching_service = MagicMock()
    service.coaching_service.generate.return_value = {}

    windows = [{"window_index": 0, "signal_sufficient": True}]

    result = service.analyze(
        "fake.wav",
        posture_windows=windows,
    )

    assert result["posture"] == {"windows": windows}

    passed_analysis_result = (
        service.coaching_service.generate.call_args[0][0]
    )

    assert passed_analysis_result["posture"] == {
        "windows": windows
    }
