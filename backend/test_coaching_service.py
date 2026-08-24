import json

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
# Gemini 호출 전 데이터
# ==========================================

speech = analysis_result[
    "speech"
]

print(
    "\n===== ANALYSIS SUMMARY ====="
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


# ==========================================
# Raw JSON
# ==========================================

print(
    "\n===== COACHING JSON ====="
)

print(
    json.dumps(
        coaching,
        ensure_ascii=False,
        indent=2,
    )
)


# ==========================================
# 프론트에서 사용할 형태로 출력
# ==========================================

print(
    "\n===== SUMMARY ====="
)

print(
    coaching[
        "summary"
    ]
)


print(
    "\n===== STRENGTHS ====="
)

if not coaching[
    "strengths"
]:

    print(
        "없음"
    )

else:

    for strength in coaching[
        "strengths"
    ]:

        print(
            "-",
            strength
        )


print(
    "\n===== IMPROVEMENTS ====="
)

if not coaching[
    "improvements"
]:

    print(
        "없음"
    )

else:

    for improvement in coaching[
        "improvements"
    ]:

        print(
            "\n제목:",
            improvement.get(
                "title",
                "",
            )
        )

        print(
            "시간:",
            improvement.get(
                "time_range"
            )
        )

        print(
            "설명:",
            improvement.get(
                "description",
                "",
            )
        )


print(
    "\n===== PRACTICE GOALS ====="
)

for index, goal in enumerate(
    coaching[
        "practice_goals"
    ],
    start=1,
):

    print(
        f"{index}.",
        goal
    )


print(
    "\n===== ONE LINE COACHING ====="
)

print(
    coaching[
        "one_line_coaching"
    ]
)