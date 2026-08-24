from app.services.sensevoice import (
    SenseVoiceService
)

from app.services.speech_analyzer import (
    SpeechAnalyzer
)

from app.services.filler_analyzer import (
    FillerAnalyzer
)

from app.services.risk_analyzer import (
    RiskAnalyzer
)


audio_path = "audio/test.wav"


# ==========================================
# 1. SenseVoice
# ==========================================

print("Loading SenseVoice...")

sensevoice = SenseVoiceService()

print("SenseVoice loaded!")

print("Starting SenseVoice analysis...")

sensevoice_result = sensevoice.analyze(
    audio_path
)

print("SenseVoice analysis complete!")


# ==========================================
# 2. SpeechAnalyzer
# ==========================================

print(
    "\nStarting SpeechAnalyzer..."
)

speech_analyzer = SpeechAnalyzer()

speech_result = (
    speech_analyzer.analyze(
        sensevoice_result[
            "segments"
        ],
        audio_path,
    )
)

print(
    "SpeechAnalyzer complete!"
)


# ==========================================
# 3. FillerAnalyzer
# ==========================================

print(
    "\nStarting FillerAnalyzer..."
)

filler_analyzer = FillerAnalyzer()

filler_result = (
    filler_analyzer.analyze(
        sensevoice_result[
            "segments"
        ]
    )
)

print(
    "FillerAnalyzer complete!"
)


# ==========================================
# 4. RiskAnalyzer
# ==========================================

print(
    "\nStarting RiskAnalyzer..."
)

risk_analyzer = RiskAnalyzer()

risk_result = (
    risk_analyzer.analyze(
        duration=speech_result[
            "duration"
        ],

        segments=sensevoice_result[
            "segments"
        ],

        speech_result=(
            speech_result
        ),

        filler_result=(
            filler_result
        ),
    )
)

print(
    "RiskAnalyzer complete!"
)


# ==========================================
# 전체 Speech 결과
# ==========================================

print(
    "\n===== SPEECH RESULT ====="
)

print(
    "어절 수:",
    speech_result[
        "word_count"
    ]
)

print(
    "발표 체감 속도:",
    speech_result[
        "presentation_rate"
    ],
    "어절/분"
)

print(
    "실제 발화 속도:",
    speech_result[
        "articulation_rate"
    ],
    "어절/분"
)

print(
    "속도 판정:",
    speech_result[
        "pace_level"
    ]
)

print(
    "Pause 비율:",
    speech_result[
        "internal_pause_ratio"
    ]
)


# ==========================================
# Filler 결과
# ==========================================

print(
    "\n===== FILLER RESULT ====="
)

if not filler_result:

    print(
        "탐지된 추임새/반복 없음"
    )

else:

    for occurrence in filler_result:

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
# Risk 결과
# ==========================================

print(
    "\n===== RISK RESULT ====="
)

print(
    "전체 위험 점수:",
    risk_result[
        "overall_score"
    ]
)

print(
    "전체 위험 수준:",
    risk_result[
        "overall_level"
    ]
)


# ==========================================
# Heatmap
# ==========================================

print(
    "\n===== HEATMAP ====="
)

for window in risk_result[
    "heatmap"
]:

    print(
        "\n----------------------------"
    )

    print(
        f"구간: "
        f"{window['start']:.2f}s"
        f" ~ "
        f"{window['end']:.2f}s"
    )

    print(
        "구간 길이:",
        window["duration"],
        "초"
    )

    print(
        "어절 수:",
        window["word_count"]
    )

    print(
        "발표 시간:",
        window[
            "presentation_time"
        ],
        "초"
    )

    print(
        "실제 발화 시간:",
        window[
            "speech_time"
        ],
        "초"
    )

    print(
        "구간 체감 속도:",
        window[
            "presentation_rate"
        ],
        "어절/분"
    )

    print(
        "구간 실제 발화 속도:",
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
        "Pause 시간:",
        window[
            "pause_time"
        ],
        "초"
    )

    print(
        "Pause:",
        window[
            "pause_count"
        ],
        "회"
    )

    print(
        "1초 이상 Pause:",
        window[
            "long_pause_count"
        ],
        "회"
    )

    print(
        "1.5초 이상 Pause:",
        window[
            "very_long_pause_count"
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
        "위험 점수:",
        window[
            "score"
        ]
    )

    print(
        "위험 수준:",
        window[
            "level"
        ]
    )

    print(
        "위험 이유:"
    )

    if not window[
        "reasons"
    ]:

        print(
            "- 특이사항 없음"
        )

    else:

        for reason in window[
            "reasons"
        ]:

            print(
                "-",
                reason
            )