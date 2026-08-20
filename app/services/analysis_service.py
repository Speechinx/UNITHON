from app.services.sensevoice import (
    SenseVoiceService
)

from app.services.speech_analyzer import (
    SpeechAnalyzer
)

from app.services.filler_analyzer import (
    FillerAnalyzer
)

from app.services.risk_analyzer import (
    RiskAnalyzer
)

from app.services.emotion_analyzer import (
    EmotionAnalyzer
)


class AnalysisService:
    def __init__(self):
        self.sensevoice = (
            SenseVoiceService()
        )

        self.speech_analyzer = (
            SpeechAnalyzer()
        )

        self.filler_analyzer = (
            FillerAnalyzer()
        )

        self.risk_analyzer = (
            RiskAnalyzer()
        )

        # 기존 SenseVoice 모델 공유
        self.emotion_analyzer = (
            EmotionAnalyzer(
                self.sensevoice
            )
        )

    def analyze(
        self,
        audio_path: str,
    ) -> dict:

        # ==========================================
        # 1. SenseVoice 전체 분석
        # ==========================================

        sensevoice_result = (
            self.sensevoice.analyze(
                audio_path
            )
        )

        segments = (
            sensevoice_result.get(
                "segments",
                [],
            )
        )

        # ==========================================
        # 2. Speech
        # ==========================================

        speech_result = (
            self.speech_analyzer.analyze(
                segments,
                audio_path,
            )
        )

        # ==========================================
        # 3. Filler / Repetition
        # ==========================================

        filler_result = (
            self.filler_analyzer.analyze(
                segments
            )
        )

        # ==========================================
        # 4. Risk
        # ==========================================

        risk_result = (
            self.risk_analyzer.analyze(
                duration=(
                    speech_result.get(
                        "duration",
                        0,
                    )
                ),
                segments=segments,
                speech_result=(
                    speech_result
                ),
                filler_result=(
                    filler_result
                ),
            )
        )

        # ==========================================
        # 5. 10초 단위 Emotion
        # ==========================================

        emotion_windows = (
            self.emotion_analyzer.analyze(
                audio_path
            )
        )

        # ==========================================
        # 6. Emotion을 Heatmap에 결합
        # ==========================================

        heatmap = (
            risk_result.get(
                "heatmap",
                [],
            )
        )

        self._merge_emotion_into_heatmap(
            heatmap,
            emotion_windows,
        )

        # ==========================================
        # 최종 반환
        # ==========================================

        return {
            "transcript": (
                sensevoice_result.get(
                    "transcript",
                    "",
                )
            ),

            # 전체 감정 신호
            "emotion": (
                sensevoice_result.get(
                    "emotion",
                    "unknown",
                )
            ),

            "duration": (
                speech_result.get(
                    "duration",
                    0,
                )
            ),

            "segments": (
                segments
            ),

            "speech": (
                speech_result
            ),

            "fillers": (
                filler_result
            ),

            "risk": (
                risk_result
            ),

            # 필요하면 디버깅에서도 확인 가능
            "emotion_windows": (
                emotion_windows
            ),
        }

    def _merge_emotion_into_heatmap(
        self,
        heatmap: list[dict],
        emotion_windows: list[dict],
    ) -> None:

        for risk_window in heatmap:
            risk_start = (
                risk_window.get(
                    "start",
                    0,
                )
            )

            risk_end = (
                risk_window.get(
                    "end",
                    0,
                )
            )

            best_match = None
            best_overlap = 0.0

            for emotion_window in (
                emotion_windows
            ):
                emotion_start = (
                    emotion_window.get(
                        "start",
                        0,
                    )
                )

                emotion_end = (
                    emotion_window.get(
                        "end",
                        0,
                    )
                )

                overlap_start = max(
                    risk_start,
                    emotion_start,
                )

                overlap_end = min(
                    risk_end,
                    emotion_end,
                )

                overlap = max(
                    0,
                    overlap_end
                    - overlap_start,
                )

                if overlap > best_overlap:
                    best_overlap = (
                        overlap
                    )

                    best_match = (
                        emotion_window
                    )

            if best_match:
                risk_window[
                    "emotion_signal"
                ] = (
                    best_match.get(
                        "emotion_signal",
                        "unknown",
                    )
                )

            else:
                risk_window[
                    "emotion_signal"
                ] = "unknown"