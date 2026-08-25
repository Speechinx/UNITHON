# Posture Upper-Body Landmark Expansion Design

> Companion docs:
> `backend/docs/superpowers/plans/2026-08-24-posture-tracking-backend.md` (original posture pipeline)
> Recent fix (this session, not yet a written spec): `posture_analyzer.py` required-landmark set was narrowed to `nose`/`left_shoulder`/`right_shoulder` only, because requiring wrist visibility caused most windows to be flagged as insufficient signal. Wrist visibility now only gates `gesture_activity_level`, independently of the window's core `signal_sufficient` flag.

## Background

Posture analysis currently extracts 5 landmarks per frame (`nose`, `left_shoulder`, `right_shoulder`, `left_wrist`, `right_wrist`) and derives 4 signals from them: shoulder tilt, head-down angle, lateral sway, and gesture activity level. The user wants a broader, "big picture" check of whether the presenter is standing/sitting in a correct posture overall — not fine-grained detail (explicitly ruled out hand/finger landmarks and eye/ear landmarks as too granular for this goal).

Two additional landmark groups were chosen to extend this: hips (`left_hip`/23, `right_hip`/24) and elbows (`left_elbow`/13, `right_elbow`/14).

## Goal

Add two new posture signals — torso lean and arm openness — computed from hip and elbow landmarks respectively, while preserving the existing lesson learned from the wrist bug: a landmark group that is frequently out of frame (hips especially, in a typical chest-up webcam framing) must never gate the window's core `signal_sufficient` flag. Each new signal degrades independently to "insufficient" without discarding the shoulder/head signals that are still reliably visible.

## Non-goals

- No face/eye/ear landmarks (explicitly ruled out — too granular for the "big picture" goal).
- No finger/hand landmarks (explicitly ruled out — same reason, and lower reliability at the current 320x240 capture resolution).
- No combined single posture score across all signals — each signal (shoulder tilt, head-down, torso lean, arm openness, gesture activity) stays independently reported, per the existing project principle against fabricating a combined subjective judgment (see `구현계획서_자세추적.md` §1).
- No change to capture cadence, resolution, or the 15-second windowing scheme.

## Design

### 1. Extend landmark extraction (`posture_frame_extractor.py`)

Add to `LANDMARK_INDICES`:

```python
"left_hip": 23,
"right_hip": 24,
"left_elbow": 13,
"right_elbow": 14,
```

No other change to `PostureFrameExtractor` — it already returns whatever keys are in `LANDMARK_INDICES` with `x`/`y`/`visibility`, so no per-landmark special-casing is needed at the extraction layer.

### 2. Generalize the optional-signal validity check (`posture_analyzer.py`)

Currently `_has_gesture_signal` is a one-off method hardcoded to `GESTURE_LANDMARKS`. Generalize it:

```python
def _has_signal(self, frame: dict, landmark_names: list[str]) -> bool:
    return all(
        key in frame
        and frame[key]["visibility"] >= self.MIN_VISIBILITY
        for key in landmark_names
    )
```

Define three named landmark groups (replacing the single `GESTURE_LANDMARKS` constant):

```python
GESTURE_LANDMARKS = ["left_wrist", "right_wrist"]
TORSO_LANDMARKS = ["left_hip", "right_hip"]
ARM_LANDMARKS = ["left_elbow", "right_elbow"]
```

`REQUIRED_LANDMARKS` (`nose`, `left_shoulder`, `right_shoulder`) is **not** changed — this is the core gate for the window's `signal_sufficient` flag and must stay minimal, per the wrist-bug lesson.

### 3. Torso lean signal

Computed from the shoulder center and hip center:

```python
def _torso_lean_deg(self, frame: dict) -> float:
    shoulder_center = self._shoulder_center(frame)  # (x, y) midpoint of both shoulders
    hip_center = self._hip_center(frame)             # (x, y) midpoint of both hips

    dx = shoulder_center[0] - hip_center[0]
    dy = shoulder_center[1] - hip_center[1]

    return abs(math.degrees(math.atan2(abs(dx), abs(dy))))
```

0° when the shoulder center sits directly above the hip center (upright spine); increases as the torso leans sideways or slumps off-vertical. This mirrors `_shoulder_tilt_deg`'s `atan2` pattern but measures deviation from *vertical* (spine) rather than from *horizontal* (shoulder line).

Window aggregation follows the existing `shoulder_tilt`/`head_down` pattern exactly: average degrees + exceed-ratio against a threshold, added to `reasons` when the ratio crosses `REASON_EXCEED_RATIO_THRESHOLD` (0.3, reused as-is).

New constant: `TORSO_LEAN_THRESHOLD_DEG = 10.0` (placeholder starting value, same status as the existing gesture/shoulder thresholds — not empirically tuned, expected to need adjustment after real demo footage).

### 4. Arm openness signal

Computed per-frame as the ratio of elbow span to shoulder span:

