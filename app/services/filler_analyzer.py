import re


class FillerAnalyzer:

    # --------------------------------
    # 기본 추임새
    # --------------------------------

    FILLERS = {
        "음",
        "어",
        "그",
        "저",
        "뭐",
        "약간",
        "그러니까",
        "사실",
        "일단",
    }

    # --------------------------------
    # 분석
    # --------------------------------

    def analyze(
        self,
        segments: list[dict],
    ) -> list[dict]:

        occurrences = []

        for segment in segments:

            text = segment.get(
                "text",
                ""
            )

            timestamps = segment.get(
                "timestamps",
                []
            )

            if not text or not timestamps:
                continue

            words = self._tokenize(
                text
            )

            # -------------------------
            # timestamp와 단어 연결
            # -------------------------

            word_items = self._align_words(
                words,
                timestamps
            )

            # -------------------------
            # 추임새 탐지
            # -------------------------

            for item in word_items:

                word = item["text"]

                if self._is_filler(
                    word,
                    word_items,
                    item["index"]
                ):

                    occurrences.append(
                        {
                            "type": "filler",
                            "text": word,
                            "start": item["start"],
                            "end": item["end"],
                        }
                    )

            # -------------------------
            # 단어 반복 탐지
            # -------------------------

            repetitions = (
                self._find_repetitions(
                    word_items
                )
            )

            occurrences.extend(
                repetitions
            )

        return sorted(
            occurrences,
            key=lambda x: x["start"]
        )

    # --------------------------------
    # 단어 분리
    # --------------------------------

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:

        return re.findall(
            r"[가-힣]+|[A-Za-z0-9]+",
            text
        )

    # --------------------------------
    # 단어 ↔ timestamp 연결
    # --------------------------------

    def _align_words(
        self,
        words: list[str],
        timestamps: list[dict],
    ) -> list[dict]:

        if not words:
            return []

        if not timestamps:
            return []

        result = []

        # --------------------------------
        # 현재 SenseVoice timestamp는
        # 음절/문자 단위에 가까우므로
        # 단어를 timestamp 구간에
        # 대략적으로 분배한다.
        # --------------------------------

        total = len(timestamps)

        for index, word in enumerate(words):

            start_index = int(
                index
                * total
                / len(words)
            )

            end_index = int(
                (index + 1)
                * total
                / len(words)
            )

            if end_index <= start_index:
                end_index = (
                    start_index + 1
                )

            end_index = min(
                end_index,
                total
            )

            selected = timestamps[
                start_index:end_index
            ]

            if not selected:
                continue

            result.append(
                {
                    "index": index,
                    "text": word,
                    "start": selected[0]["start"],
                    "end": selected[-1]["end"],
                }
            )

        return result

    # --------------------------------
    # 추임새 판단
    # --------------------------------

    def _is_filler(
        self,
        word: str,
        words: list[dict],
        index: int,
    ) -> bool:

        if word not in self.FILLERS:
            return False

        # --------------------------------
        # 1. 단독으로 등장하는 경우
        # --------------------------------

        previous_word = None
        next_word = None

        if index > 0:
            previous_word = words[
                index - 1
            ]["text"]

        if index + 1 < len(words):
            next_word = words[
                index + 1
            ]["text"]

        # --------------------------------
        # 2. 문장 시작의 "그"는
        #    추임새일 가능성이 높음
        # --------------------------------

        if word == "그":

            if next_word is None:
                return True

            # "그 사람", "그 서비스" 등은
            # 일반적인 지시어일 가능성이 높음

            return next_word not in {
                "사람",
                "분",
                "것",
                "서비스",
                "친구",
                "학생",
                "학교",
                "회사",
            }

        # --------------------------------
        # 3. "저"는 대명사인지 추임새인지
        #    구분해야 함
        # --------------------------------

        if word == "저":

            # "저는", "저의"처럼
            # 문법적으로 사용되는 경우
            # 일반 단어로 취급

            if next_word in {
                "는",
                "가",
                "의",
                "를",
                "도",
            }:
                return False

            return True

        # --------------------------------
        # 4. 일반 추임새
        # --------------------------------

        return True

    # --------------------------------
    # 반복 탐지
    # --------------------------------

    def _find_repetitions(
        self,
        words: list[dict],
    ) -> list[dict]:

        repetitions = []

        for previous, current in zip(
            words,
            words[1:]
        ):

            if (
                previous["text"]
                == current["text"]
            ):

                repetitions.append(
                    {
                        "type": "repetition",
                        "text": current["text"],
                        "start": previous["start"],
                        "end": current["end"],
                    }
                )

        return repetitions