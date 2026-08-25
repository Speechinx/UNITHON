# 설계: 프론트엔드 pr_front 이식 + 자세 캡처 통합 + 반응 영상

> 작성일: 2026-08-25
> 관련 문서: `docs/superpowers/specs/2026-08-25-posture-avatar-reaction-design.md`(avatar_state 최초 설계),
> `docs/superpowers/specs/2026-08-25-avatar-state-four-expressions-design.md`(avatar_state 4단계 판정, 백엔드 계약),
> `구현계획서_자세추적.md`(자세 추적 원설계)

---

## 0. 배경

- 팀원(serim)이 `https://github.com/2026-UNITHON-PRCoach/pr_front`(`serim_front` 브랜치)에 화면별로 분리된 새 UI(violet 테마 디자인 시스템)를 올렸다. 로컬 `frontend/lib`은 지금까지 `main.dart` 한 파일(3500줄+)에 실제 동작하는 기능(음성 녹음, 카메라 자세 캡처, `/analyze` 연동, 히스토리)이 모두 들어 있다.
- `2026-08-25-avatar-state-four-expressions-design.md`가 이미 "프론트는 손대지 않는다 — 별도로 진행 중인 커스텀 애니메이션 작업이 끝난 뒤 avatar_state 문자열 값을 그대로 받아쓰는 계약만 지키면 된다"고 명시해두었다. 이번 작업이 바로 그 "커스텀 애니메이션 작업"이며, 백엔드가 이미 내려주는 `avatar_state ∈ {focused, engaged, confused, bored, unknown}` 값을 그대로 소비한다.
- 추가로 `https://github.com/2026-UNITHON-PRCoach/pr_mp4`에 상태별 반응 영상(공감.mp4, 집중.mp4, 혼란.mp4)이 준비되어 있다. `bored`(지루함) 영상은 아직 없다.

---

## 1. 목표 & 원칙

1. `frontend/lib`을 pr_front의 화면 분리 구조(디자인 시스템)로 교체한다.
2. 그 위에 로컬에만 있던 실동작 기능(오디오 녹음, 카메라 자세 캡처·업로드, 자세 신호 상세 표시, 히스토리)을 새 구조에 맞게 다시 연결한다. 기능 손실이 없어야 한다.
3. 녹화 중 자세 상태(`avatar_state`)에 따라 반응 영상을 재생하는 컴포넌트를 추가한다.
4. 새 기능이나 새 백엔드 엔드포인트를 만들지 않는다 — 기존 `/analyze`, `/posture/window` 파이프라인을 그대로 쓴다.
5. "감정 변화 영상"이라는 표현이 가리키는 실제 구현은 `avatar_state` 기반 반응 영상 재생이다. 그 외 새로운 감정 분석 기능은 이번 스코프가 아니다.

---

## 2. 파일 구조 (교체)

```
lib/
  main.dart                 pr_front의 App + AppShell — 자세 캡처 상태/흐름 추가
  models/app_models.dart    pr_front 그대로 + Segment에 자세 필드 추가
  theme/app_colors.dart     pr_front 그대로 (violet 테마)
  utils/result_mapper.dart  pr_front 그대로 + 자세 신호 매핑 함수 추가
  widgets/{bottom_nav,common,status_bar}.dart   pr_front 그대로
  screens/home_start.dart          pr_front 그대로
  screens/home_recording.dart      수정: 실제 카메라 프리뷰 + ReactionAvatar 연결
  screens/home_loading.dart        pr_front 그대로
  screens/analysis_summary.dart    pr_front 그대로
  screens/analysis_detail.dart     수정: 구간 상세에 "자세 신호" 섹션 추가
  screens/history_list.dart        pr_front 그대로
  screens/my_page.dart             pr_front 그대로 (정적 목업, 이번 범위 아님)
  posture/avatar_widget.dart            이식 + 상태 매핑 수정 (3.3절)
  posture/reaction_avatar.dart          신규 — 영상 반응 위젯 (4절)
  posture/posture_capture_buffer.dart   이식 그대로
  posture/posture_timeline.dart         이식 그대로 (PostureWindow 모델)
  posture/posture_window_uploader.dart  이식 그대로
  posture/posture_blob_cleanup_{web,stub}.dart  이식 그대로
assets/
  reactions/engaged.mp4     (공감.mp4 재인코딩)
  reactions/focused.mp4     (집중.mp4 재인코딩)
  reactions/confused.mp4    (혼란.mp4 재인코딩)
```

`pubspec.yaml`: pr_front 기준 의존성(`file_picker ^12.0.0`, `http ^1.6.0`, `record ^7.1.1`, `shared_preferences ^2.5.5`)을 유지하고, 자세 캡처에 필요한 `camera ^0.12.0+2`, `image ^4.9.2`, 반응 영상 재생에 필요한 `video_player`를 추가한다. `flutter.assets`에 `assets/reactions/` 등록.

---

## 3. 녹음 흐름 (main.dart `AppShell`)

### 3.1 상태 확장

기존 pr_front `AppShell`에 자세 캡처용 상태를 추가한다: `CameraController?`, `PostureCaptureBuffer`, `Timer? _postureCaptureTimer`, `Timer? _postureFlushTimer`, `Future<void>? _lastPostureFlush`, `bool _isCapturingPostureFrame`, `int _postureWindowIndex`, `String? _postureSessionId`, `PostureWindowUploader?`, `String _avatarState`(기본값 `'unknown'`).

### 3.2 시작/정지

