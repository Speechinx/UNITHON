from app.services.sensevoice import SenseVoiceService
from app.services.speech_analyzer import SpeechAnalyzer


print("Loading SenseVoice...")

sensevoice = SenseVoiceService()

print("SenseVoice loaded successfully!")

print("Starting audio analysis...")

result = sensevoice.analyze(
    "audio/test.wav"
)

print("\n===== SENSEVOICE RESULT =====")

print("Transcript:")
print(result["transcript"])

print("\nDuration:")
print(result["duration"])


# SpeechAnalyzer 실행
speech_analyzer = SpeechAnalyzer()

analysis = speech_analyzer.analyze(
    result["segments"]
)


print("\n===== SPEECH ANALYSIS =====")

print("어절 수:")
print(analysis["word_count"])

print("분석 구간:")
print(
    analysis["presentation_duration"],
    "초"
)

print("실제 발화 시간:")
print(
    analysis["speaking_time"],
    "초"
)

print("Pause 시간:")
print(
    analysis["pause_time"],
    "초"
)

print("Pause 비율:")
print(
    analysis["pause_ratio"]
)

print("말하기 속도:")
print(
    analysis["speech_rate"],
    "어절/분"
)


print("\n===== PAUSES =====")

if not analysis["pauses"]:
    print("탐지된 pause 없음")

else:
    for pause in analysis["pauses"]:
        print(
            f"{pause['start']:.2f}s"
            f" ~ "
            f"{pause['end']:.2f}s "
            f"({pause['duration']:.2f}s)"
        )