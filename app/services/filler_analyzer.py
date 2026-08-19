from kiwipiepy import Kiwi


class FillerAnalyzer:

    # ----------------------------------------
    # Kiwi
    # ----------------------------------------

    def __init__(self):

        self.kiwi = Kiwi()

        # 발표에서 자주 등장하는 추임새
        self.FILLERS = {
            "음",
            "어",
            "아",
            "그",
            "저",
            "뭐",
            "약간",
            "그러니까",
            "사실",
            "일단",
        }

    # ----------------------------------------
    # 전체 분석
    # ----------------------------------------

    def analyze(
        self,
        segments: list[dict],
    ) -> list[dict]:

        occurrences = []

        for segment in segments:

            text = segment.get(
                "text",
                "",
            ).strip()

            timestamps = segment.get(
                "timestamps",
                [],
            )

            if not text:
                continue

            # --------------------------------
            # Kiwi 형태소 분석
            # --------------------------------

            kiwi_tokens = self.kiwi.tokenize(
                text
            )

            if not kiwi_tokens:
                continue

            # --------------------------------
            # Kiwi 형태소 → 어절
            # --------------------------------

            words = self._build_words(
                text,
                kiwi_tokens,
                timestamps,
            )

            # --------------------------------
            # 추임새 후보 탐지
            # --------------------------------

            filler_occurrences = (
                self._find_fillers(words)
            )

            occurrences.extend(
                filler_occurrences
            )

            # --------------------------------
            # 반복 탐지
            # --------------------------------

            repetition_occurrences = (
                self._find_repetitions(words)
            )

            occurrences.extend(
                repetition_occurrences
            )

        return sorted(
            occurrences,
            key=lambda x: x["start"],
        )

    # ==================================================
    # 어절 생성
    # ==================================================

    def _build_words(
        self,
        text: str,
        kiwi_tokens,
        timestamps: list[dict],
    ) -> list[dict]:

        words = []

        if not kiwi_tokens or not timestamps:
            return words

        current_word = []
        previous_end = None

        for token in kiwi_tokens:

            token_start = token.start
            token_end = token.start + token.len

            # --------------------------------
            # 실제 공백이 존재하면 어절 분리
            # --------------------------------

            if (
                previous_end is not None
                and token_start > previous_end
            ):

                if current_word:

                    words.append(
                        self._make_word(
                            current_word,
                            timestamps,
                            text,
                        )
                    )

                    current_word = []

            current_word.append(token)

            previous_end = token_end

        if current_word:

            words.append(
                self._make_word(
                    current_word,
                    timestamps,
                    text,
                )
            )

        return words

    # ==================================================
    # 어절 객체 생성
    # ==================================================

    def _make_word(
        self,
        tokens,
        timestamps,
        full_text,
    ) -> dict:

        first = tokens[0]
        last = tokens[-1]

        word_start = first.start

        word_end = (
            last.start
            + last.len
        )

        word_text = "".join(
            token.form
            for token in tokens
        )

        # --------------------------------
        # 전체 텍스트 기준으로 timestamp 매핑
        # --------------------------------

        text_length = max(
            len(full_text),
            1,
        )

        timestamp_count = len(
            timestamps
        )

        start_ratio = (
            word_start / text_length
        )

        end_ratio = (
            word_end / text_length
        )

        start_index = int(
            start_ratio * timestamp_count
        )

        end_index = int(
            end_ratio * timestamp_count
        )

        start_index = max(
            0,
            min(
                start_index,
                timestamp_count - 1,
            ),
        )

        end_index = max(
            start_index + 1,
            end_index,
        )

        end_index = min(
            end_index,
            timestamp_count,
        )

        selected = timestamps[
            start_index:end_index
        ]

        if not selected:

            selected = [
                timestamps[start_index]
            ]

        return {
            "text": word_text,

            "tokens": [
                {
                    "form": token.form,
                    "tag": token.tag,
                    "start": token.start,
                    "len": token.len,
                }
                for token in tokens
            ],

            "start": selected[0]["start"],
            "end": selected[-1]["end"],
        }

    # ==================================================
    # 추임새 탐지
    # ==================================================

    def _find_fillers(
        self,
        words: list[dict],
    ) -> list[dict]:

        occurrences = []

        for index, word in enumerate(words):

            text = word["text"]

            # --------------------------------
            # 1. 명확한 추임새
            # --------------------------------

            if text in {
                "음",
                "어",
                "아",
                "뭐",
                "약간",
                "그러니까",
                "사실",
                "일단",
            }:

                occurrences.append(
                    {
                        "type": "filler",
                        "text": text,
                        "start": word["start"],
                        "end": word["end"],
                        "confidence": 0.95,
                    }
                )

                continue

            # --------------------------------
            # 2. "그"
            # --------------------------------

            if text == "그":

                if self._is_filler_geu(
                    words,
                    index,
                ):

                    occurrences.append(
                        {
                            "type": "filler",
                            "text": text,
                            "start": word["start"],
                            "end": word["end"],
                            "confidence": 0.85,
                        }
                    )

                continue

            # --------------------------------
            # 3. "저"
            # --------------------------------

            if text == "저":

                if self._is_filler_jeo(
                    words,
                    index,
                ):

                    occurrences.append(
                        {
                            "type": "filler",
                            "text": text,
                            "start": word["start"],
                            "end": word["end"],
                            "confidence": 0.80,
                        }
                    )

        return occurrences

    # ==================================================
    # "그" 판단
    # ==================================================

    def _is_filler_geu(
        self,
        words,
        index,
    ) -> bool:

        # 다음 어절이 없으면
        # "그..." 같은 추임새일 가능성이 높음
        if index + 1 >= len(words):
            return True

        next_word = words[
            index + 1
        ]

        # 다음 어절의 Kiwi 품사 확인
        next_tags = {
            token["tag"]
            for token in next_word.get(
                "tokens",
                []
            )
        }

        # 명사 계열
        noun_tags = {
            "NNG",   # 일반 명사
            "NNP",   # 고유 명사
            "NP",    # 대명사
            "NR",    # 수사
        }

        # "그 사람"
        # "그 학교"
        # "그 서비스"
        # "그 친구"
        # 등처럼 명사가 뒤따르면
        # 일반적인 지시어로 판단
        if next_tags & noun_tags:
            return False

        # 명사가 뒤따르지 않으면
        # 추임새로 판단
        return True

    # ==================================================
    # "저" 판단
    # ==================================================

    def _is_filler_jeo(
        self,
        words,
        index,
    ) -> bool:

        # "저는", "저를", "저의" 등이면
        # 일반적인 대명사

        if index + 1 < len(words):

            next_word = words[
                index + 1
            ]["text"]

            if next_word in {
                "는",
                "가",
                "의",
                "를",
                "도",
                "에게",
            }:

                return False

        return True

    # ==================================================
    # 반복 탐지
    # ==================================================

    def _find_repetitions(
        self,
        words: list[dict],
    ) -> list[dict]:

        occurrences = []

        for previous, current in zip(
            words,
            words[1:],
        ):

            previous_text = (
                previous["text"]
            )

            current_text = (
                current["text"]
            )

            # --------------------------------
            # 완전히 같은 어절
            # --------------------------------

            if (
                previous_text
                == current_text
            ):

                occurrences.append(
                    {
                        "type": "repetition",
                        "text": current_text,
                        "start": previous["start"],
                        "end": current["end"],
                        "confidence": 0.98,
                    }
                )

        return occurrences