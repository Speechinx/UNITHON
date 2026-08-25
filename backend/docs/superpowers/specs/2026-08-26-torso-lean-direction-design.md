> **Superseded**: folded into and expanded by `2026-08-26-posture-plain-language-design.md`, which covers the same z-based direction work plus four more metric changes and a plain-language display layer. Kept here for the detailed derivation of the direction formula and reason-gating logic, which the newer doc references rather than repeats.

# Torso Lean Direction Design

> Companion docs:
> `backend/docs/superpowers/plans/2026-08-24-posture-tracking-backend.md` (original posture pipeline)
> `backend/docs/superpowers/specs/2026-08-25-posture-upper-body-landmarks-design.md` (added `torso_lean_avg_deg`/`torso_lean_exceed_ratio`, magnitude-only, `TORSO_LEAN_THRESHOLD_DEG = 10.0` documented there as an untuned placeholder)

## Background

`posture_analyzer.py`'s `_torso_lean_deg` currently measures only the **magnitude** of torso deviation from vertical, using `x`/`y` landmarks. Any lean beyond `TORSO_LEAN_THRESHOLD_DEG` is treated as a negative "reason" regardless of direction — leaning toward the camera (forward) and leaning away from it (backward) are scored identically.

This conflicts with published research on presenter posture: Wu, Y. (2024), *"Analyzing the influence of physical posture on audience perception in mass media presentations,"* Molecular & Cellular Biomechanics 21(4), 622. That study found audiences rate an upright posture and a **forward-leaning** posture equivalently across credibility, trustworthiness, engagement, and authority (all pairwise p > 0.4, Cohen's d < 0.21), while **backward-leaning** and (especially) **slouched** postures score significantly lower. The paper is a perception study (human raters + categorical posture conditions), not a computer-vision study — it provides no angle thresholds, only the qualitative finding that direction matters.

`PostureFrameExtractor` currently discards MediaPipe's `z` (relative depth) landmark coordinate, keeping only `x`/`y`/`visibility`. Without `z`, forward/backward lean cannot be distinguished from a frontal webcam — only left/right lean is observable in `x`/`y`.

## Goal

Add a direction signal (`torso_lean_direction`: `"forward" | "backward" | "neutral" | "unknown"`) computed from `z`, and use it to stop flagging forward lean as a negative "reason" while continuing to flag backward lean/slouch. Expose the raw direction value on the recording screen so it can be validated by physically leaning toward/away from the camera during a real webcam session — this is the only realistic way to assess whether MediaPipe's `z` estimate is trustworthy at the project's 320x240 lite-model capture resolution.

## Non-goals

- No claim that the paper's angle thresholds exist — it has none; only the directional qualitative finding is used.
- No change to the existing magnitude threshold (`TORSO_LEAN_THRESHOLD_DEG`) or to any other signal (shoulder tilt, head-down, gaze, gesture, arm openness).
- No combined posture score — each signal stays independently reported, per the existing project principle (`구현계획서_자세추적.md` §1, reaffirmed in the 2026-08-25 design doc's non-goals).
- No permanent commitment to this feature: if manual webcam validation shows `z` is too noisy at this resolution, the directional gate is designed to be revertable in one place without touching other signals.

## Design

### 1. Extract `z` (`posture_frame_extractor.py`)

Add `"z": landmarks[index].z` to the per-landmark dict returned by `extract()`, alongside the existing `x`/`y`/`visibility`. No change to `LANDMARK_INDICES` — `z` is already present on every MediaPipe landmark, so this only widens the dict built from landmarks that are already extracted.

### 2. Direction computation (`posture_analyzer.py`)

New constant:

```python
TORSO_LEAN_DIRECTION_Z_THRESHOLD = 0.05  # placeholder, needs real-webcam tuning
```

Reuses `torso_signal_sufficient` (hip visibility) as the gate — MediaPipe does not expose a separate visibility for `z`, so if `x`/`y` are trusted enough to compute magnitude, `z` is computed under the same gate.

```python
def _shoulder_center_z(self, frame: dict) -> float:
    return (frame["left_shoulder"]["z"] + frame["right_shoulder"]["z"]) / 2

def _hip_center_z(self, frame: dict) -> float:
    return (frame["left_hip"]["z"] + frame["right_hip"]["z"]) / 2

def _torso_lean_direction(self, frame: dict) -> str:
    dz = self._shoulder_center_z(frame) - self._hip_center_z(frame)

    if dz <= -self.TORSO_LEAN_DIRECTION_Z_THRESHOLD:
        return "forward"
    if dz >= self.TORSO_LEAN_DIRECTION_Z_THRESHOLD:
        return "backward"
    return "neutral"
```

(Sign convention: MediaPipe `z` decreases toward the camera. Shoulders closer to the camera than hips ⇒ forward lean.)

Window-level aggregation (inside the existing `if torso_signal_sufficient:` branch in `analyze_window`): compute per-frame direction across `torso_frames`, then take the majority direction (by count) as the window's `torso_lean_direction`. Tie-break order: `"neutral"` > `"backward"` > `"forward"` — i.e. on a tie, prefer whichever non-`"forward"` label applies, and only report `"forward"` when it strictly outnumbers both others. This keeps the conservative default consistent with the reason-gating rule in step 3 (ambiguous ⇒ still eligible to be flagged). When `torso_signal_sufficient` is `False`, report `"unknown"` (mirrors how `torso_lean_avg_deg` reports `0.0` in that case).

### 3. Reason gating

Current logic (posture_analyzer.py:374-380):

```python
if (
    torso_signal_sufficient
    and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
):
    reasons.append(f"상체 기울어짐 {torso_lean_exceed_ratio * 100:.0f}% 구간")
```

New condition adds a direction check:

```python
if (
    torso_signal_sufficient
    and torso_lean_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
    and torso_lean_direction != "forward"
):
    reasons.append(f"상체 기울어짐 {torso_lean_exceed_ratio * 100:.0f}% 구간")
```

`"backward"` and `"neutral"` both still count as a reason (conservative default when direction is ambiguous). No change to `avatar_state`'s own logic — it already derives from `reasons` + `low_engagement`, so suppressing the forward-lean reason automatically lets a forward-leaning, low-engagement-free window settle into `"engaged"` instead of `"confused"`.

### 4. Result payload

Add `"torso_lean_direction": <str>` to the dict returned by `analyze_window`, alongside the existing `torso_lean_avg_deg`/`torso_lean_exceed_ratio` fields.

### 5. Schema (`app/schemas/analysis_response.py`)

Add to `PostureWindow`:

```python
torso_lean_direction: str = "unknown"
```

### 6. Coaching prompt (`coaching_service.py`)

Extend the existing `[자세]` rule block with one line, matching its existing tone (measured-fact framing, no psychological interpretation):

> "상체가 앞으로 기울어진 구간은 문제로 언급하지 마라 — 청중 쪽으로 몸을 기울이는 것은 카메라 신호상 정상적인 참여 신호다."

### 7. Frontend (validation display)

Threaded through the existing posture display pipeline so it's visible on the actual recording/result screen during manual webcam testing:

- `frontend/lib/posture/posture_timeline.dart`: add `torsoLeanDirection` field to `PostureWindow`, parsed in `fromJson` from `torso_lean_direction` (default `'unknown'`), following the existing null-safe pattern used for `armOpennessLevel`.
- `frontend/lib/utils/result_mapper.dart`: add `torsoLeanDirectionText(String direction)` mapping function (`forward` → "앞으로", `backward` → "뒤로", `neutral` → "중립", else → "분석 없음"), following the exact shape of the existing `armOpennessText`. In `buildSegments`, populate `Segment.torsoLeanDirection` from `postureWindow?.torsoLeanDirection`.
- `frontend/lib/models/app_models.dart`: add `torsoLeanDirection` field (`String`) to `Segment`.
- `frontend/lib/screens/analysis_detail.dart` (~line 377, inside the existing 5-tile `GridView.count` under `자세 신호`): add a 6th `_statTile('상체 방향', seg.torsoLeanDirection, AppColors.gray900)`.

## Validation and rollback plan

The core risk is whether MediaPipe Pose Landmarker (lite model) produces a `z` estimate accurate enough to distinguish forward/backward lean at 320x240. This cannot be assessed with synthetic unit tests — it requires running the app, recording with the webcam, and physically leaning forward/backward while watching the "상체 방향" tile update.

If validation shows `z` is too noisy to be useful: revert the single `and torso_lean_direction != "forward"` condition in the reason-gating logic (item 3) back to the pre-existing unconditional check. This is the only place behavior depends on direction; the extraction, computation, schema, and frontend display can be left in place (harmless additional data) or removed independently without affecting any other signal.

## Testing

- `test_posture_analyzer.py`:
  - Extend the shared `_frame()` helper to accept `z` per landmark (default `0.0` for all, keeping existing tests unaffected).
  - `_torso_lean_direction` unit tests: forward (shoulder z closer than hip z beyond threshold), backward (opposite), neutral (within threshold band).
  - `analyze_window` test: torso lean magnitude exceeds `TORSO_LEAN_THRESHOLD_DEG` with `direction == "forward"` → no "상체" reason in `reasons`.
  - `analyze_window` test: same magnitude exceedance with `direction == "backward"` → "상체" reason present (existing behavior preserved).
  - `torso_signal_sufficient is False` → `torso_lean_direction == "unknown"`.
- `test_posture_frame_extractor.py`: extend `test_extract_maps_landmark_indices_correctly` to assert `z` is present per landmark.
- `test_coaching_service_posture.py`: confirm the new `[자세]` rule line is present in the built prompt when posture signals exist.
- Frontend: extend `posture_timeline_test.dart` (parses `torso_lean_direction`) and `result_mapper_posture_test.dart` (`torsoLeanDirectionText` mapping cases) following the existing `armOpennessLevel` test pattern.
- Manual: real-webcam validation of the "상체 방향" tile per the plan above — not automatable, tracked as a manual step before treating this feature as validated rather than experimental.