```python
def _arm_openness_ratio(self, frame: dict) -> float:
    shoulder_width = self._distance(frame["left_shoulder"], frame["right_shoulder"])
    elbow_width = self._distance(frame["left_elbow"], frame["right_elbow"])

    if shoulder_width == 0:
        return 1.0

    return elbow_width / shoulder_width
```

Window-level classification into three tiers (same shape as `_gesture_activity_level`, same "not a value judgment" framing):

- `ratio < ARM_OPENNESS_LOW_THRESHOLD` (placeholder `0.8`) → `"closed"` (elbows pulled in tight to the torso)
- `ratio > ARM_OPENNESS_HIGH_THRESHOLD` (placeholder `1.3`) → `"open"`
- otherwise → `"normal"`

Uses the mean ratio across arm-valid frames in the window (mirrors gesture activity using the mean of frame-to-frame wrist movement, adapted to a per-frame ratio since openness, unlike gesture activity, isn't inherently a *motion* signal).

### 5. Per-window aggregation and graceful degradation

For each of the three optional groups (gesture/torso/arm), compute the group's own valid-frame ratio within the window's already-`_is_valid` (core) frames:

```python
group_frames = [f for f in valid_frames if self._has_signal(f, GROUP_LANDMARKS)]
group_ratio = len(group_frames) / len(valid_frames) if valid_frames else 0.0
```

If `group_ratio >= MIN_VALID_FRAME_RATIO` (0.5, reused as-is): compute the group's signal(s) from `group_frames`. Otherwise: report the group as insufficient.

Because torso lean is a **numeric** metric (unlike the string-valued `gesture_activity_level`, which already has an `"unknown"` sentinel), it needs its own sufficiency flag rather than silently defaulting numeric fields to 0.0 (which would misleadingly read as "perfectly upright"). Add:

```python
"torso_signal_sufficient": bool,
"torso_lean_avg_deg": float,       # 0.0 when torso_signal_sufficient is False
"torso_lean_exceed_ratio": float,  # 0.0 when torso_signal_sufficient is False
```

`arm_openness_level` follows the existing string-sentinel pattern used by `gesture_activity_level`: `"closed" | "normal" | "open" | "unknown"`.

When `torso_signal_sufficient` is `False`, no torso-lean reason is added to `reasons`, mirroring how a window-level `signal_sufficient == False` already suppresses all reasons today.

### 6. Downstream schema changes (`app/schemas/analysis_response.py`)

Add to `PostureWindow`:

```python
torso_signal_sufficient: bool = False
torso_lean_avg_deg: float = 0.0
torso_lean_exceed_ratio: float = 0.0
arm_openness_level: str = "unknown"
```

### 7. Coaching prompt changes (`coaching_service.py`)

Extend the `[자세]` rule block (currently rules 28-1 through 28-6) with two more rules, matching the existing tone exactly:

- Torso lean is a measured geometric fact (spine vertical alignment), not a judgment about confidence/nervousness — same framing as rule 28-2.
- `torso_signal_sufficient`가 false인 구간은 상체 기울기를 언급하지 마라 — same framing as rule 28-3, scoped to the torso sub-signal.
- `arm_openness_level`은 좋고 나쁨을 판단하는 지표가 아니라 팔 벌어짐 정도(닫힘/보통/열림)일 뿐이다 — same framing as rule 28-6 for `gesture_activity_level`.

### 8. Frontend changes

- `posture_timeline.dart` (`PostureWindow.fromJson`): parse the 4 new fields with the same null-safe defaulting pattern already used for existing fields.
- `main.dart` (`_WindowDetailCard`'s posture section, ~line 2709 onward): add two more `_DetailItem` entries (torso lean, arm openness) inside the existing `if (postureWindow!.signalSufficient) ...` branch, following the existing two-column `Row` layout used for shoulder tilt / head-down (**without** `CrossAxisAlignment.stretch`, per the layout bug just fixed in this session). Torso lean's own item should additionally check `postureWindow!.torsoSignalSufficient` and show a "상체 기울기 신호 부족" style fallback text when false, analogous to how the window-level insufficient case is already handled.

## Testing

- `test_posture_analyzer.py`: extend the shared `_frame()` helper to include hip/elbow landmarks (defaulting to an upright, shoulder-width-matched pose so existing tests are unaffected). Add:
  - `_torso_lean_deg` unit tests (0° for vertically aligned shoulder/hip centers, positive value for an offset case).
  - `_arm_openness_ratio` / tier classification unit tests (closed/normal/open boundary cases).
  - A window-level test mirroring `test_analyze_window_signal_sufficient_when_only_wrists_low_visibility`: hips consistently low-visibility while shoulders/nose remain valid → `signal_sufficient is True`, `torso_signal_sufficient is False`, `torso_lean_avg_deg == 0.0`.
- `test_posture_frame_extractor.py`: confirm the extractor returns the 4 new keys when present in a test image's pose result.
- `test_coaching_service_posture.py`: confirm no torso/arm-openness content is fabricated when the corresponding sufficiency flag is false, mirroring the existing empty-posture-signal test pattern.
