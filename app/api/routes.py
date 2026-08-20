import os
import shutil
import tempfile
import wave

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from app.schemas.analysis_response import (
    AnalysisResponse
)

from app.services.presentation_analysis_service import (
    PresentationAnalysisService
)


router = APIRouter()


presentation_service = None


MAX_FILE_SIZE = 50 * 1024 * 1024


def get_presentation_service():
    global presentation_service

    if presentation_service is None:
        presentation_service = (
            PresentationAnalysisService()
        )

    return presentation_service


def validate_wav(
    file_path: str,
):
    try:
        with wave.open(
            file_path,
            "rb",
        ) as wav_file:

            channels = (
                wav_file.getnchannels()
            )

            sample_rate = (
                wav_file.getframerate()
            )

            frames = (
                wav_file.getnframes()
            )

            if frames <= 0:
                raise ValueError(
                    "빈 WAV 파일입니다."
                )

            if channels <= 0:
                raise ValueError(
                    "유효하지 않은 채널 수입니다."
                )

            if sample_rate <= 0:
                raise ValueError(
                    "유효하지 않은 샘플링 레이트입니다."
                )

    except wave.Error:
        raise HTTPException(
            status_code=400,
            detail=(
                "실제 WAV 오디오 파일이 아닙니다."
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
)
async def analyze_presentation(
    file: UploadFile = File(...)
):

    filename = (
        file.filename
        or ""
    )

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension != ".wav":
        raise HTTPException(
            status_code=400,
            detail=(
                "현재는 WAV 파일만 지원합니다."
            ),
        )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
        ) as temp_file:

            temp_path = (
                temp_file.name
            )

            total_size = 0

            while True:
                chunk = await file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_size += len(
                    chunk
                )

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "파일 크기는 최대 50MB까지 지원합니다."
                        ),
                    )

                temp_file.write(
                    chunk
                )

        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "빈 파일은 업로드할 수 없습니다."
                ),
            )

        validate_wav(
            temp_path
        )

        service = (
            get_presentation_service()
        )

        result = service.analyze(
            temp_path
        )

        speech = result.get(
            "speech",
            {},
        )

        risk = result.get(
            "risk",
            {},
        )

        return {
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