from app.services.sensevoice import SenseVoiceService


print("Loading SenseVoice...")

service = SenseVoiceService()

print("SenseVoice loaded successfully!")
print("Starting audio analysis...")

result = service.analyze(
    "audio/test.wav"
)

print("\n===== RESULT =====")

print("Transcript:")
print(result["transcript"])

print("\nDuration:")
print(result["duration"])

print("\nSegments:")

for segment in result["segments"]:
    print(segment)