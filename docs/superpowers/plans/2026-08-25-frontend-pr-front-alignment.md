# 프론트엔드 pr_front 이식 + 자세 캡처 통합 + 반응 영상 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `frontend/lib`을 pr_front(`serim_front` 브랜치)의 화면 분리형 디자인 시스템으로 교체하면서, 기존에만 존재하던 실동작 기능(오디오 녹음, 카메라 자세 캡처·업로드, 자세 신호 상세 표시, 히스토리)을 새 구조에 다시 연결하고, `avatar_state`에 따라 반응 영상을 재생하는 컴포넌트를 추가한다.

**Architecture:** pr_front의 `screens/`·`widgets/`·`models/`·`theme/`·`utils/` 구조를 그대로 들여오고, 기존 카메라 자세 캡처 로직은 `lib/posture/`로 옮긴다. `lib/main.dart`의 `AppShell`이 pr_front의 상태 머신(화면 전환)에 자세 캡처 시작/정지/업로드를 얹는다. 반응 영상은 `video_player`로 재생하는 신규 위젯이 자세 이모지 아바타를 대체하되, 영상이 없는 상태에는 기존 이모지 아바타로 폴백한다.

**Tech Stack:** Flutter 3.47.1 / Dart 3.13.1 (web 타깃), `camera`, `image`, `record`, `http`, `shared_preferences`, `file_picker`, 신규 `video_player`. 백엔드는 기존 FastAPI `/analyze`, `/posture/window` 엔드포인트를 그대로 사용 (변경 없음).

## Global Constraints

- 패키지 이름은 `pr_front` 그대로 유지한다 (이미 `pubspec.yaml`의 `name:` 및 기존 테스트의 `package:pr_front/...` import가 이 이름을 전제한다).
- UI 최대 폭은 430px 컨테이너(`BoxConstraints(maxWidth: 430)`)로 고정한다 — pr_front 전 화면이 이 규칙을 따른다.
- 색상은 반드시 `lib/theme/app_colors.dart`의 `AppColors` 토큰만 사용한다 (하드코딩된 `Color(...)` 금지) — pr_front 컨벤션.
- 백엔드 엔드포인트는 `http://127.0.0.1:8000`에 고정, `/analyze`는 WAV 파일만 허용, `/posture/window`는 세션당 15초 윈도우 단위로 업로드한다. 새 엔드포인트를 만들지 않는다.
- `avatar_state`는 `focused` / `engaged` / `confused` / `bored` / `unknown` 중 하나이며 백엔드가 이미 이 값을 내려준다 (`backend/app/services/posture_analyzer.py`, 변경 없음).
- 반응 영상은 Flutter Web(Chrome) 재생을 위해 H.264 + yuv420p + `+faststart`로 인코딩한 mp4만 사용한다. `bored` 상태는 아직 영상이 없으므로 이모지 아바타로 폴백한다.
- 모든 코드/주석/UI 문구는 기존 저장소 관례대로 한국어를 사용한다.

---

## Task 1: 반응 영상 자산 준비 + `video_player` 의존성

**Files:**
- Create: `frontend/assets/reactions/engaged.mp4`
- Create: `frontend/assets/reactions/focused.mp4`
- Create: `frontend/assets/reactions/confused.mp4`
- Modify: `frontend/pubspec.yaml`

**Interfaces:**
- Produces: `assets/reactions/{engaged,focused,confused}.mp4` — Task 5(`reaction_avatar.dart`)가 이 경로 문자열을 그대로 참조한다.

- [ ] **Step 1: `pr_mp4` 저장소를 스크래치 공간에 클론**

```bash
mkdir -p /tmp/pr_mp4_src && cd /tmp/pr_mp4_src && \
  rm -rf pr_mp4 && \
  git clone --depth 1 https://github.com/2026-UNITHON-PRCoach/pr_mp4.git
```

Expected: `pr_mp4/assets/reactions/공감.mp4`, `집중.mp4`, `혼란.mp4` 세 파일이 존재.

- [ ] **Step 2: 세 영상을 H.264 + yuv420p + faststart로 재인코딩하여 프로젝트에 복사**

```bash
mkdir -p "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend/assets/reactions"
SRC=/tmp/pr_mp4_src/pr_mp4/assets/reactions
DST="/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend/assets/reactions"

ffmpeg -y -i "$SRC/공감.mp4" -c:v libx264 -profile:v high -pix_fmt yuv420p \
  -crf 20 -preset medium -c:a aac -b:a 128k -movflags +faststart \
  "$DST/engaged.mp4"

ffmpeg -y -i "$SRC/집중.mp4" -c:v libx264 -profile:v high -pix_fmt yuv420p \
  -crf 20 -preset medium -c:a aac -b:a 128k -movflags +faststart \
  "$DST/focused.mp4"

ffmpeg -y -i "$SRC/혼란.mp4" -c:v libx264 -profile:v high -pix_fmt yuv420p \
  -crf 20 -preset medium -c:a aac -b:a 128k -movflags +faststart \
  "$DST/confused.mp4"
```

Expected: `ffmpeg`가 각 파일에 대해 `frame=... muxing overhead: ...`로 정상 종료 (exit code 0), `frontend/assets/reactions/`에 `engaged.mp4`/`focused.mp4`/`confused.mp4` 세 파일 생성.

- [ ] **Step 3: 재인코딩 결과가 H.264인지 확인**

```bash
for f in engaged focused confused; do
  ffprobe -v error -select_streams v:0 -show_entries stream=codec_name \
    -of default=noprint_wrappers=1 \
    "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend/assets/reactions/$f.mp4"
done
```

Expected: 세 줄 모두 `codec_name=h264`.

- [ ] **Step 4: `pubspec.yaml`에 asset 등록**

`frontend/pubspec.yaml`의 `flutter:` 섹션에서 아래 주석 블록을 찾는다:

```yaml
  # To add assets to your application, add an assets section, like this:
  # assets:
  #   - images/a_dot_burr.jpeg
  #   - images/a_dot_ham.jpeg
```

이 블록 바로 아래에 다음을 추가한다 (주석은 그대로 둔다):

```yaml
  assets:
    - assets/reactions/
```

- [ ] **Step 5: `video_player` 의존성 추가**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter pub add video_player
```

Expected: 명령이 성공하고 `pubspec.yaml`의 `dependencies:` 아래에 `video_player: ^<resolved-version>` 줄이 추가됨. `pubspec.lock`도 갱신됨.

- [ ] **Step 6: `flutter pub get`으로 의존성 해석 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter pub get
```

Expected: `Got dependencies!` 출력, 에러 없음.

- [ ] **Step 7: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add assets/reactions pubspec.yaml pubspec.lock && \
  git commit -m "feat(frontend): add avatar reaction video assets + video_player dependency"
```

---

## Task 2: 자세 캡처 유틸리티 모듈을 `lib/posture/`로 이동

**Files:**
- Modify (move): `frontend/lib/posture_capture_buffer.dart` → `frontend/lib/posture/posture_capture_buffer.dart`
- Modify (move): `frontend/lib/posture_timeline.dart` → `frontend/lib/posture/posture_timeline.dart`
- Modify (move): `frontend/lib/posture_window_uploader.dart` → `frontend/lib/posture/posture_window_uploader.dart`
- Modify (move): `frontend/lib/posture_blob_cleanup_web.dart` → `frontend/lib/posture/posture_blob_cleanup_web.dart`
- Modify (move): `frontend/lib/posture_blob_cleanup_stub.dart` → `frontend/lib/posture/posture_blob_cleanup_stub.dart`
- Modify: `frontend/test/posture_capture_buffer_test.dart`
- Modify: `frontend/test/posture_timeline_test.dart`
- Modify: `frontend/test/posture_window_uploader_test.dart`

**Interfaces:**
- Produces: `package:pr_front/posture/posture_capture_buffer.dart` (`PostureCaptureBuffer`), `package:pr_front/posture/posture_timeline.dart` (`PostureWindow`, `PostureWindow.fromJson`), `package:pr_front/posture/posture_window_uploader.dart` (`PostureWindowUploader`) — Task 6(`result_mapper.dart`), Task 10(`main.dart`)가 이 경로로 import한다.

이 다섯 파일은 다른 lib 파일을 import하지 않는 자기완결형 모듈이므로 내용 변경 없이 경로만 옮긴다.

- [ ] **Step 1: 디렉터리 생성 및 `git mv`로 이동**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend"
mkdir -p lib/posture
git mv lib/posture_capture_buffer.dart lib/posture/posture_capture_buffer.dart
git mv lib/posture_timeline.dart lib/posture/posture_timeline.dart
git mv lib/posture_window_uploader.dart lib/posture/posture_window_uploader.dart
git mv lib/posture_blob_cleanup_web.dart lib/posture/posture_blob_cleanup_web.dart
git mv lib/posture_blob_cleanup_stub.dart lib/posture/posture_blob_cleanup_stub.dart
```

- [ ] **Step 2: 테스트 import 경로 수정**

`frontend/test/posture_capture_buffer_test.dart`에서:

```dart
import 'package:pr_front/posture_capture_buffer.dart';
```

를

```dart
import 'package:pr_front/posture/posture_capture_buffer.dart';
```

로 바꾼다.

`frontend/test/posture_timeline_test.dart`에서:

```dart
import 'package:pr_front/posture_timeline.dart';
```

를

```dart
import 'package:pr_front/posture/posture_timeline.dart';
```

로 바꾼다.

`frontend/test/posture_window_uploader_test.dart`에서:

```dart
import 'package:pr_front/posture_window_uploader.dart';
```

를

```dart
import 'package:pr_front/posture/posture_window_uploader.dart';
```

로 바꾼다.

- [ ] **Step 3: 테스트 실행**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter test \
  test/posture_capture_buffer_test.dart \
  test/posture_timeline_test.dart \
  test/posture_window_uploader_test.dart
```

Expected: `All tests passed!`

- [ ] **Step 4: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/posture test/posture_capture_buffer_test.dart \
    test/posture_timeline_test.dart test/posture_window_uploader_test.dart && \
  git commit -m "refactor(frontend): move posture capture utilities into lib/posture/"
```

---

## Task 3: `avatar_widget.dart`를 `lib/posture/`로 이동하고 상태 매핑을 백엔드 값에 맞게 수정

**Files:**
- Modify (move): `frontend/lib/avatar_widget.dart` → `frontend/lib/posture/avatar_widget.dart`
- Modify: `frontend/test/avatar_widget_test.dart`

**Interfaces:**
- Consumes: 없음 (StatelessWidget, `state: String` 파라미터만 받음)
- Produces: `package:pr_front/posture/avatar_widget.dart`의 `AvatarWidget({required String state})` — `bored`/`unknown`/그 외 미인식 문자열(→idle 폴백)을 이모지로 렌더링. Task 5(`reaction_avatar.dart`)가 폴백 위젯으로 이 위젯을 사용한다.

**배경:** 기존 위젯은 `idle`/`good`/`bad`/`unknown` 4개 키만 처리하는데, 백엔드가 실제로 보내는 값은 `focused`/`engaged`/`confused`/`bored`/`unknown`이라 지금까지 자세 캡처 중에도 아바타가 항상 idle(💤)로만 보이는 버그가 있었다. 이번에 `engaged`/`focused`/`confused`는 Task 5의 영상으로 대체되므로, 이 위젯은 `bored`/`unknown`/`idle`(로컬 초기값) 세 가지만 이모지로 표시하면 된다.

- [ ] **Step 1: 이동**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git mv lib/avatar_widget.dart lib/posture/avatar_widget.dart
```

- [ ] **Step 2: 실패하는 테스트로 새 상태 집합 정의**

`frontend/test/avatar_widget_test.dart`를 다음 내용으로 전체 교체:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture/avatar_widget.dart';

void main() {
  testWidgets('shows idle emoji by default', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'idle')),
    );

    expect(find.text('💤'), findsOneWidget);
  });

  testWidgets('shows bored emoji for bored state', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'bored')),
    );

    expect(find.text('😴'), findsOneWidget);
  });

  testWidgets('shows unknown emoji for unknown state', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'unknown')),
    );

    expect(find.text('❔'), findsOneWidget);
  });

  testWidgets('falls back to idle emoji for an unrecognized state string', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'nonsense')),
    );

    expect(find.text('💤'), findsOneWidget);
  });
}
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/avatar_widget_test.dart
```