- `_startRecording`: 오디오 녹음 시작 후 `mode == RecordMode.voiceMotion`이면 `_startPostureCapture()` 실행 — try/catch로 감싸 카메라 실패가 음성 녹음을 막지 않게 한다. (기존 로컬 `main.dart`의 `_startPostureCapture`/`_capturePostureFrame`/`_flushPostureWindow` 로직을 그대로 포팅)
- `_stopRecording`: 자세 세션이 있으면 캡처/flush 타이머 정지 → 마지막 flush 대기 → 카메라 dispose, 그 다음 오디오 정지 처리.
- `_analyzeWavBytes`: `_postureSessionId`가 있으면 `/analyze` 요청에 `session_id` 쿼리 파라미터를 함께 보내 백엔드가 자세 데이터를 응답의 `posture.windows`에 병합하도록 한다 (기존 로컬 동작과 동일).
- `_flushPostureWindow` 응답의 `avatar_state`로 `_avatarState`를 갱신하고, 이 값을 `HomeRecording`에 내려준다.
- `dispose()`: 자세 타이머 취소 + 카메라 dispose 추가.

---

## 4. 반응 영상 — `posture/reaction_avatar.dart` (신규)

### 4.1 자산 처리

- `pr_mp4`의 세 영상 중 `집중.mp4`/`혼란.mp4`는 HEVC(H.265) 코덱이라 Flutter Web(Chrome) 재생이 보장되지 않는다 (`공감.mp4`만 H.264). 세 파일 모두 로컬 `ffmpeg`로 H.264로 재인코딩해서 프로젝트 asset으로 포함한다. 화질 손실은 무시할 수준이다.
- 매핑: `공감.mp4→engaged.mp4`, `집중.mp4→focused.mp4`, `혼란.mp4→confused.mp4`.
- 세 영상의 해상도/비율이 제각각(560×752, 800×720, 836×720)이므로, 재생 영역은 고정 크기 박스 + `BoxFit.cover`로 통일한다.

### 4.2 위젯 동작

- `avatar_state ∈ {engaged, focused, confused}`: 해당 `VideoPlayerController`를 초기화해 루프 재생. 상태가 유지되는 동안 계속 반복 재생하고, 상태가 바뀌면 이전 컨트롤러를 dispose하고 새 상태의 영상으로 교체한다.
- `avatar_state ∈ {bored, unknown}` 또는 녹화 시작 전 로컬 초기값(`idle`): 영상 대신 기존 `posture/avatar_widget.dart`(이모지 원형)로 폴백한다. `bored` 전용 영상은 아직 없으므로 이 폴백이 임시 처리다 — 영상이 준비되면 매핑만 추가하면 된다.
- 배치 위치: `home_recording.dart`의 카메라 프리뷰 옆/아래.

### 4.3 `avatar_widget.dart` 상태 매핑 수정

기존 위젯은 `idle/good/bad/unknown` 4개 키만 처리해서 실제 백엔드 값(`focused/engaged/confused/bored/unknown`)과 매칭되지 않는다 — 지금까지 자세 캡처 중에도 아바타가 항상 idle(💤)로만 보였을 가능성이 큰 버그다. `bored`/`unknown`/`idle`(로컬 초기값) 세 가지에 대한 이모지·색상만 새로 매핑한다 (engaged/focused/confused는 영상으로 대체되므로 이모지 매핑이 필요 없다).

---

## 5. 상세 결과 화면 — `analysis_detail.dart`

- `models/app_models.dart`의 `Segment`에 nullable 자세 필드 추가: `postureAvailable`, `postureSignalSufficient`, `shoulderTilt`, `headDown`, `torsoLean`, `armOpenness`, `gestureActivity`, `postureReasons`.
- `result_mapper.dart`의 `buildSegments()`가 `result['posture']['windows']`를 `window_index` 기준으로 매칭해 위 필드를 채운다 (포팅된 `PostureWindow.fromJson` 재사용). 로컬 `main.dart`에 있던 `_armOpennessText`/`_gestureActivityText` 매핑 함수를 `result_mapper.dart`로 이식한다.
- `_flowTab()`의 선택 구간 카드에서 기존 "확인된 신호" 박스 아래, 자세 데이터가 있을 때만 "자세 신호" 박스를 추가한다 (기존 `_statTile`/`_whiteBox` 재사용, 2×2 그리드 + 제스처 활동성 + 자세 관련 사유 목록).

---

## 6. 스코프 밖

- 백엔드 `avatar_state` 판정 로직 — 이미 구현되어 있고 이번 스코프는 그 계약을 소비만 한다.
- `bored` 상태 전용 반응 영상 — 준비되면 후속 작업으로 매핑만 추가.
- `my_page.dart` — pr_front의 정적 목업 그대로 둔다 (실제 계정/구독 연동 없음).
- 새로운 감정 분석/추론 기능 — "감정 변화 영상"은 기존 `avatar_state` 신호를 시각화하는 것이지 새로운 감정 판정 로직이 아니다.

---

## 7. 테스트 전략

- `flutter analyze`로 리팩터링 후 컴파일/린트 오류 확인.
- 백엔드(`127.0.0.1:8000`)를 띄운 상태에서 웹으로 수동 스모크 테스트:
  1. 음성 전용(voice) 모드: 녹음 → 분석 → 요약 → 상세(자세 신호 섹션이 보이지 않아야 함).
  2. 음성+모션(voiceMotion) 모드: 녹음 → 카메라 프리뷰 표시 → 자세 상태 변화에 따라 반응 영상 전환(engaged/focused/confused) 및 폴백(bored/unknown) 확인 → 분석 → 상세(자세 신호 섹션 표시, 값이 실제 서버 응답과 일치).
  3. 히스토리 탭에서 저장된 기록 열람이 정상 동작하는지 확인.
- 영상 자산은 재인코딩 후 실제 Chrome에서 재생되는지 눈으로 확인 (자동화 테스트 대상 아님).
