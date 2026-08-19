import re


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

            text = segment.get(
                "text",
                ""
            ).strip()

            if not text:
                continue

            words = re.findall(
                r"\S+",
                text,
            )

            count += len(words)

        return count

    def _silence_gaps(
        self,
        segments: list[dict],
    ) -> list[dict]:

        gaps = []

        ordered = sorted(
            segments,
            key=lambda x: x["start"],
        )

        for previous, current in zip(
            ordered,
            ordered[1:],
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
                        "duration": gap,
                    }
                )

        return gaps