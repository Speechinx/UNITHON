from app.services.sensevoice import SenseVoiceService
from app.services.filler_analyzer import FillerAnalyzer


print("Loading SenseVoice...")

sensevoice = SenseVoiceService()

print("SenseVoice loaded!")

print("\nAnalyzing audio...")

result = sensevoice.analyze(
    "audio/test.wav"
)

segments = result["segments"]

print("\n===== TRANSCRIPT =====")

print(result["transcript"])


print("\n===== FILLER ANALYSIS =====")

analyzer = FillerAnalyzer()

occurrences = analyzer.analyze(
    segments
)


if not occurrences:

    print("추임새 또는 반복이 발견되지 않았습니다.")

else:

    for item in occurrences:

        print(
            f"[{item['type']}] "
            f"{item['text']} "
            f"({item['start']:.2f}s"
            f" ~ "
            f"{item['end']:.2f}s)"
        )


print("\n===== SUMMARY =====")

filler_count = sum(
    1
    for item in occurrences
    if item["type"] == "filler"
)

repetition_count = sum(
    1
    for item in occurrences
    if item["type"] == "repetition"
)

print(
    f"추임새: {filler_count}회"
)

print(
    f"반복: {repetition_count}회"
)

print(
    f"전체 탐지: {len(occurrences)}회"
)