class SpeechAnalyzer:

    # 발표 중 pause라고 판단할 최소 시간
    PAUSE_THRESHOLD = 0.8

    def analyze(
        self,
        segments: list[dict],
    ) -> dict:

        if not segments:
            return {
                "word_count": 0,
                "presentation_duration": 0,
                "speaking_time": 0,
                "pause_time": 0,
                "pause_ratio": 0,
                "speech_rate": 0,
                "pauses": [],
            }

        word_count = self._count_words(
            segments
        )

        speech_intervals = (
            self._collect_speech_intervals(
                segments
            )
        )

        if not speech_intervals:
            return {
                "word_count": word_count,
                "presentation_duration": 0,
                "speaking_time": 0,
                "pause_time": 0,
                "pause_ratio": 0,
                "speech_rate": 0,
                "pauses": [],
            }

        pauses = self._find_pauses(
            speech_intervals
        )

        first_speech = (
            speech_intervals[0]["start"]
        )

        last_speech = (
            speech_intervals[-1]["end"]
        )

        presentation_duration = (
            last_speech - first_speech
        )

        pause_time = sum(
            pause["duration"]
            for pause in pauses
        )

        speaking_time = max(
            presentation_duration
            - pause_time,
            0,
        )

        speech_rate = (
            word_count
            / speaking_time
            * 60
            if speaking_time > 0
            else 0
        )

        pause_ratio = (
            pause_time
            / presentation_duration
            if presentation_duration > 0
            else 0
        )

        return {
            "word_count": word_count,

            "presentation_duration": round(
                presentation_duration,
                2,
            ),

            "speaking_time": round(
                speaking_time,
                2,
            ),

            "pause_time": round(
                pause_time,
                2,
            ),

            "pause_ratio": round(
                pause_ratio,
                3,
            ),

            # 한국어이므로 WPM보다는
            # 어절/분으로 보는 것이 적절
            "speech_rate": round(
                speech_rate,
                2,
            ),

            "pauses": pauses,
        }

    # ==============================================
    # Kiwi로 만든 normalized_words 개수
    # ==============================================

    def _count_words(
        self,
        segments: list[dict],
    ) -> int:

        return sum(
            len(
                segment.get(
                    "normalized_words",
                    [],
                )
            )
            for segment in segments
        )

    # ==============================================
    # SenseVoice 세부 timestamp 수집
    # ==============================================

    def _collect_speech_intervals(
        self,
        segments: list[dict],
    ) -> list[dict]:

        intervals = []

        for segment in segments:

            for timestamp in segment.get(
                "timestamps",
                [],
            ):

                intervals.append(
                    {
                        "start": timestamp[
                            "start"
                        ],
                        "end": timestamp[
                            "end"
                        ],
                    }
                )

        return sorted(
            intervals,
            key=lambda x: x["start"],
        )

    # ==============================================
    # 발표 도중 pause 탐지
    # ==============================================

    def _find_pauses(
        self,
        intervals: list[dict],
    ) -> list[dict]:

        pauses = []

        for previous, current in zip(
            intervals,
            intervals[1:],
        ):

            gap = (
                current["start"]
                - previous["end"]
            )

            if gap >= self.PAUSE_THRESHOLD:

                pauses.append(
                    {
                        "start": round(
                            previous["end"],
                            3,
                        ),
                        "end": round(
                            current["start"],
                            3,
                        ),
                        "duration": round(
                            gap,
                            3,
                        ),
                    }
                )

        return pauses