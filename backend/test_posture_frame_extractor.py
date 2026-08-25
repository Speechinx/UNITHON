import cv2
import numpy as np
import pytest

from app.services.posture_frame_extractor import (
    PostureFrameExtractor,
)


@pytest.fixture
def extractor():
    ext = PostureFrameExtractor()
    yield ext
    ext.close()


def test_extract_returns_none_for_image_with_no_person(extractor):
    blank_image = np.zeros(
        (240, 320, 3),
        dtype=np.uint8,
    )

    success, encoded = cv2.imencode(
        ".jpg",
        blank_image,
    )

    assert success

    result = extractor.extract(
        encoded.tobytes()
    )

    assert result is None


def test_extract_raises_on_garbage_bytes(extractor):
    result = extractor.extract(b"not a jpeg")

    assert result is None


class _FakeLandmark:
    def __init__(self, x, y, z, visibility):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


class _FakePoseLandmarkerResult:
    def __init__(self, pose_landmarks):
        self.pose_landmarks = pose_landmarks


def test_extract_maps_landmark_indices_correctly(monkeypatch, extractor):
    blank_image = np.zeros(
        (240, 320, 3),
        dtype=np.uint8,
    )

    success, encoded = cv2.imencode(".jpg", blank_image)
    assert success

    fake_landmarks = [
        _FakeLandmark(
            x=index / 100,
            y=index / 100,
            z=index / 1000,
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
        "nose": {"x": 0.0, "y": 0.0, "z": 0.0, "visibility": 0.0},
        "left_ear": {"x": 0.07, "y": 0.07, "z": 0.007, "visibility": 0.07},
        "right_ear": {"x": 0.08, "y": 0.08, "z": 0.008, "visibility": 0.08},
        "left_shoulder": {"x": 0.11, "y": 0.11, "z": 0.011, "visibility": 0.11},
        "right_shoulder": {"x": 0.12, "y": 0.12, "z": 0.012, "visibility": 0.12},
        "left_elbow": {"x": 0.13, "y": 0.13, "z": 0.013, "visibility": 0.13},
        "right_elbow": {"x": 0.14, "y": 0.14, "z": 0.014, "visibility": 0.14},
        "left_wrist": {"x": 0.15, "y": 0.15, "z": 0.015, "visibility": 0.15},
        "right_wrist": {"x": 0.16, "y": 0.16, "z": 0.016, "visibility": 0.16},
        "left_hip": {"x": 0.23, "y": 0.23, "z": 0.023, "visibility": 0.23},
        "right_hip": {"x": 0.24, "y": 0.24, "z": 0.024, "visibility": 0.24},
    }
