from app.services.sensevoice import (
    SenseVoiceService
)

from app.services.speech_analyzer import (
    SpeechAnalyzer
)


audio_path = "audio/test.wav"


print("Loading SenseVoice...")

sensevoice = SenseVoiceService()

print("SenseVoice loaded successfully!")

print("Starting audio analysis...")


# ==========================================
# SenseVoice 분석
# ==========================================

sensevoice_result = (
    sensevoice.analyze(
        audio_path
    )
)


print("\n===== SENSEVOICE RESULT =====")

print("Transcript:")
print(
    sensevoice_result[
        "transcript"
    ]
)

print("\nDuration:")
print(
    sensevoice_result[
        "duration"
    ]
)


# ==========================================
# SpeechAnalyzer 분석
# ==========================================

speech_analyzer = SpeechAnalyzer()

speech_result = (
    speech_analyzer.analyze(
        sensevoice_result[
            "segments"
        ],
        audio_path,
    )
)


print("\n===== SPEECH ANALYSIS =====")

print("어절 수:")
print(
    speech_result[
        "word_count"
    ]
)

print("전체 녹음 길이:")
print(
    speech_result[
        "duration"
    ],
    "초"
)

print("실제 발표 구간:")
print(
    speech_result[
        "presentation_duration"
    ],
    "초"
)

print("시작 전 무음:")
print(
    speech_result[
        "leading_silence"
    ],
    "초"
)

print("종료 후 무음:")
print(
    speech_result[
        "trailing_silence"
    ],
    "초"
)

print("실제 발화 시간:")
print(
    speech_result[
        "speech_time"
    ],
    "초"
)

print("발표 중 Pause 시간:")
print(
    speech_result[
        "internal_pause_time"
    ],
    "초"
)

print("발표 중 Pause 비율:")
print(
    speech_result[
        "internal_pause_ratio"
    ]
)

print("말하기 속도:")
print(
    speech_result[
        "speech_rate"
    ],
    "어절/분"
)


print("\n===== INTERNAL PAUSES =====")

if not speech_result[
    "internal_pauses"
]:
    print(
        "탐지된 내부 pause 없음"
    )

else:
    for pause in speech_result[
        "internal_pauses"
    ]:
        print(
            f"{pause['start']:.2f}s"
            f" ~ "
            f"{pause['end']:.2f}s "
            f"({pause['duration']:.2f}s)"
        )