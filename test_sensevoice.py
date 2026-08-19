from funasr import AutoModel


print("Loading SenseVoice...")

model = AutoModel(
    model="iic/SenseVoiceSmall",
    vad_model="fsmn-vad",
    vad_kwargs={
        "max_single_segment_time": 30000
    },
    spk_model="cam++",
    device="cuda:0",
)

print("SenseVoice loaded successfully!")