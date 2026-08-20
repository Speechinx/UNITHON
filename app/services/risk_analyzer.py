class RiskAnalyzer:
    WINDOW_SIZE = 10
    MIN_LAST_WINDOW = 3.0

    def analyze(
        self,
        duration: float,
        segments: list[dict],
        speech_result: dict,
        filler_result: list[dict],
    ) -> dict:

        if duration <= 0:
            return {
                "overall_score": 0,
                "overall_level": "low",
                "heatmap": [],
            }

        windows = self._build_windows(
            duration
        )

        heatmap = []

        for window in windows:
            window_result = self._analyze_window(
                start=window["start"],
                end=window["end"],
                segments=segments,
                speech_result=speech_result,
                filler_result=filler_result,
            )

            heatmap.append(
                window_result
            )

        overall_score = (
            self._calculate_overall_score(
                heatmap
            )
        )

        overall_level = (
            self._score_to_level(
                overall_score
            )
        )

        return {
            "overall_score": overall_score,
            "overall_level": overall_level,
            "heatmap": heatmap,
        }

    # ==========================================
    # Window 생성
    # ==========================================

    def _build_windows(
        self,
        duration: float,
    ) -> list[dict]:

        windows = []

        start = 0.0

        while start < duration:
            end = min(
                start + self.WINDOW_SIZE,
                duration,
            )

            windows.append(
                {
                    "start": start,
                    "end": end,
                }
            )

            start += self.WINDOW_SIZE

        # 마지막 window가 너무 짧으면
        # 이전 window와 병합
        if len(windows) >= 2:
            last = windows[-1]

            last_duration = (
                last["end"]
                - last["start"]
            )

            if (
                last_duration
                < self.MIN_LAST_WINDOW
            ):
                windows[-2]["end"] = (
                    last["end"]
                )

                windows.pop()

        return windows

    # ==========================================
    # Window 분석
    # ==========================================

    def _analyze_window(
        self,
        start: float,
        end: float,
        segments: list[dict],
        speech_result: dict,
        filler_result: list[dict],
    ) -> dict:

        score = 0
        reasons = []

        # ======================================
        # 1. 구간별 어절
        # ======================================

        words = self._get_words_in_window(
            segments,
            start,
            end,
        )

        word_count = len(words)

        # ======================================
        # 2. 구간별 Pause
        # ======================================

        pauses = self._get_pauses_in_window(
            speech_result.get(
                "internal_pauses",
                [],
            ),
            start,
            end,
        )

        pause_time = sum(
            self._get_overlap_duration(
                pause["start"],
                pause["end"],
                start,
                end,
            )
            for pause in pauses
        )

        window_duration = (
            end - start
        )

        # ======================================
        # 3. 시작 / 끝 무음 제거
        # ======================================

        edge_silence_time = 0.0

        leading_silence = (
            speech_result.get(
                "leading_silence",
                0,
            )
        )

        trailing_silence = (
            speech_result.get(
                "trailing_silence",
                0,
            )
        )

        total_duration = (
            speech_result.get(
                "duration",
                end,
            )
        )

        if leading_silence > 0:
            edge_silence_time += (
                self._get_overlap_duration(
                    0,
                    leading_silence,
                    start,
                    end,
                )
            )

        if trailing_silence > 0:
            trailing_start = (
                total_duration
                - trailing_silence
            )

            edge_silence_time += (
                self._get_overlap_duration(
                    trailing_start,
                    total_duration,
                    start,
                    end,
                )
            )

        # ======================================
        # 4. 구간의 실제 발표 시간
        #
        # 시작/끝 무음만 제외
        # 내부 pause는 포함한다.
        #
        # 즉 청중이 체감하는 템포
        # ======================================

        presentation_time = max(
            window_duration
            - edge_silence_time,
            0,
        )

        # ======================================
        # 5. 실제 음성을 낸 시간
        # ======================================

        speech_time = max(
            presentation_time
            - pause_time,
            0,
        )

        # ======================================
        # 6. 구간별 체감 발표 속도
        # ======================================

        presentation_rate = (
            word_count
            / presentation_time
            * 60
            if presentation_time > 0
            else 0
        )

        # ======================================
        # 7. 구간별 실제 발화 속도
        # ======================================

        articulation_rate = (
            word_count
            / speech_time
            * 60
            if speech_time > 0
            else 0
        )

        pace_level = self._get_pace_level(
            presentation_rate
        )

        # ======================================
        # 8. Pause 위험도
        # ======================================

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
                f"pause가 {pause_count}회 발생"
            )

        if len(long_pauses) >= 1:
            score += 15

            reasons.append(
                f"1초 이상 pause "
                f"{len(long_pauses)}회"
            )

        if len(very_long_pauses) >= 1:
            score += 20

            reasons.append(
                f"1.5초 이상 긴 pause "
                f"{len(very_long_pauses)}회"
            )

        # ======================================
        # 9. 추임새 / 반복
        # ======================================

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
            for occurrence
            in window_occurrences
            if occurrence.get(
                "type"
            ) == "filler"
        )

        repetition_count = sum(
            1
            for occurrence
            in window_occurrences
            if occurrence.get(
                "type"
            ) == "repetition"
        )

        if filler_count == 1:
            score += 5

            reasons.append(
                "추임새 1회"
            )

        elif filler_count >= 2:
            score += 15

            reasons.append(
                f"추임새 {filler_count}회"
            )

        if filler_count >= 4:
            score += 10

        if repetition_count == 1:
            score += 10

            reasons.append(
                "반복 표현 1회"
            )

        elif repetition_count >= 2:
            score += 20

            reasons.append(
                f"반복 표현 "
                f"{repetition_count}회"
            )

        # ======================================
        # 10. 구간별 발표 속도 위험도
        # ======================================

        if (
            word_count >= 3
            and presentation_time >= 2.0
        ):

            if pace_level == "slow":
                score += 15

                reasons.append(
                    f"발표 속도가 느림 "
                    f"({presentation_rate:.1f} 어절/분)"
                )

            elif pace_level == "fast":
                score += 15

                reasons.append(
                    f"발표 속도가 빠름 "
                    f"({presentation_rate:.1f} 어절/분)"
                )

        # ======================================
        # 11. 점수 제한
        # ======================================

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

            "duration": round(
                window_duration,
                2,
            ),

            "word_count": word_count,

            "presentation_time": round(
                presentation_time,
                2,
            ),

            "speech_time": round(
                speech_time,
                2,
            ),

            "presentation_rate": round(
                presentation_rate,
                2,
            ),

            "articulation_rate": round(
                articulation_rate,
                2,
            ),

            "pace_level": pace_level,

            "pause_time": round(
                pause_time,
                2,
            ),

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

            "score": score,

            "level": level,

            "reasons": reasons,
        }

    # ==========================================
    # Window 안 어절
    # ==========================================

    def _get_words_in_window(
        self,
        segments: list[dict],
        start: float,
        end: float,
    ) -> list[dict]:

        result = []

        for segment in segments:
            normalized_words = (
                segment.get(
                    "normalized_words",
                    [],
                )
            )

            for word in normalized_words:
                word_start = word.get(
                    "start"
                )

                word_end = word.get(
                    "end"
                )

                if (
                    word_start is None
                    or word_end is None
                ):
                    continue

                if (
                    start
                    <= word_start
                    < end
                ):
                    result.append(
                        word
                    )

        return result

    # ==========================================
    # Window 안 pause
    # ==========================================

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

            if (
                pause_end > start
                and pause_start < end
            ):
                result.append(
                    pause
                )

        return result

    # ==========================================
    # 겹치는 시간
    # ==========================================

    def _get_overlap_duration(
        self,
        item_start: float,
        item_end: float,
        window_start: float,
        window_end: float,
    ) -> float:

        overlap_start = max(
            item_start,
            window_start,
        )

        overlap_end = min(
            item_end,
            window_end,
        )

        return max(
            overlap_end
            - overlap_start,
            0,
        )

    # ==========================================
    # 전체 위험 점수
    # ==========================================

    def _calculate_overall_score(
        self,
        heatmap: list[dict],
    ) -> int:

        if not heatmap:
            return 0

        weighted_score = 0.0
        total_duration = 0.0

        for window in heatmap:
            duration = window.get(
                "duration",
                0,
            )

            weighted_score += (
                window["score"]
                * duration
            )

            total_duration += duration

        if total_duration <= 0:
            return 0

        return round(
            weighted_score
            / total_duration
        )

    # ==========================================
    # 발표 속도 수준
    # ==========================================

    def _get_pace_level(
        self,
        presentation_rate: float,
    ) -> str:

        if presentation_rate <= 0:
            return "unknown"

        if presentation_rate < 70:
            return "slow"

        if presentation_rate > 160:
            return "fast"

        return "normal"

    # ==========================================
    # 위험 수준
    # ==========================================

    def _score_to_level(
        self,
        score: int,
    ) -> str:

        if score >= 70:
            return "high"

        if score >= 40:
            return "medium"

        return "low"