class SpeechAnalyzer:

    def analyze(
        self,
        segments: list[dict],
    ) -> dict:

        if not segments:
            return {
                "word_count": 0,
                "speaking_time": 0,
                "speech_rate_wpm": 0,
                "silence_time": 0,
                "silence_ratio": 0,
            }

        word_count = self._count_words(
            segments
        )

        speaking_time = sum(
            max(
                segment["end"]
                - segment["start"],
                0,
            )
            for segment in segments
        )

        silence_gaps = self._silence_gaps(
            segments
        )

        silence_time = sum(
            gap["duration"]
            for gap in silence_gaps
        )

        if speaking_time > 0:

            speech_rate = (
                word_count
                / speaking_time
                * 60
            )

        else:

            speech_rate = 0

        total_duration = (
            max(
                segment["end"]
                for segment in segments
            )
        )

        silence_ratio = (
            silence_time / total_duration
            if total_duration > 0
            else 0
        )

        return {
            "word_count": word_count,
            "speaking_time": round(
                speaking_time,
                2,
            ),
            "speech_rate_wpm": round(
                speech_rate,
                2,
            ),
            "silence_time": round(
                silence_time,
                2,
            ),
            "silence_ratio": round(
                silence_ratio,
                3,
            ),
        }

    def _count_words(
        self,
        segments: list[dict],
    ) -> int:

        count = 0

        for segment in segments:

            normalized_words = segment.get(
                "normalized_words",
                []
            )

            count += len(normalized_words)

        return count

    def _silence_gaps(
        self,
        segments: list[dict],
    ) -> list[dict]:

        gaps = []

        speech_intervals = []

        # --------------------------------
        # 모든 세부 발화 구간 수집
        # --------------------------------

        for segment in segments:

            timestamps = segment.get(
                "timestamps",
                []
            )

            for timestamp in timestamps:

                speech_intervals.append(
                    {
                        "start": timestamp["start"],
                        "end": timestamp["end"],
                    }
                )

        # --------------------------------
        # 시간순 정렬
        # --------------------------------

        speech_intervals.sort(
            key=lambda x: x["start"]
        )

        # --------------------------------
        # 발화 사이의 침묵 계산
        # --------------------------------

        for previous, current in zip(
            speech_intervals,
            speech_intervals[1:],
        ):

            gap = (
                current["start"]
                - previous["end"]
            )

            if gap >= 1.0:

                gaps.append(
                    {
                        "start": previous["end"],
                        "end": current["start"],
                        "duration": round(
                            gap,
                            3,
                        ),
                    }
                )

        return gaps