Expected: FAIL — `import 'package:pr_front/posture/avatar_widget.dart'`는 이미 이동한 경로라 임포트는 되지만, `'bored'` 상태에 대해 위젯이 아직 `'💤'`(idle 폴백)을 렌더링하므로 `find.text('😴')` 매칭 실패.

- [ ] **Step 4: `lib/posture/avatar_widget.dart` 상태 매핑 수정**

`frontend/lib/posture/avatar_widget.dart`를 다음 내용으로 전체 교체:

```dart
import 'package:flutter/material.dart';

class AvatarWidget extends StatelessWidget {
  const AvatarWidget({
    super.key,
    required this.state,
  });

  final String state;

  static const Map<String, String> _emojiByState = {
    'idle': '💤',
    'bored': '😴',
    'unknown': '❔',
  };

  static const Map<String, Color> _colorByState = {
    'idle': Colors.grey,
    'bored': Colors.orange,
    'unknown': Colors.grey,
  };

  @override
  Widget build(BuildContext context) {
    final emoji = _emojiByState[state] ?? _emojiByState['idle']!;
    final color = _colorByState[state] ?? _colorByState['idle']!;

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      transitionBuilder: (child, animation) {
        return ScaleTransition(scale: animation, child: child);
      },
      child: Container(
        key: ValueKey(state),
        width: 96,
        height: 96,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withValues(alpha: 0.12),
          border: Border.all(color: color, width: 2),
        ),
        alignment: Alignment.center,
        child: Text(
          emoji,
          style: const TextStyle(fontSize: 48),
        ),
      ),
    );
  }
}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/avatar_widget_test.dart
```

Expected: `All tests passed!`

- [ ] **Step 6: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/posture/avatar_widget.dart test/avatar_widget_test.dart && \
  git commit -m "fix(frontend): match avatar_widget fallback states to backend avatar_state values"
```

---

## Task 4: pr_front 디자인 시스템 기반 파일 추가 (models / theme / widgets)

**Files:**
- Create: `frontend/lib/models/app_models.dart`
- Create: `frontend/lib/theme/app_colors.dart`
- Create: `frontend/lib/widgets/bottom_nav.dart`
- Create: `frontend/lib/widgets/common.dart`
- Create: `frontend/lib/widgets/status_bar.dart`

**Interfaces:**
- Produces:
  - `AppTab` (`home`/`history`/`mypage`), `HomeScreen` (`start`/`recording`/`loading`/`summary`/`detail`), `RecordMode` (`voice`/`voiceMotion`), `DetailTab`, `SegmentLevel`(`.label`/`.color`/`.badgeBg`/`.badgeFg`)
  - `Segment` — 생성자 파라미터: `level, time, flex, scoreLabel, score, scoreColor, speed, tone, pause, filler, repeat, signals, script, postureAvailable, postureSignalSufficient, shoulderTilt, headDown, torsoLean, armOpenness, gestureActivity, postureReasons`
  - `HistoryItem(date, badge, title, detail)`, `MetricData(label, value, sub, icon, iconColor)`
  - `AppColors` (violet/gray/amber/red/green 팔레트 상수)
  - `BottomNav({tab, onTab})`, `AppCard`, `StatusBadge`, `OverallCard`, `MetricsCard`, `FakeStatusBar`
- Consumes: 없음 (최하위 레이어)

이 중 `theme/app_colors.dart`, `widgets/bottom_nav.dart`, `widgets/common.dart`, `widgets/status_bar.dart`는 pr_front 원본과 100% 동일하게 생성한다. `models/app_models.dart`만 `Segment`에 자세 필드를 추가한다.

- [ ] **Step 1: `lib/theme/app_colors.dart` 생성**

```dart
import 'package:flutter/material.dart';

/// Tailwind 팔레트를 그대로 옮긴 색상 토큰.
class AppColors {
  AppColors._();

  // Violet (primary)
  static const violet50 = Color(0xFFF5F3FF);
  static const violet100 = Color(0xFFEDE9FE);
  static const violet300 = Color(0xFFC4B5FD);
  static const violet600 = Color(0xFF7C3AED);
  static const violet700 = Color(0xFF6D28D9);
  static const violet800 = Color(0xFF5B21B6);

  // Neutrals
  static const white = Color(0xFFFFFFFF);
  static const gray50 = Color(0xFFF9FAFB);
  static const gray100 = Color(0xFFF3F4F6);
  static const gray200 = Color(0xFFE5E7EB);
  static const gray300 = Color(0xFFD1D5DB);
  static const gray400 = Color(0xFF9CA3AF);
  static const gray500 = Color(0xFF6B7280);
  static const gray600 = Color(0xFF4B5563);
  static const gray700 = Color(0xFF374151);
  static const gray800 = Color(0xFF1F2937);
  static const gray900 = Color(0xFF111827);

  // Amber
  static const amber50 = Color(0xFFFFFBEB);
  static const amber100 = Color(0xFFFEF3C7);
  static const amber500 = Color(0xFFF59E0B);
  static const amber600 = Color(0xFFD97706);
  static const amber700 = Color(0xFFB45309);

  // Red
  static const red50 = Color(0xFFFEF2F2);
  static const red100 = Color(0xFFFEE2E2);
  static const red200 = Color(0xFFFECACA);
  static const red500 = Color(0xFFEF4444);
  static const red600 = Color(0xFFDC2626);
  static const red700 = Color(0xFFB91C1C);

  // Green
  static const green50 = Color(0xFFF0FDF4);
  static const green100 = Color(0xFFDCFCE7);
  static const green400 = Color(0xFF4ADE80);
  static const green500 = Color(0xFF22C55E);
  static const green600 = Color(0xFF16A34A);
  static const green700 = Color(0xFF15803D);
  static const green800 = Color(0xFF166534);
  static const emerald500 = Color(0xFF10B981);
}
```

- [ ] **Step 2: `lib/models/app_models.dart` 생성 (Segment에 자세 필드 추가)**

```dart
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

enum AppTab { home, history, mypage }

enum HomeScreen { start, recording, loading, summary, detail }

enum RecordMode { voice, voiceMotion }

enum DetailTab { flow, improve, script }

enum SegmentLevel { stable, caution, danger }

extension SegmentLevelX on SegmentLevel {
  String get label => switch (this) {
        SegmentLevel.stable => '안정',
        SegmentLevel.caution => '주의',
        SegmentLevel.danger => '위험',
      };

  Color get color => switch (this) {
        SegmentLevel.stable => AppColors.green500,
        SegmentLevel.caution => AppColors.amber500,
        SegmentLevel.danger => AppColors.red500,
      };

  Color get badgeBg => switch (this) {
        SegmentLevel.stable => AppColors.green100,
        SegmentLevel.caution => AppColors.amber100,
        SegmentLevel.danger => AppColors.red100,
      };

  Color get badgeFg => switch (this) {
        SegmentLevel.stable => AppColors.green700,
        SegmentLevel.caution => AppColors.amber700,
        SegmentLevel.danger => AppColors.red600,
      };
}

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
    required this.armOpenness,
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
  final String armOpenness;
  final String gestureActivity;
  final List<String> postureReasons;
}

class HistoryItem {
  const HistoryItem({
    required this.date,
    required this.badge,
    required this.title,
    required this.detail,
  });

  final String date;
  final String badge;
  final String title;
  final String detail;
}

class MetricData {
  const MetricData({
    required this.label,
    required this.value,
    required this.sub,
    required this.icon,
    required this.iconColor,
  });

  final String label;
  final String value;
  final String sub;
  final IconData icon;
  final Color iconColor;
}
```

- [ ] **Step 3: `lib/widgets/bottom_nav.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

class BottomNav extends StatelessWidget {
  const BottomNav({super.key, required this.tab, required this.onTab});

  final AppTab tab;
  final ValueChanged<AppTab> onTab;

