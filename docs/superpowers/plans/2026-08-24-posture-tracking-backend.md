# Posture Tracking Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add posture feedback to `pr_helper` by receiving sparse low-resolution webcam frames every 15 seconds, running MediaPipe Pose Landmarker on each frame, aggregating geometric posture signals per window, and feeding them into the existing `CoachingService` pipeline — without changing the existing audio analysis flow.

**Architecture:** A new, independent posture pipeline (`PostureFrameExtractor` → `PostureAnalyzer` → `PostureSessionStore`) runs parallel to the existing audio analyzers. It only touches the existing code at two points: a new `/posture/window` endpoint, and one new optional parameter threaded through `PresentationAnalysisService.analyze()` so `CoachingService` can see posture signals.

**Tech Stack:** MediaPipe Tasks (Pose Landmarker, `lite` model), OpenCV (frame decoding), FastAPI, pytest.

## Global Constraints

- Do not change existing `/analyze` behavior when no `session_id` query param is given — it must keep working exactly as it does today (backward compatible, no `posture` regressions in existing tests).
- No ffmpeg dependency — this pipeline never receives video, only individual JPEG frames.
- Follow existing code style in this repo: no comments unless the WHY is non-obvious, class-level constants for thresholds (mirrors `RiskAnalyzer.WINDOW_SIZE`), one class per responsibility.
- Coaching prompt additions must preserve the existing "never invent facts not in the data" principle already used throughout `CoachingService`.

---

## File Structure

- `app/services/posture_frame_extractor.py` — new. Wraps MediaPipe Pose Landmarker; JPEG bytes in, landmark dict or `None` out.
- `app/services/posture_analyzer.py` — new. Pure geometry/aggregation logic; no MediaPipe dependency, fully unit-testable with synthetic landmark data.
- `app/services/posture_session_store.py` — new. In-memory per-session accumulation of window results.
- `app/schemas/analysis_response.py` — modified. Add `PostureWindow` / `PostureResult` models and a `posture` field on `AnalysisResponse`.
- `app/services/presentation_analysis_service.py` — modified. Accept optional `posture_windows` and merge into the result dict passed to `CoachingService`.
- `app/services/coaching_service.py` — modified. Include `posture_signals` in the prompt data and add a `[자세]` rules section.
- `app/api/routes.py` — modified. New `POST /posture/window` endpoint; `POST /analyze` gains an optional `session_id` query param.
- `requirements.txt` — modified. Add `mediapipe`, `opencv-python`.
- `models/pose_landmarker_lite.task` — new binary asset (downloaded, not committed — see Task 1).

---

### Task 1: PostureFrameExtractor — MediaPipe wrapper

**Files:**
- Modify: `requirements.txt`
- Create: `app/services/posture_frame_extractor.py`
- Create: `tests/test_posture_frame_extractor.py` (place at repo root as `test_posture_frame_extractor.py`, matching existing convention of `test_risk_analyzer.py` etc. living at repo root)
- Modify: `.gitignore` (ignore the downloaded model file)

**Interfaces:**
- Produces: `PostureFrameExtractor.extract(jpeg_bytes: bytes) -> dict | None`. Returns `None` when no person is detected, otherwise a dict with keys `"nose"`, `"left_shoulder"`, `"right_shoulder"`, `"left_wrist"`, `"right_wrist"`, each mapping to `{"x": float, "y": float, "visibility": float}`. This exact shape is consumed by `PostureAnalyzer` in Task 3.

- [ ] **Step 1: Add dependencies**

Add these two lines to `requirements.txt` (after `numpy`):

