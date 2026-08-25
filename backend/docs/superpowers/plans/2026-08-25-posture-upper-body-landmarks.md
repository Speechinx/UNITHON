# Posture Upper-Body Landmark Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two new posture signals — torso lean (from hips) and arm openness (from elbows) — on top of the existing shoulder-tilt/head-down/sway/gesture signals, without ever letting a frequently-out-of-frame landmark group (hips especially) invalidate a whole window.

**Architecture:** Extend the MediaPipe landmark extraction dict with 4 new indices (hips, elbows). In `PostureAnalyzer`, generalize the existing wrist-only optional-signal gate into a reusable `_has_signal(frame, landmark_names)` helper, and reuse it for two new independently-gated optional groups (torso, arm). Each optional group degrades to "insufficient"/"unknown" on its own — the core `signal_sufficient` gate (nose + shoulders) is never touched. Wire the two new fields through the Pydantic schema, the coaching prompt's `[자세]` rule block, and the Flutter model/detail-card display.

**Tech Stack:** Python 3.11, FastAPI/Pydantic, pytest, Flutter/Dart, `flutter_test`.

**Design spec:** `backend/docs/superpowers/specs/2026-08-25-posture-upper-body-landmarks-design.md`

## Global Constraints

- `PostureAnalyzer.REQUIRED_LANDMARKS` (nose, left_shoulder, right_shoulder) must never gain a new member — this is the lesson from the wrist-signal bug fixed earlier this session. New landmark groups (hip, elbow) are gated independently and default to "insufficient"/"unknown", never to a fabricated value.
- No face/eye/ear landmarks and no finger/hand landmarks — explicitly out of scope per the approved design.
- No combined single posture score across signals — each signal stays independently reported.
- No change to capture cadence, resolution, or the 15-second windowing scheme.
- Reuse `MIN_VALID_FRAME_RATIO` (0.5) and `REASON_EXCEED_RATIO_THRESHOLD` (0.3) as-is for the new signals' sufficiency/reason gating — do not introduce new ratio constants for these.
- `TORSO_LEAN_THRESHOLD_DEG = 10.0`, `ARM_OPENNESS_LOW_THRESHOLD = 0.8`, `ARM_OPENNESS_HIGH_THRESHOLD = 1.3` are placeholder starting values (not empirically tuned), same status as the existing `GESTURE_LOW_THRESHOLD`/`GESTURE_HIGH_THRESHOLD` constants.
- Backend test command: `cd backend && source .venv/bin/activate && python -m pytest <file> -v`
- Frontend test command: `cd frontend && flutter test test/posture_timeline_test.dart`

---

### Task 1: Extract hip and elbow landmarks

**Files:**
- Modify: `backend/app/services/posture_frame_extractor.py:9-15`
- Test: `backend/test_posture_frame_extractor.py:81-87`

**Interfaces:**
- Produces: `PostureFrameExtractor.extract()` now returns a dict with 9 keys instead of 5 — adds `left_hip`, `right_hip`, `left_elbow`, `right_elbow`, each `{"x": float, "y": float, "visibility": float}`. Later tasks read these keys directly by name.

- [ ] **Step 1: Write the failing test**

Modify `backend/test_posture_frame_extractor.py`, replacing the `assert result == {...}` block (lines 81-87) with:

```python
    assert result == {
        "nose": {"x": 0.0, "y": 0.0, "visibility": 0.0},
        "left_shoulder": {"x": 0.11, "y": 0.11, "visibility": 0.11},
        "right_shoulder": {"x": 0.12, "y": 0.12, "visibility": 0.12},
        "left_elbow": {"x": 0.13, "y": 0.13, "visibility": 0.13},
        "right_elbow": {"x": 0.14, "y": 0.14, "visibility": 0.14},
        "left_wrist": {"x": 0.15, "y": 0.15, "visibility": 0.15},
        "right_wrist": {"x": 0.16, "y": 0.16, "visibility": 0.16},
        "left_hip": {"x": 0.23, "y": 0.23, "visibility": 0.23},
        "right_hip": {"x": 0.24, "y": 0.24, "visibility": 0.24},
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_posture_frame_extractor.py::test_extract_maps_landmark_indices_correctly -v`
Expected: FAIL — actual dict is missing `left_elbow`, `right_elbow`, `left_hip`, `right_hip` keys (assertion diff shows the 5-key dict vs the 9-key expected dict).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/posture_frame_extractor.py`, replace the `LANDMARK_INDICES` dict (lines 9-15):

```python
LANDMARK_INDICES = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_posture_frame_extractor.py -v`
Expected: all tests PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_frame_extractor.py test_posture_frame_extractor.py
git commit -m "feat: extract hip and elbow landmarks alongside existing posture points"
```

