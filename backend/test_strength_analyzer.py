from dotenv import load_dotenv

from app.services.analysis_service import (
    AnalysisService
)


load_dotenv()


audio_path = "audio/녹음.wav"


print(
    "Loading AnalysisService..."
)

service = (
    AnalysisService()
)


print(
    "Analyzing..."
)

result = service.analyze(
    audio_path
)


print(
    "\n===== SPEECH ====="
)

speech = result[
    "speech"
]

print(
    "발표 속도:",
    speech[
        "presentation_rate"
    ],
    "어절/분",
)

print(
    "속도 판정:",
    speech[
        "pace_level"
    ],
)


print(
    "\n===== STRENGTH SIGNALS ====="
)

strengths = result.get(
    "strength_signals",
    [],
)

if not strengths:
    print(
        "탐지된 긍정 신호 없음"
    )

else:
    for index, strength in enumerate(
        strengths,
        start=1,
    ):
        print(
            "\n--------------------"
        )

        print(
            f"{index}."
        )

        print(
            "Type:",
            strength.get(
                "type"
            ),
        )

        print(
            "Time:",
            strength.get(
                "start"
            ),
            "~",
            strength.get(
                "end"
            ),
        )

        print(
            "Message:",
            strength.get(
                "message"
            ),
        )

        print(
            "Evidence:",
            strength.get(
                "evidence"
            ),
        )