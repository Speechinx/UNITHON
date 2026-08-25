# Posture Plain-Language Metrics Design

> Companion docs:
> `backend/docs/superpowers/plans/2026-08-24-posture-tracking-backend.md` (original posture pipeline)
> `backend/docs/superpowers/specs/2026-08-25-posture-upper-body-landmarks-design.md` (added torso lean magnitude / arm openness)
> `backend/docs/superpowers/specs/2026-08-26-torso-lean-direction-design.md` (superseded by this doc — see its detailed derivation of the `z`-based direction formula, reused as-is here)

## Background

Two separate pieces of user input drove this design:

1. A reference table (user-compiled from published heuristics for MediaPipe-based posture scoring) proposing five geometrically-computable indicators: shoulder tilt, "open posture" (spine-vector-relative elbow/wrist distance), body sway (mid-point X variance), a gesture "power zone" (wrist Y position relative to shoulder/hip band), and head alignment / forward-head ("turtle neck") posture (ear-shoulder Z offset).
2. A request to stop surfacing raw degrees/percentages to end users and instead show plain-language, layperson-readable posture feedback.

This doc folds in the previously-committed torso-lean-direction design (same `z`-extraction dependency, same validation risk) so there is one implementation plan instead of two overlapping ones.

## Goal

- Recompute "open posture" using the spine-vector method from the reference table (replacing the current elbow-width/shoulder-width ratio), renamed `open_posture_level` to reflect the changed semantics.
- Add two new signals: gesture power-zone ratio, and head alignment / forward-head offset.
- Add torso lean direction (`forward`/`backward`/`neutral`), as previously spec'd.
- Extend the existing magnitude signals (shoulder tilt, head-down, torso lean, gaze-away, sway) with a second "severe" threshold, so each reports a 3-tier category (`stable`/`mild`/`severe`) instead of only a threshold-exceeded boolean.
- Replace all numeric degree/percentage display in the frontend posture tiles with category badges, and replace the current `"X% 구간"`-style reason strings with plain Korean sentences.

## Non-goals

- No removal of raw numeric fields (`*_avg_deg`, `*_exceed_ratio`, `sway_std`) from the backend schema — `CoachingService` and internal debugging still use them. Only the **frontend tile display** stops showing raw numbers; the JSON payload keeps them.
- No combined single posture score — each signal still reports independently, per the standing project principle (`구현계획서_자세추적.md` §1).
- No change to capture cadence, resolution, or windowing.
- No backward-compatibility shim for the `arm_openness_level` → `open_posture_level` rename — every reference (backend, schema, frontend, tests) is updated directly, per user direction.

## Design

### 1. Shared: extract `z` (`posture_frame_extractor.py`)

One change, used by both torso lean direction and head alignment:

```python
"z": landmarks[index].z
```

added to the per-landmark dict, alongside existing `x`/`y`/`visibility`.

### 2. Three-tier classification helper (`posture_analyzer.py`)

```python
def _classify(self, value: float, mild: float, severe: float) -> str:
    if value >= severe:
        return "severe"
    if value >= mild:
        return "mild"
    return "stable"
```

Used by every magnitude signal below. All threshold constants are placeholders in the same spirit as the existing `TORSO_LEAN_THRESHOLD_DEG = 10.0` (explicitly documented in the 2026-08-25 doc as untuned) — expected to be adjusted once there's real demo footage to check against.

### 3. Existing magnitude signals gain a "severe" tier

| Signal | Existing threshold (becomes "mild") | New "severe" threshold |
|---|---|---|
| Shoulder tilt | `SHOULDER_TILT_THRESHOLD_DEG` → `SHOULDER_TILT_MILD_DEG = 8.0` | `SHOULDER_TILT_SEVERE_DEG = 15.0` |
| Head down | `HEAD_DOWN_THRESHOLD_DEG` → `HEAD_DOWN_MILD_DEG = 60.0` | `HEAD_DOWN_SEVERE_DEG = 75.0` |
| Torso lean | `TORSO_LEAN_THRESHOLD_DEG` → `TORSO_LEAN_MILD_DEG = 10.0` | `TORSO_LEAN_SEVERE_DEG = 20.0` |
| Gaze away | `GAZE_AWAY_THRESHOLD_DEG` → `GAZE_AWAY_MILD_DEG = 20.0` | `GAZE_AWAY_SEVERE_DEG = 35.0` |
| Sway (new: currently reported but never classified) | `SWAY_MILD_STD = 0.02` | `SWAY_SEVERE_STD = 0.05` |

