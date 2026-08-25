# Cloud Run image for the AI Presentation Coach backend.
#
# Models are downloaded at BUILD time (baked into the image) instead of on
# first request, because Cloud Run instances have an ephemeral filesystem —
# anything written at runtime is gone on the next cold start. Baking them in
# means every cold start uses the weights already in the image; no
# re-download, no slow first request.

FROM python:3.11-slim

# libgl1/libglib2.0-0: mediapipe pulls in opencv-contrib-python, which needs
# libGL at import time even for CPU-only, headless use.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# CPU-only torch/torchaudio wheels first — the default PyPI wheels pull in
# CUDA libraries that are multiple GB and useless here (SenseVoice runs with
# device="cpu"). Installing these first means the plain `torch`/`torchaudio`
# lines in requirements.txt are already satisfied and get skipped.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
        torch torchaudio \
    && pip install --no-cache-dir -r requirements.txt

# MediaPipe pose landmarker model (see backend/README.md).
RUN mkdir -p models && \
    curl -L -o models/pose_landmarker_lite.task \
    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

# SenseVoice STT + VAD + speaker models (funasr/modelscope). This downloads
# into the default modelscope cache under /root/.cache, which then ships
# as part of the image layer.
RUN python -c "\
from funasr import AutoModel; \
AutoModel(\
    model='iic/SenseVoiceSmall', \
    vad_model='fsmn-vad', \
    vad_kwargs={'max_single_segment_time': 30000}, \
    spk_model='cam++', \
    device='cpu', \
    disable_update=True, \
)"

COPY app ./app

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# Cloud Run injects $PORT; shell form so the substitution actually happens.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
