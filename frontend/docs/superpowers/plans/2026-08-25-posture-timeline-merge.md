# Posture Timeline Merge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the standalone, unlabeled "자세 타임라인" section on `ResultPage` and instead show posture feedback (shoulder tilt, head-down, gesture activity, reasons) inside the existing tappable voice window detail card, matched by shared 15-second `window_index`.

**Architecture:** Extend the `PostureWindow` model with the fields the UI needs (currently only exceed-ratios and gesture level are parsed). Add a lookup helper on `_ResultPageState` that finds the `PostureWindow` matching the selected voice window's index. Pass it into `_WindowDetailCard`, which grows a new optional "자세 신호" subsection. Delete the now-unused `PostureTimeline`/`_PostureWindowChip` widgets.

**Tech Stack:** Flutter Web, no new dependencies.

## Global Constraints

- No backend changes — `/analyze`'s `posture.windows` payload already includes every field this plan needs (confirmed against `pr_helper/app/schemas/analysis_response.py`'s `PostureWindow` model: `window_index`, `signal_sufficient`, `valid_frame_ratio`, `shoulder_tilt_avg_deg`, `shoulder_tilt_exceed_ratio`, `head_down_avg_deg`, `head_down_exceed_ratio`, `sway_std`, `gesture_activity_level`, `reasons`).
- Do not change the audio recording/posture capture pipeline (`startRecording`, `stopRecording`, `_startPostureCapture`, etc.) — this plan is display-only.
- No combined single audio+posture risk score — the two signals stay independently labeled, per the project's existing "measured fact only, no fabricated combined judgment" principle (see `pr_helper` `CoachingService` prompt rules 21-28-6).
- No posture indicator on the voice timeline chips (`_RiskTimeline`/`_PostureWindowChip` stays gone) — the detail card is the single place posture is shown.
- Match existing code style in `main.dart`: heavily broken-out multi-line formatting (one identifier/value per line in many places) is the prevailing style in this file — when editing existing blocks, preserve surrounding formatting rather than reflowing it.

---

## File Structure

- `frontend/lib/posture_timeline.dart` — modified. `PostureWindow` gains 3 fields; `PostureTimeline`/`_PostureWindowChip` classes deleted (Task 1 adds fields, Task 3 deletes the now-dead widget classes once nothing references them).
- `frontend/test/posture_timeline_test.dart` — modified. New test cases for the added fields.
- `frontend/lib/main.dart` — modified. Remove the standalone posture section; add posture lookup + rendering to `_WindowDetailCard` (Task 2).

---

### Task 1: Extend `PostureWindow` with the fields the detail card needs

**Files:**
- Modify: `frontend/lib/posture_timeline.dart`
- Test: `frontend/test/posture_timeline_test.dart`

**Interfaces:**
- Produces: `PostureWindow` gains `shoulderTiltAvgDeg` (double), `headDownAvgDeg` (double), `reasons` (List\<String\>), on top of the existing `windowIndex`, `signalSufficient`, `shoulderTiltExceedRatio`, `headDownExceedRatio`, `gestureActivityLevel`. Consumed by Task 2.

- [ ] **Step 1: Write the failing tests**

Add these two test cases to the existing `main()` block in `frontend/test/posture_timeline_test.dart` (after the existing two tests, before the closing `}`):

```dart
  test('fromJson parses shoulder/head avg degrees and reasons', () {
    final window = PostureWindow.fromJson({
      'window_index': 1,
      'signal_sufficient': true,
      'shoulder_tilt_avg_deg': 12.5,
      'shoulder_tilt_exceed_ratio': 0.4,
      'head_down_avg_deg': 65.0,
      'head_down_exceed_ratio': 0.1,
      'gesture_activity_level': 'normal',
      'reasons': ['어깨 기울어짐 40% 구간'],
    });

    expect(window.shoulderTiltAvgDeg, 12.5);
    expect(window.headDownAvgDeg, 65.0);
    expect(window.reasons, ['어깨 기울어짐 40% 구간']);
  });

  test(
    'fromJson defaults avg degree fields to 0.0 and reasons to empty list',
    () {
      final window = PostureWindow.fromJson({
        'window_index': 0,
        'signal_sufficient': false,
      });

      expect(window.shoulderTiltAvgDeg, 0.0);
      expect(window.headDownAvgDeg, 0.0);
      expect(window.reasons, <String>[]);
    },
  );
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && flutter test test/posture_timeline_test.dart`
Expected: FAIL — analysis error, e.g. `The getter 'shoulderTiltAvgDeg' isn't defined for the type 'PostureWindow'`.

