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


class AnalysisService:
    def __init__(self):
        # ==========================================
        # 각 분석 서비스 초기화
        # ==========================================

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

    def analyze(
        self,
        audio_path: str,
    ) -> dict:

        # ==========================================
        # 1. SenseVoice 분석
        # ==========================================

        sensevoice_result = (
            self.sensevoice.analyze(
                audio_path
            )
        )

        segments = sensevoice_result.get(
            "segments",
            [],
        )

        # ==========================================
        # 2. Speech 분석
        # ==========================================

        speech_result = (
            self.speech_analyzer.analyze(
                segments,
                audio_path,
            )
        )

        # ==========================================
        # 3. 추임새 / 반복 분석
        # ==========================================

        filler_result = (
            self.filler_analyzer.analyze(
                segments
            )
        )

        # ==========================================
        # 4. Risk 분석
        # ==========================================

        risk_result = (
            self.risk_analyzer.analyze(
                duration=speech_result.get(
                    "duration",
                    0,
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
        # 5. 최종 분석 결과
        # ==========================================

        return {
            "transcript": (
                sensevoice_result.get(
                    "transcript",
                    "",
                )
            ),

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

            "segments": segments,

            "speech": speech_result,

            "fillers": filler_result,

            "risk": risk_result,
        }