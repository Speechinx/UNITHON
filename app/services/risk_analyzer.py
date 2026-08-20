class RiskAnalyzer:
    WINDOW_SIZE = 10

    def analyze(
        self,
        duration: float,
        speech_result: dict,
        filler_result: list[dict],
    ) -> dict:

        if duration <= 0:
            return {
                "overall_score": 0,
                "overall_level": "low",
                "heatmap": [],
            }

        heatmap = []

        window_start = 0.0

        while window_start < duration:
            window_end = min(
                window_start + self.WINDOW_SIZE,
                duration,
            )

            window_result = self._analyze_window(
                start=window_start,
                end=window_end,
                speech_result=speech_result,
                filler_result=filler_result,
            )

            heatmap.append(
                window_result
            )

            window_start += self.WINDOW_SIZE

        overall_score = self._calculate_overall_score(
            heatmap
        )

        overall_level = self._score_to_level(
            overall_score
        )

        return {
            "overall_score": overall_score,
            "overall_level": overall_level,
            "heatmap": heatmap,
        }

    def _analyze_window(
        self,
        start: float,
        end: float,
        speech_result: dict,
        filler_result: list[dict],
    ) -> dict:

        score = 0
        reasons = []

        # ==========================================
        # 1. Pause 분석
        # ==========================================

        pauses = self._get_pauses_in_window(
            pauses=speech_result.get(
                "internal_pauses",
                [],
            ),
            start=start,
            end=end,
        )

        pause_count = len(pauses)

        long_pauses = [
            pause
            for pause in pauses
            if pause.get(
                "duration",
                0,
            ) >= 1.0
        ]

        very_long_pauses = [
            pause
            for pause in pauses
            if pause.get(
                "duration",
                0,
            ) >= 1.5
        ]

        if pause_count >= 3:
            score += 15

            reasons.append(
                f"짧은 구간에 pause가 "
                f"{pause_count}회 발생"
            )

        if long_pauses:
            score += 15

            reasons.append(
                f"1초 이상 pause "
                f"{len(long_pauses)}회"
            )

        if very_long_pauses:
            score += 20

            reasons.append(
                f"1.5초 이상 긴 pause "
                f"{len(very_long_pauses)}회"
            )

        # ==========================================
        # 2. 추임새 / 반복 분석
        # ==========================================

        window_occurrences = []

        for occurrence in filler_result:
            occurrence_start = occurrence.get(
                "start",
                0,
            )

            if (
                start
                <= occurrence_start
                < end
            ):
                window_occurrences.append(
                    occurrence
                )

        filler_count = sum(
            1
            for occurrence in window_occurrences
            if occurrence.get(
                "type"
            ) == "filler"
        )

        repetition_count = sum(
            1
            for occurrence in window_occurrences
            if occurrence.get(
                "type"
            ) == "repetition"
        )

        if filler_count >= 2:
            score += 15

            reasons.append(
                f"추임새 {filler_count}회"
            )

        if filler_count >= 4:
            score += 10

        if repetition_count >= 1:
            score += 15

            reasons.append(
                f"반복 표현 "
                f"{repetition_count}회"
            )

        if repetition_count >= 2:
            score += 10

        # ==========================================
        # 3. 말하기 속도
        # ==========================================

        speech_rate = speech_result.get(
            "speech_rate",
            0,
        )

        if speech_rate > 0:
            if speech_rate < 70:
                score += 15

                reasons.append(
                    f"말하기 속도가 느림 "
                    f"({speech_rate:.1f} 어절/분)"
                )

            elif speech_rate > 180:
                score += 15

                reasons.append(
                    f"말하기 속도가 빠름 "
                    f"({speech_rate:.1f} 어절/분)"
                )

        # ==========================================
        # 4. 점수 제한 및 레벨
        # ==========================================

        score = min(
            score,
            100,
        )

        level = self._score_to_level(
            score
        )

        return {
            "start": round(
                start,
                2,
            ),

            "end": round(
                end,
                2,
            ),

            "score": score,

            "level": level,

            "pause_count": pause_count,

            "long_pause_count": len(
                long_pauses
            ),

            "very_long_pause_count": len(
                very_long_pauses
            ),

            "filler_count": filler_count,

            "repetition_count": (
                repetition_count
            ),

            "reasons": reasons,
        }

    def _get_pauses_in_window(
        self,
        pauses: list[dict],
        start: float,
        end: float,
    ) -> list[dict]:

        result = []

        for pause in pauses:
            pause_start = pause.get(
                "start",
                0,
            )

            pause_end = pause.get(
                "end",
                0,
            )

            # pause가 현재 window와 조금이라도 겹치면 포함
            if (
                pause_end > start
                and pause_start < end
            ):
                result.append(
                    pause
                )

        return result

    def _calculate_overall_score(
        self,
        heatmap: list[dict],
    ) -> int:

        if not heatmap:
            return 0

        scores = [
            window["score"]
            for window in heatmap
        ]

        average_score = (
            sum(scores)
            / len(scores)
        )

        return round(
            average_score
        )

    def _score_to_level(
        self,
        score: int,
    ) -> str:

        if score >= 70:
            return "high"

        if score >= 40:
            return "medium"

        return "low"