import re

from funasr import AutoModel

from app.services.text_normalizer import (
    TextNormalizer
)


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

        self.normalizer = TextNormalizer()

    def analyze(self, audio_path: str) -> dict:
        result = self.model.generate(
            input=audio_path,
            cache={},
            language="ko",
            use_itn=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )

        if not result:
            return {
                "transcript": "",
                "emotion": "unknown",
                "duration": 0,
                "segments": [],
            }

        item = result[0]

        raw_text = item.get(
            "text",
            "",
        )

        # 전체 감정 추출
        emotion = self._extract_emotion(
            raw_text
        )

        # 태그가 제거된 순수 transcript
        transcript = self._clean_text(
            raw_text
        )

        segments = self._build_segments(
            item.get(
                "sentence_info",
                [],
            )
        )

        duration = 0

        if segments:
            duration = max(
                segment["end"]
                for segment in segments
            )

        return {
            "transcript": transcript,
            "emotion": emotion,
            "duration": round(
                duration,
                2,
            ),
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
                [],
            )

            if not timestamp:
                continue

            start = (
                timestamp[0][0]
                / 1000
            )

            end = (
                timestamp[-1][1]
                / 1000
            )

            raw_text = sentence.get(
                "sentence",
                "",
            )

            # segment별 감정
            emotion = self._extract_emotion(
                raw_text
            )

            # 실제 사용자에게 보여줄 텍스트
            text = self._clean_text(
                raw_text
            )

            segment = {
                "start": round(
                    start,
                    3,
                ),

                "end": round(
                    end,
                    3,
                ),

                "text": text,

                "emotion": emotion,

                "speaker": sentence.get(
                    "spk",
                    0,
                ),

                # SenseVoice 세부 timestamp 보존
                "timestamps": [
                    {
                        "start": t[0] / 1000,
                        "end": t[1] / 1000,
                    }
                    for t in timestamp
                ],
            }

            # Kiwi 기반 어절 분석
            segment[
                "normalized_words"
            ] = (
                self.normalizer
                .normalize_segment(
                    segment
                )
            )

            segments.append(
                segment
            )

        return segments

    def _extract_emotion(
        self,
        text: str,
    ) -> str:
        """
        SenseVoice 감정 태그 추출.

        예:
        <|SAD|>     -> sad
        <|HAPPY|>   -> happy
        <|ANGRY|>   -> angry
        <|NEUTRAL|> -> neutral
        """

        if not text:
            return "unknown"

        # SenseVoice에서 자주 나오는 감정 태그
        emotion_tags = {
            "HAPPY": "happy",
            "SAD": "sad",
            "ANGRY": "angry",
            "NEUTRAL": "neutral",
            "FEARFUL": "fearful",
            "DISGUSTED": "disgusted",
            "SURPRISED": "surprised",
            "EMO_UNKNOWN": "unknown",
        }

        tags = re.findall(
            r"<\|([^|]+)\|>",
            text,
        )

        for tag in tags:
            tag = tag.upper()

            if tag in emotion_tags:
                return emotion_tags[
                    tag
                ]

        return "unknown"

    def _clean_text(
        self,
        text: str,
    ) -> str:
        """
        SenseVoice가 붙이는 모든 <|...|> 태그 제거.

        예:
        <|ko|><|SAD|><|Speech|><|withitn|>안녕하세요

        ->
        안녕하세요
        """

        if not text:
            return ""

        text = re.sub(
            r"<\|.*?\|>",
            "",
            text,
        )

        return text.strip()