Each produces a `<signal>_level: "stable" | "mild" | "severe"` field (or `"unknown"` when the underlying sufficiency flag is false), computed via `_classify(avg_value, mild, severe)`.

Reason-sentence generation replaces the current `f"{label} {ratio*100:.0f}% 구간"` strings. One sentence per signal, chosen by level, gated by the existing `exceed_ratio >= REASON_EXCEED_RATIO_THRESHOLD` check (unchanged gating condition, only the string changes):

- Shoulder tilt: mild → `"어깨가 약간 기울어진 구간이 있었어요"`, severe → `"어깨가 한쪽으로 많이 기울어져 있었어요"`
- Head down: mild → `"고개를 자주 숙이고 있었어요"`, severe → `"고개를 많이 숙인 채로 발표했어요"`
- Torso lean (only when direction != `"forward"`, per the prior design): mild → `"상체가 살짝 기울어져 있었어요"`, severe → `"상체가 많이 기울어져 있었어요"`
- Gaze away: mild → `"시선이 자주 옆으로 벗어났어요"`, severe → `"시선이 많이 벗어나 있었어요"`
- Sway (new): mild → `"몸이 조금 흔들렸어요"`, severe → `"몸이 자주 좌우로 흔들렸어요"`

(Exact copy is not load-bearing for the plan — these are the strings to start implementation with; wording can be refined in review without changing the design's structure.)

### 4. Open posture (replaces arm openness ratio)

Renamed `arm_openness_level` → `open_posture_level` everywhere (backend field, schema, Dart model field, mapper function, UI tile, all tests) — no compatibility alias.

```python
def _open_posture_distance(self, point: dict, shoulder_center, hip_center, shoulder_width: float) -> float:
    # perpendicular distance from `point` to the line through shoulder_center–hip_center,
    # normalized by shoulder_width for scale invariance.
    ...

def _open_posture_score(self, frame: dict) -> float:
    shoulder_center = self._shoulder_center(frame)
    hip_center = self._hip_center(frame)
    shoulder_width = self._distance(frame["left_shoulder"], frame["right_shoulder"])

    points = [frame["left_elbow"], frame["right_elbow"], frame["left_wrist"], frame["right_wrist"]]
    distances = [
        self._open_posture_distance(p, shoulder_center, hip_center, shoulder_width)
        for p in points
    ]
    return statistics.mean(distances)
```

Sufficiency now requires **all three** groups (`ARM_LANDMARKS`, `GESTURE_LANDMARKS`, `TORSO_LANDMARKS`) valid in the frame — a stricter gate than today's arm-only check, because the spine vector needs hips. When insufficient: `open_posture_level = "unknown"` (matches the existing sentinel pattern).

Classification: `OPEN_POSTURE_CLOSED_MAX = 0.4`, `OPEN_POSTURE_OPEN_MIN = 1.0` (placeholders, new scale — the old `0.8`/`1.3` thresholds were calibrated for the old elbow-width/shoulder-width ratio and don't carry over) → `"closed" | "normal" | "open"`.

No reason-sentence generation for this signal (unchanged from today's `arm_openness_level`, which never fed `reasons` — kept as a purely descriptive, non-judgmental signal per the project's existing philosophy for this metric).

### 5. Gesture power zone (new)

```python
def _in_power_zone(self, wrist: dict, shoulder_center_y: float, hip_center_y: float) -> bool:
    return shoulder_center_y <= wrist["y"] <= hip_center_y
```

Per frame (within frames where `GESTURE_LANDMARKS` and `TORSO_LANDMARKS` are both valid): "in zone" if the left wrist OR the right wrist falls within the shoulder–hip vertical band. `power_zone_ratio` = fraction of such frames in zone.

Sufficiency: requires both gesture and torso groups valid (reuses `gesture_ratio` and `torso_ratio` computed for their own signals). `power_zone_level = "unknown"` otherwise.

Classification: `POWER_ZONE_LOW_MAX = 0.3`, `POWER_ZONE_HIGH_MIN = 0.6` (placeholders) → `"low" | "normal" | "high"`.

No reason-sentence generation — mirrors `gesture_activity_level`'s existing "position/activity only, not a value judgment" framing.

### 6. Head alignment / forward-head offset (new)

Reuses `GAZE_LANDMARKS` (`left_ear`, `right_ear`) for its sufficiency gate — same landmarks already gate `gaze_signal_sufficient`, so no new landmark group is introduced.

```python
def _forward_head_z_offset(self, frame: dict) -> float:
    ear_center_z = (frame["left_ear"]["z"] + frame["right_ear"]["z"]) / 2
    shoulder_center_z = self._shoulder_center_z(frame)  # shared helper, see torso-lean-direction doc
    return shoulder_center_z - ear_center_z  # positive => ears closer to camera than shoulders => forward head
```

Window aggregation follows the existing avg + exceed-ratio pattern. New thresholds: `HEAD_ALIGNMENT_MILD_Z = 0.03`, `HEAD_ALIGNMENT_SEVERE_Z = 0.07` (placeholders — shares the same core risk as torso lean direction: this is only measurable via `z`, and `z` accuracy at 320x240 with the lite model is unvalidated). `head_alignment_level: "stable" | "mild" | "severe" | "unknown"`.

Reason sentences (same exceed-ratio gate as other magnitude signals): mild → `"고개가 어깨보다 살짝 앞으로 나와 있었어요"`, severe → `"고개가 어깨보다 많이 앞으로 나와 있었어요"`.

This is a distinct signal from `head_down_level` (which measures looking-down-at-notes via the nose–shoulder angle in `x`/`y`) — forward-head posture can occur while looking straight ahead, and vice versa. Both are kept, independently reported.

### 7. Torso lean direction

Unchanged from `2026-08-26-torso-lean-direction-design.md` — see that doc for the full derivation (`_torso_lean_direction`, `TORSO_LEAN_DIRECTION_Z_THRESHOLD`, majority-vote aggregation with `neutral > backward > forward` tie-break, and the reason-gating change that excludes `"forward"` from counting as a problem).

### 8. `avatar_state` and `low_engagement`

`low_engagement` currently reads `gesture_activity_level == "low" and arm_openness_level == "closed"`; update the second half to `open_posture_level == "closed"`. No other change — `avatar_state` still derives purely from `reasons` (now sway- and head-alignment-aware, since those can newly append reasons) and `low_engagement`.

### 9. Schema (`app/schemas/analysis_response.py`)

`PostureWindow` gains:

```python
shoulder_tilt_level: str = "unknown"
head_down_level: str = "unknown"
torso_lean_level: str = "unknown"
torso_lean_direction: str = "unknown"
gaze_away_level: str = "unknown"
sway_level: str = "unknown"
open_posture_level: str = "unknown"   # replaces arm_openness_level
power_zone_level: str = "unknown"
head_alignment_level: str = "unknown"
```

`arm_openness_level` is removed (not deprecated) from the schema.

### 10. Coaching prompt (`coaching_service.py`)

Extend the `[자세]` rule block with:
- The forward-lean exception (from the superseded doc).
- `power_zone_level`과 `open_posture_level`은 좋고 나쁨을 판단하는 지표가 아니라 위치/개방도 서술일 뿐이다 (extends the existing rule already covering `gesture_activity_level` to the renamed/new signal).
- `head_alignment_level`은 측정된 기하학적 사실(귀-어깨 상대 위치)일 뿐, 피로도나 집중력 저하를 단정하지 마라 — same framing as the existing torso-lean rule.

### 11. Frontend

Data flow: `posture_analyzer.py` → `PostureWindow` schema → `posture_timeline.dart` (`PostureWindow.fromJson`) → `result_mapper.dart` (`buildSegments`, plus new `*Text()` mapping functions) → `models/app_models.dart` (`Segment` fields) → `screens/analysis_detail.dart` (`_statTile` grid, ~line 375-379).

- `posture_timeline.dart`: replace `armOpennessLevel` field with `openPostureLevel`; add `shoulderTiltLevel`, `headDownLevel`, `torsoLeanLevel`, `torsoLeanDirection`, `gazeAwayLevel`, `swayLevel`, `powerZoneLevel`, `headAlignmentLevel` — all parsed with the existing null-safe `?? 'unknown'` pattern.
- `result_mapper.dart`: add one `*Text()` mapping function per new/renamed level field (following the exact shape of the existing `armOpennessText`/`gestureActivityText`), e.g. `openPostureText`, `powerZoneText`, `headAlignmentText`, `shoulderTiltLevelText`, etc. `buildSegments` populates `Segment` fields from these instead of the current `'평균 X도 · 초과 Y%'` string interpolation (lines 290-305) — those number-formatting lines are deleted, not kept alongside.
- `models/app_models.dart`: `Segment`'s `shoulderTilt`/`headDown`/`torsoLean`/`armOpenness` string fields become badge-text strings sourced from the new `*Text()` functions (same field names/types, just populated differently — no signature change needed except `armOpenness` → `openPosture` to match the rename) plus two new fields `powerZone` and `headAlignment`.
- `analysis_detail.dart` (~line 367-381): grid grows from 5 to 7 tiles (add "제스처 파워존", "머리 정렬"); all tile values are now badge text instead of "평균 X도 · 초과 Y%".

## Validation and rollback plan

Two of the new/changed signals (torso lean direction, head alignment) depend on MediaPipe's `z` estimate at 320x240 with the lite model — an unvalidated assumption. Both should be checked in the **same manual webcam session**: lean forward/backward and push your head forward/back while watching the recording screen, confirming the two new tiles ("상체 방향", "머리 정렬") react as expected.

If `z` proves unreliable for one or both:
- Torso lean direction: revert the single direction condition in the reason-gating logic (see the superseded doc, item 3) — the rest of torso lean (magnitude, level, reason) is unaffected.
- Head alignment: drop the `head_alignment_level` field and its reason generation entirely; nothing else depends on it (it doesn't feed `low_engagement` or any other computed signal).

The other three changes (open posture recompute, sway leveling, power zone) use only `x`/`y`/`visibility` — no `z` dependency, no equivalent validation risk. They can be evaluated on the existing synthetic-frame unit-test style used throughout this file.

## Testing

- `test_posture_analyzer.py`:
  - `_classify` unit tests (stable/mild/severe boundaries).
  - Extend `_frame()` helper with `z` per landmark (default `0.0`).
  - `_open_posture_score` / distance-from-spine-line unit tests: point on the spine line → `0.0`; point offset by a known amount → matches expected normalized distance.
  - `analyze_window` test: `open_posture_level == "unknown"` when hips are low-visibility (even if arms/wrists are fully visible) — the new, stricter sufficiency gate.
  - `_in_power_zone` / `power_zone_ratio` unit tests: wrist between shoulder and hip Y → in zone; wrist above shoulder or below hip → not in zone.
  - `_forward_head_z_offset` unit tests: ears at same z as shoulders → `0.0`; ears closer to camera → positive value → `"mild"`/`"severe"` per threshold.
  - Reason-sentence tests: one per signal, confirming the plain-language string (not a percentage) appears in `reasons` when the level is mild/severe and exceed-ratio crosses the threshold.
  - `low_engagement` test updated to reference `open_posture_level` instead of `arm_openness_level`.
- `test_posture_frame_extractor.py`: assert `z` present per landmark (shared with the superseded doc's test plan).
- `test_coaching_service_posture.py`: confirm the new `[자세]` rule lines are present; confirm no fabricated interpretation when `head_alignment_level`/`power_zone_level`/`open_posture_level` are `"unknown"`.
- Frontend: `posture_timeline_test.dart` (new field parsing), `result_mapper_posture_test.dart` (each new `*Text()` mapping function's category → Korean label cases), a check that `analysis_detail.dart`'s posture grid renders 7 tiles with badge text (no digits/percent signs) when signal is sufficient.
- Manual: real-webcam validation of "상체 방향" and "머리 정렬" tiles, per the plan above.
