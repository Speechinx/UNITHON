class RiskAnalyzer:

    WINDOW_SIZE = 15

    def analyze(
        self,
        segments: list[dict],
        filler_occurrences: list[dict],
    ) -> dict:

        if not segments:
            return {
                "overall_score": 0,
                "level": "low",
                "heatmap": [],
                "risk_segments": [],
            }

        duration = max(
            segment["end"]
            for segment in segments
        )

        heatmap = []

        start = 0

        while start < duration:

            end = min(
                start + self.WINDOW_SIZE,
                duration,
            )

            score, reasons = self._calculate_window(
                start,
                end,
                segments,
                filler_occurrences,
            )

            heatmap.append(
                {
                    "start": round(start, 2),
                    "end": round(end, 2),
                    "score": score,
                    "level": self._level(score),
                }
            )

            start = end

        risk_segments = [
            {
                **item,
                "reasons": self._reasons_for_window(
                    item,
                    segments,
                    filler_occurrences,
                ),
            }
            for item in heatmap
            if item["score"] >= 50
        ]

        overall_score = (
            sum(
                item["score"]
                for item in heatmap
            )
            / len(heatmap)
        )

        return {
            "overall_score": round(
                overall_score,
                2,
            ),

            "level": self._level(
                overall_score
            ),

            "heatmap": heatmap,

            "risk_segments": risk_segments,
        }

    def _calculate_window(
        self,
        start,
        end,
        segments,
        filler_occurrences,
    ):
        """
        특정 시간 구간의 발표 위험도를 계산한다.

        위험 요소:
        1. 말하기 속도
        2. 긴 침묵
        3. 추임새
        4. 반복 단어
        """

        # --------------------------------
        # 기본값
        # --------------------------------

        score = 0
        reasons = []

        # --------------------------------
        # 현재 시간 구간의 발화
        # --------------------------------

        window_segments = [
            segment
            for segment in segments
            if (
                segment["start"] < end
                and segment["end"] > start
            )
        ]

        # --------------------------------
        # 1. 침묵 분석
        # --------------------------------

        silence_gaps = self._silence_gaps(
            segments
        )

        long_silence = sum(
            gap["duration"]
            for gap in silence_gaps
            if (
                gap["start"] < end
                and gap["end"] > start
            )
        )

        if long_silence >= 3:

            score += 30

            reasons.append(
                f"긴 침묵 {long_silence:.1f}초"
            )

        elif long_silence >= 1.5:

            score += 15

            reasons.append(
                f"침묵 {long_silence:.1f}초"
            )

        # --------------------------------
        # 발화 자체가 없는 구간
        # --------------------------------

        if not window_segments:

            return min(score + 60, 100), [
                *reasons,
                "발화가 없는 구간",
            ]

        # --------------------------------
        # 2. 발화 속도
        # --------------------------------

        text_length = sum(
            len(
                segment["text"]
            )
            for segment in window_segments
        )

        speaking_time = sum(
            max(
                segment["end"]
                - segment["start"],
                0,
            )
            for segment in window_segments
        )

        if speaking_time > 0:

            approximate_wpm = (
                text_length
                / speaking_time
                * 60
            )

            if approximate_wpm > 220:

                score += 30

                reasons.append(
                    "말하기 속도가 매우 빠름"
                )

            elif approximate_wpm > 180:

                score += 15

                reasons.append(
                    "말하기 속도가 빠름"
                )

        # --------------------------------
        # 3. 추임새
        # --------------------------------

        filler_count = sum(
            1
            for item in filler_occurrences
            if (
                item["start"] < end
                and item["end"] > start
                and item["type"] == "filler"
            )
        )

        if filler_count >= 4:

            score += 30

            reasons.append(
                f"추임새 {filler_count}회"
            )

        elif filler_count >= 2:

            score += 15

            reasons.append(
                f"추임새 {filler_count}회"
            )

        # --------------------------------
        # 4. 반복 단어
        # --------------------------------

        repetition_count = sum(
            1
            for item in filler_occurrences
            if (
                item["start"] < end
                and item["end"] > start
                and item["type"] == "repetition"
            )
        )

        if repetition_count >= 2:

            score += 20

            reasons.append(
                f"단어 반복 {repetition_count}회"
            )

        return min(score, 100), reasons

    # --------------------------------
    # 침묵 구간 탐지
    # --------------------------------

    def _silence_gaps(
        self,
        segments,
    ):

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

            # 1초 이상 침묵만 분석
            if gap >= 1.0:

                gaps.append(
                    {
                        "start": previous["end"],
                        "end": current["start"],
                        "duration": gap,
                    }
                )

        return gaps

    # --------------------------------
    # 위험 구간 이유 다시 계산
    # --------------------------------

    def _reasons_for_window(
        self,
        item,
        segments,
        filler_occurrences,
    ):

        _, reasons = self._calculate_window(
            item["start"],
            item["end"],
            segments,
            filler_occurrences,
        )

        return reasons

    # --------------------------------
    # 위험도 레벨
    # --------------------------------

    def _level(self, score):

        if score >= 70:
            return "high"

        if score >= 40:
            return "medium"

        return "low"