  static const _items = <(AppTab, String, IconData)>[
    (AppTab.home, '홈', Icons.mic_none),
    (AppTab.history, '기록', Icons.menu),
    (AppTab.mypage, '마이페이지', Icons.person_outline),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.white,
        border: Border(top: BorderSide(color: AppColors.gray100)),
      ),
      child: Row(
        children: [
          for (final (id, label, icon) in _items)
            Expanded(
              child: InkWell(
                onTap: () => onTab(id),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Column(
                    children: [
                      Icon(
                        icon,
                        size: 22,
                        color: tab == id ? AppColors.violet600 : AppColors.gray400,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        label,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: tab == id ? AppColors.violet600 : AppColors.gray400,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: `lib/widgets/common.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

/// 흰 배경 + 얇은 테두리 + 부드러운 그림자 카드 (bg-white border rounded-2xl shadow-sm)
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.color = AppColors.white,
    this.borderColor = AppColors.gray100,
    this.radius = 16,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color color;
  final Color borderColor;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(color: borderColor),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0D000000),
            blurRadius: 2,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: child,
    );
  }
}

/// 라운드 알약 형태의 상태 배지
class StatusBadge extends StatelessWidget {
  const StatusBadge({
    super.key,
    required this.label,
    required this.background,
    required this.foreground,
  });

  final String label;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: foreground,
        ),
      ),
    );
  }
}

/// 종합 분석 평가 카드 (요약/상세 화면 공통)
class OverallCard extends StatelessWidget {
  const OverallCard({super.key, required this.summary, required this.level});

  final String summary;
  final SegmentLevel level;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Expanded(
                child: Text(
                  '종합 분석 평가',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
              ),
              StatusBadge(
                label: level.label,
                background: level.badgeBg,
                foreground: level.badgeFg,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            summary,
            style: const TextStyle(
              fontSize: 12,
              height: 1.6,
              color: AppColors.gray600,
            ),
          ),
        ],
      ),
    );
  }
}

/// 지표별 분석 상세 카드 (2열 그리드)
class MetricsCard extends StatelessWidget {
  const MetricsCard({super.key, required this.metrics, this.footer});

  final List<MetricData> metrics;
  final Widget? footer;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '지표별 분석 상세',
            style: TextStyle(
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.gray900,
            ),
          ),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.85,
            children: [
              for (final m in metrics)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.gray50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            m.label,
                            style: const TextStyle(
                              fontSize: 12,
                              color: AppColors.gray500,
                            ),
                          ),
                          Icon(m.icon, size: 16, color: m.iconColor),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        m.value,
                        style: const TextStyle(
                          fontSize: 17,
                          fontWeight: FontWeight.bold,
                          color: AppColors.gray900,
                        ),
                      ),
                      Text(
                        m.sub,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.gray400,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          if (footer != null) ...[
            const SizedBox(height: 16),
            Center(child: footer!),
          ],
        ],
      ),
    );
  }
}
```

- [ ] **Step 5: `lib/widgets/status_bar.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// 목업 상태 바 (9:41 · 신호 · 와이파이 · 배터리)
class FakeStatusBar extends StatelessWidget {
  const FakeStatusBar({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 16, right: 16, top: 12, bottom: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            '9:41',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.gray800,
            ),
          ),
          Row(
            children: [
              const _SignalBars(),
              const SizedBox(width: 4),
              const Icon(Icons.wifi, size: 14, color: AppColors.gray800),
              const SizedBox(width: 4),
              _battery(),
            ],
          ),
        ],
      ),
    );
  }

  Widget _battery() {
    return Row(
      children: [
        Container(
          width: 24,
          height: 12,
          padding: const EdgeInsets.all(1.5),
          decoration: BoxDecoration(
            border: Border.all(color: AppColors.gray700),
            borderRadius: BorderRadius.circular(3),
          ),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.gray800,
              borderRadius: BorderRadius.circular(1.5),
            ),
          ),
        ),
        const SizedBox(width: 1),
        Container(
          width: 2,
          height: 5,
          decoration: const BoxDecoration(
            color: AppColors.gray700,
            borderRadius: BorderRadius.horizontal(right: Radius.circular(2)),
          ),
        ),
      ],
    );
  }
}

class _SignalBars extends StatelessWidget {
  const _SignalBars();

  @override
  Widget build(BuildContext context) {
    const heights = [5.0, 7.0, 9.0, 11.0];
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        for (final h in heights)
          Container(
            width: 3,
            height: h,
            margin: const EdgeInsets.only(left: 1.5),
            decoration: BoxDecoration(
              color: AppColors.gray800,
              borderRadius: BorderRadius.circular(1),
            ),
          ),
      ],
    );
  }
}
```

- [ ] **Step 6: 정적 분석으로 컴파일 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter analyze lib/models lib/theme lib/widgets
```

Expected: `No issues found!` (다른 화면에서 아직 이 파일들을 안 쓰므로 unused-import 등 경고 없이 깨끗해야 한다).

- [ ] **Step 7: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/models lib/theme lib/widgets && \
  git commit -m "feat(frontend): add pr_front design system foundation (models/theme/widgets)"
```

---

## Task 5: 반응 영상 위젯 `posture/reaction_avatar.dart`

**Files:**
- Create: `frontend/lib/posture/reaction_avatar.dart`
- Create: `frontend/test/reaction_avatar_test.dart`

**Interfaces:**
- Consumes: Task 1의 `assets/reactions/{engaged,focused,confused}.mp4`, Task 3의 `AvatarWidget({required String state})`
- Produces: `reactionAssetForState(String state) -> String?`, `ReactionAvatar({required String state, double size = 96})` — Task 8(`home_recording.dart`)이 이 위젯을 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성 (순수 매핑 함수)**

`frontend/test/reaction_avatar_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/posture/reaction_avatar.dart';

void main() {
  test('returns the asset path for states that have a reaction video', () {
    expect(reactionAssetForState('engaged'), 'assets/reactions/engaged.mp4');
    expect(reactionAssetForState('focused'), 'assets/reactions/focused.mp4');
    expect(reactionAssetForState('confused'), 'assets/reactions/confused.mp4');
  });

  test('returns null for states without a reaction video', () {
    expect(reactionAssetForState('bored'), null);
    expect(reactionAssetForState('unknown'), null);
    expect(reactionAssetForState('idle'), null);
    expect(reactionAssetForState('nonsense'), null);
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/reaction_avatar_test.dart
```

Expected: FAIL — `lib/posture/reaction_avatar.dart` 파일이 없어 컴파일 에러.

- [ ] **Step 3: `lib/posture/reaction_avatar.dart` 구현**

```dart
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import 'avatar_widget.dart';

/// avatar_state별 반응 영상 asset 경로. 영상이 없는 상태(`bored`)는
/// 매핑에서 제외되어 [AvatarWidget] 이모지 폴백으로 처리된다.
const Map<String, String> reactionVideoAssets = {
  'engaged': 'assets/reactions/engaged.mp4',
  'focused': 'assets/reactions/focused.mp4',
  'confused': 'assets/reactions/confused.mp4',
};

String? reactionAssetForState(String state) {
  return reactionVideoAssets[state];
}

/// 자세 상태(avatar_state)에 따라 반응 영상을 루프 재생하는 위젯.
/// 반응 영상이 없는 상태거나 로딩 중이면 [AvatarWidget] 이모지로 폴백한다.
class ReactionAvatar extends StatefulWidget {
  const ReactionAvatar({
    super.key,
    required this.state,
    this.size = 96,
  });

  final String state;
  final double size;

  @override
  State<ReactionAvatar> createState() => _ReactionAvatarState();
}

class _ReactionAvatarState extends State<ReactionAvatar> {
  VideoPlayerController? _controller;
  String? _loadedAsset;

  @override
  void initState() {
    super.initState();
    _syncController();
  }

  @override
  void didUpdateWidget(covariant ReactionAvatar oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (oldWidget.state != widget.state) {
      _syncController();
    }
  }

  void _syncController() {
    final asset = reactionAssetForState(widget.state);

    if (asset == _loadedAsset) {
      return;
    }

    final previous = _controller;
    _controller = null;
    _loadedAsset = asset;
    previous?.dispose();

    if (asset == null) {
      setState(() {});
      return;
    }

    final controller = VideoPlayerController.asset(asset);
    _controller = controller;

    controller
        .initialize()
        .then((_) {
          if (!mounted || _controller != controller) {
            return;
          }

          controller
            ..setLooping(true)
            ..play();

          setState(() {});
        })
        .catchError((Object _) {
          if (!mounted) {
            return;
          }

          setState(() {
            _controller = null;
          });
        });
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = _controller;

    if (controller == null || !controller.value.isInitialized) {
      return AvatarWidget(state: widget.state);
    }

    return ClipOval(
      child: SizedBox(
        width: widget.size,
        height: widget.size,
        child: FittedBox(
          fit: BoxFit.cover,
          child: SizedBox(
            width: controller.value.size.width,
            height: controller.value.size.height,
            child: VideoPlayer(controller),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/reaction_avatar_test.dart
```

Expected: `All tests passed!`

- [ ] **Step 5: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/posture/reaction_avatar.dart test/reaction_avatar_test.dart && \
  git commit -m "feat(frontend): add ReactionAvatar video widget for avatar_state"
```

---

## Task 6: `utils/result_mapper.dart` — 자세 신호 매핑 추가

**Files:**
- Create: `frontend/lib/utils/result_mapper.dart`
- Create: `frontend/test/result_mapper_posture_test.dart`

**Interfaces:**
- Consumes: Task 2의 `package:pr_front/posture/posture_timeline.dart` (`PostureWindow`, `PostureWindow.fromJson`), Task 4의 `Segment`/`SegmentLevel`/`HistoryItem`/`MetricData`
- Produces: `buildOverall`, `buildMetrics`, `buildSegments`, `buildStrengths`, `buildOneLineCoaching`, `buildImprovements`, `buildPracticeGoals`, `buildFullScript`, `buildHistoryItem`, `gestureActivityText(String)`, `armOpennessText(String)` — Task 9(`analysis_detail.dart`), Task 10(`main.dart`)가 이 함수들을 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/test/result_mapper_posture_test.dart`:

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
            'shoulder_tilt_avg_deg': 12.5,
            'shoulder_tilt_exceed_ratio': 0.4,
            'head_down_avg_deg': 8.0,
            'head_down_exceed_ratio': 0.1,
            'gesture_activity_level': 'normal',
            'torso_signal_sufficient': true,
            'torso_lean_avg_deg': 5.0,
            'torso_lean_exceed_ratio': 0.2,
            'arm_openness_level': 'open',
            'reasons': ['어깨 기울어짐 40% 구간'],
          },
        ],
      },
    };

    final segments = mapper.buildSegments(result);

    expect(segments.length, 1);
    expect(segments.first.postureAvailable, true);
    expect(segments.first.postureSignalSufficient, true);
    expect(segments.first.shoulderTilt, '평균 12.5도 · 초과 40%');
    expect(segments.first.headDown, '평균 8.0도 · 초과 10%');
    expect(segments.first.torsoLean, '평균 5.0도 · 초과 20%');
    expect(segments.first.armOpenness, '열림');
    expect(segments.first.gestureActivity, '보통');
    expect(segments.first.postureReasons, ['어깨 기울어짐 40% 구간']);
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

  test('gestureActivityText and armOpennessText map known levels', () {
    expect(mapper.gestureActivityText('low'), '낮음');
    expect(mapper.gestureActivityText('normal'), '보통');
    expect(mapper.gestureActivityText('high'), '높음');
    expect(mapper.gestureActivityText('unknown'), '분석 없음');

    expect(mapper.armOpennessText('closed'), '닫힘');
    expect(mapper.armOpennessText('normal'), '보통');
    expect(mapper.armOpennessText('open'), '열림');
    expect(mapper.armOpennessText('unknown'), '분석 없음');
  });
}
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/result_mapper_posture_test.dart
```

Expected: FAIL — `lib/utils/result_mapper.dart` 파일이 없어 컴파일 에러.

- [ ] **Step 3: `lib/utils/result_mapper.dart` 구현**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../posture/posture_timeline.dart';
import '../theme/app_colors.dart';

/// 백엔드 `/analyze` 응답(Map)을 화면 위젯이 바로 쓸 수 있는 모델로 변환하는
/// 순수 함수 모음.

SegmentLevel levelFromApi(String? level) {
  switch (level) {
    case 'high':
      return SegmentLevel.danger;
    case 'medium':
      return SegmentLevel.caution;
    default:
      return SegmentLevel.stable;
  }
}

String paceText(String? level) {
  switch (level) {
    case 'slow':
      return '느림';
    case 'slightly_slow':
      return '약간 느림';
    case 'normal':
      return '적절';
    case 'slightly_fast':
      return '약간 빠름';
    case 'fast':
      return '빠름';
    default:
      return '판정 없음';
  }
}

String emotionText(String? emotion) {
  switch (emotion?.toLowerCase()) {
    case 'neutral':
      return '차분한 톤';
    case 'happy':
      return '밝은 톤';
    case 'sad':
      return '가라앉은 톤';
    case 'angry':
      return '강한 톤';
    case 'fearful':
      return '불안정한 톤';
    case 'surprised':
      return '변화가 큰 톤';
    case 'disgusted':
      return '거친 톤';
    case 'emo_unknown':
    case 'unknown':
      return '톤 신호 부족';
    default:
      return '분석 불가';
  }
}

String gestureActivityText(String level) {
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

String armOpennessText(String level) {
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

String _replaceBackendTerms(String text) {
  return text.replaceAll('pause', '멈춤').replaceAll('Pause', '멈춤');
}

double asDouble(dynamic value) {
  if (value is num) {
    return value.toDouble();
  }
  return 0.0;
}

String formatTime(double seconds) {
  final totalSeconds = seconds.round();
  final minutes = totalSeconds ~/ 60;
  final remainingSeconds = totalSeconds % 60;

  if (minutes > 0) {
    return '$minutes:${remainingSeconds.toString().padLeft(2, '0')}';
  }
  return '$totalSeconds초';
}

String formatHistoryDuration(double seconds) {
  final totalSeconds = seconds.round();
  final minutes = totalSeconds ~/ 60;
  final remaining = totalSeconds % 60;

  if (minutes == 0) {
    return '$remaining초';
  }
  return '$minutes분 $remaining초';
}

String formatHistoryDate(DateTime? date) {
  if (date == null) {
    return '날짜 정보 없음';
  }

  final local = date.toLocal();
  final month = local.month.toString().padLeft(2, '0');
  final day = local.day.toString().padLeft(2, '0');
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');

  return '${local.year}.$month.$day  $hour:$minute';
}

Map<String, dynamic> _asMap(dynamic value) {
  if (value is Map) {
    return Map<String, dynamic>.from(value);
  }
  return <String, dynamic>{};
}

List<Map<String, dynamic>> _asMapList(dynamic value) {
  if (value is List) {
    return value
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .toList();
  }
  return <Map<String, dynamic>>[];
}

({String summary, SegmentLevel level}) buildOverall(
  Map<String, dynamic> result,
) {
  final coaching = _asMap(result['coaching']);
  final risk = _asMap(result['risk']);

  return (
    summary: coaching['summary']?.toString() ?? '',
    level: levelFromApi(risk['overall_level']?.toString()),
  );
}

({int fillerCount, int repetitionCount}) _fillerCounts(
  Map<String, dynamic> result,
) {
  final fillers = _asMapList(result['fillers']);

  var fillerCount = 0;
  var repetitionCount = 0;

  for (final event in fillers) {
    if (event['type'] == 'filler') fillerCount++;
    if (event['type'] == 'repetition') repetitionCount++;
  }

  return (fillerCount: fillerCount, repetitionCount: repetitionCount);
}

List<MetricData> buildMetrics(Map<String, dynamic> result) {
  final speech = _asMap(result['speech']);
  final counts = _fillerCounts(result);

  final rate = asDouble(speech['presentation_rate']);
  final pauseRatio = asDouble(speech['internal_pause_ratio']) * 100;

  return [
    MetricData(
      label: '발표 속도',
      value: paceText(speech['pace_level']?.toString()),
      sub: '${rate.toStringAsFixed(0)}어/분',
      icon: Icons.access_time,
      iconColor: AppColors.violet600,
    ),
    MetricData(
      label: '멈춤 비율',
      value: '${pauseRatio.toStringAsFixed(1)}%',
      sub: '전체 대비',
      icon: Icons.error_outline,
      iconColor: AppColors.amber500,
    ),
    MetricData(
      label: '추임새 횟수',
      value: '${counts.fillerCount}회',
      sub: '총 횟수',
      icon: Icons.warning_amber_rounded,
      iconColor: AppColors.amber500,
    ),
    MetricData(
      label: '반복 횟수',
      value: '${counts.repetitionCount}회',
      sub: '총 횟수',
      icon: Icons.repeat,
      iconColor: AppColors.emerald500,
    ),
  ];
}

String _scoreLabel(SegmentLevel level) {
  switch (level) {
    case SegmentLevel.stable:
      return '안정도';
    case SegmentLevel.caution:
      return '주의도';
    case SegmentLevel.danger:
      return '위험도';
  }
}

Color _scoreColor(SegmentLevel level) {
  switch (level) {
    case SegmentLevel.stable:
      return AppColors.green600;
    case SegmentLevel.caution:
      return AppColors.amber600;
    case SegmentLevel.danger:
      return AppColors.red500;
  }
}

/// `posture.windows`를 `window_index` 기준으로 인덱싱한다. 자세 캡처가
/// 없었던 세션(voice 전용 모드)은 빈 맵을 반환한다.
Map<int, PostureWindow> _postureWindowsByIndex(Map<String, dynamic> result) {
  final posture = _asMap(result['posture']);
  final windows = _asMapList(posture['windows']);
  final byIndex = <int, PostureWindow>{};

  for (final windowJson in windows) {
    final window = PostureWindow.fromJson(windowJson);
    byIndex[window.windowIndex] = window;
  }

  return byIndex;
}

List<Segment> buildSegments(Map<String, dynamic> result) {
  final risk = _asMap(result['risk']);
  final heatmap = _asMapList(risk['heatmap']);
  final postureWindows = _postureWindowsByIndex(result);

  return heatmap.asMap().entries.map((entry) {
    final index = entry.key;
    final window = entry.value;

    final start = asDouble(window['start']);
    final end = asDouble(window['end']);
    final level = levelFromApi(window['level']?.toString());
    final duration = (end - start).clamp(0.1, double.infinity);

    final reasons = List<String>.from(window['reasons'] ?? []);
    final postureWindow = postureWindows[index];

    return Segment(
      level: level,
      time: '${formatTime(start)} ~ ${formatTime(end)}',
      flex: (duration * 10).round().clamp(1, 999),
      scoreLabel: _scoreLabel(level),
      score: '${window['score'] ?? 0}점',
      scoreColor: _scoreColor(level),
      speed: paceText(window['pace_level']?.toString()),
      tone: emotionText(window['emotion_signal']?.toString()),
      pause: '${window['pause_count'] ?? 0}회',
      filler: '${window['filler_count'] ?? 0}회',
      repeat: '${window['repetition_count'] ?? 0}회',
      signals: reasons.map(_replaceBackendTerms).toList(),
      script: window['transcript']?.toString().trim() ?? '',
      postureAvailable: postureWindow != null,
      postureSignalSufficient: postureWindow?.signalSufficient ?? false,
      shoulderTilt: postureWindow == null
          ? ''
          : '평균 ${postureWindow.shoulderTiltAvgDeg.toStringAsFixed(1)}도 '
              '· 초과 ${(postureWindow.shoulderTiltExceedRatio * 100).toStringAsFixed(0)}%',
      headDown: postureWindow == null
          ? ''
          : '평균 ${postureWindow.headDownAvgDeg.toStringAsFixed(1)}도 '
              '· 초과 ${(postureWindow.headDownExceedRatio * 100).toStringAsFixed(0)}%',
      torsoLean: postureWindow == null
          ? ''
          : (postureWindow.torsoSignalSufficient
              ? '평균 ${postureWindow.torsoLeanAvgDeg.toStringAsFixed(1)}도 '
                  '· 초과 ${(postureWindow.torsoLeanExceedRatio * 100).toStringAsFixed(0)}%'
              : '상체 기울기 신호 부족'),
      armOpenness:
          postureWindow == null ? '' : armOpennessText(postureWindow.armOpennessLevel),
      gestureActivity: postureWindow == null
          ? ''
          : gestureActivityText(postureWindow.gestureActivityLevel),
      postureReasons: postureWindow?.reasons ?? const [],
    );
  }).toList();
}

List<String> buildStrengths(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return List<String>.from(coaching['strengths'] ?? []);
}

String buildOneLineCoaching(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return coaching['one_line_coaching']?.toString() ?? '';
}

List<Map<String, dynamic>> buildImprovements(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return _asMapList(coaching['improvements']);
}

List<String> buildPracticeGoals(Map<String, dynamic> result) {
  final coaching = _asMap(result['coaching']);
  return List<String>.from(coaching['practice_goals'] ?? []);
}

String buildFullScript(Map<String, dynamic> result) {
  return result['transcript']?.toString() ?? '';
}

HistoryItem buildHistoryItem(Map<String, dynamic> result, DateTime? savedAt) {
  final speech = _asMap(result['speech']);
  final risk = _asMap(result['risk']);
  final counts = _fillerCounts(result);

  final duration = asDouble(result['duration']);
  final rate = asDouble(speech['presentation_rate']);
  final pace = paceText(speech['pace_level']?.toString());
  final level = levelFromApi(risk['overall_level']?.toString());

  return HistoryItem(
    date: formatHistoryDate(savedAt),
    badge: level.label,
    title: '${formatHistoryDuration(duration)} · $pace',
    detail:
        '${rate.toStringAsFixed(0)} 어절/분 · 추임새 ${counts.fillerCount}회 · 반복 ${counts.repetitionCount}회',
  );
}
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/result_mapper_posture_test.dart
```

Expected: `All tests passed!`

- [ ] **Step 5: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/utils test/result_mapper_posture_test.dart && \
  git commit -m "feat(frontend): map posture window signals into Segment in result_mapper"
```

---

## Task 7: pr_front 화면 중 변경 없는 화면 추가 (home_start / home_loading / analysis_summary / history_list / my_page)

**Files:**
- Create: `frontend/lib/screens/home_start.dart`
- Create: `frontend/lib/screens/home_loading.dart`
- Create: `frontend/lib/screens/analysis_summary.dart`
- Create: `frontend/lib/screens/history_list.dart`
- Create: `frontend/lib/screens/my_page.dart`

**Interfaces:**
- Consumes: Task 4의 `models/app_models.dart`, `theme/app_colors.dart`, `widgets/common.dart`
- Produces: `HomeStart({mode, onModeChanged, onRecord, onUpload, errorMessage})`, `HomeLoading({mode})`, `AnalysisSummary({summary, level, metrics, onBack, onDetail})`, `HistoryList({items, onDelete, onTap})`, `HistoryEmpty({onStart})`, `MyPage()` — Task 10(`main.dart`)이 이 위젯들을 사용한다.

이 다섯 파일은 pr_front 원본과 100% 동일하다 (이번 스코프에서 수정하지 않음).

- [ ] **Step 1: `lib/screens/home_start.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

class HomeStart extends StatelessWidget {
  const HomeStart({
    super.key,
    required this.mode,
    required this.onModeChanged,
    required this.onRecord,
    required this.onUpload,
    this.errorMessage,
  });

  final RecordMode mode;
  final ValueChanged<RecordMode> onModeChanged;
  final VoidCallback onRecord;
  final VoidCallback onUpload;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Header
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Expanded(
                child: Text(
                  'AI Presentation Coach',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
              ),
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.gray200),
                ),
                child: const Icon(
                  Icons.help_outline,
                  size: 18,
                  color: AppColors.gray500,
                ),
              ),
            ],
          ),
        ),

        // Headline + mode toggle
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'AI SPEAKER COACH',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.2,
                  color: AppColors.violet600,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                '발표를 녹음하고\nAI 피드백을 받아보세요',
                style: TextStyle(
                  fontSize: 24,
                  height: 1.25,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  _ModeChip(
                    label: '음성만',
                    selected: mode == RecordMode.voice,
                    onTap: () => onModeChanged(RecordMode.voice),
                  ),
                  const SizedBox(width: 8),
                  _ModeChip(
                    label: '음성+모션(카메라)',
                    selected: mode == RecordMode.voiceMotion,
                    onTap: () => onModeChanged(RecordMode.voiceMotion),
                  ),
                ],
              ),
              if (errorMessage != null) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.red50,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    errorMessage!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.red600,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),

        // Mic button, centered
        Expanded(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _PulsingMicButton(onTap: onRecord),
                const SizedBox(height: 24),
                const Text(
                  '발표 준비가 되셨나요?',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.gray800,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '마이크 버튼을 눌러 녹음을 시작하거나 WAV 파일을 업로드\n해 발표 습관을 분석해보세요',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 12,
                    height: 1.6,
                    color: AppColors.gray500,
                  ),
                ),
              ],
            ),
          ),
        ),

        // Upload
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, bottom: 10),
          child: GestureDetector(
            onTap: onUpload,
            child: CustomPaint(
              painter: _DashedBorderPainter(),
              child: const SizedBox(
                height: 48,
                child: Center(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.file_upload_outlined,
                          size: 18, color: AppColors.gray600),
                      SizedBox(width: 8),
                      Text(
                        '파일 업로드',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: AppColors.gray600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _ModeChip extends StatelessWidget {
  const _ModeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? AppColors.violet600 : AppColors.gray100,
          borderRadius: BorderRadius.circular(999),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: selected ? AppColors.white : AppColors.gray500,
          ),
        ),
      ),
    );
  }
}

