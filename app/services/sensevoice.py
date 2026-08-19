from funasr import AutoModel


class SenseVoiceService:

    def __init__(self):

        self.model = AutoModel(
            model="iic/SenseVoiceSmall",
            vad_model="fsmn-vad",
            vad_kwargs={
                "max_single_segment_time": 30000
            },
            spk_model="cam++",
            device="cuda:0",
        )

    def analyze(self, audio_path: str) -> dict:

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
                "transcript": "",
                "duration": 0,
                "segments": [],
            }

        item = result[0]

        transcript = self._clean_text(
            item.get("text", "")
        )

        segments = self._build_segments(
            item.get("sentence_info", [])
        )

        duration = 0

        if segments:
            duration = max(
                segment["end"]
                for segment in segments
            )

        return {
            "transcript": transcript,
            "duration": round(duration, 2),
            "segments": segments,
        }

    def _build_segments(
        self,
        sentence_info: list[dict],
    ) -> list[dict]:

        segments = []

        for sentence in sentence_info:

            timestamp = sentence.get(
                "timestamp",
                []
            )

            if not timestamp:
                continue

            start = timestamp[0][0] / 1000
            end = timestamp[-1][1] / 1000

            text = self._clean_text(
                sentence.get(
                    "sentence",
                    ""
                )
            )

            segments.append(
                {
                    "start": round(start, 3),
                    "end": round(end, 3),
                    "text": text,
                    "speaker": sentence.get(
                        "spk",
                        0
                    ),

                    # SenseVoice의 세부 timestamp 보존
                    "timestamps": [
                        {
                            "start": t[0] / 1000,
                            "end": t[1] / 1000,
                        }
                        for t in timestamp
                    ],
                }
            )

        return segments

    def _clean_text(
        self,
        text: str,
    ) -> str:

        tags = [
            "<|ko|>",
            "<|en|>",
            "<|zh|>",
            "<|ja|>",
            "<|EMO_UNKNOWN|>",
            "<|Speech|>",
            "<|withitn|>",
        ]

        for tag in tags:
            text = text.replace(
                tag,
                ""
            )

        return text.strip()