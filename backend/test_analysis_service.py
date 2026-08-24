from app.services.analysis_service import (
    AnalysisService
)


audio_path = "audio/test.wav"


print(
    "Loading AnalysisService..."
)

service = AnalysisService()

print(
    "AnalysisService loaded!"
)

print(
    "Starting full analysis..."
)


result = service.analyze(
    audio_path
)


# ==========================================
# Basic
# ==========================================

print(
    "\n===== BASIC RESULT ====="
)

print(
    "Transcript:"
)

print(
    result[
        "transcript"
    ]
)

print(
    "\nEmotion:",
    result[
        "emotion"
    ]
)

print(
    "Duration:",
    result[
        "duration"
    ],
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
    "발표 구간:",
    speech[
        "presentation_duration"
    ],
    "초"
)

print(
    "실제 발화 시간:",
    speech[
        "speech_time"
    ],
    "초"
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


# ==========================================
# Fillers
# ==========================================

print(
    "\n===== FILLERS ====="
)

fillers = result[
    "fillers"
]

if not fillers:

    print(
        "탐지된 추임새/반복 없음"
    )

else:

    for occurrence in fillers:

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


# ==========================================
# Heatmap
# ==========================================

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
        "발표 시간:",
        window[
            "presentation_time"
        ]
    )

    print(
        "실제 발화 시간:",
        window[
            "speech_time"
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
        "실제 발화 속도:",
        window[
            "articulation_rate"
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