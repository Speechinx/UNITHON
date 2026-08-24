import json

from dotenv import load_dotenv

from app.services.presentation_analysis_service import (
    PresentationAnalysisService
)


load_dotenv()


audio_path = "audio/test.wav"


print(
    "Loading PresentationAnalysisService..."
)

service = (
    PresentationAnalysisService()
)

print(
    "PresentationAnalysisService loaded!"
)

print(
    "Starting full presentation analysis..."
)


# ==========================================
# 전체 분석 + Gemini 코칭
# ==========================================

result = service.analyze(
    audio_path
)


print(
    "\n===== BASIC ====="
)

print(
    "Transcript:"
)

print(
    result["transcript"]
)

print(
    "\nEmotion:",
    result["emotion"]
)

print(
    "Duration:",
    result["duration"],
    "초"
)


# ==========================================
# Speech
# ==========================================

speech = result[
    "speech"
]

print(
    "\n===== SPEECH ====="
)

print(
    "어절 수:",
    speech[
        "word_count"
    ]
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
    "Pause 시간:",
    speech[
        "internal_pause_time"
    ],
    "초"
)

print(
    "Pause 비율:",
    speech[
        "internal_pause_ratio"
    ]
)


# ==========================================
# Fillers
# ==========================================

print(
    "\n===== FILLERS ====="
)

if not result[
    "fillers"
]:

    print(
        "탐지된 추임새/반복 없음"
    )

else:

    for occurrence in result[
        "fillers"
    ]:

        print(
            f"[{occurrence['type']}] "
            f"{occurrence['text']} "
            f"("
            f"{occurrence['start']:.2f}s"
            f" ~ "
            f"{occurrence['end']:.2f}s"
            f")"
        )


# ==========================================
# Risk
# ==========================================

risk = result[
    "risk"
]

print(
    "\n===== RISK ====="
)

print(
    "전체 위험 점수:",
    risk[
        "overall_score"
    ]
)

print(
    "전체 위험 수준:",
    risk[
        "overall_level"
    ]
)


print(
    "\n===== HEATMAP ====="
)

for window in risk[
    "heatmap"
]:

    print(
        "\n----------------------------"
    )

    print(
        f"{window['start']:.2f}s"
        f" ~ "
        f"{window['end']:.2f}s"
    )

    print(
        "어절:",
        window[
            "word_count"
        ]
    )

    print(
        "체감 속도:",
        window[
            "presentation_rate"
        ],
        "어절/분"
    )

    print(
        "속도 판정:",
        window[
            "pace_level"
        ]
    )

    print(
        "Pause:",
        window[
            "pause_count"
        ],
        "회"
    )

    print(
        "추임새:",
        window[
            "filler_count"
        ],
        "회"
    )

    print(
        "반복:",
        window[
            "repetition_count"
        ],
        "회"
    )

    print(
        "Risk:",
        window[
            "score"
        ],
        "/",
        window[
            "level"
        ]
    )

    if window[
        "reasons"
    ]:

        print(
            "이유:"
        )

        for reason in window[
            "reasons"
        ]:

            print(
                "-",
                reason
            )


# ==========================================
# Coaching
# ==========================================

coaching = result[
    "coaching"
]

print(
    "\n===== COACHING ====="
)

print(
    json.dumps(
        coaching,
        ensure_ascii=False,
        indent=2,
    )
)


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
            "time_range",
            "",
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