import os
import tempfile
import wave


class EmotionAnalyzer:
    WINDOW_SIZE = 10.0
    MIN_LAST_WINDOW = 3.0

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
            start = window["start"]
            end = window["end"]

            temp_path = None

            try:
                temp_path = (
                    self._extract_wav_segment(
                        audio_path,
                        start,
                        end,
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
                    emotion = "unknown"

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
                # 감정 분석 실패가
                # 전체 발표 분석을 실패시키지 않도록 함
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

        # 마지막 구간이 너무 짧으면
        # 바로 앞 구간에 병합
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

            start_frame = int(
                start
                * sample_rate
            )

            end_frame = int(
                end
                * sample_rate
            )

            frame_count = max(
                0,
                end_frame
                - start_frame,
            )

            source.setpos(
                min(
                    start_frame,
                    source.getnframes(),
                )
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