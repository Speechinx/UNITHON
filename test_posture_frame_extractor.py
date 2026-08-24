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
