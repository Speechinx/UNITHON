import io

from fastapi.testclient import TestClient

import app.api.routes as routes_module
from app.main import app


client = TestClient(app)


class _FakeExtractor:
    def extract(self, jpeg_bytes: bytes):
        return {
            "nose": {"x": 0.5, "y": 0.2, "visibility": 1.0},
            "left_shoulder": {"x": 0.4, "y": 0.4, "visibility": 1.0},
            "right_shoulder": {"x": 0.6, "y": 0.4, "visibility": 1.0},
            "left_wrist": {"x": 0.35, "y": 0.6, "visibility": 1.0},
            "right_wrist": {"x": 0.65, "y": 0.6, "visibility": 1.0},
        }


def test_posture_window_endpoint_returns_signal_sufficient_result(
    monkeypatch,
):
    monkeypatch.setattr(
        routes_module,
        "get_posture_extractor",
        lambda: _FakeExtractor(),
    )

    files = [
        (
            "frames",
            (
                f"frame_{i}.jpg",
                io.BytesIO(b"fake-jpeg-bytes"),
                "image/jpeg",
            ),
        )
        for i in range(3)
    ]

    response = client.post(
        "/posture/window",
        params={"session_id": "test-session", "window_index": 0},
        files=files,
    )

    assert response.status_code == 200

    body = response.json()

    assert body["window_index"] == 0
    assert body["signal_sufficient"] is True

    routes_module.posture_store.clear("test-session")
