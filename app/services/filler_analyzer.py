import re
from collections import Counter


KNOWN_FILLERS = {
    "음",
    "어",
    "에",
    "아",
    "그",
    "저",
    "뭐",
    "약간",
    "사실",
    "그러니까",
    "이제",
    "뭔가",
    "일단",
}


class FillerAnalyzer:

    def analyze(self, segments: list[dict]) -> dict:

        occurrences = []

        filler_counter = Counter()
        repeated_counter = Counter()

        for segment in segments:

            text = segment["text"]

            words = self._tokenize(text)

            # --------------------------------
            # 1. 알려진 추임새
            # --------------------------------

            for index, word in enumerate(words):

                if word in KNOWN_FILLERS:

                    filler_counter[word] += 1

                    occurrences.append(
                        {
                            "type": "filler",
                            "word": word,
                            "start": segment["start"],
                            "end": segment["end"],
                        }
                    )

            # --------------------------------
            # 2. 연속 반복
            # --------------------------------

            for i in range(len(words) - 1):

                current = words[i]
                next_word = words[i + 1]

                if current == next_word:

                    if len(current) >= 1:

                        repeated_counter[current] += 1

                        occurrences.append(
                            {
                                "type": "repetition",
                                "word": current,
                                "start": segment["start"],
                                "end": segment["end"],
                            }
                        )

        return {
            "total_count": sum(
                filler_counter.values()
            ),

            "words": dict(
                filler_counter
            ),

            "repeated_words": dict(
                repeated_counter
            ),

            "occurrences": occurrences,
        }

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:

        return re.findall(
            r"[가-힣A-Za-z0-9]+",
            text,
        )