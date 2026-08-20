from app.services.analysis_service import (
    AnalysisService
)

from app.services.coaching_service import (
    CoachingService
)


class PresentationAnalysisService:
    def __init__(self):
        self.analysis_service = (
            AnalysisService()
        )

        self.coaching_service = (
            CoachingService()
        )

    def analyze(
        self,
        audio_path: str,
    ) -> dict:

        # ==========================================
        # 1. 음성 분석
        # ==========================================

        analysis_result = (
            self.analysis_service.analyze(
                audio_path
            )
        )

        # ==========================================
        # 2. Gemini 코칭 생성
        # ==========================================

        coaching_result = (
            self.coaching_service.generate(
                analysis_result
            )
        )

        # ==========================================
        # 3. 최종 결과 통합
        # ==========================================

        return {
            "transcript": (
                analysis_result.get(
                    "transcript",
                    "",
                )
            ),

            "emotion": (
                analysis_result.get(
                    "emotion",
                    "unknown",
                )
            ),

            "duration": (
                analysis_result.get(
                    "duration",
                    0,
                )
            ),

            "segments": (
                analysis_result.get(
                    "segments",
                    [],
                )
            ),

            "speech": (
                analysis_result.get(
                    "speech",
                    {},
                )
            ),

            "fillers": (
                analysis_result.get(
                    "fillers",
                    [],
                )
            ),

            "risk": (
                analysis_result.get(
                    "risk",
                    {},
                )
            ),

            "coaching": (
                coaching_result
            ),
        }