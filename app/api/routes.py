import os
import shutil
import tempfile

from app.schemas.analysis_response import (
    AnalysisResponse
)

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from app.services.presentation_analysis_service import (
    PresentationAnalysisService
)


router = APIRouter()


# 서버 시작 후 최초 요청 시 모델이 로딩됨
presentation_service = None


def get_presentation_service():
    global presentation_service

    if presentation_service is None:
        presentation_service = (
            PresentationAnalysisService()
        )

    return presentation_service


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
)
async def analyze_presentation(
    file: UploadFile = File(...)
):

    # ==========================================
    # 1. 파일 형식 확인
    # ==========================================

    filename = (
        file.filename
        or ""
    )

    extension = os.path.splitext(
        filename
    )[1].lower()

    allowed_extensions = {
        ".wav",
    }

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                "현재는 WAV 파일만 지원합니다."
            ),
        )

    # ==========================================
    # 2. 임시 WAV 파일 생성
    # ==========================================

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
        ) as temp_file:

            temp_path = (
                temp_file.name
            )

            shutil.copyfileobj(
                file.file,
                temp_file,
            )

        # ==========================================
        # 3. 전체 분석 실행
        # ==========================================

        service = (
            get_presentation_service()
        )

        result = service.analyze(
            temp_path
        )

        # ==========================================
        # 4. 프론트용 결과 정리
        # ==========================================

        speech = result.get(
            "speech",
            {},
        )

        risk = result.get(
            "risk",
            {},
        )

        response = {
            "transcript": (
                result.get(
                    "transcript",
                    "",
                )
            ),

            "duration": (
                result.get(
                    "duration",
                    0,
                )
            ),

            "speech": {
                "word_count": (
                    speech.get(
                        "word_count",
                        0,
                    )
                ),

                "presentation_duration": (
                    speech.get(
                        "presentation_duration",
                        0,
                    )
                ),

                "speech_time": (
                    speech.get(
                        "speech_time",
                        0,
                    )
                ),

                "presentation_rate": (
                    speech.get(
                        "presentation_rate",
                        0,
                    )
                ),

                "articulation_rate": (
                    speech.get(
                        "articulation_rate",
                        0,
                    )
                ),

                "pace_level": (
                    speech.get(
                        "pace_level",
                        "unknown",
                    )
                ),

                "internal_pause_time": (
                    speech.get(
                        "internal_pause_time",
                        0,
                    )
                ),

                "internal_pause_ratio": (
                    speech.get(
                        "internal_pause_ratio",
                        0,
                    )
                ),

                "internal_pauses": (
                    speech.get(
                        "internal_pauses",
                        [],
                    )
                ),
            },

            "fillers": (
                result.get(
                    "fillers",
                    [],
                )
            ),

            "risk": {
                "overall_score": (
                    risk.get(
                        "overall_score",
                        0,
                    )
                ),

                "overall_level": (
                    risk.get(
                        "overall_level",
                        "low",
                    )
                ),

                "heatmap": (
                    risk.get(
                        "heatmap",
                        [],
                    )
                ),
            },

            "coaching": (
                result.get(
                    "coaching",
                    {},
                )
            ),
        }

        return response

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"분석 중 오류가 발생했습니다: {str(e)}"
            ),
        )

    finally:
        # ==========================================
        # 5. 임시 파일 삭제
        # ==========================================

        try:
            await file.close()
        except Exception:
            pass

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