```
mediapipe
opencv-python
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: installs without error (mediapipe pulls in its own numpy/protobuf pins — resolve any conflicts by upgrading pip first if install fails: `pip install --upgrade pip`).

- [ ] **Step 3: Download the pose model asset**

```bash
mkdir -p models
curl -L -o models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
```

Expected: a file at `models/pose_landmarker_lite.task` several MB in size. If this URL 404s (Google occasionally rotates these), get the current URL from https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/index#models and substitute it here.

Add a line to `.gitignore`:
```
models/*.task
```

(This is a binary ML asset — don't commit it. Document the download command in the README instead, in a later task.)

- [ ] **Step 4: Write the failing test**

Create `test_posture_frame_extractor.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it fails**

Run: `pytest test_posture_frame_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.posture_frame_extractor'`

- [ ] **Step 6: Write the implementation**

Create `app/services/posture_frame_extractor.py`:

```python
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
```

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest test_posture_frame_extractor.py -v`
Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git add requirements.txt .gitignore app/services/posture_frame_extractor.py test_posture_frame_extractor.py
git commit -m "feat: add MediaPipe pose frame extractor"
```

---

### Task 2: PostureAnalyzer — frame validity and angle geometry

**Files:**
- Create: `app/services/posture_analyzer.py`
- Create: `test_posture_analyzer.py`

**Interfaces:**
- Consumes: landmark dicts shaped like `PostureFrameExtractor.extract()`'s return value (Task 1).
- Produces: `PostureAnalyzer._is_valid(frame) -> bool`, `PostureAnalyzer._shoulder_tilt_deg(frame) -> float`, `PostureAnalyzer._head_down_deg(frame) -> float`. Consumed by Task 3's `analyze_window`.

- [ ] **Step 1: Write the failing tests**

Create `test_posture_analyzer.py`:

```python
import math

from app.services.posture_analyzer import (
    PostureAnalyzer,
)


def _landmark(x, y, visibility=1.0):
    return {"x": x, "y": y, "visibility": visibility}


def _frame(
    nose=(0.5, 0.2),
    left_shoulder=(0.4, 0.4),
    right_shoulder=(0.6, 0.4),
    left_wrist=(0.35, 0.6),
    right_wrist=(0.65, 0.6),
    visibility=1.0,
):
    return {
        "nose": _landmark(*nose, visibility),
        "left_shoulder": _landmark(*left_shoulder, visibility),
        "right_shoulder": _landmark(*right_shoulder, visibility),
        "left_wrist": _landmark(*left_wrist, visibility),
        "right_wrist": _landmark(*right_wrist, visibility),
    }


def test_is_valid_true_for_complete_high_visibility_frame():
    analyzer = PostureAnalyzer()

    assert analyzer._is_valid(_frame()) is True


def test_is_valid_false_for_none_frame():
    analyzer = PostureAnalyzer()

    assert analyzer._is_valid(None) is False


def test_is_valid_false_when_visibility_too_low():
    analyzer = PostureAnalyzer()

    frame = _frame(visibility=0.1)

    assert analyzer._is_valid(frame) is False


def test_shoulder_tilt_deg_is_zero_for_level_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.4, 0.4),
        right_shoulder=(0.6, 0.4),
    )

    assert analyzer._shoulder_tilt_deg(frame) == 0.0


def test_shoulder_tilt_deg_for_45_degree_tilt():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.4, 0.4),
        right_shoulder=(0.6, 0.6),
    )

    assert math.isclose(
        analyzer._shoulder_tilt_deg(frame),
        45.0,
        abs_tol=0.01,
    )


def test_head_down_deg_is_zero_when_nose_directly_above_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.5, 0.2),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    assert math.isclose(
        analyzer._head_down_deg(frame),
        0.0,
        abs_tol=0.01,
    )


def test_head_down_deg_is_90_when_nose_level_with_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.8, 0.5),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    assert math.isclose(
        analyzer._head_down_deg(frame),
        90.0,
        abs_tol=0.01,
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_posture_analyzer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.posture_analyzer'`

- [ ] **Step 3: Write the implementation**

Create `app/services/posture_analyzer.py`:

```python
import math


class PostureAnalyzer:
    MIN_VISIBILITY = 0.5

    REQUIRED_LANDMARKS = [
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_wrist",
        "right_wrist",
    ]

    def _is_valid(
        self,
        frame: dict | None,
    ) -> bool:

        if frame is None:
            return False

        return all(
            key in frame
            and frame[key]["visibility"] >= self.MIN_VISIBILITY
            for key in self.REQUIRED_LANDMARKS
        )

    def _shoulder_tilt_deg(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        dx = right["x"] - left["x"]
        dy = right["y"] - left["y"]

        return abs(
            math.degrees(
                math.atan2(dy, dx)
            )
        )

    def _head_down_deg(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]
        nose = frame["nose"]

        mid_x = (left["x"] + right["x"]) / 2
        mid_y = (left["y"] + right["y"]) / 2

        dx = nose["x"] - mid_x
        dy = nose["y"] - mid_y

        magnitude = math.hypot(dx, dy)

        if magnitude == 0:
            return 0.0

        cos_angle = -dy / magnitude
        cos_angle = max(-1.0, min(1.0, cos_angle))

        return math.degrees(
            math.acos(cos_angle)
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_posture_analyzer.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: add posture frame validity and angle geometry"
```

---

### Task 3: PostureAnalyzer — window aggregation

**Files:**
- Modify: `app/services/posture_analyzer.py`
- Modify: `test_posture_analyzer.py`

**Interfaces:**
- Consumes: `_is_valid`, `_shoulder_tilt_deg`, `_head_down_deg` from Task 2.
- Produces: `PostureAnalyzer.analyze_window(frames: list[dict | None]) -> dict`. Consumed by Task 6 (the `/posture/window` endpoint) and by `CoachingService` indirectly via `PostureSessionStore`.

  Return shape when `signal_sufficient` is `False`:
  ```python
  {"signal_sufficient": False, "valid_frame_ratio": 0.2}
  ```

  Return shape when `signal_sufficient` is `True`:
  ```python
  {
      "signal_sufficient": True,
      "valid_frame_ratio": 0.9,
      "shoulder_tilt_avg_deg": 4.2,
      "shoulder_tilt_exceed_ratio": 0.1,
      "head_down_avg_deg": 10.5,
      "head_down_exceed_ratio": 0.0,
      "sway_std": 0.02,
      "gesture_activity_level": "normal",
      "reasons": ["어깨 기울어짐 35% 구간"],
  }
  ```

- [ ] **Step 1: Write the failing tests**

Append to `test_posture_analyzer.py` (add this import at the top alongside the existing `math` import: no new imports needed):

```python
def test_analyze_window_signal_insufficient_when_too_many_invalid_frames():
    analyzer = PostureAnalyzer()

    frames = [None, None, None, _frame()]

    result = analyzer.analyze_window(frames)

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.25,
    }


def test_analyze_window_empty_list_is_insufficient():
    analyzer = PostureAnalyzer()

    result = analyzer.analyze_window([])

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.0,
    }


def test_analyze_window_all_level_frames_has_zero_tilt_and_low_activity():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["valid_frame_ratio"] == 1.0
    assert result["shoulder_tilt_avg_deg"] == 0.0
    assert result["shoulder_tilt_exceed_ratio"] == 0.0
    assert result["gesture_activity_level"] == "low"
    assert result["reasons"] == []


def test_analyze_window_flags_shoulder_tilt_reason_when_exceed_ratio_high():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["shoulder_tilt_exceed_ratio"] == 0.8
    assert any(
        "어깨" in reason
        for reason in result["reasons"]
    )


def test_analyze_window_detects_high_gesture_activity_from_moving_wrists():
    analyzer = PostureAnalyzer()

    frames = [
        _frame(left_wrist=(0.1, 0.6), right_wrist=(0.9, 0.6)),
        _frame(left_wrist=(0.5, 0.2), right_wrist=(0.5, 0.2)),
        _frame(left_wrist=(0.1, 0.6), right_wrist=(0.9, 0.6)),
    ]

    result = analyzer.analyze_window(frames)

    assert result["gesture_activity_level"] == "high"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_posture_analyzer.py -v`
Expected: FAIL with `AttributeError: 'PostureAnalyzer' object has no attribute 'analyze_window'`

- [ ] **Step 3: Write the implementation**

Add to `app/services/posture_analyzer.py` (add `import statistics` at the top, and add these constants + methods to the `PostureAnalyzer` class):

```python
import statistics
import math


class PostureAnalyzer:
    MIN_VISIBILITY = 0.5
    MIN_VALID_FRAME_RATIO = 0.5

    SHOULDER_TILT_THRESHOLD_DEG = 8.0
    HEAD_DOWN_THRESHOLD_DEG = 15.0

    REASON_EXCEED_RATIO_THRESHOLD = 0.3

    GESTURE_LOW_THRESHOLD = 0.01
    GESTURE_HIGH_THRESHOLD = 0.05

    REQUIRED_LANDMARKS = [
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_wrist",
        "right_wrist",
    ]

    # ... existing _is_valid, _shoulder_tilt_deg, _head_down_deg stay unchanged ...

    def analyze_window(
        self,
        frames: list[dict | None],
    ) -> dict:

        valid_frames = [
            frame
            for frame in frames
            if self._is_valid(frame)
        ]

        valid_ratio = (
            len(valid_frames) / len(frames)
            if frames
            else 0.0
        )

        if valid_ratio < self.MIN_VALID_FRAME_RATIO:
            return {
                "signal_sufficient": False,
                "valid_frame_ratio": round(valid_ratio, 2),
            }

        shoulder_tilts = [
            self._shoulder_tilt_deg(frame)
            for frame in valid_frames
        ]

        head_downs = [
            self._head_down_deg(frame)
            for frame in valid_frames
        ]

        shoulder_centers_x = [
            self._shoulder_center_x(frame)
            for frame in valid_frames
        ]

        wrist_series = [
            self._wrist_positions(frame)
            for frame in valid_frames
        ]

        shoulder_tilt_avg = statistics.mean(shoulder_tilts)
        shoulder_tilt_exceed_ratio = self._exceed_ratio(
            shoulder_tilts,
            self.SHOULDER_TILT_THRESHOLD_DEG,
        )

        head_down_avg = statistics.mean(head_downs)
        head_down_exceed_ratio = self._exceed_ratio(
            head_downs,
            self.HEAD_DOWN_THRESHOLD_DEG,
        )

        sway_std = (
            statistics.pstdev(shoulder_centers_x)
            if len(shoulder_centers_x) > 1
            else 0.0
        )

        gesture_activity = self._gesture_activity_level(
            wrist_series
        )

        reasons = []

        if shoulder_tilt_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            reasons.append(
                f"어깨 기울어짐 {shoulder_tilt_exceed_ratio * 100:.0f}% 구간"
            )

        if head_down_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            reasons.append(
                f"고개 숙임 {head_down_exceed_ratio * 100:.0f}% 구간"
            )

        return {
            "signal_sufficient": True,
            "valid_frame_ratio": round(valid_ratio, 2),
            "shoulder_tilt_avg_deg": round(shoulder_tilt_avg, 2),
            "shoulder_tilt_exceed_ratio": round(shoulder_tilt_exceed_ratio, 2),
            "head_down_avg_deg": round(head_down_avg, 2),
            "head_down_exceed_ratio": round(head_down_exceed_ratio, 2),
            "sway_std": round(sway_std, 4),
            "gesture_activity_level": gesture_activity,
            "reasons": reasons,
        }

    def _shoulder_center_x(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        return (left["x"] + right["x"]) / 2

    def _wrist_positions(
        self,
        frame: dict,
    ) -> tuple[float, float, float, float]:

        left = frame["left_wrist"]
        right = frame["right_wrist"]

        return (
            left["x"],
            left["y"],
            right["x"],
            right["y"],
        )

    def _gesture_activity_level(
        self,
        wrist_series: list[tuple[float, float, float, float]],
    ) -> str:

        if len(wrist_series) < 2:
            return "low"

        total_movement = 0.0

        for previous, current in zip(
            wrist_series,
            wrist_series[1:],
        ):
            lx0, ly0, rx0, ry0 = previous
            lx1, ly1, rx1, ry1 = current

            total_movement += math.hypot(
                lx1 - lx0,
                ly1 - ly0,
            )

            total_movement += math.hypot(
                rx1 - rx0,
                ry1 - ry0,
            )

        avg_movement = total_movement / (len(wrist_series) - 1)

        if avg_movement < self.GESTURE_LOW_THRESHOLD:
            return "low"

        if avg_movement > self.GESTURE_HIGH_THRESHOLD:
            return "high"

        return "normal"

    def _exceed_ratio(
        self,
        values: list[float],
        threshold: float,
    ) -> float:

        if not values:
            return 0.0

        exceeding = sum(
            1
            for value in values
            if value >= threshold
        )

        return exceeding / len(values)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_posture_analyzer.py -v`
Expected: PASS (12 tests total)

- [ ] **Step 5: Commit**

```bash
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: add posture window aggregation and scoring"
```

---

### Task 4: PostureSessionStore

**Files:**
- Create: `app/services/posture_session_store.py`
- Create: `test_posture_session_store.py`

**Interfaces:**
- Produces: `PostureSessionStore.add_window(session_id, window_index, result)`, `.get_windows(session_id) -> list[dict]` (sorted by `window_index`), `.clear(session_id)`. Consumed by Task 6 (endpoint) and Task 7 (`/analyze` merge).

- [ ] **Step 1: Write the failing tests**

Create `test_posture_session_store.py`:

```python
from app.services.posture_session_store import (
    PostureSessionStore,
)


def test_get_windows_returns_sorted_by_index():
    store = PostureSessionStore()

    store.add_window("abc", 1, {"score": 10})
    store.add_window("abc", 0, {"score": 5})

    assert store.get_windows("abc") == [
        {"score": 5},
        {"score": 10},
    ]


def test_get_windows_unknown_session_returns_empty_list():
    store = PostureSessionStore()

    assert store.get_windows("nope") == []


def test_clear_removes_session():
    store = PostureSessionStore()

    store.add_window("abc", 0, {"score": 5})
    store.clear("abc")

    assert store.get_windows("abc") == []


def test_sessions_are_isolated():
    store = PostureSessionStore()

    store.add_window("abc", 0, {"score": 1})
    store.add_window("xyz", 0, {"score": 2})

    assert store.get_windows("abc") == [{"score": 1}]
    assert store.get_windows("xyz") == [{"score": 2}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_posture_session_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

Create `app/services/posture_session_store.py`:

```python
class PostureSessionStore:
    def __init__(self):
        self._sessions: dict[str, dict[int, dict]] = {}

    def add_window(
        self,
        session_id: str,
        window_index: int,
        result: dict,
    ) -> None:

        self._sessions.setdefault(
            session_id,
            {},
        )[window_index] = result

    def get_windows(
        self,
        session_id: str,
    ) -> list[dict]:

        windows = self._sessions.get(
            session_id,
            {},
        )

        return [
            windows[index]
            for index in sorted(windows.keys())
        ]

    def clear(
        self,
        session_id: str,
    ) -> None:

        self._sessions.pop(session_id, None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest test_posture_session_store.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add app/services/posture_session_store.py test_posture_session_store.py
git commit -m "feat: add in-memory posture session store"
```

---

### Task 5: Response schema additions

**Files:**
- Modify: `app/schemas/analysis_response.py`

**Interfaces:**
- Produces: `PostureWindow`, `PostureResult` Pydantic models; `AnalysisResponse.posture: PostureResult`. Consumed by Task 7 (route response) and by the frontend plan (Task F5).

- [ ] **Step 1: Add the new models and field**

In `app/schemas/analysis_response.py`, add after the `RiskResult` class (which ends at the current line 91) and before `class Improvement`:

```python
class PostureWindow(
    BaseModel
):
    window_index: int

    signal_sufficient: bool
    valid_frame_ratio: float

    shoulder_tilt_avg_deg: float = 0.0
    shoulder_tilt_exceed_ratio: float = 0.0

    head_down_avg_deg: float = 0.0
    head_down_exceed_ratio: float = 0.0

    sway_std: float = 0.0

    gesture_activity_level: str = "unknown"

    reasons: List[
        str
    ] = []


class PostureResult(
    BaseModel
):
    windows: List[
        PostureWindow
    ]
```

Then add a `posture: PostureResult` field to `AnalysisResponse`, after the existing `risk: RiskResult` line:

```python
class AnalysisResponse(
    BaseModel
):
    transcript: str

    duration: float

    speech: SpeechResult

    fillers: List[
        SpeechEvent
    ]

    risk: RiskResult

    posture: PostureResult

    coaching: CoachingResult
```

There is no test file for this schema module in the existing codebase (it's a pure data contract with no behavior), so this task has no automated test — verify it another way:

- [ ] **Step 2: Verify the schema imports and instantiates**

Run:
```bash
python -c "
from app.schemas.analysis_response import AnalysisResponse, PostureResult
print(PostureResult(windows=[]))
"
```
Expected: prints `windows=[]` with no errors.

- [ ] **Step 3: Commit**

```bash
git add app/schemas/analysis_response.py
git commit -m "feat: add posture fields to AnalysisResponse schema"
```

---

### Task 6: `POST /posture/window` endpoint

**Files:**
- Modify: `app/api/routes.py`
- Create: `test_posture_route.py`

**Interfaces:**
- Consumes: `PostureFrameExtractor.extract` (Task 1), `PostureAnalyzer.analyze_window` (Task 2/3), `PostureSessionStore` (Task 4).
- Produces: `POST /posture/window?session_id=<str>&window_index=<int>` with multipart `frames` files, returning the `analyze_window` dict plus `window_index`.

- [ ] **Step 1: Add httpx as a test dependency**

Add to `requirements.txt` (needed for FastAPI's `TestClient`):
```
httpx
```

Run: `pip install httpx`

- [ ] **Step 2: Write the failing test**

Create `test_posture_route.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest test_posture_route.py -v`
Expected: FAIL with `404 Not Found` (route doesn't exist yet) or `AttributeError` on `get_posture_extractor`

- [ ] **Step 4: Write the implementation**

In `app/api/routes.py`, add these imports near the top (alongside the existing `from app.services.presentation_analysis_service import ...`):

```python
from fastapi import Query

from app.services.posture_frame_extractor import (
    PostureFrameExtractor
)

from app.services.posture_analyzer import (
    PostureAnalyzer
)

from app.services.posture_session_store import (
    PostureSessionStore
)
```

Add these module-level singletons near the existing `presentation_service = None` / `MAX_FILE_SIZE` block:

```python
posture_extractor = None
posture_analyzer = PostureAnalyzer()
posture_store = PostureSessionStore()


def get_posture_extractor():
    global posture_extractor

    if posture_extractor is None:
        posture_extractor = PostureFrameExtractor()

    return posture_extractor
```

Add the new endpoint (anywhere after the existing `/analyze` route):

```python
@router.post(
    "/posture/window",
)
async def analyze_posture_window(
    session_id: str = Query(...),
    window_index: int = Query(...),
    frames: list[UploadFile] = File(...),
):

    extractor = get_posture_extractor()

    landmark_frames = []

    for frame in frames:
        content = await frame.read()

        landmark_frames.append(
            extractor.extract(content)
        )

    result = posture_analyzer.analyze_window(
        landmark_frames
    )

    result["window_index"] = window_index

    posture_store.add_window(
        session_id,
        window_index,
        result,
    )

    return result
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest test_posture_route.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt app/api/routes.py test_posture_route.py
git commit -m "feat: add POST /posture/window endpoint"
```

---

### Task 7: Merge posture windows into `/analyze`

**Files:**
- Modify: `app/services/presentation_analysis_service.py`
- Modify: `app/api/routes.py`
- Create: `test_presentation_analysis_service_posture.py`

**Interfaces:**
- Consumes: `PostureSessionStore.get_windows` (Task 4).
- Produces: `PresentationAnalysisService.analyze(audio_path, posture_windows=None)` — the returned dict now always has a `"posture": {"windows": [...]}` key. Consumed by Task 8 (`CoachingService`) and the frontend plan (Task F5, via the route response).

- [ ] **Step 1: Write the failing test**

Create `test_presentation_analysis_service_posture.py`:

```python
from unittest.mock import MagicMock

from app.services.presentation_analysis_service import (
    PresentationAnalysisService
)


def test_analyze_includes_empty_posture_when_none_given():
    service = PresentationAnalysisService.__new__(
        PresentationAnalysisService
    )

    service.analysis_service = MagicMock()
    service.analysis_service.analyze.return_value = {
        "transcript": "hello",
    }

    service.coaching_service = MagicMock()
    service.coaching_service.generate.return_value = {}

    result = service.analyze("fake.wav")

    assert result["posture"] == {"windows": []}


def test_analyze_passes_posture_windows_into_coaching_data():
    service = PresentationAnalysisService.__new__(
        PresentationAnalysisService
    )

    service.analysis_service = MagicMock()
    service.analysis_service.analyze.return_value = {
        "transcript": "hello",
    }

    service.coaching_service = MagicMock()
    service.coaching_service.generate.return_value = {}

    windows = [{"window_index": 0, "signal_sufficient": True}]

    result = service.analyze(
        "fake.wav",
        posture_windows=windows,
    )

    assert result["posture"] == {"windows": windows}

    passed_analysis_result = (
        service.coaching_service.generate.call_args[0][0]
    )

    assert passed_analysis_result["posture"] == {
        "windows": windows
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest test_presentation_analysis_service_posture.py -v`
Expected: FAIL with `TypeError: analyze() got an unexpected keyword argument 'posture_windows'`

- [ ] **Step 3: Modify `PresentationAnalysisService.analyze`**

In `app/services/presentation_analysis_service.py`, change the `analyze` method signature and body:

```python
    def analyze(
        self,
        audio_path: str,
        posture_windows: list[dict] | None = None,
    ) -> dict:

        # ==========================================
        # 1. 음성 분석
        # ==========================================

        analysis_result = (
            self.analysis_service.analyze(
                audio_path
            )
        )

        analysis_result["posture"] = {
            "windows": posture_windows or []
        }

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

            "posture": (
                analysis_result["posture"]
            ),

            "coaching": (
                coaching_result
            ),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest test_presentation_analysis_service_posture.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Wire `session_id` through the `/analyze` route**

In `app/api/routes.py`, change the `analyze_presentation` function signature from:

```python
async def analyze_presentation(
    file: UploadFile = File(...)
):
```

to:

```python
async def analyze_presentation(
    file: UploadFile = File(...),
    session_id: str | None = Query(default=None),
):
```

Then find the line `result = service.analyze(temp_path)` and change it to:

```python
        posture_windows = (
            posture_store.get_windows(session_id)
            if session_id
            else None
        )

        result = service.analyze(
            temp_path,
            posture_windows=posture_windows,
        )
```

In the same function's return dict, add a `posture` key alongside the existing `risk` key:

```python
            "posture": (
                result.get(
                    "posture",
                    {"windows": []},
                )
            ),
```

Finally, in the existing `finally:` block (where the temp file is cleaned up), add session cleanup right after the `os.remove(temp_path)` block:

```python
        if session_id:
            posture_store.clear(session_id)
```

- [ ] **Step 6: Run the full existing test suite to confirm no regressions**

Run: `pytest -v`
Expected: all existing tests still PASS, plus the new posture tests.

- [ ] **Step 7: Commit**

```bash
git add app/services/presentation_analysis_service.py app/api/routes.py test_presentation_analysis_service_posture.py
git commit -m "feat: merge posture windows into /analyze response"
```

---

### Task 8: Extend `CoachingService` prompt with posture signals

**Files:**
- Modify: `app/services/coaching_service.py`
- Create: `test_coaching_service_posture.py`

**Interfaces:**
- Consumes: `analysis_result["posture"]` (Task 7).

- [ ] **Step 1: Write the failing tests**

Create `test_coaching_service_posture.py`:

```python
from unittest.mock import MagicMock, patch


with patch.dict(
    "os.environ",
    {"GEMINI_API_KEY": "fake-key-for-tests"},
):
    from app.services.coaching_service import (
        CoachingService
    )


def _service():
    with patch.dict(
        "os.environ",
        {"GEMINI_API_KEY": "fake-key-for-tests"},
    ):
        return CoachingService()


def test_build_coaching_data_includes_posture_signals():
    service = _service()

    analysis_result = {
        "transcript": "hello",
        "posture": {"windows": [{"window_index": 0}]},
    }

    data = service._build_coaching_data(analysis_result)

    assert data["posture_signals"] == {
        "windows": [{"window_index": 0}]
    }


def test_build_coaching_data_defaults_posture_signals_when_missing():
    service = _service()

    data = service._build_coaching_data({"transcript": "hello"})

    assert data["posture_signals"] == {}


def test_build_prompt_includes_posture_rules_section():
    service = _service()

    coaching_data = service._build_coaching_data(
        {"transcript": "hello"}
    )

    prompt = service._build_prompt(coaching_data)

    assert "[자세]" in prompt
    assert "posture_signals" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest test_coaching_service_posture.py -v`
Expected: FAIL — `_build_coaching_data` result has no `"posture_signals"` key, and `"[자세]"` not in prompt.

- [ ] **Step 3: Modify `_build_coaching_data`**

In `app/services/coaching_service.py`, inside `_build_coaching_data`, add `posture_signals` to the returned dict, right after the existing `"strength_signals"` entry:

```python
            "strength_signals": (
                analysis_result.get(
                    "strength_signals",
                    [],
                )
            ),

            "posture_signals": (
                analysis_result.get(
                    "posture",
                    {},
                )
            ),
```

- [ ] **Step 4: Add the `[자세]` rules section to `_build_prompt`**

In `_build_prompt`, find the end of the `[Emotion]` section — the line `28. 특별한 이유가 없다면` / `emotion_signal을 코칭에서 굳이 언급하지 않아도 된다.` — and insert this new block immediately after it, before the `[잘한 점]` section:

```
[자세]

28-1. posture_signals는 카메라 프레임에서 측정한 신체 자세 신호
    (어깨 기울기, 고개 숙임, 좌우 흔들림, 손 제스처 활동성)일 뿐이다.

28-2. posture_signals의 신호로 발표자의 자신감, 긴장 정도,
    실제 심리 상태를 단정하지 마라.

28-3. 각 구간의 signal_sufficient가 false라면
    해당 구간의 자세는 언급하지 마라.

28-4. shoulder_tilt_exceed_ratio나 head_down_exceed_ratio가 낮으면
    굳이 자세를 언급하지 않아도 된다.

28-5. reasons에 기록된 구체적인 수치·구간을 근거로만
    자세 피드백을 작성하라.

28-6. gesture_activity_level은 좋고 나쁨을 판단하는 지표가 아니라
    활동성 수준(낮음/보통/높음)일 뿐이다.
    "low"라고 해서 무조건 개선이 필요하다고 말하지 마라.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest test_coaching_service_posture.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add app/services/coaching_service.py test_coaching_service_posture.py
git commit -m "feat: add posture signals to coaching prompt"
```

---

### Task 9: README updates

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document the new setup step and feature**

Add a new numbered feature section (after section 9, "AI 발표 코칭") describing the posture feature in the same style as the rest of the README (mirrors the existing 감정/톤 신호 section's "참고 신호일 뿐" framing), and add an "설치" section documenting:
```bash
pip install -r requirements.txt
mkdir -p models
curl -L -o models/pose_landmarker_lite.task \
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document posture tracking feature and setup"
```

---

## Self-Review Notes

- **Spec coverage**: all 5 posture signals from the design doc (어깨 기울기, 고개 숙임, 좌우 흔들림, 손 제스처, 신뢰도) are covered by Tasks 2–3. The 15-second chunk streaming transport is covered by Task 6. The "separate from `risk`, merged only at coaching" decision is covered by Tasks 5, 7, 8. Session cleanup risk from the design doc's risk table is covered by Task 7 Step 5.
- **Type consistency**: `PostureAnalyzer.analyze_window` return keys match `PostureWindow` schema fields exactly (Task 3 vs Task 5) and match what `test_posture_route.py` and `test_presentation_analysis_service_posture.py` assert.
- **Not in scope for this plan**: real-time UI updates during recording, unified voice+posture risk score, `image` resizing (that's client-side, see the frontend plan).