---

### Task 2: Torso lean signal

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Modify: `backend/app/schemas/analysis_response.py:94-115`
- Modify: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: frame dicts now carry `left_hip`/`right_hip` keys (Task 1).
- Produces:
  - `PostureAnalyzer._has_signal(self, frame: dict, landmark_names: list[str]) -> bool` — replaces `_has_gesture_signal`; later tasks (Task 3) reuse this for the arm group.
  - `PostureAnalyzer._torso_lean_deg(self, frame: dict) -> float`
  - `analyze_window()`'s returned dict gains `torso_signal_sufficient: bool`, `torso_lean_avg_deg: float`, `torso_lean_exceed_ratio: float`.
  - `PostureWindow` schema gains the same 3 fields with defaults `False`/`0.0`/`0.0`.

- [ ] **Step 1: Write the failing tests**

In `backend/test_posture_analyzer.py`, replace the `_frame()` helper (lines 12-26) to add hip parameters:

```python
def _frame(
    nose=(0.5, 0.2),
    left_shoulder=(0.4, 0.4),
    right_shoulder=(0.6, 0.4),
    left_wrist=(0.35, 0.6),
    right_wrist=(0.65, 0.6),
    left_hip=(0.45, 0.75),
    right_hip=(0.55, 0.75),
    visibility=1.0,
):
    return {
        "nose": _landmark(*nose, visibility),
        "left_shoulder": _landmark(*left_shoulder, visibility),
        "right_shoulder": _landmark(*right_shoulder, visibility),
        "left_wrist": _landmark(*left_wrist, visibility),
        "right_wrist": _landmark(*right_wrist, visibility),
        "left_hip": _landmark(*left_hip, visibility),
        "right_hip": _landmark(*right_hip, visibility),
    }
```

Then add these tests at the end of the file:

```python
def test_torso_lean_deg_is_zero_when_shoulder_center_is_above_hip_center():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.4, 0.3),
        right_shoulder=(0.6, 0.3),
        left_hip=(0.4, 0.7),
        right_hip=(0.6, 0.7),
    )

    assert analyzer._torso_lean_deg(frame) == 0.0


def test_torso_lean_deg_for_45_degree_lean():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.5, 0.3),
        right_shoulder=(0.5, 0.3),
        left_hip=(0.7, 0.5),
        right_hip=(0.7, 0.5),
    )

    assert math.isclose(
        analyzer._torso_lean_deg(frame),
        45.0,
        abs_tol=0.01,
    )


def test_analyze_window_all_level_frames_reports_torso_lean_too():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["torso_signal_sufficient"] is True
    assert result["torso_lean_avg_deg"] == 0.0
    assert result["torso_lean_exceed_ratio"] == 0.0


def test_analyze_window_torso_insufficient_when_hips_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_hip"]["visibility"] = 0.1
    frame["right_hip"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["torso_signal_sufficient"] is False
    assert result["torso_lean_avg_deg"] == 0.0
    assert result["torso_lean_exceed_ratio"] == 0.0


def test_analyze_window_flags_torso_lean_reason_when_exceed_ratio_high():
    analyzer = PostureAnalyzer()

    leaned_frame = _frame(
        left_shoulder=(0.55, 0.3),
        right_shoulder=(0.55, 0.3),
        left_hip=(0.4, 0.7),
        right_hip=(0.4, 0.7),
    )

    frames = [leaned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_exceed_ratio"] == 0.8
    assert any(
        "상체" in reason
        for reason in result["reasons"]
    )


def test_analyze_window_result_is_compatible_with_posture_window_schema():
    from app.schemas.analysis_response import PostureWindow

    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)
    result["window_index"] = 0

    PostureWindow(**result)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_posture_analyzer.py -v`
