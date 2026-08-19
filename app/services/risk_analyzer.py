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

            score, reasons = (
                self._calculate_window(
                    start,
                    end,
                    segments,
                    filler_occurrences,
                )
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

        window_segments = [
            segment
            for segment in segments
            if (
                segment["start"] < end
                and segment["end"] > start
            )
        ]

        if not window_segments:

            return 60, ["긴 침묵"]

        score = 0

        reasons = []

        # ----------------------------
        # 1. 발화 속도
        # ----------------------------

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

        # ----------------------------
        # 2. 추임새
        # ----------------------------

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

        # ----------------------------
        # 3. 반복
        # ----------------------------

        repetition_count = sum(
            1
            for item in filler_occurrences
            if (
                item["start"] < end
                and item["end"] > start
                and item["type"]
                == "repetition"
            )
        )

        if repetition_count >= 2:

            score += 20

            reasons.append(
                f"단어 반복 {repetition_count}회"
            )

        return min(score, 100), reasons

    def _reasons_for_window(
        self,
        item,
        segments,
        filler_occurrences,
    ):

        _, reasons = (
            self._calculate_window(
                item["start"],
                item["end"],
                segments,
                filler_occurrences,
            )
        )

        return reasons

    def _level(self, score):

        if score >= 70:
            return "high"

        if score >= 40:
            return "medium"

        return "low"