/// 링이 퍼지는 마이크 버튼 (pulse-ring 애니메이션 대체)
class _PulsingMicButton extends StatefulWidget {
  const _PulsingMicButton({required this.onTap});

  final VoidCallback onTap;

  @override
  State<_PulsingMicButton> createState() => _PulsingMicButtonState();
}

class _PulsingMicButtonState extends State<_PulsingMicButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 2000),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 180,
      height: 180,
      child: Stack(
        alignment: Alignment.center,
        children: [
          AnimatedBuilder(
            animation: _controller,
            builder: (context, _) {
              final t = _controller.value;
              return Stack(
                alignment: Alignment.center,
                children: [
                  for (final delay in [0.0, 0.5])
                    _ring((t + delay) % 1.0),
                ],
              );
            },
          ),
          GestureDetector(
            onTap: widget.onTap,
            child: Container(
              width: 112,
              height: 112,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.violet100,
                border: Border.all(color: AppColors.violet300, width: 2),
              ),
              child: const Icon(Icons.mic, size: 48, color: AppColors.violet600),
            ),
          ),
        ],
      ),
    );
  }

  Widget _ring(double t) {
    return Container(
      width: 112 + 68 * t,
      height: 112 + 68 * t,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.violet100.withValues(alpha: 0.5 * (1 - t)),
      ),
    );
  }
}

/// border-2 border-dashed 대체
class _DashedBorderPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.gray300
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(12),
    );
    final path = Path()..addRRect(rrect);

    const dash = 6.0;
    const gap = 5.0;
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        canvas.drawPath(
          metric.extractPath(distance, distance + dash),
          paint,
        );
        distance += dash + gap;
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
```

- [ ] **Step 2: `lib/screens/home_loading.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';