Expected: the new `test_torso_lean_deg_*` tests FAIL with `AttributeError: 'PostureAnalyzer' object has no attribute '_torso_lean_deg'`; the new `test_analyze_window_*torso*` tests FAIL with `KeyError: 'torso_signal_sufficient'`; the schema-compat test FAILS with a pydantic `ValidationError` (unexpected keyword `torso_signal_sufficient` is actually fine for pydantic — it will fail instead because `analyze_window()` doesn't produce that key yet, so the schema test fails at the `KeyError`-free path... confirm it fails with a clear pydantic error or passes-early; either way it must not silently pass before Step 3). All other existing tests still PASS.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/posture_analyzer.py`:

3a. Add `TORSO_LEAN_THRESHOLD_DEG` next to the other threshold constants (after line 10, `HEAD_DOWN_THRESHOLD_DEG = 60.0`):

```python
    TORSO_LEAN_THRESHOLD_DEG = 10.0
```

3b. Add `TORSO_LANDMARKS` next to `GESTURE_LANDMARKS` (lines 23-26):

```python
    GESTURE_LANDMARKS = [
        "left_wrist",
        "right_wrist",
    ]

    TORSO_LANDMARKS = [
        "left_hip",
        "right_hip",
    ]
```

3c. Replace `_has_gesture_signal` (lines 42-51) with a generalized version:

```python
    def _has_signal(
        self,
        frame: dict,
        landmark_names: list[str],
    ) -> bool:

        return all(
            key in frame
            and frame[key]["visibility"] >= self.MIN_VISIBILITY
            for key in landmark_names
        )
```

3d. Update the call site in `analyze_window` (the `gesture_frames` comprehension, lines 141-145) to use the generalized helper:

```python
        gesture_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.GESTURE_LANDMARKS)
        ]
```

3e. Add `_shoulder_center`, `_hip_center`, and `_torso_lean_deg` methods, right after `_head_down_deg` (after line 101):

```python
    def _shoulder_center(
        self,
        frame: dict,
    ) -> tuple[float, float]:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        return (
            (left["x"] + right["x"]) / 2,
            (left["y"] + right["y"]) / 2,
        )

    def _hip_center(
        self,
        frame: dict,
    ) -> tuple[float, float]:

        left = frame["left_hip"]
        right = frame["right_hip"]

        return (
            (left["x"] + right["x"]) / 2,
            (left["y"] + right["y"]) / 2,
        )

    def _torso_lean_deg(
        self,
        frame: dict,
    ) -> float:

        shoulder_x, shoulder_y = self._shoulder_center(frame)
        hip_x, hip_y = self._hip_center(frame)

        dx = shoulder_x - hip_x
        dy = shoulder_y - hip_y

        return abs(
            math.degrees(
                math.atan2(
                    abs(dx),
                    abs(dy),
                )
            )
        )
```

3f. In `analyze_window`, right after the `gesture_ratio` block (after line 151, before `shoulder_tilt_avg = statistics.mean(...)`), insert the torso computation:

```python
        torso_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.TORSO_LANDMARKS)
        ]

        torso_ratio = (
            len(torso_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        torso_signal_sufficient = (
            torso_ratio >= self.MIN_VALID_FRAME_RATIO
        )

        if torso_signal_sufficient:
            torso_leans = [
                self._torso_lean_deg(frame)
                for frame in torso_frames
            ]

            torso_lean_avg = statistics.mean(torso_leans)
            torso_lean_exceed_ratio = self._exceed_ratio(
                torso_leans,
                self.TORSO_LEAN_THRESHOLD_DEG,
            )
        else:
            torso_lean_avg = 0.0
            torso_lean_exceed_ratio = 0.0
```

3g. Add the torso reason, right after the existing `head_down_exceed_ratio` reason block (after line 193, before `return {`):

```python
        if (
            torso_signal_sufficient
            and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            reasons.append(
                f"상체 기울어짐 {torso_lean_exceed_ratio * 100:.0f}% 구간"
            )
```

3h. Add the 3 new keys to the `return` dict (lines 195-205), inserting them after `"gesture_activity_level": gesture_activity,` and before `"reasons": reasons,`:

```python
            "torso_signal_sufficient": torso_signal_sufficient,
            "torso_lean_avg_deg": round(torso_lean_avg, 2),
            "torso_lean_exceed_ratio": round(torso_lean_exceed_ratio, 2),
```

In `backend/app/schemas/analysis_response.py`, add 3 fields to `PostureWindow` (after `gesture_activity_level: str = "unknown"`, line 110):

```python
    torso_signal_sufficient: bool = False
    torso_lean_avg_deg: float = 0.0
    torso_lean_exceed_ratio: float = 0.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_posture_analyzer.py test_posture_route.py test_posture_frame_extractor.py test_posture_session_store.py test_presentation_analysis_service_posture.py -v`
Expected: all tests PASS (32 passed: 25 existing + 6 new torso tests + 1 schema-compat test, plus the 4 extractor tests already covered in Task 1 — actual count depends on final tally, but zero failures/errors).

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py app/schemas/analysis_response.py test_posture_analyzer.py
git commit -m "feat: add torso lean posture signal from hip landmarks"
```

---

### Task 3: Arm openness signal

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Modify: `backend/app/schemas/analysis_response.py`
- Modify: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: frame dicts now carry `left_elbow`/`right_elbow` keys (Task 1); reuses `PostureAnalyzer._has_signal` (Task 2).
- Produces: `analyze_window()`'s returned dict gains `arm_openness_level: str` (`"closed" | "normal" | "open" | "unknown"`); `PostureWindow` schema gains the same field with default `"unknown"`.

- [ ] **Step 1: Write the failing tests**

In `backend/test_posture_analyzer.py`, replace the `_frame()` helper again to add elbow parameters (keep the hip parameters added in Task 2):

```python
def _frame(
    nose=(0.5, 0.2),
    left_shoulder=(0.4, 0.4),
    right_shoulder=(0.6, 0.4),
    left_wrist=(0.35, 0.6),
    right_wrist=(0.65, 0.6),
    left_hip=(0.45, 0.75),
    right_hip=(0.55, 0.75),
    left_elbow=(0.38, 0.55),
    right_elbow=(0.62, 0.55),
    visibility=1.0,
):
    return {
        "nose": _landmark(*nose, visibility),
        "left_shoulder": _landmark(*left_shoulder, visibility),
        "right_shoulder": _landmark(*right_shoulder, visibility),
        "left_wrist": _landmark(*left_wrist, visibility),
        "right_wrist": _landmark(*right_wrist, visibility),
        "left_hip": _landmark(*left_hip, visibility),
        "right_hip": _landmark(*right_hip, visibility),
        "left_elbow": _landmark(*left_elbow, visibility),
        "right_elbow": _landmark(*right_elbow, visibility),
    }
```

Then add these tests at the end of the file:

```python
def test_arm_openness_ratio_greater_than_one_when_elbows_wider_than_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(
        left_shoulder=(0.45, 0.4),
        right_shoulder=(0.55, 0.4),
        left_elbow=(0.2, 0.4),
        right_elbow=(0.8, 0.4),
    )

    assert analyzer._arm_openness_ratio(frame) == 6.0


def test_arm_openness_level_closed_when_ratio_low():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([0.5, 0.6]) == "closed"


def test_arm_openness_level_open_when_ratio_high():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([1.5, 1.6]) == "open"


def test_arm_openness_level_normal_at_middle_ratio():
    analyzer = PostureAnalyzer()

    assert analyzer._arm_openness_level([1.0, 1.0]) == "normal"


def test_analyze_window_all_level_frames_has_normal_arm_openness():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["arm_openness_level"] == "normal"


def test_analyze_window_arm_openness_unknown_when_elbows_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_elbow"]["visibility"] = 0.1
    frame["right_elbow"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["arm_openness_level"] == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_posture_analyzer.py -v`
Expected: the new `test_arm_openness_ratio_*` and `test_arm_openness_level_*` tests FAIL with `AttributeError` (`_arm_openness_ratio`/`_arm_openness_level` not defined); the two `test_analyze_window_*arm*` tests FAIL with `KeyError: 'arm_openness_level'`. All other tests (including Task 2's torso tests and the schema-compat test) still PASS.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/posture_analyzer.py`:

3a. Add `ARM_LANDMARKS` and the two openness thresholds next to the other landmark/threshold constants:

```python
    ARM_LANDMARKS = [
        "left_elbow",
        "right_elbow",
    ]
```

```python
    ARM_OPENNESS_LOW_THRESHOLD = 0.8
    ARM_OPENNESS_HIGH_THRESHOLD = 1.3
```

3b. Add `_distance`, `_arm_openness_ratio`, and `_arm_openness_level` methods, right after `_wrist_positions`:

```python
    def _distance(
        self,
        a: dict,
        b: dict,
    ) -> float:

        return math.hypot(
            b["x"] - a["x"],
            b["y"] - a["y"],
        )

    def _arm_openness_ratio(
        self,
        frame: dict,
    ) -> float:

        shoulder_width = self._distance(
            frame["left_shoulder"],
            frame["right_shoulder"],
        )

        if shoulder_width == 0:
            return 1.0

        elbow_width = self._distance(
            frame["left_elbow"],
            frame["right_elbow"],
        )

        return elbow_width / shoulder_width

    def _arm_openness_level(
        self,
        ratios: list[float],
    ) -> str:

        avg_ratio = statistics.mean(ratios)

        if avg_ratio < self.ARM_OPENNESS_LOW_THRESHOLD:
            return "closed"

        if avg_ratio > self.ARM_OPENNESS_HIGH_THRESHOLD:
            return "open"

        return "normal"
```

3c. In `analyze_window`, right after the torso block added in Task 2 (after the `torso_lean_avg`/`torso_lean_exceed_ratio` if/else, before `shoulder_tilt_avg = statistics.mean(...)`), insert the arm computation:

```python
        arm_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.ARM_LANDMARKS)
        ]

        arm_ratio = (
            len(arm_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        if arm_ratio >= self.MIN_VALID_FRAME_RATIO:
            arm_openness = self._arm_openness_level(
                [
                    self._arm_openness_ratio(frame)
                    for frame in arm_frames
                ]
            )
        else:
            arm_openness = "unknown"
```

3d. Add `"arm_openness_level": arm_openness,` to the `return` dict, after `"torso_lean_exceed_ratio": round(torso_lean_exceed_ratio, 2),` and before `"reasons": reasons,`.

In `backend/app/schemas/analysis_response.py`, add to `PostureWindow` (after `torso_lean_exceed_ratio: float = 0.0`):

```python
    arm_openness_level: str = "unknown"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_posture_analyzer.py test_posture_route.py test_posture_frame_extractor.py test_posture_session_store.py test_presentation_analysis_service_posture.py -v`
Expected: all tests PASS, zero failures/errors.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py app/schemas/analysis_response.py test_posture_analyzer.py
git commit -m "feat: add arm openness posture signal from elbow landmarks"
```

---

### Task 4: Coaching prompt rules for the new signals

**Files:**
- Modify: `backend/app/services/coaching_service.py:436-455`
- Modify: `backend/test_coaching_service_posture.py`

**Interfaces:**
- Consumes: `torso_signal_sufficient`, `torso_lean_avg_deg`, `torso_lean_exceed_ratio`, `arm_openness_level` field names (Tasks 2-3) — referenced by name in the prompt rule text only, no code-level dependency.

- [ ] **Step 1: Write the failing test**

In `backend/test_coaching_service_posture.py`, replace `test_build_prompt_includes_posture_rules_section` (lines 44-55) with:

```python
def test_build_prompt_includes_posture_rules_section():
    service = _service()

    coaching_data = service._build_coaching_data(
        {"transcript": "hello"}
    )

    prompt = service._build_prompt(coaching_data)

    assert "[자세]" in prompt
    assert "posture_signals" in prompt
    assert "torso_signal_sufficient" in prompt
    assert "arm_openness_level" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_coaching_service_posture.py::test_build_prompt_includes_posture_rules_section -v`
Expected: FAIL — `AssertionError` because the prompt text doesn't mention `torso_signal_sufficient` or `arm_openness_level` yet.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/coaching_service.py`, insert two new rules after rule `28-6` (after line 455, before the blank lines leading into `[잘한 점]`):

```
28-7. torso_lean_exceed_ratio가 낮거나 torso_signal_sufficient가 false이면
    상체 기울기를 언급하지 않아도 된다.

28-8. arm_openness_level은 좋고 나쁨을 판단하는 지표가 아니라
    팔이 벌어진 정도(닫힘/보통/열림)일 뿐이다.
    "closed"라고 해서 무조건 소극적이라고 말하지 마라.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && source .venv/bin/activate && python -m pytest test_coaching_service_posture.py -v`
Expected: all tests PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/coaching_service.py test_coaching_service_posture.py
git commit -m "feat: add coaching prompt rules for torso lean and arm openness signals"
```

---

### Task 5: Frontend model and display

**Files:**
- Modify: `frontend/lib/posture_timeline.dart`
- Modify: `frontend/lib/main.dart` (posture detail section ~line 2709-2794, and `_gestureActivityText` ~line 3306-3322)
- Modify: `frontend/test/posture_timeline_test.dart`

**Interfaces:**
- Consumes: JSON field names `torso_signal_sufficient`, `torso_lean_avg_deg`, `torso_lean_exceed_ratio`, `arm_openness_level` from the backend response (Tasks 2-3).
- Produces: `PostureWindow` gains `torsoSignalSufficient: bool`, `torsoLeanAvgDeg: double`, `torsoLeanExceedRatio: double`, `armOpennessLevel: String` fields, consumed by `_WindowDetailCard`'s posture section in `main.dart`.

- [ ] **Step 1: Write the failing tests**

In `frontend/test/posture_timeline_test.dart`, add these two tests before the closing `}`:

```dart
  test('fromJson parses torso lean and arm openness fields', () {
    final window = PostureWindow.fromJson({
      'window_index': 1,
      'signal_sufficient': true,
      'torso_signal_sufficient': true,
      'torso_lean_avg_deg': 12.0,
      'torso_lean_exceed_ratio': 0.4,
      'arm_openness_level': 'open',
    });

    expect(window.torsoSignalSufficient, true);
    expect(window.torsoLeanAvgDeg, 12.0);
    expect(window.torsoLeanExceedRatio, 0.4);
    expect(window.armOpennessLevel, 'open');
  });

  test(
    'fromJson defaults torso fields to insufficient and arm openness to unknown',
    () {
      final window = PostureWindow.fromJson({
        'window_index': 0,
        'signal_sufficient': false,
      });

      expect(window.torsoSignalSufficient, false);
      expect(window.torsoLeanAvgDeg, 0.0);
      expect(window.torsoLeanExceedRatio, 0.0);
      expect(window.armOpennessLevel, 'unknown');
    },
  );
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && flutter test test/posture_timeline_test.dart`
Expected: FAIL — compile error, `torsoSignalSufficient`/`torsoLeanAvgDeg`/`torsoLeanExceedRatio`/`armOpennessLevel` are not defined on `PostureWindow`.

- [ ] **Step 3: Write minimal implementation**

Replace the full contents of `frontend/lib/posture_timeline.dart` with:

```dart
class PostureWindow {
  const PostureWindow({
    required this.windowIndex,
    required this.signalSufficient,
    required this.shoulderTiltAvgDeg,
    required this.shoulderTiltExceedRatio,
    required this.headDownAvgDeg,
    required this.headDownExceedRatio,
    required this.gestureActivityLevel,
    required this.torsoSignalSufficient,
    required this.torsoLeanAvgDeg,
    required this.torsoLeanExceedRatio,
    required this.armOpennessLevel,
    required this.reasons,
  });

  final int windowIndex;
  final bool signalSufficient;
  final double shoulderTiltAvgDeg;
  final double shoulderTiltExceedRatio;
  final double headDownAvgDeg;
  final double headDownExceedRatio;
  final String gestureActivityLevel;
  final bool torsoSignalSufficient;
  final double torsoLeanAvgDeg;
  final double torsoLeanExceedRatio;
  final String armOpennessLevel;
  final List<String> reasons;

  factory PostureWindow.fromJson(Map<String, dynamic> json) {
    return PostureWindow(
      windowIndex: json['window_index'] as int? ?? 0,
      signalSufficient: json['signal_sufficient'] as bool? ?? false,
      shoulderTiltAvgDeg:
          (json['shoulder_tilt_avg_deg'] as num?)?.toDouble() ?? 0.0,
      shoulderTiltExceedRatio:
          (json['shoulder_tilt_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      headDownAvgDeg:
          (json['head_down_avg_deg'] as num?)?.toDouble() ?? 0.0,
      headDownExceedRatio:
          (json['head_down_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      gestureActivityLevel:
          json['gesture_activity_level'] as String? ?? 'unknown',
      torsoSignalSufficient:
          json['torso_signal_sufficient'] as bool? ?? false,
      torsoLeanAvgDeg:
          (json['torso_lean_avg_deg'] as num?)?.toDouble() ?? 0.0,
      torsoLeanExceedRatio:
          (json['torso_lean_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      armOpennessLevel:
          json['arm_openness_level'] as String? ?? 'unknown',
      reasons:
          (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
```

Add `_armOpennessText` to `frontend/lib/main.dart` right after `_gestureActivityText` (after line 3322):

```dart
String _armOpennessText(
  String level,
) {
  switch (level) {
    case 'closed':
      return '닫힘';

    case 'normal':
      return '보통';

    case 'open':
      return '열림';

    default:
      return '분석 없음';
  }
}
```

In `frontend/lib/main.dart`, in the posture section's `else ...[` branch (starting at line 2758), replace the block from the first `Row(` (line 2759) through the closing `),` of that Row (line 2783) — i.e. the 어깨 기울기/고개 숙임 row — by keeping it as-is and inserting a second Row immediately after it (after line 2783's closing `),`, before the `const SizedBox(height: 12,),` at line 2785):

```dart
              const SizedBox(
                height: 12,
              ),

              Row(
                children: [
                  Expanded(
                    child: _DetailItem(
                      label: '상체 기울기',
                      value: postureWindow!.torsoSignalSufficient
                          ? '평균 ${postureWindow!.torsoLeanAvgDeg.toStringAsFixed(1)}도 '
                              '· 초과 ${(postureWindow!.torsoLeanExceedRatio * 100).toStringAsFixed(0)}%'
                          : '상체 기울기 신호 부족',
                    ),
                  ),

                  const SizedBox(
                    width: 12,
                  ),

                  Expanded(
                    child: _DetailItem(
                      label: '팔 벌어짐',
                      value: _armOpennessText(
                        postureWindow!.armOpennessLevel,
                      ),
                    ),
                  ),
                ],
              ),
```

(The existing `const SizedBox(height: 12,),` immediately before `_DetailItem(label: '제스처 활동성', ...)` at line 2789 stays as-is, now separating this new Row from the gesture item below it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && flutter test test/posture_timeline_test.dart`
Expected: all tests PASS (6 passed)

Also run: `cd frontend && flutter analyze lib/posture_timeline.dart lib/main.dart`
Expected: no new errors (pre-existing lints, if any, are unaffected by this change).

- [ ] **Step 5: Manual smoke test**

Restart both servers per the project's normal dev flow (`uvicorn app.main:app --reload --reload-dir app` from `backend/`, `flutter run -d chrome --web-port 5173` from `frontend/`), record a short webcam test through the app, run analysis, and open the window detail card. Confirm:
- "상체 기울기" and "팔 벌어짐" appear as a second row beneath "어깨 기울기"/"고개 숙임".
- No layout exceptions appear in the `flutter run` console (watch for `CrossAxisAlignment`/`infinite height` errors, per the layout bug fixed earlier this session).

- [ ] **Step 6: Commit**

```bash
cd frontend
git add lib/posture_timeline.dart lib/main.dart test/posture_timeline_test.dart
git commit -m "feat: display torso lean and arm openness in posture detail card"
```

---

## Self-Review Notes

- **Spec coverage:** Task 1 covers spec §1 (extraction); Task 2 covers §3 (torso lean) + the relevant slice of §6 (schema); Task 3 covers §4 (arm openness) + the relevant slice of §6; Task 4 covers §7 (coaching prompt); Task 5 covers §8 (frontend). §5 (per-window aggregation/degradation pattern) is threaded through Tasks 2-3 rather than being a standalone task, since it has no independent deliverable apart from the two signals it gates. §9 (testing) is folded into each task's own test steps rather than a separate task, per the "fold into the task whose deliverable needs it" guidance.
- **Type consistency:** `torso_signal_sufficient`/`torsoSignalSufficient`, `torso_lean_avg_deg`/`torsoLeanAvgDeg`, `torso_lean_exceed_ratio`/`torsoLeanExceedRatio`, `arm_openness_level`/`armOpennessLevel` are spelled identically (snake_case Python key ↔ matching camelCase Dart field) across Tasks 2, 3, and 5 — verified by re-reading each task's return-dict/schema/fromJson snippets side by side.
- **Placeholder scan:** no TBD/TODO markers; every step has literal code, not a description of code.
