from dotenv import load_dotenv

from app.services.analysis_service import (
    AnalysisService
)

from app.services.coaching_service import (
    CoachingService
)


load_dotenv()


audio_path = "audio/test.wav"


# ==========================================
# Analysis
# ==========================================

print(
    "Loading AnalysisService..."
)

analysis_service = (
    AnalysisService()
)

print(
    "Starting full analysis..."
)

analysis_result = (
    analysis_service.analyze(
        audio_path
    )
)

print(
    "Analysis complete!"
)


# ==========================================
# Gemini 호출 전 핵심 데이터 확인
# ==========================================

speech = analysis_result[
    "speech"
]

print(
    "\n===== DATA SENT TO GEMINI ====="
)

print(
    "발표 체감 속도:",
    speech[
        "presentation_rate"
    ],
    "어절/분"
)

print(
    "실제 발화 속도:",
    speech[
        "articulation_rate"
    ],
    "어절/분"
)

print(
    "속도 판정:",
    speech[
        "pace_level"
    ]
)

print(
    "Pause 비율:",
    speech[
        "internal_pause_ratio"
    ]
)

print(
    "전체 Risk:",
    analysis_result[
        "risk"
    ][
        "overall_score"
    ],
    "/",
    analysis_result[
        "risk"
    ][
        "overall_level"
    ]
)


# ==========================================
# Gemini
# ==========================================

print(
    "\nLoading CoachingService..."
)

coaching_service = (
    CoachingService()
)

print(
    "Generating Gemini coaching..."
)

coaching = (
    coaching_service.generate(
        analysis_result
    )
)


print(
    "\n===== GEMINI COACHING ====="
)

print(
    coaching
)