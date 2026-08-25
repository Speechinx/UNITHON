# Posture Plain-Language Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework posture analysis so five existing signals gain a 3-tier severity (stable/mild/severe) with plain-Korean-sentence feedback instead of raw degrees/percentages, add three new signals (open posture recompute, gesture power zone, head alignment), add torso-lean direction awareness, and thread all of it through the schema, coaching prompt, and Flutter UI as badges instead of numbers.

**Architecture:** All new geometry and classification logic lives in `PostureAnalyzer` (backend/app/services/posture_analyzer.py), which already owns every other posture signal. The Pydantic schema, coaching prompt, and Flutter display layer are thin pass-throughs updated to carry the new/renamed fields — no new services or files.

**Tech Stack:** Python 3.11 / pytest (backend), Flutter/Dart / `flutter_test` (frontend).

## Global Constraints

- No backward-compatibility shim for `arm_openness_level` → `open_posture_level` — every reference (backend field, schema, Dart model, mapper, tests) is renamed directly, no alias kept.
- Raw numeric fields (`*_avg_deg`, `*_exceed_ratio`, `sway_std`) stay in the schema for `CoachingService` and debugging — only the frontend tile display stops showing them.
- No combined single posture score — every signal stays independently reported.
- Every new threshold constant is an explicitly-labeled untuned placeholder (matches the project's existing convention for `TORSO_LEAN_THRESHOLD_DEG`), needing real-webcam tuning later — do not treat these numbers as final.
- All existing tests in `test_posture_analyzer.py`, `test_posture_timeline.dart`, `test_result_mapper_posture_test.dart` that assert on now-removed fields/strings (`arm_openness_level`, the `'평균 X도 · 초과 Y%'` format) are rewritten in place, not left alongside new ones.

---

## File Structure

**Backend (modify only, no new files):**
- `backend/app/services/posture_frame_extractor.py` — add `z` to extracted landmark dict.
- `backend/app/services/posture_analyzer.py` — all new constants, `_classify` helper, recomputed/new signal methods, updated `analyze_window` aggregation and reason generation.
- `backend/app/schemas/analysis_response.py` — `PostureWindow` field additions/rename.
- `backend/app/services/coaching_service.py` — `[자세]` prompt rule additions.
- `backend/test_posture_frame_extractor.py`, `backend/test_posture_analyzer.py`, `backend/test_coaching_service_posture.py` — updated/new tests.

**Frontend (modify only, no new files):**
- `frontend/lib/posture/posture_timeline.dart` — `PostureWindow` field additions/rename.
- `frontend/lib/utils/result_mapper.dart` — new `*Text()` mapping functions, `buildSegments` changes.
- `frontend/lib/models/app_models.dart` — `Segment` field additions/rename.
- `frontend/lib/screens/analysis_detail.dart` — posture tile grid grows from 5 to 8 tiles, values become badge text.
- `frontend/test/posture_timeline_test.dart`, `frontend/test/result_mapper_posture_test.dart` — updated/new tests.

---

## Task 1: Extract `z` landmark coordinate

**Files:**
- Modify: `backend/app/services/posture_frame_extractor.py:61-68`
- Test: `backend/test_posture_frame_extractor.py`

**Interfaces:**
- Produces: every landmark dict returned by `PostureFrameExtractor.extract()` now has a `"z"` key (float) alongside `"x"`, `"y"`, `"visibility"`. Consumed by Task 5 (torso lean direction) and Task 8 (head alignment).

- [ ] **Step 1: Write the failing test**

Extend `test_extract_maps_landmark_indices_correctly` in `backend/test_posture_frame_extractor.py`:

```python
class _FakeLandmark:
    def __init__(self, x, y, z, visibility):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


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
```

(Replace the existing `_FakeLandmark` class at the top of the file with this 4-arg version — the old 3-arg version has no `z`.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_posture_frame_extractor.py::test_extract_maps_landmark_indices_correctly -v`
Expected: FAIL — `KeyError: 'z'` or dict mismatch (actual dicts lack `z`).

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/posture_frame_extractor.py`, change the `extract` method's return dict:

```python
        return {
            name: {
                "x": landmarks[index].x,
                "y": landmarks[index].y,
                "z": landmarks[index].z,
                "visibility": landmarks[index].visibility,
            }
            for name, index in LANDMARK_INDICES.items()
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_posture_frame_extractor.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_frame_extractor.py test_posture_frame_extractor.py
git commit -m "feat: extract z landmark coordinate for posture depth signals"
```

---

## Task 2: Add `_classify` 3-tier helper

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Produces: `PostureAnalyzer._classify(self, value: float, mild: float, severe: float) -> str`, returning `"stable" | "mild" | "severe"`. Used by every task below that adds a leveled signal.

- [ ] **Step 1: Write the failing test**

Add to `backend/test_posture_analyzer.py`:

```python
def test_classify_stable_below_mild_threshold():
    analyzer = PostureAnalyzer()

    assert analyzer._classify(5.0, mild=8.0, severe=15.0) == "stable"


def test_classify_mild_at_or_above_mild_threshold():
    analyzer = PostureAnalyzer()

    assert analyzer._classify(8.0, mild=8.0, severe=15.0) == "mild"
    assert analyzer._classify(12.0, mild=8.0, severe=15.0) == "mild"


def test_classify_severe_at_or_above_severe_threshold():
    analyzer = PostureAnalyzer()

    assert analyzer._classify(15.0, mild=8.0, severe=15.0) == "severe"
    assert analyzer._classify(20.0, mild=8.0, severe=15.0) == "severe"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k test_classify -v`
Expected: FAIL — `AttributeError: 'PostureAnalyzer' object has no attribute '_classify'`.

- [ ] **Step 3: Write minimal implementation**

Add this method to the `PostureAnalyzer` class in `backend/app/services/posture_analyzer.py` (near the other private helpers, e.g. right after `_has_signal`):

```python
    def _classify(
        self,
        value: float,
        mild: float,
        severe: float,
    ) -> str:

        if value >= severe:
            return "severe"

        if value >= mild:
            return "mild"

        return "stable"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k test_classify -v`
Expected: all 3 PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: add 3-tier stable/mild/severe classification helper"
```

---

## Task 3: Severe tier + plain-language reasons for shoulder tilt, head-down, gaze-away, sway

This renames the four existing single-threshold constants to `*_MILD_DEG`/`*_MILD_STD`, adds matching `*_SEVERE_*` constants, adds a `*_level` field for each, and replaces the four percentage-based reason strings (plus adds a new sway reason, which previously fed no reason at all) with plain Korean sentences.

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: `self._classify` (Task 2).
- Produces: `analyze_window()` result dict gains `shoulder_tilt_level`, `head_down_level`, `gaze_away_level`, `sway_level` (each `"stable"|"mild"|"severe"`). `reasons` entries for these four signals are now plain sentences, not `"... N% 구간"`.

- [ ] **Step 1: Write the failing tests**

Add to `backend/test_posture_analyzer.py`:

```python
def test_analyze_window_shoulder_tilt_level_mild_produces_plain_reason():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.38),
        right_shoulder=(0.6, 0.43),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["shoulder_tilt_level"] == "mild"
    assert "어깨가 약간 기울어진 구간이 있었어요" in result["reasons"]


def test_analyze_window_shoulder_tilt_level_severe_produces_plain_reason():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["shoulder_tilt_level"] == "severe"
    assert "어깨가 한쪽으로 많이 기울어져 있었어요" in result["reasons"]


def test_analyze_window_shoulder_tilt_level_stable_for_level_frames():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["shoulder_tilt_level"] == "stable"
    assert result["reasons"] == []


def test_analyze_window_head_down_level_mild_produces_plain_reason():
    analyzer = PostureAnalyzer()

    hunched_frame = _frame(
        nose=(0.5, 0.42),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    frames = [hunched_frame] * 4 + [_frame(nose=(0.5, 0.1))]

    result = analyzer.analyze_window(frames)

    assert result["head_down_level"] == "mild"
    assert "고개를 자주 숙이고 있었어요" in result["reasons"]


def test_analyze_window_head_down_level_severe_produces_plain_reason():
    analyzer = PostureAnalyzer()

    very_hunched_frame = _frame(
        nose=(0.5, 0.495),
        left_shoulder=(0.4, 0.5),
        right_shoulder=(0.6, 0.5),
    )

    frames = [very_hunched_frame] * 4 + [_frame(nose=(0.5, 0.1))]

    result = analyzer.analyze_window(frames)

    assert result["head_down_level"] == "severe"
    assert "고개를 많이 숙인 채로 발표했어요" in result["reasons"]


def test_analyze_window_gaze_away_level_mild_produces_plain_reason():
    analyzer = PostureAnalyzer()

    turned_frame = _frame(
        nose=(0.545, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    frames = [turned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["gaze_away_level"] == "mild"
    assert "시선이 자주 옆으로 벗어났어요" in result["reasons"]


def test_analyze_window_gaze_away_level_severe_produces_plain_reason():
    analyzer = PostureAnalyzer()

    turned_frame = _frame(
        nose=(0.58, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    frames = [turned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["gaze_away_level"] == "severe"
    assert "시선이 많이 벗어나 있었어요" in result["reasons"]


def test_analyze_window_sway_level_stable_for_level_frames():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(4)]

    result = analyzer.analyze_window(frames)

    assert result["sway_level"] == "stable"
    assert result["reasons"] == []


def test_analyze_window_sway_level_mild_produces_plain_reason():
    analyzer = PostureAnalyzer()

    frames = [
        _frame(left_shoulder=(0.37, 0.4), right_shoulder=(0.57, 0.4)),
        _frame(left_shoulder=(0.43, 0.4), right_shoulder=(0.63, 0.4)),
        _frame(left_shoulder=(0.37, 0.4), right_shoulder=(0.57, 0.4)),
        _frame(left_shoulder=(0.43, 0.4), right_shoulder=(0.63, 0.4)),
    ]

    result = analyzer.analyze_window(frames)

    assert result["sway_level"] == "mild"
    assert "몸이 조금 흔들렸어요" in result["reasons"]


def test_analyze_window_sway_level_severe_produces_plain_reason():
    analyzer = PostureAnalyzer()

    frames = [
        _frame(left_shoulder=(0.32, 0.4), right_shoulder=(0.52, 0.4)),
        _frame(left_shoulder=(0.48, 0.4), right_shoulder=(0.68, 0.4)),
        _frame(left_shoulder=(0.32, 0.4), right_shoulder=(0.52, 0.4)),
        _frame(left_shoulder=(0.48, 0.4), right_shoulder=(0.68, 0.4)),
    ]

    result = analyzer.analyze_window(frames)

    assert result["sway_level"] == "severe"
    assert "몸이 자주 좌우로 흔들렸어요" in result["reasons"]
```

Numeric derivations behind these fixtures (for reviewer sanity-check, not part of the code). **Important:** each `*_level` is classified against the **window average** across all 5 frames in `[X] * 4 + [Y]`, not the single extreme frame's own angle — the trailing 5th frame's value pulls the mean toward it, so a fixture must be sized so the *average*, not the single-frame value, lands in the intended band:
- Shoulder tilt mild: `left=(0.4,0.38)`, `right=(0.6,0.43)` → single-frame `dx=0.2, dy=0.05` → `atan2(0.05,0.2)=14.04°`; averaged with the trailing default frame's `0°` → `(4×14.04+0)/5=11.23°` → `mild` (`8 <= 11.23 < 15`).
- Shoulder tilt severe: `left=(0.4,0.35), right=(0.6,0.55)` → single-frame `45°`; averaged with `0°` → `(4×45+0)/5=36°` → `severe` (`>=15`, wide margin).
- Head down mild: shoulder mid_y=0.5, shoulder_width=`hypot(0.2,0)=0.2`. `nose=(0.5,0.42)` → single-frame `dy=-0.08` → `atan2(0.2,0.08)=68.2°`; the trailing frame here is `_frame(nose=(0.5,0.1))`, whose *shoulders* stay at the plain default `(0.4,0.4)/(0.6,0.4)` (only `nose` is overridden), giving mid_y=0.4 and its own non-zero angle `atan2(0.2,0.3)=33.69°` — averaged: `(4×68.2+33.69)/5=61.3°` → `mild` (`60 <= 61.3 < 75`, narrow ~1.3° margin).
- Head down severe: `nose=(0.5,0.495)` → single-frame `dy=-0.005` → `atan2(0.2,0.005)=88.57°`; averaged with the same `33.69°` trailing-frame value → `(4×88.57+33.69)/5=77.59°` → `severe` (`>=75`).
- Gaze away mild: ears at `0.42`/`0.58` → `ear_half_distance=0.08`. `nose=(0.545,0.2)` → single-frame `dx=0.045` → `atan2(0.045,0.08)=29.36°`; averaged with the trailing default frame's `0°` → `(4×29.36+0)/5=23.49°` → `mild` (`20 <= 23.49 < 35`).
- Gaze away severe: `nose=(0.58,0.2)` → single-frame `dx=0.08` → `atan2(0.08,0.08)=45°`; averaged with `0°` → `(4×45+0)/5=36°` → `severe` (`>=35`, narrow ~1° margin).
- Sway mild: shoulder centers alternate `0.47/0.53` across 4 distinct frames (no diluting 5th frame here — sway's population stdev is computed directly over all frames given) → deviations `±0.03` from mean `0.5` → population stdev `=0.03` → `mild` (`0.02 <= 0.03 < 0.05`).
- Sway severe: shoulder centers alternate `0.42/0.58` → deviations `±0.08` → population stdev `=0.08` → `severe` (`>=0.05`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k "shoulder_tilt_level or head_down_level or gaze_away_level or sway_level" -v`
Expected: FAIL — `KeyError` on the new `*_level` keys (they don't exist yet), and reason strings don't match the old `"...% 구간"` format.

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/posture_analyzer.py`, rename the class constants (near the top of the class):

```python
    SHOULDER_TILT_MILD_DEG = 8.0
    SHOULDER_TILT_SEVERE_DEG = 15.0

    HEAD_DOWN_MILD_DEG = 60.0
    HEAD_DOWN_SEVERE_DEG = 75.0

    TORSO_LEAN_MILD_DEG = 10.0
    TORSO_LEAN_SEVERE_DEG = 20.0

    GAZE_AWAY_MILD_DEG = 20.0
    GAZE_AWAY_SEVERE_DEG = 35.0

    SWAY_MILD_STD = 0.02
    SWAY_SEVERE_STD = 0.05
```

(This replaces `SHOULDER_TILT_THRESHOLD_DEG`, `HEAD_DOWN_THRESHOLD_DEG`, `TORSO_LEAN_THRESHOLD_DEG`, `GAZE_AWAY_THRESHOLD_DEG` entirely — `TORSO_LEAN_MILD_DEG` is added now but only *used* starting Task 4.)

In `analyze_window`, after `shoulder_tilt_exceed_ratio = self._exceed_ratio(shoulder_tilts, self.SHOULDER_TILT_MILD_DEG)` (renamed from `SHOULDER_TILT_THRESHOLD_DEG`), add:

```python
        shoulder_tilt_level = self._classify(
            shoulder_tilt_avg,
            self.SHOULDER_TILT_MILD_DEG,
            self.SHOULDER_TILT_SEVERE_DEG,
        )
```

Same pattern right after `head_down_exceed_ratio = self._exceed_ratio(head_downs, self.HEAD_DOWN_MILD_DEG)`:

```python
        head_down_level = self._classify(
            head_down_avg,
            self.HEAD_DOWN_MILD_DEG,
            self.HEAD_DOWN_SEVERE_DEG,
        )
```

Right after the existing `sway_std = statistics.pstdev(...)` block:

```python
        sway_level = self._classify(
            sway_std,
            self.SWAY_MILD_STD,
            self.SWAY_SEVERE_STD,
        )
```

Inside the `if gaze_signal_sufficient:` branch, right after `gaze_away_exceed_ratio = self._exceed_ratio(gaze_away_degs, self.GAZE_AWAY_MILD_DEG)`:

```python
            gaze_away_level = self._classify(
                gaze_away_avg,
                self.GAZE_AWAY_MILD_DEG,
                self.GAZE_AWAY_SEVERE_DEG,
            )
```

and in its `else:` branch (where `gaze_away_avg = 0.0` etc. are set), add:

```python
            gaze_away_level = "unknown"
```

Replace the four reason-building blocks (the ones starting `if shoulder_tilt_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:` through the gaze one) with:

```python
        if shoulder_tilt_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            if shoulder_tilt_level == "severe":
                reasons.append("어깨가 한쪽으로 많이 기울어져 있었어요")
            elif shoulder_tilt_level == "mild":
                reasons.append("어깨가 약간 기울어진 구간이 있었어요")

        if head_down_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD:
            if head_down_level == "severe":
                reasons.append("고개를 많이 숙인 채로 발표했어요")
            elif head_down_level == "mild":
                reasons.append("고개를 자주 숙이고 있었어요")

        if (
            torso_signal_sufficient
            and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            reasons.append(
                f"상체 기울어짐 {torso_lean_exceed_ratio * 100:.0f}% 구간"
            )

        if (
            gaze_signal_sufficient
            and gaze_away_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            if gaze_away_level == "severe":
                reasons.append("시선이 많이 벗어나 있었어요")
            elif gaze_away_level == "mild":
                reasons.append("시선이 자주 옆으로 벗어났어요")

        if sway_level == "severe":
            reasons.append("몸이 자주 좌우로 흔들렸어요")
        elif sway_level == "mild":
            reasons.append("몸이 조금 흔들렸어요")
```

(The torso block is left with its old string for now — Task 4 replaces it.)

Finally, add the four new fields to the dict returned by `analyze_window` (next to their existing `*_avg_deg`/`*_exceed_ratio`/`sway_std` siblings):

```python
            "shoulder_tilt_level": shoulder_tilt_level,
            "head_down_level": head_down_level,
            "sway_level": sway_level,
            "gaze_away_level": gaze_away_level,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS. If `test_analyze_window_flags_shoulder_tilt_reason_when_exceed_ratio_high` or `test_analyze_window_flags_gaze_away_reason_when_exceed_ratio_high` fail because they assert the old `"어깨" in reason` / `"시선" in reason` substring — those still pass since the new sentences still contain "어깨"/"시선". If any test still asserts the literal old `f"...% 구간"` string, update it to the new plain sentence.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: plain-language severity levels for shoulder/head/gaze/sway signals"
```

---

## Task 4: Severe tier + plain-language reason for torso lean magnitude

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: `self._classify` (Task 2), `TORSO_LEAN_MILD_DEG`/`TORSO_LEAN_SEVERE_DEG` (Task 3).
- Produces: `torso_lean_level` field (`"stable"|"mild"|"severe"|"unknown"`).

- [ ] **Step 1: Write the failing tests**

```python
def test_analyze_window_torso_lean_level_mild_produces_plain_reason():
    analyzer = PostureAnalyzer()

    leaned_frame = _frame(
        left_shoulder=(0.52, 0.3),
        right_shoulder=(0.52, 0.3),
        left_hip=(0.4, 0.7),
        right_hip=(0.4, 0.7),
    )

    frames = [leaned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_level"] == "mild"
    assert "상체가 살짝 기울어져 있었어요" in result["reasons"]


def test_analyze_window_torso_lean_level_severe_produces_plain_reason():
    analyzer = PostureAnalyzer()

    leaned_frame = _frame(
        left_shoulder=(0.55, 0.486),
        right_shoulder=(0.55, 0.486),
        left_hip=(0.4, 0.7),
        right_hip=(0.4, 0.7),
    )

    frames = [leaned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_level"] == "severe"
    assert "상체가 많이 기울어져 있었어요" in result["reasons"]


def test_analyze_window_torso_lean_level_unknown_when_insufficient():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_hip"]["visibility"] = 0.1
    frame["right_hip"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["torso_signal_sufficient"] is False
    assert result["torso_lean_level"] == "unknown"
```

`analyze_window` classifies `torso_lean_level` against the **window average** across all 5 frames (4 fixture frames + 1 trailing default `_frame()`, whose own torso lean is `0°`), not the single fixture frame's raw angle — the average is `0.8×` the single-frame value here. Numeric check for the mild fixture: single-frame `shoulder_center=(0.52,0.3)`, `hip_center=(0.4,0.7)` → `dx=0.12, dy=-0.4` → `atan2(0.12,0.4)=16.70°` → window avg `=0.8×16.70=13.36°`, inside `[MILD=10, SEVERE=20)` → `mild`. Severe fixture: single-frame `shoulder_center=(0.55,0.486)`, `hip_center=(0.4,0.7)` → `dx=0.15, dy=-0.214` → `atan2(0.15,0.214)=35.06°` → window avg `=0.8×35.06=28.05°`, `>=20` → `severe`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k torso_lean_level -v`
Expected: FAIL — `KeyError: 'torso_lean_level'`.

- [ ] **Step 3: Write minimal implementation**

In `analyze_window`, inside the `if torso_signal_sufficient:` branch, right after `torso_lean_exceed_ratio = self._exceed_ratio(...)`:

```python
            torso_lean_level = self._classify(
                torso_lean_avg,
                self.TORSO_LEAN_MILD_DEG,
                self.TORSO_LEAN_SEVERE_DEG,
            )
```

In the matching `else:` branch:

```python
            torso_lean_level = "unknown"
```

Replace the torso reason block (still using the old `f"상체 기울어짐 {ratio}% 구간"` string from Task 3) with:

```python
        if (
            torso_signal_sufficient
            and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            if torso_lean_level == "severe":
                reasons.append("상체가 많이 기울어져 있었어요")
            elif torso_lean_level == "mild":
                reasons.append("상체가 살짝 기울어져 있었어요")
```

Add `"torso_lean_level": torso_lean_level,` to the returned dict, next to `torso_lean_exceed_ratio`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS. Update `test_analyze_window_flags_torso_lean_reason_when_exceed_ratio_high` if it asserts the old `"상체" in reason` substring check — that substring still matches the new sentences, so it should pass unchanged.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: plain-language severity level for torso lean magnitude"
```

---

## Task 5: Torso lean direction (z-based) + forward-lean reason exclusion

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: `z` on landmarks (Task 1).
- Produces: `torso_lean_direction` field (`"forward"|"backward"|"neutral"|"unknown"`); torso-lean reason (Task 4) no longer fires when direction is `"forward"`.

- [ ] **Step 1: Write the failing tests**

First, extend the shared `_frame()` test helper (top of `backend/test_posture_analyzer.py`) so every landmark carries a `z` value defaulting to `0.0`:

```python
def _landmark(x, y, z=0.0, visibility=1.0):
    return {"x": x, "y": y, "z": z, "visibility": visibility}


def _frame(
    nose=(0.5, 0.2),
    left_ear=(0.42, 0.2),
    right_ear=(0.58, 0.2),
    left_shoulder=(0.4, 0.4),
    right_shoulder=(0.6, 0.4),
    left_wrist=(0.35, 0.6),
    right_wrist=(0.65, 0.6),
    left_hip=(0.45, 0.75),
    right_hip=(0.55, 0.75),
    left_elbow=(0.38, 0.55),
    right_elbow=(0.62, 0.55),
    z=None,
    visibility=1.0,
):
    z = z or {}

    def landmark(name, xy):
        return _landmark(*xy, z=z.get(name, 0.0), visibility=visibility)

    return {
        "nose": landmark("nose", nose),
        "left_ear": landmark("left_ear", left_ear),
        "right_ear": landmark("right_ear", right_ear),
        "left_shoulder": landmark("left_shoulder", left_shoulder),
        "right_shoulder": landmark("right_shoulder", right_shoulder),
        "left_wrist": landmark("left_wrist", left_wrist),
        "right_wrist": landmark("right_wrist", right_wrist),
        "left_hip": landmark("left_hip", left_hip),
        "right_hip": landmark("right_hip", right_hip),
        "left_elbow": landmark("left_elbow", left_elbow),
        "right_elbow": landmark("right_elbow", right_elbow),
    }
```

(This changes `_frame()`'s signature — it gains an optional `z` dict keyed by landmark name, e.g. `_frame(z={"left_shoulder": -0.1, "right_shoulder": -0.1})`. Every existing call site keeps working unchanged since `z` defaults to `{}` → all landmarks default to `z=0.0`.)

Then add:

```python
def test_torso_lean_direction_forward_when_shoulders_closer_than_hips():
    analyzer = PostureAnalyzer()

    frame = _frame(
        z={
            "left_shoulder": -0.1,
            "right_shoulder": -0.1,
            "left_hip": 0.0,
            "right_hip": 0.0,
        }
    )

    assert analyzer._torso_lean_direction(frame) == "forward"


def test_torso_lean_direction_backward_when_shoulders_farther_than_hips():
    analyzer = PostureAnalyzer()

    frame = _frame(
        z={
            "left_shoulder": 0.1,
            "right_shoulder": 0.1,
            "left_hip": 0.0,
            "right_hip": 0.0,
        }
    )

    assert analyzer._torso_lean_direction(frame) == "backward"


def test_torso_lean_direction_neutral_when_within_threshold():
    analyzer = PostureAnalyzer()

    frame = _frame(
        z={
            "left_shoulder": 0.01,
            "right_shoulder": 0.01,
            "left_hip": 0.0,
            "right_hip": 0.0,
        }
    )

    assert analyzer._torso_lean_direction(frame) == "neutral"


def test_analyze_window_torso_lean_direction_unknown_when_insufficient():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_hip"]["visibility"] = 0.1
    frame["right_hip"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_direction"] == "unknown"


def test_analyze_window_forward_lean_does_not_produce_torso_reason():
    analyzer = PostureAnalyzer()

    leaned_forward_frame = _frame(
        left_shoulder=(0.55, 0.486),
        right_shoulder=(0.55, 0.486),
        left_hip=(0.4, 0.7),
        right_hip=(0.4, 0.7),
        z={
            "left_shoulder": -0.1,
            "right_shoulder": -0.1,
            "left_hip": 0.0,
            "right_hip": 0.0,
        },
    )

    frames = [leaned_forward_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_level"] == "severe"
    assert result["torso_lean_direction"] == "forward"
    assert not any("상체" in reason for reason in result["reasons"])


def test_analyze_window_backward_lean_still_produces_torso_reason():
    analyzer = PostureAnalyzer()

    leaned_backward_frame = _frame(
        left_shoulder=(0.55, 0.486),
        right_shoulder=(0.55, 0.486),
        left_hip=(0.4, 0.7),
        right_hip=(0.4, 0.7),
        z={
            "left_shoulder": 0.1,
            "right_shoulder": 0.1,
            "left_hip": 0.0,
            "right_hip": 0.0,
        },
    )

    frames = [leaned_backward_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["torso_lean_direction"] == "backward"
    assert "상체가 많이 기울어져 있었어요" in result["reasons"]
```

Numeric check: `torso_lean_level` is classified against the **window average** across all 5 frames (4 fixture frames + 1 trailing default `_frame()`, whose own torso lean is `0°`), so the average is `0.8×` the single-frame value. Both fixtures use `shoulder_center=(0.55,0.486)`, `hip_center=(0.4,0.7)` → `dx=0.15, dy=-0.214` → single-frame `atan2(0.15,0.214)=35.06°` → window avg `=0.8×35.06=28.05°`, `>=TORSO_LEAN_SEVERE_DEG(20)` → `severe` (this is the same magnitude fixture as Task 4's severe test — only `z` differs here to add direction).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: FAIL — `AttributeError: '_torso_lean_direction'` for the direct unit tests, `KeyError: 'torso_lean_direction'` for the `analyze_window` tests. (Also confirm the `_frame()` signature change alone doesn't break any pre-existing test — run the full suite, not just the new tests, at this step.)

- [ ] **Step 3: Write minimal implementation**

Add the constant near the other torso constants:

```python
    TORSO_LEAN_DIRECTION_Z_THRESHOLD = 0.05
```

Add these methods near `_torso_lean_deg`:

```python
    def _shoulder_center_z(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_shoulder"]
        right = frame["right_shoulder"]

        return (left["z"] + right["z"]) / 2

    def _hip_center_z(
        self,
        frame: dict,
    ) -> float:

        left = frame["left_hip"]
        right = frame["right_hip"]

        return (left["z"] + right["z"]) / 2

    def _torso_lean_direction(
        self,
        frame: dict,
    ) -> str:

        dz = (
            self._shoulder_center_z(frame)
            - self._hip_center_z(frame)
        )

        if dz <= -self.TORSO_LEAN_DIRECTION_Z_THRESHOLD:
            return "forward"

        if dz >= self.TORSO_LEAN_DIRECTION_Z_THRESHOLD:
            return "backward"

        return "neutral"
```

In `analyze_window`, inside `if torso_signal_sufficient:`, after computing `torso_lean_level`, add majority-vote direction with the `neutral > backward > forward` tie-break:

```python
            torso_directions = [
                self._torso_lean_direction(frame)
                for frame in torso_frames
            ]

            direction_counts = {
                "neutral": torso_directions.count("neutral"),
                "backward": torso_directions.count("backward"),
                "forward": torso_directions.count("forward"),
            }

            torso_lean_direction = max(
                direction_counts,
                key=lambda direction: direction_counts[direction],
            )
```

(Python's `max` returns the first key with the maximum value when iterating a dict in insertion order, so listing `"neutral"` first, then `"backward"`, then `"forward"` in `direction_counts` gives exactly the `neutral > backward > forward` tie-break the design calls for.)

In the matching `else:` branch:

```python
            torso_lean_direction = "unknown"
```

Update the torso reason condition (from Task 4) to exclude forward lean:

```python
        if (
            torso_signal_sufficient
            and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
            and torso_lean_direction != "forward"
        ):
            if torso_lean_level == "severe":
                reasons.append("상체가 많이 기울어져 있었어요")
            elif torso_lean_level == "mild":
                reasons.append("상체가 살짝 기울어져 있었어요")
```

Add `"torso_lean_direction": torso_lean_direction,` to the returned dict.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: detect torso lean direction from z depth, exclude forward lean from reasons"
```

---

## Task 6: Recompute open posture from spine vector, rename to `open_posture_level`

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Produces: `open_posture_level` field (`"closed"|"normal"|"open"|"unknown"`), replacing `arm_openness_level` entirely. `low_engagement` now reads `open_posture_level == "closed"`.

- [ ] **Step 1: Write the failing tests**

Remove these existing tests (they test the retired ratio-only method): `test_arm_openness_ratio_greater_than_one_when_elbows_wider_than_shoulders`, `test_arm_openness_level_closed_when_ratio_low`, `test_arm_openness_level_open_when_ratio_high`, `test_arm_openness_level_normal_at_middle_ratio`, `test_arm_openness_level_normal_at_low_boundary`, `test_arm_openness_level_normal_at_high_boundary`, `test_analyze_window_all_level_frames_has_normal_arm_openness`, `test_analyze_window_arm_openness_unknown_when_elbows_low_visibility`, `test_analyze_window_avatar_state_engaged_when_arm_openness_unknown`.

Replace them with:

```python
def test_open_posture_distance_is_zero_for_point_on_spine_line():
    analyzer = PostureAnalyzer()

    point = {"x": 0.5, "y": 0.55, "z": 0.0, "visibility": 1.0}

    assert analyzer._open_posture_distance(
        point,
        shoulder_center=(0.5, 0.4),
        hip_center=(0.5, 0.75),
        shoulder_width=0.2,
    ) == 0.0


def test_open_posture_distance_normalizes_by_shoulder_width():
    analyzer = PostureAnalyzer()

    point = {"x": 0.6, "y": 0.55, "z": 0.0, "visibility": 1.0}

    distance = analyzer._open_posture_distance(
        point,
        shoulder_center=(0.5, 0.4),
        hip_center=(0.5, 0.75),
        shoulder_width=0.2,
    )

    assert math.isclose(distance, 0.5, abs_tol=0.01)


def test_analyze_window_default_frames_have_normal_open_posture():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["open_posture_level"] == "normal"


def test_analyze_window_open_posture_closed_when_limbs_near_spine():
    analyzer = PostureAnalyzer()

    closed_frame = _frame(
        left_elbow=(0.47, 0.55),
        right_elbow=(0.53, 0.55),
        left_wrist=(0.48, 0.6),
        right_wrist=(0.52, 0.6),
    )

    frames = [closed_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["open_posture_level"] == "closed"


def test_analyze_window_open_posture_open_when_limbs_far_from_spine():
    analyzer = PostureAnalyzer()

    open_frame = _frame(
        left_elbow=(0.1, 0.55),
        right_elbow=(0.9, 0.55),
        left_wrist=(0.05, 0.6),
        right_wrist=(0.95, 0.6),
    )

    frames = [open_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["open_posture_level"] == "open"


def test_analyze_window_open_posture_unknown_when_hips_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_hip"]["visibility"] = 0.1
    frame["right_hip"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["open_posture_level"] == "unknown"


def test_analyze_window_open_posture_unknown_when_elbows_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_elbow"]["visibility"] = 0.1
    frame["right_elbow"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["open_posture_level"] == "unknown"


def test_analyze_window_avatar_state_focused_when_no_reasons_and_low_engagement():
    analyzer = PostureAnalyzer()

    closed_posture_frame = _frame(
        left_elbow=(0.47, 0.55),
        right_elbow=(0.53, 0.55),
        left_wrist=(0.48, 0.6),
        right_wrist=(0.52, 0.6),
    )

    frames = [closed_posture_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] == []
    assert result["gesture_activity_level"] == "low"
    assert result["open_posture_level"] == "closed"
    assert result["avatar_state"] == "focused"


def test_analyze_window_avatar_state_bored_when_reasons_present_and_low_engagement():
    analyzer = PostureAnalyzer()

    tilted_closed_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
        left_elbow=(0.47, 0.55),
        right_elbow=(0.53, 0.55),
        left_wrist=(0.48, 0.6),
        right_wrist=(0.52, 0.6),
    )

    # All 5 frames identical (not "4 + 1 default" like the other severity
    # tests) — the wrists must not move between frames here, or
    # gesture_activity_level would compute as "high" instead of "low".
    frames = [tilted_closed_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] != []
    assert result["gesture_activity_level"] == "low"
    assert result["open_posture_level"] == "closed"
    assert result["avatar_state"] == "bored"
```

Numeric check: default frame → `shoulder_center=(0.5,0.4)`, `hip_center=(0.5,0.75)`, `shoulder_width=0.2`. Elbow offsets `|0.38-0.5|=0.12` (×2), wrist offsets `|0.35-0.5|=0.15` (×2) → mean raw distance `=(0.12+0.12+0.15+0.15)/4=0.135` → normalized `0.135/0.2=0.675` → between `0.4` and `1.0` → `normal`. ✓
Closed fixture: elbow offsets `0.03`(×2), wrist offsets `0.02`(×2) → mean `0.025` → normalized `0.125` → `< 0.4` → `closed`. ✓
Open fixture: elbow offsets `0.4`(×2), wrist offsets `0.45`(×2) → mean `0.425` → normalized `2.125` → `> 1.0` → `open`. ✓

Also update the two existing `test_analyze_window_avatar_state_engaged_when_no_reasons_and_default_engagement` / `test_analyze_window_avatar_state_confused_when_reasons_present_and_default_engagement` tests: replace their `assert result["arm_openness_level"] == "normal"` lines with `assert result["open_posture_level"] == "normal"`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: FAIL — `AttributeError: '_open_posture_distance'`, `KeyError: 'open_posture_level'`.

- [ ] **Step 3: Write minimal implementation**

Add near the top of the class, replacing `ARM_OPENNESS_LOW_THRESHOLD`/`ARM_OPENNESS_HIGH_THRESHOLD`:

```python
    OPEN_POSTURE_CLOSED_MAX = 0.4
    OPEN_POSTURE_OPEN_MIN = 1.0
```

Add near `_arm_openness_ratio` (which this replaces — delete `_arm_openness_ratio` and `_arm_openness_level` entirely):

```python
    def _open_posture_distance(
        self,
        point: dict,
        shoulder_center: tuple[float, float],
        hip_center: tuple[float, float],
        shoulder_width: float,
    ) -> float:

        ax, ay = hip_center
        bx, by = shoulder_center
        px, py = point["x"], point["y"]

        line_length = math.hypot(bx - ax, by - ay)

        if line_length == 0 or shoulder_width == 0:
            return 0.0

        cross = abs(
            (bx - ax) * (py - ay)
            - (by - ay) * (px - ax)
        )

        return (cross / line_length) / shoulder_width

    def _open_posture_score(
        self,
        frame: dict,
    ) -> float:

        shoulder_center = self._shoulder_center(frame)
        hip_center = self._hip_center(frame)

        shoulder_width = self._distance(
            frame["left_shoulder"],
            frame["right_shoulder"],
        )

        points = [
            frame["left_elbow"],
            frame["right_elbow"],
            frame["left_wrist"],
            frame["right_wrist"],
        ]

        distances = [
            self._open_posture_distance(
                point,
                shoulder_center,
                hip_center,
                shoulder_width,
            )
            for point in points
        ]

        return statistics.mean(distances)

    def _open_posture_level(
        self,
        scores: list[float],
    ) -> str:

        avg_score = statistics.mean(scores)

        if avg_score < self.OPEN_POSTURE_CLOSED_MAX:
            return "closed"

        if avg_score > self.OPEN_POSTURE_OPEN_MIN:
            return "open"

        return "normal"
```

In `analyze_window`, replace the `arm_frames`/`arm_ratio` block (which currently only checks `ARM_LANDMARKS`) so it also requires `TORSO_LANDMARKS` and `GESTURE_LANDMARKS`:

```python
        open_posture_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.ARM_LANDMARKS)
            and self._has_signal(frame, self.GESTURE_LANDMARKS)
            and self._has_signal(frame, self.TORSO_LANDMARKS)
        ]

        open_posture_ratio = (
            len(open_posture_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        if open_posture_ratio >= self.MIN_VALID_FRAME_RATIO:
            open_posture_level = self._open_posture_level(
                [
                    self._open_posture_score(frame)
                    for frame in open_posture_frames
                ]
            )
        else:
            open_posture_level = "unknown"
```

(This replaces the old `arm_frames`/`arm_ratio`/`arm_openness` block entirely.)

Update `low_engagement`:

```python
        low_engagement = (
            gesture_activity == "low"
            and open_posture_level == "closed"
        )
```

Replace `"arm_openness_level": arm_openness,` in the returned dict with `"open_posture_level": open_posture_level,`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: recompute open posture from spine-vector distance, rename from arm openness"
```

---

## Task 7: Gesture power zone (new signal)

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Produces: `power_zone_level` field (`"low"|"normal"|"high"|"unknown"`). No reason generated (matches `gesture_activity_level`'s non-judgmental framing).

- [ ] **Step 1: Write the failing tests**

```python
def test_in_power_zone_true_when_wrist_between_shoulder_and_hip_y():
    analyzer = PostureAnalyzer()

    wrist = {"x": 0.5, "y": 0.55, "z": 0.0, "visibility": 1.0}

    assert analyzer._in_power_zone(
        wrist,
        shoulder_center_y=0.4,
        hip_center_y=0.75,
    ) is True


def test_in_power_zone_false_when_wrist_above_shoulder():
    analyzer = PostureAnalyzer()

    wrist = {"x": 0.5, "y": 0.2, "z": 0.0, "visibility": 1.0}

    assert analyzer._in_power_zone(
        wrist,
        shoulder_center_y=0.4,
        hip_center_y=0.75,
    ) is False


def test_in_power_zone_false_when_wrist_below_hip():
    analyzer = PostureAnalyzer()

    wrist = {"x": 0.5, "y": 0.9, "z": 0.0, "visibility": 1.0}

    assert analyzer._in_power_zone(
        wrist,
        shoulder_center_y=0.4,
        hip_center_y=0.75,
    ) is False


def test_analyze_window_default_frames_have_high_power_zone():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["power_zone_level"] == "high"


def test_analyze_window_power_zone_low_when_wrists_above_shoulders():
    analyzer = PostureAnalyzer()

    raised_frame = _frame(
        left_wrist=(0.35, 0.1),
        right_wrist=(0.65, 0.1),
    )

    frames = [raised_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["power_zone_level"] == "low"


def test_analyze_window_power_zone_unknown_when_hips_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_hip"]["visibility"] = 0.1
    frame["right_hip"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["power_zone_level"] == "unknown"
```

Numeric check: default frame — `shoulder_center_y=0.4`, `hip_center_y=0.75`, wrists at `y=0.6` → `0.4<=0.6<=0.75` → in zone for both hands → `power_zone_ratio=1.0` → `>0.6` → `high`. Raised fixture: wrists at `y=0.1` → below shoulder band → not in zone for either hand → ratio `0.0` → `<0.3` → `low`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k power_zone -v`
Expected: FAIL — `AttributeError: '_in_power_zone'`, `KeyError: 'power_zone_level'`.

- [ ] **Step 3: Write minimal implementation**

Add the constants:

```python
    POWER_ZONE_LOW_MAX = 0.3
    POWER_ZONE_HIGH_MIN = 0.6
```

Add near `_wrist_positions`:

```python
    def _in_power_zone(
        self,
        wrist: dict,
        shoulder_center_y: float,
        hip_center_y: float,
    ) -> bool:

        return shoulder_center_y <= wrist["y"] <= hip_center_y

    def _power_zone_level(
        self,
        ratio: float,
    ) -> str:

        if ratio < self.POWER_ZONE_LOW_MAX:
            return "low"

        if ratio > self.POWER_ZONE_HIGH_MIN:
            return "high"

        return "normal"
```

In `analyze_window`, reusing `gesture_frames`/`torso_frames` already computed for the existing signals, add a power-zone-eligible frame set and ratio:

```python
        power_zone_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.GESTURE_LANDMARKS)
            and self._has_signal(frame, self.TORSO_LANDMARKS)
        ]

        power_zone_eligible_ratio = (
            len(power_zone_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        if power_zone_eligible_ratio >= self.MIN_VALID_FRAME_RATIO:
            in_zone_count = 0

            for frame in power_zone_frames:
                shoulder_center_y = self._shoulder_center(frame)[1]
                hip_center_y = self._hip_center(frame)[1]

                if (
                    self._in_power_zone(frame["left_wrist"], shoulder_center_y, hip_center_y)
                    or self._in_power_zone(frame["right_wrist"], shoulder_center_y, hip_center_y)
                ):
                    in_zone_count += 1

            power_zone_ratio = in_zone_count / len(power_zone_frames)
            power_zone_level = self._power_zone_level(power_zone_ratio)
        else:
            power_zone_level = "unknown"
```

Add `"power_zone_level": power_zone_level,` to the returned dict.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: add gesture power-zone signal"
```

---

## Task 8: Head alignment / forward-head offset (new signal)

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: `z` on ear/shoulder landmarks (Task 1), `self._classify` (Task 2), `self._shoulder_center_z` (Task 5).
- Produces: `head_alignment_level` field (`"stable"|"mild"|"severe"|"unknown"`); reuses `gaze_signal_sufficient` (ear-visibility gate).

- [ ] **Step 1: Write the failing tests**

```python
def test_forward_head_z_offset_zero_when_ears_level_with_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(z={"left_ear": 0.0, "right_ear": 0.0, "left_shoulder": 0.0, "right_shoulder": 0.0})

    assert analyzer._forward_head_z_offset(frame) == 0.0


def test_forward_head_z_offset_positive_when_ears_closer_than_shoulders():
    analyzer = PostureAnalyzer()

    frame = _frame(z={"left_ear": -0.08, "right_ear": -0.08, "left_shoulder": 0.0, "right_shoulder": 0.0})

    assert math.isclose(analyzer._forward_head_z_offset(frame), 0.08, abs_tol=1e-9)


def test_analyze_window_head_alignment_stable_for_level_frames():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["head_alignment_level"] == "stable"


def test_analyze_window_head_alignment_mild_produces_plain_reason():
    analyzer = PostureAnalyzer()

    forward_head_frame = _frame(
        z={
            "left_ear": -0.06,
            "right_ear": -0.06,
            "left_shoulder": 0.0,
            "right_shoulder": 0.0,
        }
    )

    frames = [forward_head_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["head_alignment_level"] == "mild"
    assert "고개가 어깨보다 살짝 앞으로 나와 있었어요" in result["reasons"]


def test_analyze_window_head_alignment_severe_produces_plain_reason():
    analyzer = PostureAnalyzer()

    forward_head_frame = _frame(
        z={
            "left_ear": -0.12,
            "right_ear": -0.12,
            "left_shoulder": 0.0,
            "right_shoulder": 0.0,
        }
    )

    frames = [forward_head_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["head_alignment_level"] == "severe"
    assert "고개가 어깨보다 많이 앞으로 나와 있었어요" in result["reasons"]


def test_analyze_window_head_alignment_unknown_when_ears_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_ear"]["visibility"] = 0.1
    frame["right_ear"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["gaze_signal_sufficient"] is False
    assert result["head_alignment_level"] == "unknown"
```

`head_alignment_level` is classified against the **window average** across all 5 frames (4 fixture frames + 1 trailing default `_frame()`, whose own offset is `0.0`), so the average is `0.8×` the single-frame offset. Numeric check: mild fixture single-frame `offset=0.06` → window avg `=0.8×0.06=0.048`, inside `[HEAD_ALIGNMENT_MILD_Z=0.03, SEVERE=0.07)` → `mild`. Severe fixture single-frame `offset=0.12` → window avg `=0.8×0.12=0.096`, `>=0.07` → `severe`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k "forward_head or head_alignment" -v`
Expected: FAIL — `AttributeError: '_forward_head_z_offset'`, `KeyError: 'head_alignment_level'`.

- [ ] **Step 3: Write minimal implementation**

Add the constants:

```python
    HEAD_ALIGNMENT_MILD_Z = 0.03
    HEAD_ALIGNMENT_SEVERE_Z = 0.07
```

Add near `_gaze_away_deg`:

```python
    def _forward_head_z_offset(
        self,
        frame: dict,
    ) -> float:

        ear_center_z = (
            frame["left_ear"]["z"] + frame["right_ear"]["z"]
        ) / 2

        shoulder_center_z = self._shoulder_center_z(frame)

        return shoulder_center_z - ear_center_z
```

In `analyze_window`, inside the existing `if gaze_signal_sufficient:` branch (which already gathers `gaze_frames`), add:

```python
            head_alignment_offsets = [
                self._forward_head_z_offset(frame)
                for frame in gaze_frames
            ]

            head_alignment_avg = statistics.mean(head_alignment_offsets)
            head_alignment_exceed_ratio = self._exceed_ratio(
                head_alignment_offsets,
                self.HEAD_ALIGNMENT_MILD_Z,
            )
            head_alignment_level = self._classify(
                head_alignment_avg,
                self.HEAD_ALIGNMENT_MILD_Z,
                self.HEAD_ALIGNMENT_SEVERE_Z,
            )
```

In the matching `else:` branch:

```python
            head_alignment_avg = 0.0
            head_alignment_exceed_ratio = 0.0
            head_alignment_level = "unknown"
```

Add a reason block alongside the other gaze-gated one:

```python
        if (
            gaze_signal_sufficient
            and head_alignment_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            if head_alignment_level == "severe":
                reasons.append("고개가 어깨보다 많이 앞으로 나와 있었어요")
            elif head_alignment_level == "mild":
                reasons.append("고개가 어깨보다 살짝 앞으로 나와 있었어요")
```

Add `"head_alignment_level": head_alignment_level,` to the returned dict.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/posture_analyzer.py test_posture_analyzer.py
git commit -m "feat: add head alignment / forward-head posture signal"
```

---

## Task 9: `PostureWindow` schema update

**Files:**
- Modify: `backend/app/schemas/analysis_response.py`
- Test: `backend/test_posture_analyzer.py` (existing schema-compatibility test)

**Interfaces:**
- Consumes: every field name introduced in Tasks 3–8.
- Produces: `PostureWindow` accepts and validates all new/renamed fields.

- [ ] **Step 1: Write the failing test**

Update `test_analyze_window_result_is_compatible_with_posture_window_schema` in `backend/test_posture_analyzer.py`:

```python
def test_analyze_window_result_is_compatible_with_posture_window_schema():
    from app.schemas.analysis_response import PostureWindow

    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)
    result["window_index"] = 0

    window = PostureWindow(**result)

    assert window.torso_signal_sufficient is True
    assert window.gaze_signal_sufficient is True
    assert window.avatar_state == "engaged"
    assert window.shoulder_tilt_level == "stable"
    assert window.head_down_level == "stable"
    assert window.sway_level == "stable"
    assert window.gaze_away_level == "stable"
    assert window.torso_lean_level == "stable"
    assert window.torso_lean_direction == "neutral"
    assert window.open_posture_level == "normal"
    assert window.power_zone_level == "high"
    assert window.head_alignment_level == "stable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_posture_analyzer.py -k schema -v`
Expected: FAIL — `pydantic.ValidationError` or `AttributeError` for the new fields (unset on `PostureWindow`).

- [ ] **Step 3: Write minimal implementation**

Replace the `PostureWindow` class body in `backend/app/schemas/analysis_response.py`:

```python
class PostureWindow(
    BaseModel
):
    window_index: int

    signal_sufficient: bool
    valid_frame_ratio: float

    shoulder_tilt_avg_deg: float = 0.0
    shoulder_tilt_exceed_ratio: float = 0.0
    shoulder_tilt_level: str = "unknown"

    head_down_avg_deg: float = 0.0
    head_down_exceed_ratio: float = 0.0
    head_down_level: str = "unknown"

    sway_std: float = 0.0
    sway_level: str = "unknown"

    gesture_activity_level: str = "unknown"

    torso_signal_sufficient: bool = False
    torso_lean_avg_deg: float = 0.0
    torso_lean_exceed_ratio: float = 0.0
    torso_lean_level: str = "unknown"
    torso_lean_direction: str = "unknown"

    open_posture_level: str = "unknown"

    power_zone_level: str = "unknown"

    gaze_signal_sufficient: bool = False
    gaze_away_avg_deg: float = 0.0
    gaze_away_exceed_ratio: float = 0.0
    gaze_away_level: str = "unknown"

    head_alignment_level: str = "unknown"

    reasons: List[
        str
    ] = []

    avatar_state: str = "unknown"
```

(`arm_openness_level` is not present — removed, not deprecated.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_posture_analyzer.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/schemas/analysis_response.py test_posture_analyzer.py
git commit -m "feat: extend PostureWindow schema with plain-language level fields"
```

---

## Task 10: Coaching prompt rules + existing test rename

**Files:**
- Modify: `backend/app/services/coaching_service.py:458-487`
- Test: `backend/test_coaching_service_posture.py`

**Interfaces:**
- Consumes: none (prompt text only).
- Produces: `[자세]` rule block covers the forward-lean exception and the two new non-judgmental signals.

- [ ] **Step 1: Write the failing test**

Update `test_build_prompt_includes_posture_rules_section` in `backend/test_coaching_service_posture.py`:

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
    assert "open_posture_level" in prompt
    assert "power_zone_level" in prompt
    assert "head_alignment_level" in prompt
    assert "앞으로 기울어진" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest test_coaching_service_posture.py -v`
Expected: FAIL — the old prompt still says `arm_openness_level`, has no `power_zone_level`/`head_alignment_level`/forward-lean mention.

- [ ] **Step 3: Write minimal implementation**

Replace the `[자세]` block (`backend/app/services/coaching_service.py:458-487`) with:

```
[자세]

28-1. posture_signals는 카메라 프레임에서 측정한 신체 자세 신호
    (어깨 기울기, 고개 숙임, 좌우 흔들림, 손 제스처 활동성, 상체 기울기, 자세 개방성,
    제스처 파워존, 머리 정렬, 시선(고개 회전) 이탈)일 뿐이다.

28-2. posture_signals의 신호로 발표자의 자신감, 긴장 정도,
    실제 심리 상태를 단정하지 마라.

28-3. 각 구간의 signal_sufficient가 false라면
    해당 구간의 자세는 언급하지 마라.

28-4. shoulder_tilt_level이나 head_down_level이 stable이면
    굳이 자세를 언급하지 않아도 된다.

28-5. reasons에 기록된 문장을 근거로만
    자세 피드백을 작성하라.

28-6. gesture_activity_level은 좋고 나쁨을 판단하는 지표가 아니라
    활동성 수준(낮음/보통/높음)일 뿐이다.
    "low"라고 해서 무조건 개선이 필요하다고 말하지 마라.

28-7. torso_lean_level이 stable이거나 torso_signal_sufficient가 false이면
    상체 기울기를 언급하지 않아도 된다.

28-8. 상체가 앞으로 기울어진 구간은 문제로 언급하지 마라 —
    청중 쪽으로 몸을 기울이는 것은 카메라 신호상 정상적인 참여 신호다.

28-9. open_posture_level과 power_zone_level은 좋고 나쁨을 판단하는 지표가 아니라
    팔이 벌어진 정도와 손이 몸통 앞 영역에 머문 비율을 서술할 뿐이다.
    "closed"나 "low"라고 해서 무조건 소극적이라고 말하지 마라.

28-10. gaze_away_level이 stable이거나 gaze_signal_sufficient가 false이면
    시선 이탈을 언급하지 않아도 된다.

28-11. head_alignment_level은 귀와 어깨의 상대 위치를 측정한
    기하학적 사실일 뿐이며, 피로도나 집중력 저하를 단정하지 마라.
```

(Keep the surrounding `[잘한 점]` section and its numbering — only the `[자세]` block's content changes; its rules are renumbered `28-1`–`28-11` as shown, replacing the old `28-1`–`28-9`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest test_coaching_service_posture.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/coaching_service.py test_coaching_service_posture.py
git commit -m "feat: update coaching prompt for renamed/new posture signals"
```

---

## Task 11: Frontend — `posture_timeline.dart` field updates

**Files:**
- Modify: `frontend/lib/posture/posture_timeline.dart`
- Test: `frontend/test/posture_timeline_test.dart`

**Interfaces:**
- Produces: `PostureWindow` (Dart) gains `shoulderTiltLevel`, `headDownLevel`, `swayLevel`, `gazeAwayLevel`, `torsoLeanLevel`, `torsoLeanDirection`, `powerZoneLevel`, `headAlignmentLevel`; `armOpennessLevel` is renamed to `openPostureLevel`.

- [ ] **Step 1: Write the failing tests**

Update `frontend/test/posture_timeline_test.dart` — replace the `arm_openness_level`-based test and add coverage for the new fields:

```dart
  test('fromJson parses torso lean and open posture fields', () {
    final window = PostureWindow.fromJson({
      'window_index': 1,
      'signal_sufficient': true,
      'torso_signal_sufficient': true,
      'torso_lean_avg_deg': 12.0,
      'torso_lean_exceed_ratio': 0.4,
      'torso_lean_level': 'mild',
      'torso_lean_direction': 'forward',
      'open_posture_level': 'open',
    });

    expect(window.torsoSignalSufficient, true);
    expect(window.torsoLeanAvgDeg, 12.0);
    expect(window.torsoLeanExceedRatio, 0.4);
    expect(window.torsoLeanLevel, 'mild');
    expect(window.torsoLeanDirection, 'forward');
    expect(window.openPostureLevel, 'open');
  });

  test(
    'fromJson defaults torso fields to insufficient and open posture to unknown',
    () {
      final window = PostureWindow.fromJson({
        'window_index': 0,
        'signal_sufficient': false,
      });

      expect(window.torsoSignalSufficient, false);
      expect(window.torsoLeanAvgDeg, 0.0);
      expect(window.torsoLeanExceedRatio, 0.0);
      expect(window.torsoLeanLevel, 'unknown');
      expect(window.torsoLeanDirection, 'unknown');
      expect(window.openPostureLevel, 'unknown');
    },
  );

  test('fromJson parses shoulder/head/gaze/sway levels', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': true,
      'shoulder_tilt_level': 'mild',
      'head_down_level': 'stable',
      'sway_level': 'severe',
      'gaze_away_level': 'mild',
    });

    expect(window.shoulderTiltLevel, 'mild');
    expect(window.headDownLevel, 'stable');
    expect(window.swayLevel, 'severe');
    expect(window.gazeAwayLevel, 'mild');
  });

  test('fromJson defaults new level fields to unknown', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': false,
    });

    expect(window.shoulderTiltLevel, 'unknown');
    expect(window.headDownLevel, 'unknown');
    expect(window.swayLevel, 'unknown');
    expect(window.gazeAwayLevel, 'unknown');
    expect(window.powerZoneLevel, 'unknown');
    expect(window.headAlignmentLevel, 'unknown');
  });

  test('fromJson parses power zone and head alignment levels', () {
    final window = PostureWindow.fromJson({
      'window_index': 0,
      'signal_sufficient': true,
      'power_zone_level': 'high',
      'head_alignment_level': 'severe',
    });

    expect(window.powerZoneLevel, 'high');
    expect(window.headAlignmentLevel, 'severe');
  });
```

Remove the old test `'fromJson parses torso lean and arm openness fields'` and its insufficient-case counterpart (superseded by the two rewritten tests above).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && flutter test test/posture_timeline_test.dart`
Expected: FAIL — `NoSuchMethodError` / undefined getters for the new/renamed fields.

- [ ] **Step 3: Write minimal implementation**

Replace `frontend/lib/posture/posture_timeline.dart` entirely with:

```dart
class PostureWindow {
  const PostureWindow({
    required this.windowIndex,
    required this.signalSufficient,
    required this.shoulderTiltAvgDeg,
    required this.shoulderTiltExceedRatio,
    required this.shoulderTiltLevel,
    required this.headDownAvgDeg,
    required this.headDownExceedRatio,
    required this.headDownLevel,
    required this.swayLevel,
    required this.gestureActivityLevel,
    required this.torsoSignalSufficient,
    required this.torsoLeanAvgDeg,
    required this.torsoLeanExceedRatio,
    required this.torsoLeanLevel,
    required this.torsoLeanDirection,
    required this.openPostureLevel,
    required this.powerZoneLevel,
    required this.gazeAwayLevel,
    required this.headAlignmentLevel,
    required this.reasons,
  });

  final int windowIndex;
  final bool signalSufficient;
  final double shoulderTiltAvgDeg;
  final double shoulderTiltExceedRatio;
  final String shoulderTiltLevel;
  final double headDownAvgDeg;
  final double headDownExceedRatio;
  final String headDownLevel;
  final String swayLevel;
  final String gestureActivityLevel;
  final bool torsoSignalSufficient;
  final double torsoLeanAvgDeg;
  final double torsoLeanExceedRatio;
  final String torsoLeanLevel;
  final String torsoLeanDirection;
  final String openPostureLevel;
  final String powerZoneLevel;
  final String gazeAwayLevel;
  final String headAlignmentLevel;
  final List<String> reasons;

  factory PostureWindow.fromJson(Map<String, dynamic> json) {
    return PostureWindow(
      windowIndex: json['window_index'] as int? ?? 0,
      signalSufficient: json['signal_sufficient'] as bool? ?? false,
      shoulderTiltAvgDeg:
          (json['shoulder_tilt_avg_deg'] as num?)?.toDouble() ?? 0.0,
      shoulderTiltExceedRatio:
          (json['shoulder_tilt_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      shoulderTiltLevel: json['shoulder_tilt_level'] as String? ?? 'unknown',
      headDownAvgDeg:
          (json['head_down_avg_deg'] as num?)?.toDouble() ?? 0.0,
      headDownExceedRatio:
          (json['head_down_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      headDownLevel: json['head_down_level'] as String? ?? 'unknown',
      swayLevel: json['sway_level'] as String? ?? 'unknown',
      gestureActivityLevel:
          json['gesture_activity_level'] as String? ?? 'unknown',
      torsoSignalSufficient:
          json['torso_signal_sufficient'] as bool? ?? false,
      torsoLeanAvgDeg:
          (json['torso_lean_avg_deg'] as num?)?.toDouble() ?? 0.0,
      torsoLeanExceedRatio:
          (json['torso_lean_exceed_ratio'] as num?)?.toDouble() ?? 0.0,
      torsoLeanLevel: json['torso_lean_level'] as String? ?? 'unknown',
      torsoLeanDirection:
          json['torso_lean_direction'] as String? ?? 'unknown',
      openPostureLevel: json['open_posture_level'] as String? ?? 'unknown',
      powerZoneLevel: json['power_zone_level'] as String? ?? 'unknown',
      gazeAwayLevel: json['gaze_away_level'] as String? ?? 'unknown',
      headAlignmentLevel:
          json['head_alignment_level'] as String? ?? 'unknown',
      reasons:
          (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && flutter test test/posture_timeline_test.dart`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add lib/posture/posture_timeline.dart test/posture_timeline_test.dart
git commit -m "feat: parse plain-language posture level fields in PostureWindow"
```

---

## Task 12: Frontend — `result_mapper.dart` badge text + `buildSegments`

**Files:**
- Modify: `frontend/lib/utils/result_mapper.dart`
- Test: `frontend/test/result_mapper_posture_test.dart`

**Interfaces:**
- Consumes: `PostureWindow` (Task 11).
- Produces: `levelText(String)`, `torsoLeanDirectionText(String)`, `openPostureText(String)`, `powerZoneText(String)` mapping functions; `buildSegments` populates `Segment` with badge text instead of `'평균 X도 · 초과 Y%'` strings.

- [ ] **Step 1: Write the failing tests**

Replace `frontend/test/result_mapper_posture_test.dart` entirely with:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/utils/result_mapper.dart' as mapper;

void main() {
  test('buildSegments fills posture fields when posture windows are present', () {
    final result = {
      'risk': {
        'heatmap': [
          {
            'start': 0.0,
            'end': 15.0,
            'level': 'low',
            'score': 90,
            'pace_level': 'normal',
            'emotion_signal': 'neutral',
            'pause_count': 1,
            'filler_count': 0,
            'repetition_count': 0,
            'reasons': <String>[],
            'transcript': '안녕하세요',
          },
        ],
      },
      'posture': {
        'windows': [
          {
            'window_index': 0,
            'signal_sufficient': true,
            'shoulder_tilt_level': 'mild',
            'head_down_level': 'stable',
            'gesture_activity_level': 'normal',
            'torso_signal_sufficient': true,
            'torso_lean_level': 'stable',
            'torso_lean_direction': 'forward',
            'open_posture_level': 'open',
            'power_zone_level': 'high',
            'head_alignment_level': 'mild',
            'reasons': ['어깨가 약간 기울어진 구간이 있었어요'],
          },
        ],
      },
    };

    final segments = mapper.buildSegments(result);

    expect(segments.length, 1);
    expect(segments.first.postureAvailable, true);
    expect(segments.first.postureSignalSufficient, true);
    expect(segments.first.shoulderTilt, '약간 기울어짐');
    expect(segments.first.headDown, '안정');
    expect(segments.first.torsoLean, '안정');
    expect(segments.first.openPosture, '열림');
    expect(segments.first.powerZone, '높음');
    expect(segments.first.headAlignment, '약간 기울어짐');
    expect(segments.first.torsoLeanDirection, '앞으로');
    expect(segments.first.gestureActivity, '보통');
    expect(segments.first.postureReasons, ['어깨가 약간 기울어진 구간이 있었어요']);
  });

  test(
    'buildSegments leaves posture fields empty when posture data is absent',
    () {
      final result = {
        'risk': {
          'heatmap': [
            {
              'start': 0.0,
              'end': 15.0,
              'level': 'low',
              'score': 90,
              'reasons': <String>[],
            },
          ],
        },
      };

      final segments = mapper.buildSegments(result);

      expect(segments.first.postureAvailable, false);
      expect(segments.first.postureSignalSufficient, false);
      expect(segments.first.shoulderTilt, '');
      expect(segments.first.postureReasons, <String>[]);
    },
  );

  test('buildSegments reports insufficient torso signal separately', () {
    final result = {
      'risk': {
        'heatmap': [
          {'start': 0.0, 'end': 15.0, 'level': 'low', 'score': 90, 'reasons': <String>[]},
        ],
      },
      'posture': {
        'windows': [
          {
            'window_index': 0,
            'signal_sufficient': true,
            'torso_signal_sufficient': false,
          },
        ],
      },
    };

    final segments = mapper.buildSegments(result);

    expect(segments.first.torsoLean, '상체 기울기 신호 부족');
  });

  test('gestureActivityText maps known levels', () {
    expect(mapper.gestureActivityText('low'), '낮음');
    expect(mapper.gestureActivityText('normal'), '보통');
    expect(mapper.gestureActivityText('high'), '높음');
    expect(mapper.gestureActivityText('unknown'), '분석 없음');
  });

  test('levelText maps stable/mild/severe/unknown', () {
    expect(mapper.levelText('stable'), '안정');
    expect(mapper.levelText('mild'), '약간 기울어짐');
    expect(mapper.levelText('severe'), '많이 기울어짐');
    expect(mapper.levelText('unknown'), '분석 없음');
  });

  test('openPostureText maps closed/normal/open/unknown', () {
    expect(mapper.openPostureText('closed'), '닫힘');
    expect(mapper.openPostureText('normal'), '보통');
    expect(mapper.openPostureText('open'), '열림');
    expect(mapper.openPostureText('unknown'), '분석 없음');
  });

  test('powerZoneText maps low/normal/high/unknown', () {
    expect(mapper.powerZoneText('low'), '낮음');
    expect(mapper.powerZoneText('normal'), '보통');
    expect(mapper.powerZoneText('high'), '높음');
    expect(mapper.powerZoneText('unknown'), '분석 없음');
  });

  test('torsoLeanDirectionText maps forward/backward/neutral/unknown', () {
    expect(mapper.torsoLeanDirectionText('forward'), '앞으로');
    expect(mapper.torsoLeanDirectionText('backward'), '뒤로');
    expect(mapper.torsoLeanDirectionText('neutral'), '중립');
    expect(mapper.torsoLeanDirectionText('unknown'), '분석 없음');
  });
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && flutter test test/result_mapper_posture_test.dart`
Expected: FAIL — `levelText`/`openPostureText`/`powerZoneText`/`torsoLeanDirectionText` undefined; `shoulderTilt`/`torsoLean` still return the old `'평균 X도 · 초과 Y%'` strings; `openPosture`/`powerZone` fields don't exist on `Segment` yet (this last part is fixed by Task 13 — for now, comment out the `openPosture`/`powerZone` assertions or accept this test only fully passes once Task 13 lands; note this explicitly when running).

- [ ] **Step 3: Write minimal implementation**

In `frontend/lib/utils/result_mapper.dart`, replace `armOpennessText` with three new mapping functions (keep `gestureActivityText` unchanged):

```dart
String levelText(String level) {
  switch (level) {
    case 'stable':
      return '안정';
    case 'mild':
      return '약간 기울어짐';
    case 'severe':
      return '많이 기울어짐';
    default:
      return '분석 없음';
  }
}

String openPostureText(String level) {
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

String powerZoneText(String level) {
  switch (level) {
    case 'low':
      return '낮음';
    case 'normal':
      return '보통';
    case 'high':
      return '높음';
    default:
      return '분석 없음';
  }
}

String torsoLeanDirectionText(String direction) {
  switch (direction) {
    case 'forward':
      return '앞으로';
    case 'backward':
      return '뒤로';
    case 'neutral':
      return '중립';
    default:
      return '분석 없음';
  }
}
```

In `buildSegments`, replace the `shoulderTilt`/`headDown`/`torsoLean`/`armOpenness` field population (currently the `'평균 X도 · 초과 Y%'` string interpolation) with:

```dart
      shoulderTilt: postureWindow == null
          ? ''
          : levelText(postureWindow.shoulderTiltLevel),
      headDown: postureWindow == null
          ? ''
          : levelText(postureWindow.headDownLevel),
      torsoLean: postureWindow == null
          ? ''
          : (postureWindow.torsoSignalSufficient
              ? levelText(postureWindow.torsoLeanLevel)
              : '상체 기울기 신호 부족'),
      openPosture: postureWindow == null
          ? ''
          : openPostureText(postureWindow.openPostureLevel),
      powerZone: postureWindow == null
          ? ''
          : powerZoneText(postureWindow.powerZoneLevel),
      headAlignment: postureWindow == null
          ? ''
          : levelText(postureWindow.headAlignmentLevel),
      torsoLeanDirection: postureWindow == null
          ? ''
          : torsoLeanDirectionText(postureWindow.torsoLeanDirection),
      gestureActivity: postureWindow == null
          ? ''
          : gestureActivityText(postureWindow.gestureActivityLevel),
      postureReasons: postureWindow?.reasons ?? const [],
```

(`armOpenness: ...` line is deleted, replaced by the two new `openPosture`/`powerZone` lines above.)

- [ ] **Step 4: Run tests to verify they pass**

This task's tests fully pass only once Task 13 adds `openPosture`/`powerZone` to `Segment` — run both:

Run: `cd frontend && flutter test test/result_mapper_posture_test.dart`
Expected: FAIL only on `openPosture`/`powerZone` field access (undefined getter) until Task 13 lands — this is expected and resolved by the next task. Every other assertion in this file passes now.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add lib/utils/result_mapper.dart test/result_mapper_posture_test.dart
git commit -m "feat: map posture levels to plain-language badge text"
```

---

## Task 13: Frontend — `app_models.dart` `Segment` fields

**Files:**
- Modify: `frontend/lib/models/app_models.dart`

**Interfaces:**
- Consumes: `openPosture`/`powerZone` fields referenced by Task 12's `buildSegments`.
- Produces: `Segment` compiles with the new fields; Task 12's tests now fully pass.

- [ ] **Step 1: Write the failing test**

No new test file — Task 12's `result_mapper_posture_test.dart` is the test for this task; it currently fails on `Segment`'s missing `openPosture`/`powerZone` getters.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && flutter test test/result_mapper_posture_test.dart`
Expected: FAIL — compile error, `Segment` has no `openPosture`/`powerZone` parameter.

- [ ] **Step 3: Write minimal implementation**

In `frontend/lib/models/app_models.dart`, update the `Segment` class:

```dart
class Segment {
  const Segment({
    required this.level,
    required this.time,
    required this.flex,
    required this.scoreLabel,
    required this.score,
    required this.scoreColor,
    required this.speed,
    required this.tone,
    required this.pause,
    required this.filler,
    required this.repeat,
    required this.signals,
    required this.script,
    required this.postureAvailable,
    required this.postureSignalSufficient,
    required this.shoulderTilt,
    required this.headDown,
    required this.torsoLean,
    required this.openPosture,
    required this.powerZone,
    required this.headAlignment,
    required this.torsoLeanDirection,
    required this.gestureActivity,
    required this.postureReasons,
  });

  final SegmentLevel level;
  final String time;

  /// 타임라인에서 차지하는 비율 (원본의 width % 값).
  final int flex;
  final String scoreLabel;
  final String score;
  final Color scoreColor;
  final String speed;
  final String tone;
  final String pause;
  final String filler;
  final String repeat;
  final List<String> signals;
  final String script;

  /// 이 구간에 자세(카메라) 데이터가 있는지 여부.
  final bool postureAvailable;
  final bool postureSignalSufficient;
  final String shoulderTilt;
  final String headDown;
  final String torsoLean;
  final String openPosture;
  final String powerZone;
  final String headAlignment;
  final String torsoLeanDirection;
  final String gestureActivity;
  final List<String> postureReasons;
}
```

(`armOpenness` is removed, replaced by `openPosture`, `powerZone`, `headAlignment`, and `torsoLeanDirection`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && flutter test test/result_mapper_posture_test.dart test/posture_timeline_test.dart`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add lib/models/app_models.dart
git commit -m "feat: rename Segment.armOpenness to openPosture, add powerZone"
```

---

## Task 14: Frontend — `analysis_detail.dart` posture tile grid

**Files:**
- Modify: `frontend/lib/screens/analysis_detail.dart:367-381`

**Interfaces:**
- Consumes: `Segment.openPosture`/`powerZone` (Task 13).
- Produces: posture grid renders 7 badge tiles instead of 5 numeric ones.

- [ ] **Step 1: Write the failing test**

No new automated test (this is a widget layout change with no existing widget test covering this exact grid) — verified manually per Step 4 below. If a golden/widget test framework is later added for this screen, it should assert the grid renders 7 `_statTile` children with no digit characters in their values when `postureSignalSufficient` is true; none exists today, so this step is a manual check.

- [ ] **Step 2: (no automated test to run — skip to implementation)**

- [ ] **Step 3: Write minimal implementation**

In `frontend/lib/screens/analysis_detail.dart`, replace lines 374-380 (the `GridView.count` children list):

```dart
                    children: [
                      _statTile('어깨 기울기', seg.shoulderTilt, AppColors.gray900),
                      _statTile('고개 숙임', seg.headDown, AppColors.gray900),
                      _statTile('상체 기울기', seg.torsoLean, AppColors.gray900),
                      _statTile('상체 방향', seg.torsoLeanDirection, AppColors.gray900),
                      _statTile('자세 개방성', seg.openPosture, AppColors.gray900),
                      _statTile('제스처 파워존', seg.powerZone, AppColors.gray900),
                      _statTile('머리 정렬', seg.headAlignment, AppColors.gray900),
                      _statTile('제스처 활동성', seg.gestureActivity, AppColors.gray900),
                    ],
```

(`seg.headAlignment` was populated in Task 12 and added to `Segment` in Task 13 — this task only wires it into the visible grid.)

- [ ] **Step 4: Manual verification**

Run: `cd frontend && flutter run -d chrome` (or any available device), record a short session with posture capture enabled, open the result detail screen, and confirm the "자세 신호" grid shows 8 tiles with Korean badge text (no digits or `%`) — 어깨 기울기, 고개 숙임, 상체 기울기, 상체 방향, 자세 개방성, 제스처 파워존, 머리 정렬, 제스처 활동성.

- [ ] **Step 5: Commit**

```bash
cd frontend
git add lib/screens/analysis_detail.dart
git commit -m "feat: show 8-tile plain-language posture grid in result detail screen"
```

---

## Post-plan manual validation (not a task — tracked separately)

Per the design doc's validation plan: after all 14 tasks land, do a real-webcam session leaning forward/backward and pushing your head forward/back while watching the "상체 방향" and "머리 정렬" tiles (both added in Task 14) update. If MediaPipe's `z` proves unreliable at 320x240:
- Revert the `torso_lean_direction != "forward"` condition in Task 5's reason-gating code (posture_analyzer.py) back to the unconditional check from Task 4.
- Drop `head_alignment_level` (Task 8) and its reason block entirely — nothing else depends on it.
