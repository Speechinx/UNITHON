import os
import shutil
import uuid

from fastapi import (
    APIRouter,
    File,
    UploadFile,
    HTTPException,
)

from app.services.sensevoice import (
    SenseVoiceService,
)

from app.services.filler_analyzer import (
    FillerAnalyzer,
)

from app.services.speech_analyzer import (
    SpeechAnalyzer,
)

from app.services.risk_analyzer import (
    RiskAnalyzer,
)


router = APIRouter()


sensevoice_service = SenseVoiceService()

filler_analyzer = FillerAnalyzer()

speech_analyzer = SpeechAnalyzer()

risk_analyzer = RiskAnalyzer()


AUDIO_DIR = "audio"

os.makedirs(
    AUDIO_DIR,
    exist_ok=True,
)


@router.get("/health")
def health():

    return {
        "status": "ok",
        "service": "presentation-coach-ai",
    }


@router.post("/analyze")
async def analyze_audio(
    file: UploadFile = File(...),
):

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="Audio file is required.",
        )

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    allowed = {
        ".wav",
        ".mp3",
        ".m4a",
        ".webm",
        ".ogg",
        ".flac",
    }

    if extension not in allowed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported audio format."
            ),
        )

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    file_path = os.path.join(
        AUDIO_DIR,
        filename,
    )

    try:

        with open(
            file_path,
            "wb",
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer,
            )

        # =================================
        # 1. SenseVoice
        # =================================

        raw_result = (
            sensevoice_service.analyze(
                file_path
            )
        )

        sentence_info = (
            raw_result.get(
                "sentence_info",
                [],
            )
        )

        segments = (
            _convert_segments(
                sentence_info
            )
        )

        transcript = (
            raw_result.get(
                "text",
                "",
            )
        )

        # =================================
        # 2. 추임새
        # =================================

        filler_result = (
            filler_analyzer.analyze(
                segments
            )
        )

        # =================================
        # 3. 발화
        # =================================

        speech_result = (
            speech_analyzer.analyze(
                segments
            )
        )

        # =================================
        # 4. 위험도
        # =================================

        risk_result = (
            risk_analyzer.analyze(
                segments,
                filler_result[
                    "occurrences"
                ],
            )
        )

        # =================================
        # 5. 최종 응답
        # =================================

        return {
            "transcript": transcript,

            "duration": speech_result[
                "duration"
            ],

            "filler": filler_result,

            "speech": speech_result,

            "risk": risk_result,

            "segments": segments,
        }

    finally:

        if os.path.exists(
            file_path
        ):

            os.remove(file_path)


def _convert_segments(
    sentence_info,
):

    segments = []

    for item in sentence_info:

        text = (
            item.get("text")
            or item.get("sentence")
            or ""
        )

        emotion = None
        event = None

        # SenseVoice raw tag 처리
        if "<|" in text:

            tags = []

            parts = text.split("<|")

            for part in parts[1:]:

                if "|>" in part:

                    tag = (
                        part.split("|>")[0]
                    )

                    tags.append(tag)

            emotion_candidates = {
                "HAPPY",
                "SAD",
                "ANGRY",
                "NEUTRAL",
                "FEAR",
                "SURPRISED",
            }

            event_candidates = {
                "Speech",
                "Applause",
                "Laughter",
                "BGM",
                "Cry",
                "Sneeze",
                "Breath",
                "Cough",
            }

            for tag in tags:

                if tag in emotion_candidates:
                    emotion = tag

                if tag in event_candidates:
                    event = tag

        clean_text = text

        for tag in [
            "NEUTRAL",
            "HAPPY",
            "SAD",
            "ANGRY",
            "FEAR",
            "SURPRISED",
            "Speech",
            "Applause",
            "Laughter",
            "BGM",
            "Cry",
            "Sneeze",
            "Breath",
            "Cough",
        ]:

            clean_text = clean_text.replace(
                f"<|{tag}|>",
                "",
            )

        segments.append(
            {
                "start": (
                    item.get(
                        "start",
                        0,
                    )
                    / 1000
                ),

                "end": (
                    item.get(
                        "end",
                        0,
                    )
                    / 1000
                ),

                "speaker": (
                    f"speaker_{item['spk']}"
                    if "spk" in item
                    else None
                ),

                "text": clean_text.strip(),

                "emotion": emotion,

                "event": event,
            }
        )

    return segments