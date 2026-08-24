import wave
import numpy as np


class AudioPauseAnalyzer:
    FRAME_MS = 30
    MIN_PAUSE_MS = 800
    MERGE_GAP_MS = 120

    def analyze(self, audio_path: str) -> dict:
        audio, sample_rate = self._load_wav(audio_path)

        if len(audio) == 0:
            return {
                "duration": 0,
                "leading_silence": 0,
                "trailing_silence": 0,
                "internal_pause_time": 0,
                "internal_pause_ratio": 0,
                "speech_time": 0,
                "threshold": 0,
                "internal_pauses": [],
            }

        duration = len(audio) / sample_rate

        frame_size = max(
            int(sample_rate * self.FRAME_MS / 1000),
            1,
        )

        rms_values = self._calculate_rms(
            audio,
            frame_size,
        )

        threshold = self._estimate_threshold(
            rms_values
        )

        silence_flags = rms_values < threshold

        silence_segments = self._build_silence_segments(
            silence_flags,
            frame_size,
            sample_rate,
            duration,
        )

        silence_segments = self._merge_close_segments(
            silence_segments
        )

        pauses = [
            segment
            for segment in silence_segments
            if segment["duration"] * 1000
            >= self.MIN_PAUSE_MS
        ]

        (
            leading_silence,
            trailing_silence,
            internal_pauses,
        ) = self._classify_pauses(
            pauses,
            duration,
        )

        internal_pause_time = sum(
            pause["duration"]
            for pause in internal_pauses
        )

        presentation_start = leading_silence
        presentation_end = (
            duration - trailing_silence
        )

        presentation_duration = max(
            presentation_end
            - presentation_start,
            0,
        )

        speech_time = max(
            presentation_duration
            - internal_pause_time,
            0,
        )

        internal_pause_ratio = (
            internal_pause_time
            / presentation_duration
            if presentation_duration > 0
            else 0
        )

        return {
            "duration": round(
                duration,
                2,
            ),

            "presentation_duration": round(
                presentation_duration,
                2,
            ),

            "leading_silence": round(
                leading_silence,
                2,
            ),

            "trailing_silence": round(
                trailing_silence,
                2,
            ),

            "internal_pause_time": round(
                internal_pause_time,
                2,
            ),

            "internal_pause_ratio": round(
                internal_pause_ratio,
                3,
            ),

            "speech_time": round(
                speech_time,
                2,
            ),

            "threshold": round(
                float(threshold),
                6,
            ),

            "internal_pauses": internal_pauses,
        }

    def _load_wav(
        self,
        audio_path: str,
    ):
        with wave.open(
            audio_path,
            "rb",
        ) as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()

            raw = wav.readframes(
                frame_count
            )

        if sample_width == 2:
            audio = np.frombuffer(
                raw,
                dtype=np.int16,
            ).astype(np.float32)

            audio /= 32768.0

        elif sample_width == 1:
            audio = np.frombuffer(
                raw,
                dtype=np.uint8,
            ).astype(np.float32)

            audio = (
                audio - 128
            ) / 128.0

        elif sample_width == 4:
            audio = np.frombuffer(
                raw,
                dtype=np.int32,
            ).astype(np.float32)

            audio /= 2147483648.0

        else:
            raise ValueError(
                f"지원하지 않는 WAV sample width: "
                f"{sample_width}"
            )

        if channels > 1:
            audio = audio.reshape(
                -1,
                channels,
            )

            audio = np.mean(
                audio,
                axis=1,
            )

        return audio, sample_rate

    def _calculate_rms(
        self,
        audio: np.ndarray,
        frame_size: int,
    ) -> np.ndarray:
        values = []

        for start in range(
            0,
            len(audio),
            frame_size,
        ):
            frame = audio[
                start:start + frame_size
            ]

            if len(frame) == 0:
                continue

            rms = np.sqrt(
                np.mean(
                    np.square(frame)
                )
            )

            values.append(rms)

        return np.array(
            values,
            dtype=np.float32,
        )

    def _estimate_threshold(
        self,
        rms_values: np.ndarray,
    ) -> float:
        if len(rms_values) == 0:
            return 0

        noise_floor = np.percentile(
            rms_values,
            20,
        )

        median = np.median(
            rms_values
        )

        threshold = (
            noise_floor
            + (
                median
                - noise_floor
            )
            * 0.35
        )

        return max(
            float(threshold),
            0.0005,
        )

    def _build_silence_segments(
        self,
        silence_flags,
        frame_size,
        sample_rate,
        duration,
    ):
        segments = []
        start_index = None

        for index, is_silent in enumerate(
            silence_flags
        ):
            if is_silent:
                if start_index is None:
                    start_index = index

            else:
                if start_index is not None:
                    segment = self._make_segment(
                        start_index,
                        index,
                        frame_size,
                        sample_rate,
                        duration,
                    )

                    segments.append(
                        segment
                    )

                    start_index = None

        if start_index is not None:
            segment = self._make_segment(
                start_index,
                len(silence_flags),
                frame_size,
                sample_rate,
                duration,
            )

            segments.append(
                segment
            )

        return segments

    def _make_segment(
        self,
        start_index,
        end_index,
        frame_size,
        sample_rate,
        duration,
    ):
        start = (
            start_index
            * frame_size
            / sample_rate
        )

        end = (
            end_index
            * frame_size
            / sample_rate
        )

        end = min(
            end,
            duration,
        )

        return {
            "start": round(
                start,
                3,
            ),
            "end": round(
                end,
                3,
            ),
            "duration": round(
                end - start,
                3,
            ),
        }

    def _merge_close_segments(
        self,
        segments: list[dict],
    ) -> list[dict]:
        if not segments:
            return []

        merged = [
            segments[0]
        ]

        max_gap = (
            self.MERGE_GAP_MS
            / 1000
        )

        for current in segments[1:]:
            previous = merged[-1]

            gap = (
                current["start"]
                - previous["end"]
            )

            if gap <= max_gap:
                previous["end"] = (
                    current["end"]
                )

                previous["duration"] = round(
                    previous["end"]
                    - previous["start"],
                    3,
                )

            else:
                merged.append(
                    current
                )

        return merged

    def _classify_pauses(
        self,
        pauses: list[dict],
        duration: float,
    ):
        leading_silence = 0
        trailing_silence = 0
        internal_pauses = []

        for pause in pauses:
            # 파일 시작부터 이어지는 무음
            if pause["start"] <= 0.05:
                leading_silence = max(
                    leading_silence,
                    pause["duration"],
                )

            # 파일 끝까지 이어지는 무음
            elif (
                duration
                - pause["end"]
                <= 0.05
            ):
                trailing_silence = max(
                    trailing_silence,
                    pause["duration"],
                )

            else:
                internal_pauses.append(
                    pause
                )

        return (
            leading_silence,
            trailing_silence,
            internal_pauses,
        )