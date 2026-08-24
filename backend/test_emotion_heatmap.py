from dotenv import load_dotenv

from app.services.analysis_service import (
    AnalysisService
)


load_dotenv()


audio_path = "audio/test.wav"


print(
    "Loading AnalysisService..."
)

service = AnalysisService()


print(
    "Analyzing..."
)

result = service.analyze(
    audio_path
)


print(
    "\n===== EMOTION HEATMAP ====="
)


for window in result[
    "risk"
][
    "heatmap"
]:

    print(
        "\n--------------------"
    )

    print(
        f"{window['start']:.2f}s"
        f" ~ "
        f"{window['end']:.2f}s"
    )

    print(
        "Risk:",
        window[
            "level"
        ],
        "/",
        window[
            "score"
        ],
    )

    print(
        "Emotion signal:",
        window.get(
            "emotion_signal",
            "unknown",
        ),
    )

    print(
        "Pace:",
        window[
            "pace_level"
        ],
    )