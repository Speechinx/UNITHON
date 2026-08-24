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
print(
    result["transcript"]
)

print("\nEmotion:")
print(
    result["emotion"]
)

print("\nDuration:")
print(
    result["duration"]
)

print("\nSegments:")

for segment in result["segments"]:

    print(
        "\nTEXT:"
    )

    print(
        segment["text"]
    )

    print(
        "EMOTION:",
        segment["emotion"]
    )

    print(
        "SPEAKER:",
        segment["speaker"]
    )