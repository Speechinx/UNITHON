from typing import Any

from funasr import AutoModel

from app.core.config import settings


class SenseVoiceService:

    def __init__(self):
        print("Loading SenseVoice...")

        self.model = AutoModel(
            model="iic/SenseVoiceSmall",

            vad_model="fsmn-vad",

            vad_kwargs={
                "max_single_segment_time": 30000
            },

            spk_model="cam++",

            device=settings.sensevoice_device,
        )

        print("SenseVoice loaded.")

    def analyze(
        self,
        audio_path: str,
    ) -> dict[str, Any]:

        result = self.model.generate(
            input=audio_path,
            cache={},

            language="auto",

            use_itn=True,

            batch_size_s=60,

            merge_vad=True,

            merge_length_s=15,
        )

        if not result:
            return {
                "text": "",
                "sentence_info": [],
            }

        return result[0]