import cv2
import numpy as np

from app.services.posture_frame_extractor import (
    PostureFrameExtractor,
)


def test_extract_returns_none_for_image_with_no_person():
    blank_image = np.zeros(
        (240, 320, 3),
        dtype=np.uint8,
    )

    success, encoded = cv2.imencode(
        ".jpg",
        blank_image,
    )

    assert success

    extractor = PostureFrameExtractor()

    result = extractor.extract(
        encoded.tobytes()
    )

    assert result is None


def test_extract_raises_on_garbage_bytes():
    extractor = PostureFrameExtractor()

    result = extractor.extract(b"not a jpeg")

    assert result is None


class _FakeLandmark:
    def __init__(self, x, y, visibility):
        self.x = x
        self.y = y
        self.visibility = visibility


class _FakePoseLandmarkerResult:
    def __init__(self, pose_landmarks):
        self.pose_landmarks = pose_landmarks


def test_extract_maps_landmark_indices_correctly(monkeypatch):
    blank_image = np.zeros(
        (240, 320, 3),
        dtype=np.uint8,
    )

    success, encoded = cv2.imencode(".jpg", blank_image)
    assert success

    extractor = PostureFrameExtractor()

    fake_landmarks = [
        _FakeLandmark(
            x=index / 100,
            y=index / 100,
            visibility=index / 100,
        )
        for index in range(33)
    ]

    monkeypatch.setattr(
        extractor._landmarker,
        "detect",
        lambda image: _FakePoseLandmarkerResult([fake_landmarks]),
    )

    result = extractor.extract(encoded.tobytes())

    assert result == {
        "nose": {"x": 0.0, "y": 0.0, "visibility": 0.0},
        "left_shoulder": {"x": 0.11, "y": 0.11, "visibility": 0.11},
        "right_shoulder": {"x": 0.12, "y": 0.12, "visibility": 0.12},
        "left_wrist": {"x": 0.15, "y": 0.15, "visibility": 0.15},
        "right_wrist": {"x": 0.16, "y": 0.16, "visibility": 0.16},
    }
