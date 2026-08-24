from kiwipiepy import Kiwi


class TextNormalizer:

    def __init__(self):
        self.kiwi = Kiwi()

    def normalize_segment(
        self,
        segment: dict,
    ) -> list[dict]:

        text = segment.get("text", "").strip()
        timestamps = segment.get("timestamps", [])

        if not text:
            return []

        tokens = self.kiwi.tokenize(text)

        words = self._group_tokens(
            tokens
        )

        words = self._attach_timestamps(
            words,
            timestamps,
            text,
        )

        return words

    # --------------------------------
    # Kiwi 형태소 → 어절
    # --------------------------------

    def _group_tokens(
        self,
        tokens,
    ) -> list[dict]:

        words = []

        current_tokens = []

        previous_end = None

        for token in tokens:

            # 문장부호는 분석 어절에서 제외
            if token.tag.startswith("S"):
                continue

            if previous_end is not None:

                gap = token.start - previous_end

                # 원문에서 공백이 존재하면
                # 새로운 어절
                if gap > 0:

                    if current_tokens:

                        words.append(
                            self._make_word(
                                current_tokens
                            )
                        )

                    current_tokens = []

            current_tokens.append(token)

            previous_end = (
                token.start
                + token.len
            )

        if current_tokens:

            words.append(
                self._make_word(
                    current_tokens
                )
            )

        return words

    # --------------------------------
    # 어절 객체 생성
    # --------------------------------

    def _make_word(
        self,
        tokens,
    ) -> dict:

        text = "".join(
            token.form
            for token in tokens
        )

        return {
            "text": text,
            "start_offset": tokens[0].start,
            "end_offset": (
                tokens[-1].start
                + tokens[-1].len
            ),
            "morphemes": [
                {
                    "form": token.form,
                    "tag": token.tag,
                    "start": token.start,
                    "len": token.len,
                }
                for token in tokens
            ],
        }

    # --------------------------------
    # SenseVoice timestamp 연결
    # --------------------------------

    def _attach_timestamps(
        self,
        words,
        timestamps,
        text,
    ) -> list[dict]:

        if not timestamps:
            return words

        text_length = len(text)

        if text_length == 0:
            return words

        for word in words:

            start_offset = word[
                "start_offset"
            ]

            end_offset = word[
                "end_offset"
            ]

            # 원문 위치 → timestamp 위치
            start_ratio = (
                start_offset
                / text_length
            )

            end_ratio = (
                end_offset
                / text_length
            )

            start_index = int(
                start_ratio
                * len(timestamps)
            )

            end_index = int(
                end_ratio
                * len(timestamps)
            )

            start_index = min(
                start_index,
                len(timestamps) - 1,
            )

            end_index = min(
                end_index,
                len(timestamps),
            )

            if end_index <= start_index:
                end_index = (
                    start_index + 1
                )

            selected = timestamps[
                start_index:end_index
            ]

            if selected:

                word["start"] = (
                    selected[0]["start"]
                )

                word["end"] = (
                    selected[-1]["end"]
                )

            else:

                word["start"] = None
                word["end"] = None

        return words