import cv2
import mediapipe as mp
import numpy as np

from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision


LANDMARK_INDICES = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_wrist": 15,
    "right_wrist": 16,
}


class PostureFrameExtractor:
    def __init__(
        self,
        model_path: str = "models/pose_landmarker_lite.task",
    ):
        base_options = mp_python.BaseOptions(
            model_asset_path=model_path
        )

        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
        )

        self._landmarker = (
            mp_vision.PoseLandmarker.create_from_options(
                options
            )
        )

    def extract(
        self,
        jpeg_bytes: bytes,
    ) -> dict | None:

        image = self._decode(jpeg_bytes)

        if image is None:
            return None

        result = self._landmarker.detect(image)

        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]

        return {
            name: {
                "x": landmarks[index].x,
                "y": landmarks[index].y,
                "visibility": landmarks[index].visibility,
            }
            for name, index in LANDMARK_INDICES.items()
        }

    def _decode(
        self,
        jpeg_bytes: bytes,
    ):
        array = np.frombuffer(
            jpeg_bytes,
            dtype=np.uint8,
        )

        bgr = cv2.imdecode(
            array,
            cv2.IMREAD_COLOR,
        )

        if bgr is None:
            return None

        rgb = cv2.cvtColor(
            bgr,
            cv2.COLOR_BGR2RGB,
        )

        return mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )
