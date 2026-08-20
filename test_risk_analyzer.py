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

print("\nStarting SpeechAnalyzer...")

speech_analyzer = SpeechAnalyzer()

speech_result = speech_analyzer.analyze(
    sensevoice_result["segments"],
    audio_path,
)

print("SpeechAnalyzer complete!")


# ==========================================
# 3. FillerAnalyzer
# ==========================================

print("\nStarting FillerAnalyzer...")

filler_analyzer = FillerAnalyzer()

filler_result = filler_analyzer.analyze(
    sensevoice_result["segments"]
)

print("FillerAnalyzer complete!")


# ==========================================
# 4. RiskAnalyzer
# ==========================================

print("\nStarting RiskAnalyzer...")

risk_analyzer = RiskAnalyzer()

risk_result = risk_analyzer.analyze(
    duration=speech_result["duration"],

    segments=sensevoice_result[
        "segments"
    ],

    speech_result=speech_result,

    filler_result=filler_result,
)

print("RiskAnalyzer complete!")


# ==========================================
# SenseVoice 결과
# ==========================================

print(
    "\n===== SENSEVOICE RESULT ====="
)

print("Transcript:")

print(
    sensevoice_result["transcript"]
)

print("\nDuration:")

print(
    sensevoice_result["duration"],
    "초"
)


# ==========================================
# Speech 결과
# ==========================================

print(
    "\n===== SPEECH RESULT ====="
)

print(
    "어절 수:",
    speech_result["word_count"]
)

print(
    "전체 녹음:",
    speech_result["duration"],
    "초"
)

print(
    "발표 구간:",
    speech_result[
        "presentation_duration"
    ],
    "초"
)

print(
    "실제 발화:",
    speech_result["speech_time"],
    "초"
)

print(
    "Pause 시간:",
    speech_result[
        "internal_pause_time"
    ],
    "초"
)

print(
    "Pause 비율:",
    speech_result[
        "internal_pause_ratio"
    ]
)

print(
    "전체 평균 말하기 속도:",
    speech_result["speech_rate"],
    "어절/분"
)


# ==========================================
# 추임새 / 반복 결과
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

        occurrence_type = (
            occurrence.get(
                "type",
                "unknown",
            )
        )

        text = occurrence.get(
            "text",
            "",
        )

        start = occurrence.get(
            "start",
            0,
        )

        end = occurrence.get(
            "end",
            0,
        )

        print(
            f"[{occurrence_type}] "
            f"{text} "
            f"({start:.2f}s"
            f" ~ "
            f"{end:.2f}s)"
        )


# ==========================================
# Risk 결과
# ==========================================

print(
    "\n===== RISK RESULT ====="
)

print(
    "전체 위험 점수:",
    risk_result["overall_score"]
)

print(
    "전체 위험 수준:",
    risk_result["overall_level"]
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
        "실제 발화 시간:",
        window["speech_time"],
        "초"
    )

    print(
        "구간 말하기 속도:",
        window["speech_rate"],
        "어절/분"
    )

    print(
        "Pause 시간:",
        window["pause_time"],
        "초"
    )

    print(
        "Pause:",
        window["pause_count"],
        "회"
    )

    print(
        "1초 이상 Pause:",
        window["long_pause_count"],
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
        window["filler_count"],
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
        window["score"]
    )

    print(
        "위험 수준:",
        window["level"]
    )

    print(
        "위험 이유:"
    )

    if not window["reasons"]:

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