- [ ] **Step 3: Write the implementation**

Replace the entire `PostureWindow` class in `frontend/lib/posture_timeline.dart` (the `class PostureWindow { ... }` block, lines 3-30 of the current file) with:

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
      reasons:
          (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
```

Leave the rest of the file (the `PostureTimeline` and `_PostureWindowChip` classes below it) untouched for now — they're deleted in Task 3, after `main.dart` stops using them.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && flutter test test/posture_timeline_test.dart`
Expected: PASS (4 tests: the 2 pre-existing plus the 2 new ones).

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/posture_timeline.dart frontend/test/posture_timeline_test.dart
git commit -m "feat: add shoulder/head avg degrees and reasons to PostureWindow"
```

---

### Task 2: Show posture data in the voice window detail card

**Files:**
- Modify: `frontend/lib/main.dart`

**Interfaces:**
- Consumes: `PostureWindow` (Task 1) — specifically `.windowIndex`, `.signalSufficient`, `.shoulderTiltAvgDeg`, `.shoulderTiltExceedRatio`, `.headDownAvgDeg`, `.headDownExceedRatio`, `.gestureActivityLevel`, `.reasons`.
- Produces: `_ResultPageState._postureWindowForIndex(int index) -> PostureWindow?`. `_WindowDetailCard` gains `required bool hasPostureData` and `required PostureWindow? postureWindow` parameters.

No automated test for this task — it's Flutter widget wiring inside `main.dart`, consistent with how the original posture display wiring (`ResultPage`/`_SectionCard` usage) was done in this codebase without a widget test. Verify manually in Step 7.

- [ ] **Step 1: Remove the standalone "자세 타임라인" section**

In `frontend/lib/main.dart`, find this block (currently at approximately lines 1892-1938 — the spacer + section right after the voice risk timeline's `_SectionCard` closes, and right before `if (selectedWindow != null) ...[`):

```dart
                        const SizedBox(
                          height: 16,
                        ),

                        // ==================================================
                        // 자세 타임라인
                        // ==================================================
                        _SectionCard(
                          title:
                              '자세 타임라인',
                          child:
                              Column(
                            crossAxisAlignment:
                                CrossAxisAlignment.start,
                            children: [
                              const Text(
                                '녹화 중 촬영된 자세 신호를 구간별로 보여줍니다.',
                                style:
                                    TextStyle(
                                  fontSize:
                                      12,
                                  color:
                                      Colors.black54,
                                  height:
                                      1.4,
                                ),
                              ),

                              const SizedBox(
                                height: 16,
                              ),

                              if (
                                  _postureWindows.isEmpty
                              )
                                const Text(
                                  '자세 분석 결과가 없습니다.',
                                )
                              else
                                PostureTimeline(
                                  windows:
                                      _postureWindows,
                                ),
                            ],
                          ),
                        ),

                        if (
                            selectedWindow !=
                            null
                        ) ...[
```

Replace it with just:

```dart
                        if (
                            selectedWindow !=
                            null
                        ) ...[
```

(The `if (selectedWindow != null) ...[` block that follows already opens with its own `SizedBox(height: 16)` before `_WindowDetailCard`, so spacing is preserved — no gap is lost.)

- [ ] **Step 2: Add the posture lookup helper**

Find the existing `_postureWindows` getter in `_ResultPageState`:

```dart
  List<PostureWindow> get _postureWindows {
    final posture =
        widget.result['posture'];

    if (posture is! Map<String, dynamic>) {
      return [];
    }

    final windows =
        posture['windows'];

    if (windows is! List) {
      return [];
    }

    return windows
        .whereType<Map<String, dynamic>>()
        .map(PostureWindow.fromJson)
        .toList();
  }
```

Add this new method directly after its closing `}`:

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

- [ ] **Step 3: Pass posture data into the `_WindowDetailCard` call site**

Find:

```dart
                          _WindowDetailCard(
                            window: selectedWindow,
                            showTranscriptFull:
                                showSelectedTranscriptFull,
                            onToggleTranscript: () {
                              setState(() {
                                showSelectedTranscriptFull =
                                    !showSelectedTranscriptFull;
                              });
                            },
                          ),
```

Replace it with:

```dart
                          _WindowDetailCard(
                            window: selectedWindow,
                            hasPostureData:
                                _postureWindows.isNotEmpty,
                            postureWindow:
                                _postureWindowForIndex(
                              selectedWindowIndex,
                            ),
                            showTranscriptFull:
                                showSelectedTranscriptFull,
                            onToggleTranscript: () {
                              setState(() {
                                showSelectedTranscriptFull =
                                    !showSelectedTranscriptFull;
                              });
                            },
                          ),
```

- [ ] **Step 4: Add the new fields and constructor parameters to `_WindowDetailCard`**

Find:

```dart
class _WindowDetailCard
    extends StatelessWidget {
  final Map<String, dynamic> window;

  final bool showTranscriptFull;

  final VoidCallback onToggleTranscript;

  const _WindowDetailCard({
    required this.window,
    required this.showTranscriptFull,
    required this.onToggleTranscript,
  });
```

Replace it with:

```dart
class _WindowDetailCard
    extends StatelessWidget {
  final Map<String, dynamic> window;

  final bool hasPostureData;

  final PostureWindow? postureWindow;

  final bool showTranscriptFull;

  final VoidCallback onToggleTranscript;

  const _WindowDetailCard({
    required this.window,
    required this.hasPostureData,
    required this.postureWindow,
    required this.showTranscriptFull,
    required this.onToggleTranscript,
  });
```

- [ ] **Step 5: Render the "자세 신호" subsection**

Find this block inside `_WindowDetailCard.build()` — the end of the reasons list rendering, right before the transcript section comment:

```dart
                );
              },
            ),

          // ==============================
          // 해당 15초 구간 발표 내용
          // ==============================

          if (transcript.isNotEmpty) ...[
```

Replace it with (this inserts the new posture block between the reasons list and the transcript section):

```dart
                );
              },
            ),

          // ==============================
          // 자세 신호
          // ==============================

          if (hasPostureData) ...[
            const SizedBox(
              height: 18,
            ),

            const Divider(),

            const SizedBox(
              height: 10,
            ),

            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '자세 신호',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey.shade700,
                ),
              ),
            ),

            const SizedBox(
              height: 10,
            ),

            if (postureWindow == null)
              const Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '이 구간은 자세 데이터가 없습니다.',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.black54,
                  ),
                ),
              )
            else if (!postureWindow!.signalSufficient)
              const Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '자세 신호 부족',
                  style: TextStyle(
                    fontSize: 13,
                    color: Colors.black54,
                  ),
                ),
              )
            else ...[
              Row(
                children: [
                  Expanded(
                    child: _DetailItem(
                      label: '어깨 기울기',
                      value:
                          '평균 ${postureWindow!.shoulderTiltAvgDeg.toStringAsFixed(1)}도 '
                          '· 초과 ${(postureWindow!.shoulderTiltExceedRatio * 100).toStringAsFixed(0)}%',
                    ),
                  ),

                  const SizedBox(
                    width: 12,
                  ),

                  Expanded(
                    child: _DetailItem(
                      label: '고개 숙임',
                      value:
                          '평균 ${postureWindow!.headDownAvgDeg.toStringAsFixed(1)}도 '
                          '· 초과 ${(postureWindow!.headDownExceedRatio * 100).toStringAsFixed(0)}%',
                    ),
                  ),
                ],
              ),

              const SizedBox(
                height: 12,
              ),

              _DetailItem(
                label: '제스처 활동성',
                value: _gestureActivityText(
                  postureWindow!.gestureActivityLevel,
                ),
              ),

              if (postureWindow!.reasons.isNotEmpty) ...[
                const SizedBox(
                  height: 12,
                ),

                ...postureWindow!.reasons.map(
                  (reason) {
                    return Padding(
                      padding: const EdgeInsets.only(
                        bottom: 7,
                      ),
                      child: Row(
                        crossAxisAlignment:
                            CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '• ',
                            style: TextStyle(
                              fontSize: 13,
                            ),
                          ),

                          Expanded(
                            child: Text(
                              _replaceBackendTerms(
                                reason,
                              ),
                              style: const TextStyle(
                                fontSize: 13,
                                height: 1.4,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
              ],
            ],
          ],

          // ==============================
          // 해당 15초 구간 발표 내용
          // ==============================

          if (transcript.isNotEmpty) ...[
```

- [ ] **Step 6: Add the `_gestureActivityText` helper**

Find the `_riskLabel` function:

```dart
String _riskLabel(
  String level,
) {
  switch (level) {
    case 'high':
      return '주의';

    case 'medium':
      return '보통';

    case 'low':
      return '안정';

    default:
      return '분석 없음';
  }
}
```

Add this new function directly after its closing `}`:

```dart

String _gestureActivityText(
  String level,
) {
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
```

- [ ] **Step 7: Manual verification**

Run: `cd frontend && flutter run -d chrome --web-port 5173`

With the backend running (`uvicorn app.main:app --reload --reload-dir app` in `pr_helper`, `models/pose_landmarker_lite.task` present):

1. Record ≥30 seconds with camera permission granted. Stop, wait for the result screen.
2. Confirm there is no separate "자세 타임라인" section anymore — only the single voice timeline.
3. Tap a voice window chip whose corresponding posture window has `signal_sufficient: true` (check the backend's `/posture/window` response logs to know which index). Confirm the detail card now shows a "자세 신호" subsection with 어깨 기울기/고개 숙임/제스처 활동성 and, if applicable, bullet reasons.
4. Tap a window index beyond what posture data covers (e.g. the very last, very short window). Confirm it shows "이 구간은 자세 데이터가 없습니다." instead of crashing.
5. Record a presentation under 15 seconds (or use the file-upload path, `pickAndAnalyzeWav`, which never attaches `session_id`). Confirm the detail card renders with no "자세 신호" subsection at all (since `hasPostureData` is false) — no crash, no empty grey box.

- [ ] **Step 8: Commit**

```bash
git add frontend/lib/main.dart
git commit -m "feat: show posture signals in the voice window detail card"
```

---

### Task 3: Delete the now-unused posture timeline widget

**Files:**
- Modify: `frontend/lib/posture_timeline.dart`

**Interfaces:**
- None — this is dead code removal. `PostureWindow` (Task 1) is untouched.

- [ ] **Step 1: Confirm nothing still references the widget**

Run: `cd frontend && grep -rn "PostureTimeline(" lib/`
Expected: no output (Task 2 removed the only call site).

- [ ] **Step 2: Delete the unused classes**

In `frontend/lib/posture_timeline.dart`, delete the `PostureTimeline` and `_PostureWindowChip` classes (everything from `class PostureTimeline extends StatelessWidget {` to the end of the file), leaving only the `import 'package:flutter/material.dart';` line and the `PostureWindow` class from Task 1.

The full resulting file:

```dart
import 'package:flutter/material.dart';

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
      reasons:
          (json['reasons'] as List?)?.whereType<String>().toList() ?? [],
    );
  }
}
```

Note `import 'package:flutter/material.dart';` is kept even though nothing in this trimmed file uses it directly beyond... actually `PostureWindow` itself has no Flutter dependency. Remove the import too — the final file should be just the `PostureWindow` class with no imports.

- [ ] **Step 3: Run static analysis and the full test suite**

Run: `cd frontend && flutter analyze && flutter test`
Expected: `flutter analyze` reports no errors (unused-import/unused-element warnings gone); all tests pass, including `test/posture_timeline_test.dart`'s 4 tests.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/posture_timeline.dart
git commit -m "refactor: remove unused PostureTimeline widget"
```
