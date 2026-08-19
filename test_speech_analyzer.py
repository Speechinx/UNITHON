from app.services.sensevoice import SenseVoiceService
from app.services.speech_analyzer import SpeechAnalyzer


print("Loading SenseVoice...")

sensevoice = SenseVoiceService()

print("SenseVoice loaded!")

print("\nAnalyzing audio...")

result = sensevoice.analyze(
    "audio/test.wav"
)

segments = result["segments"]

print("\n===== SENSEVOICE RESULT =====")

print("Transcript:")
print(result["transcript"])

print("\nDuration:")
print(result["duration"])

print("\n===== SPEECH ANALYSIS =====")

analyzer = SpeechAnalyzer()

analysis = analyzer.analyze(
    segments
)

print("어절 수:")
print(analysis["word_count"])

print("발화 시간:")
print(analysis["speaking_time"])

print("말하기 속도:")
print(
    analysis["speech_rate_wpm"],
    "어절/분"
)

print("침묵 시간:")
print(
    analysis["silence_time"],
    "초"
)

print("침묵 비율:")
print(
    analysis["silence_ratio"]
)

print("\n===== SILENCE GAPS =====")

gaps = analyzer._silence_gaps(
    segments
)

for gap in gaps:
    print(
        f"{gap['start']:.2f}s"
        f" ~ "
        f"{gap['end']:.2f}s"
        f" "
        f"({gap['duration']:.2f}s)"
    )