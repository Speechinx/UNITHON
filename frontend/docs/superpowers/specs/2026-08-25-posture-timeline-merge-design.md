# Posture Timeline Merge Design

> Companion doc: `frontend/docs/superpowers/plans/2026-08-24-posture-tracking-frontend.md` (original posture capture/upload/display implementation — this design revises the display part only)

## Background

The original posture tracking implementation added a standalone "자세 타임라인" section to `ResultPage`, rendered by `PostureTimeline` (small colored chips, one per 15-second window, colored by risk and labeled only with the window index). In manual testing this proved confusing: the chips carry no legend, aren't tappable, and show no numeric detail — unlike the existing voice risk timeline (`_RiskTimeline` + `_WindowDetailCard`), which is tappable and shows time range, risk label, score, and concrete `reasons` when a window is selected.

Investigation also confirmed that the voice risk analyzer (`risk_analyzer.py`) already uses `WINDOW_SIZE = 15` seconds — the same cadence as posture windows — so `window_index` values line up between the two pipelines in the common case (both start at 0 and advance by one every 15 seconds of recording time).

## Goal

Give the user real posture feedback (not just an unlabeled color) by merging posture data into the existing, already-working voice timeline interaction, instead of maintaining a second parallel timeline UI.

## Non-goals

- No backend changes — `/analyze`'s `posture.windows` payload already carries everything needed (`shoulder_tilt_avg_deg`, `shoulder_tilt_exceed_ratio`, `head_down_avg_deg`, `head_down_exceed_ratio`, `gesture_activity_level`, `reasons`, `signal_sufficient`).
- No combined single audio+posture risk score. Each signal stays independently displayed and independently labeled, per the existing project principle of not fabricating a combined subjective judgment.
- No small posture indicator dot/icon on the voice timeline chips themselves — the detail card is the single place posture is shown, to avoid duplicate UI surface for a hackathon-scope feature.

## Design

### 1. Remove the standalone posture timeline section

Delete the `_SectionCard(title: '자세 타임라인', ...)` block in `ResultPage.build()` (main.dart, currently ~line 1896-1937) that renders the old `PostureTimeline` widget and its "자세 분석 결과가 없습니다." empty state.

### 2. Extend `_WindowDetailCard` with an optional posture section

`_WindowDetailCard` currently renders the selected voice risk window's score/level/reasons/transcript. Add two new parameters: `bool hasPostureData` (true iff `_postureWindows.isNotEmpty` for the whole session) and `PostureWindow? postureWindow` (the window matching the selected index, or `null`). When building the card in `ResultPage`, look it up by matching the currently selected voice window's index against `_postureWindows`:

```dart
PostureWindow? _postureWindowForIndex(int index) {
  for (final window in _postureWindows) {
    if (window.windowIndex == index) {
      return window;
    }
  }
  return null;
}
```

Pass `_postureWindowForIndex(selectedWindowIndex)` into `_WindowDetailCard` at its call site.

Render logic inside `_WindowDetailCard`, appended after the existing reasons/transcript content:

- If `hasPostureData` is `false` → render nothing for posture (this session had no camera data at all; don't clutter every card with an irrelevant note).
- Else if `postureWindow == null` (no window uploaded for this specific index — e.g. a flush failed) → small muted line: "이 구간은 자세 데이터가 없습니다."
- Else if `!postureWindow.signalSufficient` → small muted line: "자세 신호 부족" (grey, same tone as the existing "신호 부족" language used elsewhere in the project).
- Else → a "자세 신호" subheading followed by:
  - 어깨 기울기: 평균 `{shoulderTiltAvgDeg}`도 (초과 구간 `{shoulderTiltExceedRatio*100}`%)
  - 고개 숙임: 평균 `{headDownAvgDeg}`도 (초과 구간 `{headDownExceedRatio*100}`%)
  - 제스처 활동성: 낮음/보통/높음 (map from `low`/`normal`/`high`; omit line entirely if `unknown`)
  - `reasons`가 비어있지 않으면 각 항목을 bullet로 표시; 비어있으면 근거 줄 자체를 생략 (음성 쪽 reasons 표시 패턴과 동일)

### 3. Trim `posture_timeline.dart` to just the model

Delete the `PostureTimeline` and `_PostureWindowChip` widget classes (no longer referenced anywhere after step 1). Keep and extend `PostureWindow`:

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
    required this.reasons,
  });

  final int windowIndex;
  final bool signalSufficient;
  final double shoulderTiltAvgDeg;
  final double shoulderTiltExceedRatio;
  final double headDownAvgDeg;
  final double headDownExceedRatio;
  final String gestureActivityLevel;
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
      reasons: (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
```

`main.dart`'s existing `_postureWindows` getter (parses `result['posture']['windows']`) is unchanged — it already maps to `PostureWindow.fromJson`.

`main.dart`'s `import 'posture_timeline.dart';` stays (still needed for the `PostureWindow` type); any import of the now-deleted `PostureTimeline` widget usage is removed along with the section in step 1.

## Data flow

Unchanged capture/upload pipeline (camera → 15s buffer → `POST /posture/window` → in-memory `PostureSessionStore` → merged into `POST /analyze` response under `posture.windows`, keyed by `window_index`). Only the *display* layer changes: instead of its own timeline, posture data is looked up per-index and folded into the voice detail card on tap.

## Error handling / edge cases

- Recording shorter than one posture flush (~15s): `_postureWindows` will be empty or have only a partial final window; per the rules above this renders nothing or "이 구간은 자세 데이터가 없습니다." — never a crash, matching the graceful-degradation principle already established for posture (`signal_sufficient: false`).
- Voice and posture window counts don't match exactly (e.g. last voice window got merged per `MIN_LAST_WINDOW`, but posture's final flush didn't merge): handled by the `postureWindow == null` fallback per index — no assumption that the two lists are the same length.
- Camera never granted this session: `_postureWindows` is empty for the whole session; per the design, the posture subsection is omitted entirely from every card (not shown as "부족" repeatedly for every window).

## Testing

- `frontend/test/posture_timeline_test.dart`: extend `PostureWindow.fromJson` tests to cover the three new fields (`shoulder_tilt_avg_deg`, `head_down_avg_deg`, `reasons`), including a default-missing-fields case (defaults to `0.0` / `[]`).
- `_WindowDetailCard`'s new posture section has no automated test, consistent with the existing project pattern for this file (private widget inside `main.dart`, verified manually). Manual verification: record ≥30s with camera permission granted, tap a window with `signal_sufficient=true` and confirm the posture subsection numbers match what the corresponding `/posture/window` response logged; tap a window with no posture data and confirm the "데이터 없음" fallback text appears without crashing.
