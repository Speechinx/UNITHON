import re


class SpeechAnalyzer:

    def analyze(
        self,
        segments: list[dict],
    ) -> dict:

        if not segments:

            return {
                "duration": 0,
                "speaking_time": 0,
                "silence_time": 0,
                "silence_ratio": 0,
                "word_count": 0,
                "speech_rate_wpm": 0,
            }

        duration = max(
            segment["end"]
            for segment in segments
        )

        speaking_time = sum(
            max(
                segment["end"] - segment["start"],
                0,
            )
            for segment in segments
        )

        silence_time = max(
            duration - speaking_time,
            0,
        )

        transcript = " ".join(
            segment["text"]
            for segment in segments
        )

        words = re.findall(
            r"[가-힣A-Za-z0-9]+",
            transcript,
        )

        word_count = len(words)

        if speaking_time > 0:

            wpm = (
                word_count
                / speaking_time
                * 60
            )

        else:

            wpm = 0

        silence_ratio = (
            silence_time / duration
            if duration > 0
            else 0
        )

        return {
            "duration": round(
                duration,
                2,
            ),

            "speaking_time": round(
                speaking_time,
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

            "word_count": word_count,

            "speech_rate_wpm": round(
                wpm,
                2,
            ),
        }