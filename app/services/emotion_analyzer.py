import os
import tempfile
import wave


class EmotionAnalyzer:
    WINDOW_SIZE = 10.0

    MIN_LAST_WINDOW = 3.0

    # 감정 분석 시 문맥 확보용
    CONTEXT_PADDING = 1.5

    def __init__(
        self,
        sensevoice_service,
    ):
        self.sensevoice = (
            sensevoice_service
        )

    def analyze(
        self,
        audio_path: str,
    ) -> list[dict]:

        duration = (
            self._get_duration(
                audio_path
            )
        )

        windows = (
            self._build_windows(
                duration
            )
        )

        results = []

        for window in windows:
            start = (
                window["start"]
            )

            end = (
                window["end"]
            )

            # ==========================================
            # 실제 감정 분석에는 앞뒤 문맥을 추가
            # ==========================================

            analysis_start = max(
                0.0,
                start
                - self.CONTEXT_PADDING,
            )

            analysis_end = min(
                duration,
                end
                + self.CONTEXT_PADDING,
            )

            temp_path = None

            try:
                temp_path = (
                    self._extract_wav_segment(
                        audio_path,
                        analysis_start,
                        analysis_end,
                    )
                )

                sensevoice_result = (
                    self.sensevoice.analyze(
                        temp_path
                    )
                )

                emotion = (
                    sensevoice_result.get(
                        "emotion",
                        "unknown",
                    )
                )

                if not emotion:
                    emotion = (
                        "unknown"
                    )

                # ==========================================
                # 주의:
                #
                # 분석에는 padding된 시간을 사용하지만
                # 결과 시간은 원래 10초 window 그대로 반환
                # ==========================================

                results.append(
                    {
                        "start": round(
                            start,
                            2,
                        ),

                        "end": round(
                            end,
                            2,
                        ),

                        "emotion_signal": (
                            emotion
                        ),
                    }
                )

            except Exception:
                # 감정 분석 실패 때문에
                # 전체 발표 분석까지 실패시키지 않음

                results.append(
                    {
                        "start": round(
                            start,
                            2,
                        ),

                        "end": round(
                            end,
                            2,
                        ),

                        "emotion_signal": (
                            "unknown"
                        ),
                    }
                )

            finally:
                if (
                    temp_path
                    and os.path.exists(
                        temp_path
                    )
                ):
                    try:
                        os.remove(
                            temp_path
                        )

                    except OSError:
                        pass

        return results

    def _get_duration(
        self,
        audio_path: str,
    ) -> float:

        with wave.open(
            audio_path,
            "rb",
        ) as wav_file:

            frame_count = (
                wav_file.getnframes()
            )

            sample_rate = (
                wav_file.getframerate()
            )

        if sample_rate <= 0:
            return 0.0

        return (
            frame_count
            / sample_rate
        )

    def _build_windows(
        self,
        duration: float,
    ) -> list[dict]:

        if duration <= 0:
            return []

        windows = []

        start = 0.0

        while start < duration:
            end = min(
                start
                + self.WINDOW_SIZE,
                duration,
            )

            windows.append(
                {
                    "start": start,
                    "end": end,
                }
            )

            start = end

        # ==========================================
        # 마지막 구간이 3초보다 짧으면
        # 이전 구간에 병합
        #
        # 예:
        # 0~10
        # 10~20
        # 20~22
        #
        # ->
        #
        # 0~10
        # 10~22
        # ==========================================

        if len(windows) >= 2:
            last_window = (
                windows[-1]
            )

            last_duration = (
                last_window["end"]
                - last_window["start"]
            )

            if (
                last_duration
                < self.MIN_LAST_WINDOW
            ):
                windows[-2]["end"] = (
                    last_window["end"]
                )

                windows.pop()

        return windows

    def _extract_wav_segment(
        self,
        audio_path: str,
        start: float,
        end: float,
    ) -> str:

        with wave.open(
            audio_path,
            "rb",
        ) as source:

            params = (
                source.getparams()
            )

            sample_rate = (
                source.getframerate()
            )

            total_frames = (
                source.getnframes()
            )

            start_frame = int(
                start
                * sample_rate
            )

            end_frame = int(
                end
                * sample_rate
            )

            start_frame = max(
                0,
                min(
                    start_frame,
                    total_frames,
                ),
            )

            end_frame = max(
                start_frame,
                min(
                    end_frame,
                    total_frames,
                ),
            )

            frame_count = (
                end_frame
                - start_frame
            )

            source.setpos(
                start_frame
            )

            frames = (
                source.readframes(
                    frame_count
                )
            )

        temp_file = (
            tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".wav",
            )
        )

        temp_path = (
            temp_file.name
        )

        temp_file.close()

        with wave.open(
            temp_path,
            "wb",
        ) as target:

            target.setparams(
                params
            )

            target.writeframes(
                frames
            )

        return temp_path