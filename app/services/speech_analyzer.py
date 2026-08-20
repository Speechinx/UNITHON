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

        speech_time = pause_result.get(
            "speech_time",
            0,
        )

        presentation_duration = (
            pause_result.get(
                "presentation_duration",
                0,
            )
        )

        # ==========================================
        # 3. 발표 전체 체감 속도
        #
        # pause를 포함한 실제 발표 구간을 기준으로 계산
        # ==========================================

        presentation_rate = (
            word_count
            / presentation_duration
            * 60
            if presentation_duration > 0
            else 0
        )

        # ==========================================
        # 4. 실제 발화 순간의 속도
        #
        # pause를 제외한 실제 음성 구간 기준
        # ==========================================

        articulation_rate = (
            word_count
            / speech_time
            * 60
            if speech_time > 0
            else 0
        )

        # ==========================================
        # 5. 발표 속도 수준
        # ==========================================

        pace_level = self._get_pace_level(
            presentation_rate
        )

        # ==========================================
        # 6. 최종 결과
        # ==========================================

        return {
            "word_count": word_count,

            "duration": pause_result.get(
                "duration",
                0,
            ),

            "presentation_duration": (
                presentation_duration
            ),

            "leading_silence": (
                pause_result.get(
                    "leading_silence",
                    0,
                )
            ),

            "trailing_silence": (
                pause_result.get(
                    "trailing_silence",
                    0,
                )
            ),

            "speech_time": speech_time,

            "internal_pause_time": (
                pause_result.get(
                    "internal_pause_time",
                    0,
                )
            ),

            "internal_pause_ratio": (
                pause_result.get(
                    "internal_pause_ratio",
                    0,
                )
            ),

            "presentation_rate": round(
                presentation_rate,
                2,
            ),

            "articulation_rate": round(
                articulation_rate,
                2,
            ),

            "pace_level": pace_level,

            "internal_pauses": (
                pause_result.get(
                    "internal_pauses",
                    [],
                )
            ),
        }

    def _count_words(
        self,
        segments: list[dict],
    ) -> int:
        """
        SenseVoiceService 안에서
        TextNormalizer가 생성한 normalized_words 기준으로
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

    def _get_pace_level(
        self,
        presentation_rate: float,
    ) -> str:
        """
        발표 전체 체감 속도를 기준으로 분류한다.

        현재 값은 MVP용 기준이며,
        향후 실제 발표 데이터로 튜닝한다.
        """

        if presentation_rate <= 0:
            return "unknown"

        if presentation_rate < 70:
            return "slow"

        if presentation_rate > 160:
            return "fast"

        return "normal"