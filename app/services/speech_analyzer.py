from app.services.audio_pause_analyzer import AudioPauseAnalyzer


class SpeechAnalyzer:
    def __init__(self):
        self.pause_analyzer = AudioPauseAnalyzer()

    def analyze(
        self,
        segments: list[dict],
        audio_path: str,
    ) -> dict:

        # ==========================================
        # 1. Kiwi 기준 어절 수
        # ==========================================

        word_count = self._count_words(
            segments
        )

        # ==========================================
        # 2. WAV 기반 pause 분석
        # ==========================================

        pause_result = (
            self.pause_analyzer.analyze(
                audio_path
            )
        )

        speech_time = pause_result[
            "speech_time"
        ]

        # ==========================================
        # 3. 한국어 말하기 속도 계산
        # ==========================================

        speech_rate = (
            word_count
            / speech_time
            * 60
            if speech_time > 0
            else 0
        )

        # ==========================================
        # 4. 결과 반환
        # ==========================================

        return {
            "word_count": word_count,

            "duration": pause_result[
                "duration"
            ],

            "presentation_duration": (
                pause_result[
                    "presentation_duration"
                ]
            ),

            "leading_silence": (
                pause_result[
                    "leading_silence"
                ]
            ),

            "trailing_silence": (
                pause_result[
                    "trailing_silence"
                ]
            ),

            "speech_time": speech_time,

            "internal_pause_time": (
                pause_result[
                    "internal_pause_time"
                ]
            ),

            "internal_pause_ratio": (
                pause_result[
                    "internal_pause_ratio"
                ]
            ),

            "speech_rate": round(
                speech_rate,
                2,
            ),

            "internal_pauses": (
                pause_result[
                    "internal_pauses"
                ]
            ),
        }

    def _count_words(
        self,
        segments: list[dict],
    ) -> int:
        """
        SenseVoiceService 내부에서
        TextNormalizer가 만들어준 normalized_words를 이용해
        한국어 어절 수를 계산한다.
        """

        return sum(
            len(
                segment.get(
                    "normalized_words",
                    [],
                )
            )
            for segment in segments
        )