class HomeLoading extends StatelessWidget {
  const HomeLoading({super.key, required this.mode});

  final RecordMode mode;

  @override
  Widget build(BuildContext context) {
    final isMotion = mode == RecordMode.voiceMotion;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Text(
            'AI Presentation Coach',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.gray900,
            ),
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const SizedBox(
                  width: 96,
                  height: 96,
                  child: CircularProgressIndicator(
                    strokeWidth: 8,
                    strokeCap: StrokeCap.round,
                    color: AppColors.violet600,
                    backgroundColor: AppColors.violet100,
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  isMotion ? '발표 음성과 동작을 분석하고 있어요...' : '발표를 분석하고 있어요...',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  isMotion
                      ? '음성 분석과 관련 분석을 함께 처리하고 있어요'
                      : '발표 속도, 발음, 습관어를 추출하고 있습니다.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 14,
                    color: AppColors.gray500,
                  ),
                ),
                const SizedBox(height: 24),
                const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('녹음 정지',
                        style: TextStyle(fontSize: 12, color: AppColors.gray400)),
                    SizedBox(width: 8),
                    Icon(Icons.arrow_forward, size: 14, color: AppColors.gray300),
                    SizedBox(width: 8),
                    Text('분석 완료',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColors.violet600,
                        )),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
```

- [ ] **Step 3: `lib/screens/analysis_summary.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class AnalysisSummary extends StatelessWidget {
  const AnalysisSummary({
    super.key,
    required this.summary,
    required this.level,
    required this.metrics,
    required this.onBack,
    required this.onDetail,
  });

  final String summary;
  final SegmentLevel level;
  final List<MetricData> metrics;
  final VoidCallback onBack;
  final VoidCallback onDetail;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            children: [
              GestureDetector(
                onTap: onBack,
                child: const Icon(Icons.chevron_left, size: 24, color: AppColors.gray700),
              ),
              const SizedBox(width: 8),
              const Text(
                '발표 분석 결과',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 16),
            child: Column(
              children: [
                OverallCard(summary: summary, level: level),
                const SizedBox(height: 16),
                MetricsCard(metrics: metrics),
              ],
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, bottom: 20),
          child: GestureDetector(
            onTap: onDetail,
            child: Container(
              height: 56,
              decoration: BoxDecoration(
                color: AppColors.violet600,
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '상세 보기',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: AppColors.white,
                    ),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.expand_more, size: 20, color: AppColors.white),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
```

- [ ] **Step 4: `lib/screens/history_list.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class HistoryList extends StatelessWidget {
  const HistoryList({
    super.key,
    required this.items,
    required this.onDelete,
    required this.onTap,
  });

  final List<HistoryItem> items;
  final ValueChanged<int> onDelete;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '발표 기록',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              Icon(Icons.filter_alt_outlined,
                  size: 20, color: AppColors.gray700),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 16),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, i) {
              final item = items[i];
              final isCaution = item.badge == '주의';
              return GestureDetector(
                onTap: () => onTap(i),
                child: AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                item.date,
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: AppColors.gray400,
                                ),
                              ),
                              const SizedBox(width: 8),
                              StatusBadge(
                                label: item.badge,
                                background: isCaution
                                    ? AppColors.amber100
                                    : AppColors.red100,
                                foreground: isCaution
                                    ? AppColors.amber700
                                    : AppColors.red700,
                              ),
                            ],
                          ),
                          GestureDetector(
                            onTap: () => onDelete(i),
                            child: const Icon(Icons.delete_outline,
                                size: 18, color: AppColors.gray400),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        item.title,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                          color: AppColors.gray900,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        item.detail,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.gray500,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class HistoryEmpty extends StatelessWidget {
  const HistoryEmpty({super.key, required this.onStart});

  final VoidCallback onStart;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Text(
            '발표 기록',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.gray900,
            ),
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.help_outline,
                    size: 48, color: AppColors.gray300),
                const SizedBox(height: 16),
                const Text(
                  '아직 분석한 발표가 없어요',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 4),
                const Text(
                  '첫 번째 발표를 녹음하고 AI 분석을 경험해보세요',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14, color: AppColors.gray500),
                ),
                const SizedBox(height: 16),
                GestureDetector(
                  onTap: onStart,
                  child: Container(
                    width: double.infinity,
                    height: 52,
                    decoration: BoxDecoration(
                      color: AppColors.violet600,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Center(
                      child: Text(
                        '발표 연습하러 가기',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: AppColors.white,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
```

- [ ] **Step 5: `lib/screens/my_page.dart` 생성**

```dart
import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../widgets/common.dart';

class MyPage extends StatefulWidget {
  const MyPage({super.key});

  @override
  State<MyPage> createState() => _MyPageState();
}

class _MyPageState extends State<MyPage> {
  bool _logoutConfirm = false;

  static const _menuItems = [
    '구독/결제 상태',
    '알림 설정',
    '계정 설정',
    '문의하기',
  ];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 16),
          child: Text(
            '마이페이지',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: AppColors.gray900,
            ),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Profile
                AppCard(
                  child: Row(
                    children: [
                      Container(
                        width: 56,
                        height: 56,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppColors.gray200,
                        ),
                        child: const Icon(Icons.person_outline,
                            size: 28, color: AppColors.gray400),
                      ),
                      const SizedBox(width: 16),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              '김서연',
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.bold,
                                color: AppColors.gray900,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'sy.kim@email.com',
                              style: TextStyle(
                                fontSize: 12,
                                color: AppColors.gray500,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppColors.violet50,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          '수정',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.violet600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Menu
                AppCard(
                  padding: EdgeInsets.zero,
                  child: Column(
                    children: [
                      for (var i = 0; i < _menuItems.length; i++) ...[
                        if (i > 0)
                          const Divider(
                              height: 1, thickness: 1, color: AppColors.gray50),
                        InkWell(
                          onTap: () {},
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 14),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  _menuItems[i],
                                  style: const TextStyle(
                                    fontSize: 14,
                                    fontWeight: FontWeight.w500,
                                    color: AppColors.gray800,
                                  ),
                                ),
                                const Icon(Icons.chevron_right,
                                    size: 18, color: AppColors.gray400),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // Logout
                GestureDetector(
                  onTap: () => setState(() => _logoutConfirm = !_logoutConfirm),
                  child: const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      '로그아웃',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.red500,
                      ),
                    ),
                  ),
                ),
                if (_logoutConfirm)
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: AppColors.red50,
                      border: Border.all(color: AppColors.red100),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        const Text(
                          '정말 로그아웃 하시겠어요?',
                          style: TextStyle(
                            fontSize: 14,
                            color: AppColors.red600,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: GestureDetector(
                                onTap: () =>
                                    setState(() => _logoutConfirm = false),
                                child: Container(
                                  height: 36,
                                  decoration: BoxDecoration(
                                    color: AppColors.gray100,
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: const Center(
                                    child: Text(
                                      '취소',
                                      style: TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w500,
                                        color: AppColors.gray700,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Container(
                                height: 36,
                                decoration: BoxDecoration(
                                  color: AppColors.red500,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Center(
                                  child: Text(
                                    '로그아웃',
                                    style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w500,
                                      color: AppColors.white,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
```

- [ ] **Step 6: 정적 분석**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter analyze lib/screens/home_start.dart lib/screens/home_loading.dart \
    lib/screens/analysis_summary.dart lib/screens/history_list.dart lib/screens/my_page.dart
```

Expected: `No issues found!`

- [ ] **Step 7: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/screens/home_start.dart lib/screens/home_loading.dart \
    lib/screens/analysis_summary.dart lib/screens/history_list.dart lib/screens/my_page.dart && \
  git commit -m "feat(frontend): add pr_front home/loading/summary/history/my_page screens"
```

---

## Task 8: `screens/home_recording.dart` — 카메라 프리뷰 + ReactionAvatar 연결

**Files:**
- Create: `frontend/lib/screens/home_recording.dart`

**Interfaces:**
- Consumes: Task 4의 `models/app_models.dart`/`theme/app_colors.dart`, Task 5의 `ReactionAvatar({state, size})`, `package:camera/camera.dart`(`CameraController`, `CameraPreview`)
- Produces: `HomeRecording({mode, seconds, onStop, cameraController, avatarState})` — Task 10(`main.dart`)이 `HomeScreen.recording` 분기에서 사용한다.

pr_front 원본 대비 변경점: 생성자에 `cameraController`(nullable)와 `avatarState`를 추가하고, `_cameraSection()`의 정적 placeholder를 실제 `CameraPreview` + `ReactionAvatar`로 교체한다. 그 외(제목 바, REC 배지, 타이머, 정지 버튼, `_voiceSection()`, `_Waveform` 등)는 변경 없음.

- [ ] **Step 1: `lib/screens/home_recording.dart` 생성**

```dart
import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../models/app_models.dart';
import '../posture/reaction_avatar.dart';
import '../theme/app_colors.dart';

class HomeRecording extends StatelessWidget {
  const HomeRecording({
    super.key,
    required this.mode,
    required this.seconds,
    required this.onStop,
    required this.cameraController,
    required this.avatarState,
  });

  final RecordMode mode;
  final int seconds;
  final VoidCallback onStop;
  final CameraController? cameraController;
  final String avatarState;

  @override
  Widget build(BuildContext context) {
    final mm = (seconds ~/ 60).toString().padLeft(2, '0');
    final ss = (seconds % 60).toString().padLeft(2, '0');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'AI Presentation Coach',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.red50,
                  border: Border.all(color: AppColors.red200),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _BlinkingDot(),
                    SizedBox(width: 6),
                    Text(
                      'REC',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: AppColors.red600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Column(
              children: [
                if (mode == RecordMode.voiceMotion)
                  Expanded(child: _cameraSection())
                else
                  Expanded(child: _voiceSection()),

                // Timer
                Column(
                  children: [
                    Text(
                      '$mm:$ss',
                      style: const TextStyle(
                        fontSize: 46,
                        fontWeight: FontWeight.bold,
                        color: AppColors.gray900,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      mode == RecordMode.voiceMotion
                          ? '카메라 없이 음성만 계속 진행'
                          : '목소리가 정상적으로 입력되고 있습니다',
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.gray500,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 24),
                Row(
                  children: [
                    const Expanded(child: Divider(color: AppColors.gray200, height: 1)),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Text('녹음 시작',
                          style: TextStyle(fontSize: 12, color: AppColors.gray400)),
                    ),
                    const Expanded(child: Divider(color: AppColors.gray200, height: 1)),
                    const Padding(
                      padding: EdgeInsets.symmetric(horizontal: 8),
                      child: Text('녹음 정지',
                          style: TextStyle(fontSize: 12, color: AppColors.gray400)),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                GestureDetector(
                  onTap: onStop,
                  child: Container(
                    height: 56,
                    margin: const EdgeInsets.only(bottom: 24),
                    decoration: BoxDecoration(
                      color: AppColors.gray900,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.stop, size: 22, color: AppColors.white),
                        SizedBox(width: 12),
                        Text(
                          '정지',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: AppColors.white,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _voiceSection() {
    return Column(
      children: [
        const SizedBox(height: 16),
        const Align(
          alignment: Alignment.centerLeft,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '발표 진행 중...',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: AppColors.red500,
                ),
              ),
              SizedBox(height: 4),
              Text(
                '자연스럽고 편안하게\n준비한 발표를 말해보세요',
                style: TextStyle(
                  fontSize: 20,
                  height: 1.35,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 128,
                  height: 128,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.violet50,
                    border: Border.all(color: AppColors.violet100, width: 4),
                  ),
                  child: const Icon(Icons.mic, size: 52, color: AppColors.violet600),
                ),
                const SizedBox(height: 12),
                const Text('홈으로 이동',
                    style: TextStyle(fontSize: 12, color: AppColors.gray400)),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _cameraSection() {
    final controller = cameraController;
    final isReady = controller != null && controller.value.isInitialized;

    return Column(
      children: [
        const SizedBox(height: 8),
        const Align(
          alignment: Alignment.centerLeft,
          child: Text(
            '자세를 실시간으로 분석하고 있어요',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: AppColors.red500,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 288),
            child: Container(
              width: double.infinity,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                color: AppColors.gray900,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  if (isReady)
                    Center(
                      child: AspectRatio(
                        aspectRatio: controller.value.aspectRatio,
                        child: CameraPreview(controller),
                      ),
                    )
                  else
                    const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.videocam_outlined,
                              size: 32, color: AppColors.gray400),
                          SizedBox(height: 8),
                          Text('카메라를 준비하고 있어요',
                              style: TextStyle(
                                  fontSize: 14, color: AppColors.gray500)),
                        ],
                      ),
                    ),
                  Positioned(
                    top: 12,
                    right: 12,
                    child: ReactionAvatar(state: avatarState, size: 56),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const _Waveform(),
      ],
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.color, required this.size});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

/// animate-pulse 대체
class _BlinkingDot extends StatefulWidget {
  const _BlinkingDot();

  @override
  State<_BlinkingDot> createState() => _BlinkingDotState();
}

class _BlinkingDotState extends State<_BlinkingDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: Tween<double>(begin: 0.35, end: 1).animate(_controller),
      child: const _Dot(color: AppColors.red500, size: 8),
    );
  }
}

/// wave-bar 애니메이션 대체
class _Waveform extends StatefulWidget {
  const _Waveform();

  @override
  State<_Waveform> createState() => _WaveformState();
}

class _WaveformState extends State<_Waveform>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1000),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            for (var i = 0; i < 20; i++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: Container(
                  width: 4,
                  height: _barHeight(i),
                  decoration: BoxDecoration(
                    color: AppColors.violet600,
                    borderRadius: BorderRadius.circular(999),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  double _barHeight(int index) {
    final t = (_controller.value + index * 0.05) % 1.0;
    final wave = 1 - (2 * t - 1).abs();
    return 4 + wave * 26;
  }
}
```

`fontFeatures: [FontFeature.tabularFigures()]`를 쓰려면 `dart:ui` 임포트가 필요하다 — 원본 pr_front 파일도 명시적 `import 'dart:ui'` 없이 `flutter/material.dart`가 재노출하는 것에 의존한다. `flutter analyze`에서 `undefined_identifier` 에러가 나면 이 파일 최상단에 `import 'dart:ui';`를 추가한다.

- [ ] **Step 2: 정적 분석 (다른 파일 미완성으로 인한 import 에러는 이 시점에 정상)**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter analyze lib/screens/home_recording.dart
```

Expected: `CameraController`/`CameraPreview`/`ReactionAvatar` 관련 타입 에러가 없어야 한다 (이 파일이 참조하는 `../posture/reaction_avatar.dart`는 Task 5에서 이미 생성됨).

- [ ] **Step 3: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/screens/home_recording.dart && \
  git commit -m "feat(frontend): wire live camera preview and ReactionAvatar into home_recording"
```

---

## Task 9: `screens/analysis_detail.dart` — 자세 신호 섹션 추가

**Files:**
- Create: `frontend/lib/screens/analysis_detail.dart`

**Interfaces:**
- Consumes: Task 4의 `Segment`(postureAvailable 등 포함)/`SegmentLevel`, `widgets/common.dart`
- Produces: `AnalysisDetail({summary, level, metrics, segments, strengths, oneLineCoaching, improvements, practiceGoals, fullScript, onBack})` — Task 10(`main.dart`)이 `HomeScreen.detail` 분기에서 사용한다.

pr_front 원본 대비 변경점: `_flowTab()`의 선택 구간 카드에서 "확인된 신호" 박스와 "해당 구간 발표 내용" 박스 사이에 `seg.postureAvailable`일 때만 보이는 "자세 신호" 섹션을 추가한다. 그 외 로직(탭 전환, 복사, 개선/스크립트 탭)은 변경 없음.

- [ ] **Step 1: `lib/screens/analysis_detail.dart` 생성**

```dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/app_models.dart';
import '../theme/app_colors.dart';
import '../widgets/common.dart';

class AnalysisDetail extends StatefulWidget {
  const AnalysisDetail({
    super.key,
    required this.summary,
    required this.level,
    required this.metrics,
    required this.segments,
    required this.strengths,
    required this.oneLineCoaching,
    required this.improvements,
    required this.practiceGoals,
    required this.fullScript,
    required this.onBack,
  });

  final String summary;
  final SegmentLevel level;
  final List<MetricData> metrics;
  final List<Segment> segments;
  final List<String> strengths;
  final String oneLineCoaching;
  final List<Map<String, dynamic>> improvements;
  final List<String> practiceGoals;
  final String fullScript;
  final VoidCallback onBack;

  @override
  State<AnalysisDetail> createState() => _AnalysisDetailState();
}

class _AnalysisDetailState extends State<AnalysisDetail> {
  DetailTab _tab = DetailTab.flow;
  bool _expanded = true;
  bool _copied = false;
  int _selectedSeg = 0;

  static const _tabLabels = {
    DetailTab.flow: '발표 흐름',
    DetailTab.improve: '개선사항',
    DetailTab.script: '발표 스크립트',
  };

  Future<void> _copyScript() async {
    await Clipboard.setData(ClipboardData(text: widget.fullScript));
    if (!mounted) return;
    setState(() => _copied = true);
    await Future<void>.delayed(const Duration(seconds: 2));
    if (!mounted) return;
    setState(() => _copied = false);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 20, right: 20, top: 12, bottom: 8),
          child: Row(
            children: [
              GestureDetector(
                onTap: widget.onBack,
                child: const Icon(Icons.chevron_left,
                    size: 24, color: AppColors.gray700),
              ),
              const SizedBox(width: 8),
              const Text(
                '발표 분석 결과',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.only(left: 20, right: 20, bottom: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                OverallCard(summary: widget.summary, level: widget.level),
                const SizedBox(height: 16),
                MetricsCard(
                  metrics: widget.metrics,
                  footer: GestureDetector(
                    onTap: () => setState(() => _expanded = !_expanded),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '상세 분석 ${_expanded ? "닫기" : "열기"}',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: AppColors.violet600,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          _expanded ? Icons.expand_less : Icons.expand_more,
                          size: 16,
                          color: AppColors.violet600,
                        ),
                      ],
                    ),
                  ),
                ),
                if (_expanded) ...[
                  const SizedBox(height: 16),
                  _tabBar(),
                  const SizedBox(height: 16),
                  switch (_tab) {
                    DetailTab.flow => _flowTab(),
                    DetailTab.improve => _improveTab(),
                    DetailTab.script => _scriptTab(),
                  },
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _tabBar() {
    return Row(
      children: [
        for (final t in DetailTab.values)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: GestureDetector(
              onTap: () => setState(() => _tab = t),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                decoration: BoxDecoration(
                  color: _tab == t ? AppColors.violet600 : AppColors.gray100,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _tabLabels[t]!,
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: _tab == t ? AppColors.white : AppColors.gray500,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _flowTab() {
    final segments = widget.segments;

    if (segments.isEmpty) {
      return const AppCard(
        child: Text(
          '구간 분석 결과가 없습니다.',
          style: TextStyle(fontSize: 13, color: AppColors.gray500),
        ),
      );
    }

    final selectedIndex = _selectedSeg.clamp(0, segments.length - 1);
    final seg = segments[selectedIndex];

    final timeLabels = [
      for (final s in segments) s.time.split(' ~ ').first,
      segments.last.time.split(' ~ ').last,
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Timeline
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                '발표 흐름',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: SizedBox(
                  height: 40,
                  child: Row(
                    children: [
                      for (var i = 0; i < segments.length; i++)
                        Expanded(
                          flex: segments[i].flex,
                          child: GestureDetector(
                            onTap: () => setState(() => _selectedSeg = i),
                            child: Container(
                              decoration: BoxDecoration(
                                color: segments[i].level.color,
                                border: selectedIndex == i
                                    ? Border.all(
                                        color: AppColors.white
                                            .withValues(alpha: 0.6),
                                        width: 2,
                                      )
                                    : null,
                              ),
                              child: Center(
                                child: Text(
                                  segments[i].level.label,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: AppColors.white,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  for (final label in timeLabels) _TimeLabel(label),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                '구간을 탭해서 상세 분석을 확인하세요',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: AppColors.gray400),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Selected segment
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: seg.level.color.withValues(alpha: 0.03),
            border: Border.all(color: seg.level.color.withValues(alpha: 0.25)),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    '${seg.time} 상세',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: AppColors.gray900,
                    ),
                  ),
                  StatusBadge(
                    label: seg.level.label,
                    background: seg.level.badgeBg,
                    foreground: seg.level.badgeFg,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              GridView.count(
                crossAxisCount: 3,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 1.5,
                children: [
                  _statTile(seg.scoreLabel, seg.score, seg.scoreColor),
                  _statTile('발표 속도', seg.speed, AppColors.gray900),
                  _statTile('음성 톤', seg.tone, AppColors.gray900),
                  _statTile('멈춤 횟수', seg.pause, AppColors.gray900),
                  _statTile('추임새', seg.filler, AppColors.gray900),
                  _statTile('반복', seg.repeat, AppColors.gray900),
                ],
              ),
              const SizedBox(height: 12),
              _whiteBox(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '확인된 신호',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.gray700,
                      ),
                    ),
                    const SizedBox(height: 8),
                    for (final s in seg.signals)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('•',
                                style: TextStyle(
                                    fontSize: 12, color: seg.level.color)),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                s,
                                style: const TextStyle(
                                  fontSize: 12,
                                  height: 1.5,
                                  color: AppColors.gray600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
              if (seg.postureAvailable) ...[
                const SizedBox(height: 12),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    '자세 신호',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.gray700,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                if (!seg.postureSignalSufficient)
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      '자세 신호 부족',
                      style: TextStyle(fontSize: 12, color: AppColors.gray500),
                    ),
                  )
                else ...[
                  GridView.count(
                    crossAxisCount: 3,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 8,
                    crossAxisSpacing: 8,
                    childAspectRatio: 1.5,
                    children: [
                      _statTile('어깨 기울기', seg.shoulderTilt, AppColors.gray900),
                      _statTile('고개 숙임', seg.headDown, AppColors.gray900),
                      _statTile('상체 기울기', seg.torsoLean, AppColors.gray900),
                      _statTile('팔 벌어짐', seg.armOpenness, AppColors.gray900),
                      _statTile('제스처 활동성', seg.gestureActivity, AppColors.gray900),
                    ],
                  ),
                  if (seg.postureReasons.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _whiteBox(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (final reason in seg.postureReasons)
                            Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('•',
                                      style: TextStyle(
                                          fontSize: 12, color: seg.level.color)),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      reason,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        height: 1.5,
                                        color: AppColors.gray600,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ],
              ],
              const SizedBox(height: 12),
              _whiteBox(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      '해당 구간 발표 내용',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: AppColors.gray700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      seg.script,
                      style: const TextStyle(
                        fontSize: 12,
                        height: 1.6,
                        color: AppColors.gray600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _statTile(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(label,
              style: const TextStyle(fontSize: 11, color: AppColors.gray500)),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _whiteBox({required Widget child}) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(12),
      ),
      child: child,
    );
  }

  Widget _improveTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.green50,
            border: Border.all(color: AppColors.green100),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '잘한 점',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppColors.green800,
                ),
              ),
              const SizedBox(height: 8),
              for (final line in widget.strengths)
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• ',
                          style: TextStyle(
                              fontSize: 12, color: AppColors.green700)),
                      Expanded(
                        child: Text(
                          line,
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.5,
                            color: AppColors.green700,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.violet50,
            border: Border.all(color: AppColors.violet100),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                '한 줄 코칭',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppColors.violet800,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                widget.oneLineCoaching,
                style: const TextStyle(
                  fontSize: 14,
                  height: 1.6,
                  fontWeight: FontWeight.w500,
                  color: AppColors.violet700,
                ),
              ),
            ],
          ),
        ),
        if (widget.improvements.isNotEmpty) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '개선할 점',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 12),
                for (final entry in widget.improvements.asMap().entries)
                  Padding(
                    padding: EdgeInsets.only(
                      bottom: entry.key == widget.improvements.length - 1 ? 0 : 14,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${entry.key + 1}. ${entry.value['title'] ?? ''}',
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppColors.gray900,
                          ),
                        ),
                        if ((entry.value['time_range'] ?? '').toString().isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            entry.value['time_range'].toString(),
                            style: const TextStyle(fontSize: 11, color: AppColors.gray400),
                          ),
                        ],
                        const SizedBox(height: 4),
                        Text(
                          entry.value['description']?.toString() ?? '',
                          style: const TextStyle(
                            fontSize: 12,
                            height: 1.5,
                            color: AppColors.gray600,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
        if (widget.practiceGoals.isNotEmpty) ...[
          const SizedBox(height: 16),
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  '다음 연습 목표',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppColors.gray900,
                  ),
                ),
                const SizedBox(height: 12),
                for (final entry in widget.practiceGoals.asMap().entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      '${entry.key + 1}. ${entry.value}',
                      style: const TextStyle(
                        fontSize: 12,
                        height: 1.5,
                        color: AppColors.gray600,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _scriptTab() {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                '발표 내용 스크립트',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: AppColors.gray900,
                ),
              ),
              GestureDetector(
                onTap: _copyScript,
                child: _copied
                    ? const Text(
                        '복사됨!',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: AppColors.violet600,
                        ),
                      )
                    : const Icon(Icons.copy_outlined,
                        size: 18, color: AppColors.gray400),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            widget.fullScript,
            style: const TextStyle(
              fontSize: 12,
              height: 1.7,
              color: AppColors.gray600,
            ),
          ),
        ],
      ),
    );
  }
}

class _TimeLabel extends StatelessWidget {
  const _TimeLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(fontSize: 12, color: AppColors.gray400),
    );
  }
}
```

- [ ] **Step 2: 정적 분석**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter analyze lib/screens/analysis_detail.dart
```

Expected: `No issues found!` (Task 4에서 만든 `Segment`의 새 필드들과 타입이 일치해야 한다).

- [ ] **Step 3: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/screens/analysis_detail.dart && \
  git commit -m "feat(frontend): show posture signal section in analysis_detail when available"
```

---

## Task 10: `lib/main.dart` — AppShell에 자세 캡처 흐름 통합

**Files:**
- Modify: `frontend/lib/main.dart`

**Interfaces:**
- Consumes: Task 2의 `posture/posture_capture_buffer.dart`(`PostureCaptureBuffer`), `posture/posture_window_uploader.dart`(`PostureWindowUploader`), `posture/posture_blob_cleanup_{web,stub}.dart`(`revokePostureFrameBlobUrl`); Task 4의 모든 모델/테마; Task 6의 `result_mapper.dart`; Task 7의 `home_start.dart`/`home_loading.dart`/`analysis_summary.dart`/`history_list.dart`/`my_page.dart`; Task 8의 `home_recording.dart`; Task 9의 `analysis_detail.dart`
- Produces: `PresentationCoachApp`, `AppShell` — Task 11(`widget_test.dart`)이 `PresentationCoachApp`을 pump한다.

이 파일은 지금 존재하는 로컬 `main.dart`(구 `HomePage`/`HistoryPage`/`ResultPage` 단일 파일 구현)를 완전히 대체한다. pr_front의 `AppShell` 상태 머신에, 로컬에만 있던 카메라 자세 캡처 로직(`_startPostureCapture`/`_capturePostureFrame`/`_resizeJpeg`/`_flushPostureWindow`/`_stopPostureCapture`)을 이식하고, `mode == RecordMode.voiceMotion`일 때만 실행되도록 연결한다.

- [ ] **Step 1: `lib/main.dart`를 다음 내용으로 전체 교체**

```dart
import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'dart:ui' show PointerDeviceKind;

import 'package:camera/camera.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;
import 'package:record/record.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'models/app_models.dart';
import 'posture/posture_blob_cleanup_stub.dart'
    if (dart.library.html) 'posture/posture_blob_cleanup_web.dart';
import 'posture/posture_capture_buffer.dart';
import 'posture/posture_window_uploader.dart';
import 'screens/analysis_detail.dart';
import 'screens/analysis_summary.dart';
import 'screens/history_list.dart';
import 'screens/home_loading.dart';
import 'screens/home_recording.dart';
import 'screens/home_start.dart';
import 'screens/my_page.dart';
import 'theme/app_colors.dart';
import 'utils/result_mapper.dart' as mapper;
import 'widgets/bottom_nav.dart';

void main() {
  runApp(
    const PresentationCoachApp(),
  );
}

// ============================================================
// APP
// ============================================================

class PresentationCoachApp extends StatelessWidget {
  const PresentationCoachApp({
    super.key,
  });

  @override
  Widget build(
    BuildContext context,
  ) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'AI Presentation Coach',

      scrollBehavior:
          const MaterialScrollBehavior().copyWith(
        dragDevices: {
          PointerDeviceKind.touch,
          PointerDeviceKind.mouse,
          PointerDeviceKind.trackpad,
          PointerDeviceKind.stylus,
        },
      ),

      theme: ThemeData(
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.gray50,
      ),

      home: const AppShell(),
    );
  }
}

// ============================================================
// APP SHELL
// ============================================================

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  final AudioRecorder _audioRecorder = AudioRecorder();

  AppTab currentTab = AppTab.home;
  HomeScreen homeScreen = HomeScreen.start;
  RecordMode mode = RecordMode.voice;

  bool isRecording = false;
  bool _isStartingRecording = false;
  int recordingSeconds = 0;
  Timer? _recordingTimer;

  bool isAnalyzing = false;
  String? errorMessage;

  Map<String, dynamic>? currentResult;
  bool viewingFromHistory = false;

  List<Map<String, dynamic>> rawHistory = [];

  // ============================================================
  // POSTURE CAPTURE STATE
  // ============================================================
  CameraController? _cameraController;
  final PostureCaptureBuffer _postureBuffer = PostureCaptureBuffer();
  Timer? _postureCaptureTimer;
  Timer? _postureFlushTimer;
  Future<void>? _lastPostureFlush;
  bool _isCapturingPostureFrame = false;
  int _postureWindowIndex = 0;
  String? _postureSessionId;
  PostureWindowUploader? _postureUploader;
  String _avatarState = 'unknown';

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  @override
  void dispose() {
    _recordingTimer?.cancel();
    _audioRecorder.dispose();
    _postureCaptureTimer?.cancel();
    _postureFlushTimer?.cancel();
    _cameraController?.dispose();
    super.dispose();
  }

  // ============================================================
  // RECORDING
  // ============================================================

  Future<void> _startRecording() async {
    if (isAnalyzing || isRecording || _isStartingRecording) {
      return;
    }

    // await 구간 동안 중복 탭으로 재진입하는 것을 막기 위해
    // 동기적으로 즉시 가드를 세운다 (isRecording은 start() 완료 후에나 true가 됨).
    _isStartingRecording = true;

    try {
      setState(() {
        errorMessage = null;
      });

      final hasPermission = await _audioRecorder.hasPermission();

      if (!hasPermission) {
        setState(() {
          errorMessage = '마이크 권한을 허용해주세요.';
        });
        return;
      }

      await _audioRecorder.start(
        const RecordConfig(
          encoder: AudioEncoder.wav,
          sampleRate: 16000,
          numChannels: 1,
          echoCancel: true,
          noiseSuppress: true,
          autoGain: true,
        ),
        path: 'presentation.wav',
      );

      setState(() {
        isRecording = true;
        recordingSeconds = 0;
        homeScreen = HomeScreen.recording;
      });

      _recordingTimer?.cancel();
      _recordingTimer = Timer.periodic(const Duration(seconds: 1), (_) {
        if (!mounted) return;
        setState(() {
          recordingSeconds++;
        });
      });

      if (mode == RecordMode.voiceMotion) {
        try {
          await _startPostureCapture();
        } catch (e) {
          debugPrint('자세 캡처를 시작하지 못했습니다: $e');
        }
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        errorMessage = '녹음을 시작할 수 없습니다: $e';
      });
    } finally {
      _isStartingRecording = false;
    }
  }

  Future<void> _stopRecording() async {
    if (!isRecording) {
      return;
    }

    try {
      _recordingTimer?.cancel();

      if (mode == RecordMode.voiceMotion) {
        await _stopPostureCapture();
      }

      final path = await _audioRecorder.stop();

      if (!mounted) return;

      setState(() {
        isRecording = false;
      });

      if (path == null) {
        throw Exception('녹음 파일을 생성하지 못했습니다.');
      }

      // Flutter Web에서는 녹음 파일이 blob:http://localhost:5173/... 형태로 반환됨
      final blobResponse = await http.get(Uri.parse(path));

      if (blobResponse.statusCode != 200) {
        throw Exception('녹음 파일을 불러오지 못했습니다.');
      }

      final bytes = blobResponse.bodyBytes;

      if (bytes.isEmpty) {
        throw Exception('녹음된 오디오가 비어 있습니다.');
      }

      await _analyzeWavBytes(
        bytes,
        filename: 'recorded_presentation.wav',
        sessionId: _postureSessionId,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        isRecording = false;
        homeScreen = HomeScreen.start;
        errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  // ============================================================
  // POSTURE CAPTURE
  // ============================================================

  Future<void> _startPostureCapture() async {
    _postureBuffer.flush();

    _postureSessionId =
        '${DateTime.now().millisecondsSinceEpoch}-${Random().nextInt(1000000)}';
    _postureWindowIndex = 0;

    _postureUploader = PostureWindowUploader(
      baseUrl: 'http://127.0.0.1:8000',
      sessionId: _postureSessionId!,
    );

    final cameras = await availableCameras();

    if (cameras.isEmpty) {
      return;
    }

    final frontCamera = cameras.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _cameraController = CameraController(
      frontCamera,
      ResolutionPreset.low,
      enableAudio: false,
    );

    await _cameraController!.initialize();

    if (!mounted) return;

    // 카메라 초기화가 끝났음을 HomeRecording에 알려 실시간 프리뷰를 그리게 한다.
    setState(() {});

    _postureCaptureTimer = Timer.periodic(
      const Duration(milliseconds: 400),
      (_) => _capturePostureFrame(),
    );

    _postureFlushTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) {
        _lastPostureFlush = _flushPostureWindow();
      },
    );
  }

  Future<void> _capturePostureFrame() async {
    if (_isCapturingPostureFrame) {
      return;
    }

    final controller = _cameraController;

    if (controller == null || !controller.value.isInitialized) {
      return;
    }

    _isCapturingPostureFrame = true;

    try {
      final file = await controller.takePicture();
      final bytes = await file.readAsBytes();

      revokePostureFrameBlobUrl(file.path);

      final resized = _resizeJpeg(bytes);

      _postureBuffer.addFrame(resized);
    } catch (e) {
      debugPrint('자세 프레임 캡처 실패: $e');
    } finally {
      _isCapturingPostureFrame = false;
    }
  }

  List<int> _resizeJpeg(Uint8List originalBytes) {
    final decoded = img.decodeImage(originalBytes);

    if (decoded == null) {
      return originalBytes;
    }

    final resized = img.copyResize(decoded, width: 320, height: 240);

    return img.encodeJpg(resized, quality: 70);
  }

  Future<void> _flushPostureWindow() async {
    final frames = _postureBuffer.flush();
    final windowIndex = _postureWindowIndex;
    _postureWindowIndex += 1;

    if (frames.isEmpty || _postureUploader == null) {
      return;
    }

    try {
      final result = await _postureUploader!.uploadWindow(
        windowIndex: windowIndex,
        frames: frames,
      );

      final avatarState = result['avatar_state'] as String?;

      if (avatarState != null && mounted) {
        setState(() {
          _avatarState = avatarState;
        });
      }
    } catch (e) {
      debugPrint('자세 window 업로드 실패 (건너뜀): $e');
    }
  }

  Future<void> _stopPostureCapture() async {
    _postureCaptureTimer?.cancel();
    _postureFlushTimer?.cancel();

    if (_lastPostureFlush != null) {
      await _lastPostureFlush;
    }

    await _flushPostureWindow();

    if (mounted) {
      setState(() {
        _avatarState = 'unknown';
      });
    }

    try {
      await _cameraController?.dispose();
    } catch (e) {
      debugPrint('카메라 정리 실패: $e');
    }

    _cameraController = null;
  }

  // ============================================================
  // ANALYZE / UPLOAD
  // ============================================================

  Future<void> _analyzeWavBytes(
    Uint8List bytes, {
    String filename = 'presentation.wav',
    String? sessionId,
  }) async {
    setState(() {
      isAnalyzing = true;
      errorMessage = null;
      homeScreen = HomeScreen.loading;
    });

    try {
      final analyzeUri = Uri.parse(
        'http://127.0.0.1:8000/analyze',
      ).replace(
        queryParameters:
            sessionId == null ? null : {'session_id': sessionId},
      );

      final request = http.MultipartRequest(
        'POST',
        analyzeUri,
      );

      request.files.add(
        http.MultipartFile.fromBytes('file', bytes, filename: filename),
      );

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode != 200) {
        String detail = '분석 중 오류가 발생했습니다.';

        try {
          final errorJson = jsonDecode(utf8.decode(response.bodyBytes));
          if (errorJson is Map && errorJson['detail'] != null) {
            detail = errorJson['detail'].toString();
          }
        } catch (_) {}

        throw Exception(detail);
      }

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));

      if (decoded is! Map<String, dynamic>) {
        throw Exception('서버 응답 형식이 올바르지 않습니다.');
      }

      if (!mounted) return;

      await _saveAnalysisHistory(decoded);

      if (!mounted) return;

      setState(() {
        currentResult = decoded;
        viewingFromHistory = false;
        homeScreen = HomeScreen.summary;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        homeScreen = HomeScreen.start;
        errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          isAnalyzing = false;
        });
      }
    }
  }

  Future<void> _pickAndAnalyzeWav() async {
    setState(() {
      errorMessage = null;
    });

    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: ['wav', 'm4a'],
    );

    if (file == null) {
      return;
    }

    try {
      final bytes = await file.xFile.readAsBytes();
      await _analyzeWavBytes(bytes, filename: file.name);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  // ============================================================
  // HISTORY (SharedPreferences)
  // ============================================================

  Future<void> _loadHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final savedHistory = prefs.getStringList('analysis_history') ?? [];

    final items = <Map<String, dynamic>>[];

    for (final item in savedHistory) {
      try {
        final decoded = jsonDecode(item);
        if (decoded is Map<String, dynamic>) {
          items.add(decoded);
        }
      } catch (_) {}
    }

    if (!mounted) return;

    setState(() {
      rawHistory = items;
    });
  }

  Future<void> _saveAnalysisHistory(Map<String, dynamic> result) async {
    final prefs = await SharedPreferences.getInstance();
    final history = prefs.getStringList('analysis_history') ?? [];

    final item = {
      'saved_at': DateTime.now().toIso8601String(),
      'result': result,
    };

    history.insert(0, jsonEncode(item));

    // MVP에서는 최근 20개만 저장
    if (history.length > 20) {
      history.removeRange(20, history.length);
    }

    await prefs.setStringList('analysis_history', history);
    await _loadHistory();
  }

  Future<void> _deleteHistoryItem(int index) async {
    final prefs = await SharedPreferences.getInstance();
    final savedHistory = prefs.getStringList('analysis_history') ?? [];

    if (index < 0 || index >= savedHistory.length) {
      return;
    }

    savedHistory.removeAt(index);
    await prefs.setStringList('analysis_history', savedHistory);
    await _loadHistory();
  }

  List<HistoryItem> get _historyDisplayItems {
    return rawHistory.map((entry) {
      final result = entry['result'];
      final resultMap =
          result is Map ? Map<String, dynamic>.from(result) : <String, dynamic>{};
      final savedAt = DateTime.tryParse(entry['saved_at']?.toString() ?? '');
      return mapper.buildHistoryItem(resultMap, savedAt);
    }).toList();
  }

  void _openHistoryItem(int index) {
    final result = rawHistory[index]['result'];
    if (result is! Map) return;

    setState(() {
      currentResult = Map<String, dynamic>.from(result);
      viewingFromHistory = true;
      homeScreen = HomeScreen.summary;
    });
  }

  // ============================================================
  // NAVIGATION HELPERS
  // ============================================================

  void _handleSummaryBack() {
    setState(() {
      homeScreen = HomeScreen.start;
      if (viewingFromHistory) {
        currentTab = AppTab.history;
      }
      viewingFromHistory = false;
    });
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    final showNav = homeScreen == HomeScreen.start;

    return Scaffold(
      body: Center(
        child: Container(
          width: double.infinity,
          constraints: const BoxConstraints(maxWidth: 430),
          color: AppColors.white,
          child: SafeArea(
            child: Column(
              children: [
                Expanded(child: _buildBody()),
                if (showNav)
                  BottomNav(
                    tab: currentTab,
                    onTab: (tab) => setState(() => currentTab = tab),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (homeScreen == HomeScreen.summary || homeScreen == HomeScreen.detail) {
      return _buildResultScreen();
    }

    switch (currentTab) {
      case AppTab.home:
        return _buildHomeScreen();
      case AppTab.history:
        return rawHistory.isEmpty
            ? HistoryEmpty(
                onStart: () => setState(() => currentTab = AppTab.home),
              )
            : HistoryList(
                items: _historyDisplayItems,
                onDelete: _deleteHistoryItem,
                onTap: _openHistoryItem,
              );
      case AppTab.mypage:
        return const MyPage();
    }
  }

  Widget _buildHomeScreen() {
    switch (homeScreen) {
      case HomeScreen.start:
        return HomeStart(
          mode: mode,
          onModeChanged: (m) => setState(() => mode = m),
          onRecord: _startRecording,
          onUpload: _pickAndAnalyzeWav,
          errorMessage: errorMessage,
        );
      case HomeScreen.recording:
        return HomeRecording(
          mode: mode,
          seconds: recordingSeconds,
          onStop: _stopRecording,
          cameraController: _cameraController,
          avatarState: _avatarState,
        );
      case HomeScreen.loading:
        return HomeLoading(mode: mode);
      case HomeScreen.summary:
      case HomeScreen.detail:
        return const SizedBox.shrink();
    }
  }

  Widget _buildResultScreen() {
    final result = currentResult;
    if (result == null) {
      return const SizedBox.shrink();
    }

    final overall = mapper.buildOverall(result);
    final metrics = mapper.buildMetrics(result);

    if (homeScreen == HomeScreen.detail) {
      return AnalysisDetail(
        summary: overall.summary,
        level: overall.level,
        metrics: metrics,
        segments: mapper.buildSegments(result),
        strengths: mapper.buildStrengths(result),
        oneLineCoaching: mapper.buildOneLineCoaching(result),
        improvements: mapper.buildImprovements(result),
        practiceGoals: mapper.buildPracticeGoals(result),
        fullScript: mapper.buildFullScript(result),
        onBack: () => setState(() => homeScreen = HomeScreen.summary),
      );
    }

    return AnalysisSummary(
      summary: overall.summary,
      level: overall.level,
      metrics: metrics,
      onBack: _handleSummaryBack,
      onDetail: () => setState(() => homeScreen = HomeScreen.detail),
    );
  }
}
```

- [ ] **Step 2: 전체 프로젝트 정적 분석**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter analyze
```

Expected: `No issues found!` (Task 11에서 `widget_test.dart`를 아직 안 고쳤다면 그 파일에서만 에러가 날 수 있음 — 다음 태스크에서 해결).

- [ ] **Step 3: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add lib/main.dart && \
  git commit -m "feat(frontend): rebuild AppShell on pr_front structure with posture capture wired in"
```

---

## Task 11: `test/widget_test.dart` 갱신

**Files:**
- Modify: `frontend/test/widget_test.dart`

**Interfaces:**
- Consumes: Task 10의 `PresentationCoachApp`

기존 테스트는 옛 단일 파일 UI 문구("발표 녹음 시작")를 찾고 있어 새 `HomeStart` 화면과 맞지 않는다. 새 화면의 실제 문구로 교체한다. `AppShell.initState()`가 `SharedPreferences`를 사용하므로 mock 초기값을 설정해야 한다.

- [ ] **Step 1: `test/widget_test.dart` 전체 교체**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/main.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('홈 화면이 정상적으로 표시된다', (WidgetTester tester) async {
    await tester.pumpWidget(const PresentationCoachApp());
    await tester.pump();

    expect(find.text('AI Presentation Coach'), findsOneWidget);
    expect(find.text('발표 준비가 되셨나요?'), findsOneWidget);
    expect(find.text('파일 업로드'), findsOneWidget);
  });
}
```

- [ ] **Step 2: 테스트 실행**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  flutter test test/widget_test.dart
```

Expected: `All tests passed!`

- [ ] **Step 3: 전체 테스트 스위트 실행**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter test
```

Expected: `All tests passed!` (posture_capture_buffer, posture_timeline, posture_window_uploader, avatar_widget, reaction_avatar, result_mapper_posture, widget_test 전부 포함).

- [ ] **Step 4: 커밋**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  git add test/widget_test.dart && \
  git commit -m "test(frontend): update smoke test for pr_front home_start screen"
```

---

## Task 12: 최종 검증

**Files:** 없음 (검증 전용 태스크)

**Interfaces:** 없음

- [ ] **Step 1: 전체 정적 분석**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter analyze
```

Expected: `No issues found!`

- [ ] **Step 2: 전체 테스트 스위트**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && flutter test
```

Expected: `All tests passed!`

- [ ] **Step 3: 남은 구식 파일이 없는지 확인**

```bash
cd "/Users/baegseoyeong/Desktop/유니톤/UNITHON/frontend" && \
  ls lib/*.dart 2>/dev/null || echo "lib 루트에 남은 .dart 파일 없음 (정상)"
```

Expected: `lib 루트에 남은 .dart 파일 없음 (정상)` — 모든 파일이 `lib/screens`, `lib/models`, `lib/theme`, `lib/utils`, `lib/widgets`, `lib/posture` 하위로 이동했어야 한다.

- [ ] **Step 4: 수동 스모크 테스트 (사람이 직접 수행 — 자동화 대상 아님)**

1. 백엔드 실행: `cd backend && uvicorn app.main:app --reload` (별도 터미널, `127.0.0.1:8000`에서 뜨는지 확인).
2. 프론트 실행: `cd frontend && flutter run -d chrome`.
3. **음성 전용 경로**: 홈 화면에서 "음성만" 모드 선택 → 마이크 버튼으로 녹음 → 정지 → 분석 완료 후 요약 화면 → "상세 보기"에서 "자세 신호" 섹션이 보이지 않는지 확인.
4. **음성+모션 경로**: "음성+모션(카메라)" 모드 선택 → 녹음 시작 → 카메라 프리뷰가 실제로 뜨는지, 우측 상단에 반응 영상/이모지 아바타가 자세 상태에 따라 바뀌는지 확인 → 정지 → 분석 완료 후 상세 화면에서 "자세 신호" 섹션에 어깨 기울기/고개 숙임/상체 기울기/팔 벌어짐/제스처 활동성 값이 채워지는지 확인.
5. 히스토리 탭에서 방금 두 기록이 보이고, 탭하면 해당 상세로 이동하는지 확인.

Expected: 위 5가지가 모두 육안으로 확인됨. 문제가 있으면 해당 Task로 돌아가 수정한다.
