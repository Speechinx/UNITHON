from app.services.audio_pause_analyzer import (
    AudioPauseAnalyzer
)


audio_path = "audio/test.wav"

print("Starting audio pause analysis...")

analyzer = AudioPauseAnalyzer()

result = analyzer.analyze(
    audio_path
)


print("\n===== AUDIO PAUSE ANALYSIS =====")

print("전체 녹음 길이:")
print(
    result["duration"],
    "초"
)

print("실제 발표 구간:")
print(
    result["presentation_duration"],
    "초"
)

print("시작 전 무음:")
print(
    result["leading_silence"],
    "초"
)

print("종료 후 무음:")
print(
    result["trailing_silence"],
    "초"
)

print("발표 중 Pause 시간:")
print(
    result["internal_pause_time"],
    "초"
)

print("발표 중 Pause 비율:")
print(
    result["internal_pause_ratio"]
)

print("추정 실제 발화 시간:")
print(
    result["speech_time"],
    "초"
)

print("RMS threshold:")
print(
    result["threshold"]
)


print("\n===== INTERNAL PAUSES =====")

if not result["internal_pauses"]:
    print("탐지된 내부 pause 없음")

else:
    for pause in result[
        "internal_pauses"
    ]:
        print(
            f"{pause['start']:.2f}s"
            f" ~ "
            f"{pause['end']:.2f}s "
            f"({pause['duration']:.2f}s)"
        )