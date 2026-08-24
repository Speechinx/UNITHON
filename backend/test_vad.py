from funasr import AutoModel


print("Loading VAD...")

vad_model = AutoModel(
    model="fsmn-vad",
    device="cuda:0",
)

print("VAD loaded successfully!")

print("Starting VAD analysis...")

result = vad_model.generate(
    input="audio/test.wav",
)

print("\n===== VAD RESULT =====")

print(result)