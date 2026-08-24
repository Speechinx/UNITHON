class StrengthAnalyzer:
    MIN_CONTINUOUS_DURATION = 20.0
    MAX_STRENGTHS = 3

    def analyze(
        self,
        speech_result: dict,
        filler_result: list[dict],
        risk_result: dict,
    ) -> list[dict]:

        heatmap = risk_result.get(
            "heatmap",
            [],
        )

        candidates = []

        # ==========================================
        # 1. 전체 발표 속도
        # ==========================================

        pace_level = speech_result.get(
            "pace_level",
            "unknown",
        )

        presentation_rate = speech_result.get(
            "presentation_rate",
            0,
        )

        if pace_level == "normal":
            candidates.append(
                {
                    "type": "overall_good_pace",
                    "priority": 100,
                    "start": 0.0,
                    "end": speech_result.get(
                        "presentation_duration",
                        0,
                    ),
                    "message": (
                        "전체 발표 속도가 "
                        "적절한 범위로 유지되었습니다."
                    ),
                    "evidence": {
                        "presentation_rate": (
                            presentation_rate
                        ),
                        "pace_level": (
                            pace_level
                        ),
                    },
                }
            )

        # ==========================================
        # 2. 전체 발표에서 반복 표현 없음
        # ==========================================

        repetition_events = [
            event
            for event in filler_result
            if event.get(
                "type"
            ) == "repetition"
        ]

        if not repetition_events:
            candidates.append(
                {
                    "type": "overall_no_repetition",
                    "priority": 95,
                    "start": 0.0,
                    "end": speech_result.get(
                        "presentation_duration",
                        0,
                    ),
                    "message": (
                        "발표 전체에서 반복 표현이 "
                        "탐지되지 않았습니다."
                    ),
                    "evidence": {
                        "repetition_count": 0,
                    },
                }
            )

        # ==========================================
        # 3. 전체 발표에서 추임새 없음
        # ==========================================

        filler_events = [
            event
            for event in filler_result
            if event.get(
                "type"
            ) == "filler"
        ]

        if not filler_events:
            candidates.append(
                {
                    "type": "overall_no_filler",
                    "priority": 95,
                    "start": 0.0,
                    "end": speech_result.get(
                        "presentation_duration",
                        0,
                    ),
                    "message": (
                        "발표 전체에서 추임새가 "
                        "탐지되지 않았습니다."
                    ),
                    "evidence": {
                        "filler_count": 0,
                    },
                }
            )

        # ==========================================
        # 4. 연속된 LOW Risk 구간
        # ==========================================

        stable_ranges = (
            self._find_continuous_ranges(
                heatmap=heatmap,
                predicate=lambda window: (
                    window.get(
                        "level"
                    ) == "low"
                ),
            )
        )

        for stable_range in stable_ranges:
            duration = (
                stable_range["end"]
                - stable_range["start"]
            )

            if (
                duration
                < self.MIN_CONTINUOUS_DURATION
            ):
                continue

            signals = (
                self._collect_range_signals(
                    stable_range[
                        "windows"
                    ]
                )
            )

            message = (
                self._build_stable_message(
                    stable_range["start"],
                    stable_range["end"],
                    signals,
                )
            )

            candidates.append(
                {
                    "type": "stable_delivery",
                    "priority": 90,
                    "start": (
                        stable_range["start"]
                    ),
                    "end": (
                        stable_range["end"]
                    ),
                    "message": message,
                    "evidence": {
                        "duration": round(
                            duration,
                            2,
                        ),
                        "signals": signals,
                    },
                }
            )

        # ==========================================
        # 5. 적절한 속도가 20초 이상 연속
        # ==========================================

        pace_ranges = (
            self._find_continuous_ranges(
                heatmap=heatmap,
                predicate=lambda window: (
                    window.get(
                        "pace_level"
                    ) == "normal"
                ),
            )
        )

        for pace_range in pace_ranges:
            duration = (
                pace_range["end"]
                - pace_range["start"]
            )

            if (
                duration
                < self.MIN_CONTINUOUS_DURATION
            ):
                continue

            candidates.append(
                {
                    "type": "continuous_good_pace",
                    "priority": 80,
                    "start": (
                        pace_range["start"]
                    ),
                    "end": (
                        pace_range["end"]
                    ),
                    "message": (
                        f"{self._format_range(pace_range)} 동안 "
                        "발표 속도가 적절한 범위로 "
                        "유지되었습니다."
                    ),
                    "evidence": {
                        "duration": round(
                            duration,
                            2,
                        ),
                    },
                }
            )

        # ==========================================
        # 6. 추임새가 없는 구간
        # ==========================================

        no_filler_ranges = (
            self._find_continuous_ranges(
                heatmap=heatmap,
                predicate=lambda window: (
                    window.get(
                        "filler_count",
                        0,
                    ) == 0
                ),
            )
        )

        for no_filler_range in (
            no_filler_ranges
        ):
            duration = (
                no_filler_range["end"]
                - no_filler_range["start"]
            )

            if (
                duration
                < self.MIN_CONTINUOUS_DURATION
            ):
                continue

            candidates.append(
                {
                    "type": "continuous_no_filler",
                    "priority": 70,
                    "start": (
                        no_filler_range[
                            "start"
                        ]
                    ),
                    "end": (
                        no_filler_range[
                            "end"
                        ]
                    ),
                    "message": (
                        f"{self._format_range(no_filler_range)} 동안 "
                        "추임새가 탐지되지 않았습니다."
                    ),
                    "evidence": {
                        "duration": round(
                            duration,
                            2,
                        ),
                    },
                }
            )

        # ==========================================
        # 7. 반복 표현이 없는 구간
        # ==========================================

        # 전체 반복 0회인 경우에는
        # 이미 overall_no_repetition이 있으므로
        # 구간별 신호를 또 만들지 않음.

        if repetition_events:
            no_repetition_ranges = (
                self._find_continuous_ranges(
                    heatmap=heatmap,
                    predicate=lambda window: (
                        window.get(
                            "repetition_count",
                            0,
                        ) == 0
                    ),
                )
            )

            for no_repetition_range in (
                no_repetition_ranges
            ):
                duration = (
                    no_repetition_range["end"]
                    - no_repetition_range["start"]
                )

                if (
                    duration
                    < self.MIN_CONTINUOUS_DURATION
                ):
                    continue

                candidates.append(
                    {
                        "type": (
                            "continuous_no_repetition"
                        ),
                        "priority": 65,
                        "start": (
                            no_repetition_range[
                                "start"
                            ]
                        ),
                        "end": (
                            no_repetition_range[
                                "end"
                            ]
                        ),
                        "message": (
                            f"{self._format_range(no_repetition_range)} 동안 "
                            "반복 표현이 탐지되지 않았습니다."
                        ),
                        "evidence": {
                            "duration": round(
                                duration,
                                2,
                            ),
                        },
                    }
                )

        # ==========================================
        # 8. 긴 멈춤이 적은 연속 구간
        # ==========================================

        smooth_ranges = (
            self._find_continuous_ranges(
                heatmap=heatmap,
                predicate=lambda window: (
                    window.get(
                        "pause_count",
                        0,
                    ) <= 1
                ),
            )
        )

        for smooth_range in smooth_ranges:
            duration = (
                smooth_range["end"]
                - smooth_range["start"]
            )

            if (
                duration
                < self.MIN_CONTINUOUS_DURATION
            ):
                continue

            candidates.append(
                {
                    "type": "smooth_flow",
                    "priority": 60,
                    "start": (
                        smooth_range["start"]
                    ),
                    "end": (
                        smooth_range["end"]
                    ),
                    "message": (
                        f"{self._format_range(smooth_range)} 동안 "
                        "긴 멈춤이 적어 비교적 "
                        "끊김 없이 발표가 이어졌습니다."
                    ),
                    "evidence": {
                        "duration": round(
                            duration,
                            2,
                        ),
                    },
                }
            )

        # ==========================================
        # 우선순위 정렬
        # ==========================================

        candidates.sort(
            key=lambda item: (
                -item.get(
                    "priority",
                    0,
                ),
                -(
                    item.get(
                        "end",
                        0,
                    )
                    - item.get(
                        "start",
                        0,
                    )
                ),
            )
        )

        # ==========================================
        # 중복 제거
        # ==========================================

        selected = (
            self._remove_redundant_signals(
                candidates
            )
        )

        # priority는 Gemini에 굳이 보낼 필요 없음
        results = []

        for item in selected[
            :self.MAX_STRENGTHS
        ]:
            results.append(
                {
                    "type": (
                        item.get(
                            "type"
                        )
                    ),
                    "start": round(
                        item.get(
                            "start",
                            0,
                        ),
                        2,
                    ),
                    "end": round(
                        item.get(
                            "end",
                            0,
                        ),
                        2,
                    ),
                    "message": (
                        item.get(
                            "message",
                            "",
                        )
                    ),
                    "evidence": (
                        item.get(
                            "evidence",
                            {},
                        )
                    ),
                }
            )

        return results

    # ============================================================
    # 연속 구간 탐색
    # ============================================================

    def _find_continuous_ranges(
        self,
        heatmap: list[dict],
        predicate,
    ) -> list[dict]:

        ranges = []

        current_windows = []

        for window in heatmap:
            if predicate(
                window
            ):
                if not current_windows:
                    current_windows = [
                        window
                    ]

                else:
                    previous = (
                        current_windows[-1]
                    )

                    previous_end = (
                        previous.get(
                            "end",
                            0,
                        )
                    )

                    current_start = (
                        window.get(
                            "start",
                            0,
                        )
                    )

                    if (
                        abs(
                            previous_end
                            - current_start
                        )
                        <= 0.1
                    ):
                        current_windows.append(
                            window
                        )

                    else:
                        ranges.append(
                            self._make_range(
                                current_windows
                            )
                        )

                        current_windows = [
                            window
                        ]

            else:
                if current_windows:
                    ranges.append(
                        self._make_range(
                            current_windows
                        )
                    )

                    current_windows = []

        if current_windows:
            ranges.append(
                self._make_range(
                    current_windows
                )
            )

        return ranges

    def _make_range(
        self,
        windows: list[dict],
    ) -> dict:

        return {
            "start": windows[
                0
            ].get(
                "start",
                0,
            ),

            "end": windows[
                -1
            ].get(
                "end",
                0,
            ),

            "windows": windows,
        }

    # ============================================================
    # 안정 구간에 포함된 좋은 신호 수집
    # ============================================================

    def _collect_range_signals(
        self,
        windows: list[dict],
    ) -> list[str]:

        signals = [
            "low_risk"
        ]

        if all(
            window.get(
                "pace_level"
            ) == "normal"
            for window in windows
        ):
            signals.append(
                "good_pace"
            )

        if all(
            window.get(
                "filler_count",
                0,
            ) == 0
            for window in windows
        ):
            signals.append(
                "no_filler"
            )

        if all(
            window.get(
                "repetition_count",
                0,
            ) == 0
            for window in windows
        ):
            signals.append(
                "no_repetition"
            )

        if all(
            window.get(
                "pause_count",
                0,
            ) <= 1
            for window in windows
        ):
            signals.append(
                "smooth_flow"
            )

        return signals

    def _build_stable_message(
        self,
        start: float,
        end: float,
        signals: list[str],
    ) -> str:

        time_range = (
            self._format_time_range(
                start,
                end,
            )
        )

        details = []

        if "good_pace" in signals:
            details.append(
                "적절한 발표 속도"
            )

        if "no_filler" in signals:
            details.append(
                "추임새 없이"
            )

        if "no_repetition" in signals:
            details.append(
                "반복 표현 없이"
            )

        if "smooth_flow" in signals:
            details.append(
                "긴 멈춤이 적은 흐름으로"
            )

        if not details:
            return (
                f"{time_range} 동안 "
                "개선 신호가 적은 안정적인 "
                "발표 흐름을 유지했습니다."
            )

        detail_text = (
            ", ".join(
                details
            )
        )

        return (
            f"{time_range} 동안 "
            f"{detail_text} "
            "안정적인 발표 흐름을 유지했습니다."
        )

    # ============================================================
    # 중복 후보 제거
    # ============================================================

    def _remove_redundant_signals(
        self,
        candidates: list[dict],
    ) -> list[dict]:

        selected = []

        has_overall_good_pace = any(
            item.get(
                "type"
            ) == "overall_good_pace"
            for item in candidates
        )

        has_overall_no_filler = any(
            item.get(
                "type"
            ) == "overall_no_filler"
            for item in candidates
        )

        has_overall_no_repetition = any(
            item.get(
                "type"
            ) == "overall_no_repetition"
            for item in candidates
        )

        for candidate in candidates:
            candidate_type = (
                candidate.get(
                    "type"
                )
            )

            # 전체 속도가 이미 적절하다면
            # 구간별 적절 속도는 중복
            if (
                candidate_type
                == "continuous_good_pace"
                and has_overall_good_pace
            ):
                continue

            # 전체에서 filler가 없으면
            # 구간별 no filler는 중복
            if (
                candidate_type
                == "continuous_no_filler"
                and has_overall_no_filler
            ):
                continue

            # 전체 반복 0이면
            # 구간별 no repetition은 중복
            if (
                candidate_type
                == "continuous_no_repetition"
                and has_overall_no_repetition
            ):
                continue

            # 같은 type은 가장 좋은 하나만
            if any(
                selected_item.get(
                    "type"
                )
                == candidate_type
                for selected_item
                in selected
            ):
                continue

            selected.append(
                candidate
            )

        return selected

    # ============================================================
    # 시간 문자열
    # ============================================================

    def _format_range(
        self,
        range_data: dict,
    ) -> str:

        return (
            self._format_time_range(
                range_data.get(
                    "start",
                    0,
                ),
                range_data.get(
                    "end",
                    0,
                ),
            )
        )

    def _format_time_range(
        self,
        start: float,
        end: float,
    ) -> str:

        return (
            f"{self._format_time(start)}"
            f"~"
            f"{self._format_time(end)}"
        )

    def _format_time(
        self,
        seconds: float,
    ) -> str:

        seconds = int(
            round(
                seconds
            )
        )

        minutes = (
            seconds // 60
        )

        remaining = (
            seconds % 60
        )

        if minutes > 0:
            return (
                f"{minutes}분 "
                f"{remaining}초"
            )

        return (
            f"{remaining}초"
        )