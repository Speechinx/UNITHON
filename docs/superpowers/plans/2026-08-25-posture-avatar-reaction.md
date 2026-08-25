# 자세 기반 실시간 반응형 아바타 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 녹화 중 자세(어깨 기울기/고개 숙임/상체 기울어짐/시선 이탈) 신호에 따라 화면 속 단일 아바타 캐릭터가 15초 윈도우마다 표정을 바꾸는 실시간 반응 기능을 추가한다.

**Architecture:** 기존 `/posture/window` 파이프라인(2~5fps JPEG 캡처 → 15초 버퍼 → 업로드 → 즉시 window 단위 분석)을 그대로 확장한다. `PostureFrameExtractor`에 귀 랜드마크 2개를 추가하고, `PostureAnalyzer.analyze_window()`가 시선 이탈 신호를 계산해 기존 `reasons` 로직에 통합한 뒤 `avatar_state`(good/bad/unknown)를 판정해 응답에 싣는다. 프론트는 이미 존재하는 window 업로드 응답을 그동안 버려왔는데, 이를 파싱해 `AvatarWidget`에 반영하기만 하면 된다. 새 엔드포인트, 새 모델, 새 통신 계층(WebSocket 등)은 도입하지 않는다.

**Tech Stack:** Python/FastAPI/MediaPipe Pose Landmarker(backend), Flutter Web/Dart(frontend), pytest, flutter_test

## Global Constraints

- 새 엔드포인트/새 ML 모델/새 통신 계층(WebSocket 등)을 도입하지 않는다 — 기존 `/posture/window` 파이프라인만 확장한다.
- 측정된 기하학적 사실만 다룬다 ("고개가 정면 대비 N도 회전" 같은 표현만 사용, "시선을 피했다/집중하지 않았다" 같은 해석적 표현 금지 — 판정 로직에서).
- 랜드마크 신뢰도가 낮은 구간은 기존 패턴(`_has_signal`, `torso_signal_sufficient`류)과 동일하게 "신호 부족"으로 처리하고 억지로 판정하지 않는다.
- `avatar_state`는 `"good"` / `"bad"` / `"unknown"` 3가지 값만 가진다.
- 이번 스코프에 음성 신호 연동은 포함하지 않는다.
- 기존 테스트를 깨뜨리는 변경은 반드시 해당 테스트를 함께 갱신한다.

---

## 파일 구조

- Modify: `backend/app/services/posture_frame_extractor.py` — 귀 랜드마크 인덱스 추가
- Modify: `backend/test_posture_frame_extractor.py` — 랜드마크 매핑 테스트 갱신
- Modify: `backend/app/services/posture_analyzer.py` — `gaze_away_deg` 계산 + `avatar_state` 판정 추가
- Modify: `backend/app/schemas/analysis_response.py` — `PostureWindow`에 gaze/avatar_state 필드 추가
- Modify: `backend/test_posture_analyzer.py` — 신규 로직 테스트 추가/기존 테스트 갱신
- Modify: `frontend/lib/posture_window_uploader.dart` — 업로드 응답 body를 파싱해 반환하도록 변경
- Modify: `frontend/test/posture_window_uploader_test.dart` — 반환값 테스트 추가
- Create: `frontend/lib/avatar_widget.dart` — 상태별 표정을 보여주는 위젯
- Create: `frontend/test/avatar_widget_test.dart` — 위젯 상태별 렌더링 테스트
- Modify: `frontend/lib/main.dart` — 아바타 상태 필드 추가, window 응답 반영, 화면에 위젯 배치

---

### Task 1: 귀 랜드마크 추출 추가

**Files:**
- Modify: `backend/app/services/posture_frame_extractor.py:9-19`
- Test: `backend/test_posture_frame_extractor.py:81-91`

**Interfaces:**
- Consumes: 없음 (기존 `PoseLandmarker`가 이미 계산하는 33개 랜드마크 중 2개를 더 꺼내는 것뿐)
- Produces: `PostureFrameExtractor.extract()`가 반환하는 dict에 `"left_ear"`, `"right_ear"` 키 추가 (`{"x": float, "y": float, "visibility": float}`) — Task 2가 이 키를 사용함

- [ ] **Step 1: 실패하는 테스트로 먼저 갱신**

`backend/test_posture_frame_extractor.py`의 `test_extract_maps_landmark_indices_correctly` 안의 기대값 dict(81~91행)를 아래로 교체:

```python
    assert result == {
        "nose": {"x": 0.0, "y": 0.0, "visibility": 0.0},
        "left_ear": {"x": 0.07, "y": 0.07, "visibility": 0.07},
        "right_ear": {"x": 0.08, "y": 0.08, "visibility": 0.08},
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

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/bin/pytest test_posture_frame_extractor.py::test_extract_maps_landmark_indices_correctly -v`
Expected: FAIL (actual dict에 `left_ear`/`right_ear` 키가 없어서 딕셔너리 불일치)

- [ ] **Step 3: 구현 — `LANDMARK_INDICES`에 귀 추가**

`backend/app/services/posture_frame_extractor.py:9-19`를 아래로 교체:

```python
LANDMARK_INDICES = {
    "nose": 0,
    "left_ear": 7,
    "right_ear": 8,
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

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/bin/pytest test_posture_frame_extractor.py -v`
Expected: PASS (전체 파일)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/posture_frame_extractor.py backend/test_posture_frame_extractor.py
git commit -m "feat: extract ear landmarks for gaze-away detection"
```

---

### Task 2: `gaze_away` 신호 계산 (PostureAnalyzer + 스키마)

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Modify: `backend/app/schemas/analysis_response.py:94-120`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: Task 1이 추가한 `frame["left_ear"]`/`frame["right_ear"]` (`{"x", "y", "visibility"}`)
- Produces: `PostureAnalyzer.analyze_window()` 반환 dict에 `gaze_signal_sufficient: bool`, `gaze_away_avg_deg: float`, `gaze_away_exceed_ratio: float` 추가. `reasons` 리스트에 시선 이탈 사유가 섞여 들어감. `PostureAnalyzer._gaze_away_deg(frame) -> float` 메서드 신설 — Task 3이 이 값들을 그대로 사용함.

- [ ] **Step 1: 테스트 헬퍼에 귀 랜드마크 기본값 추가**

`backend/test_posture_analyzer.py:12-34`의 `_frame()` 함수를 아래로 교체 (기존 파라미터 유지, `left_ear`/`right_ear` 파라미터와 반환 키만 추가):

```python
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
    visibility=1.0,
):
    return {
        "nose": _landmark(*nose, visibility),
        "left_ear": _landmark(*left_ear, visibility),
        "right_ear": _landmark(*right_ear, visibility),
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

`left_ear`/`right_ear` 기본값은 `nose=(0.5, ...)`와 x축상 정확히 중점이 되도록 잡았다 (귀 중점 x = (0.42+0.58)/2 = 0.5 = 코 x) — 즉 기본 프레임은 "정면 응시"로 취급되어 `gaze_away_deg == 0.0`이 되어야 한다.

- [ ] **Step 2: `_gaze_away_deg` 단위 테스트 추가 (실패하는 테스트)**

`backend/test_posture_analyzer.py`의 `_torso_lean_deg` 관련 테스트들(약 243~270행) 뒤에 추가:

```python
def test_gaze_away_deg_is_zero_when_nose_centered_between_ears():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.5, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    assert analyzer._gaze_away_deg(frame) == 0.0


def test_gaze_away_deg_for_45_degree_turn():
    analyzer = PostureAnalyzer()

    frame = _frame(
        nose=(0.58, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    assert math.isclose(
        analyzer._gaze_away_deg(frame),
        45.0,
        abs_tol=0.01,
    )
```

- [ ] **Step 3: window 집계 테스트 추가 (실패하는 테스트)**

같은 파일에서, `test_analyze_window_all_level_frames_has_normal_arm_openness` 근처에 추가:

```python
def test_analyze_window_all_level_frames_reports_gaze_away_too():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["gaze_signal_sufficient"] is True
    assert result["gaze_away_avg_deg"] == 0.0
    assert result["gaze_away_exceed_ratio"] == 0.0


def test_analyze_window_gaze_insufficient_when_ears_low_visibility():
    analyzer = PostureAnalyzer()

    frame = _frame()
    frame["left_ear"]["visibility"] = 0.1
    frame["right_ear"]["visibility"] = 0.1

    frames = [frame for _ in range(10)]

    result = analyzer.analyze_window(frames)

    assert result["signal_sufficient"] is True
    assert result["gaze_signal_sufficient"] is False
    assert result["gaze_away_avg_deg"] == 0.0
    assert result["gaze_away_exceed_ratio"] == 0.0


def test_analyze_window_flags_gaze_away_reason_when_exceed_ratio_high():
    analyzer = PostureAnalyzer()

    turned_frame = _frame(
        nose=(0.58, 0.2),
        left_ear=(0.42, 0.2),
        right_ear=(0.58, 0.2),
    )

    frames = [turned_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["gaze_away_exceed_ratio"] == 0.8
    assert any(
        "시선" in reason
        for reason in result["reasons"]
    )
```

- [ ] **Step 4: 스키마 호환성 테스트 보강**

`test_analyze_window_result_is_compatible_with_posture_window_schema` 테스트(기존 323~335행)에 아래 assertion 한 줄 추가:

```python
    assert window.gaze_signal_sufficient is True
```

- [ ] **Step 5: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py -v`
Expected: 새로 추가한 테스트들은 FAIL (`_gaze_away_deg` 없음, `gaze_signal_sufficient` 키 없음), 기존 테스트는 그대로 PASS

- [ ] **Step 6: 구현 — 상수 및 `_gaze_away_deg` 추가**

`backend/app/services/posture_analyzer.py`의 `ARM_OPENNESS_HIGH_THRESHOLD = 1.3`(40행) 바로 다음 줄에 추가:

```python

    GAZE_AWAY_THRESHOLD_DEG = 20.0

    GAZE_LANDMARKS = [
        "left_ear",
        "right_ear",
    ]
```

`_torso_lean_deg` 메서드(144~162행) 바로 뒤, `analyze_window` 메서드(164행) 바로 앞에 추가:

```python
    def _gaze_away_deg(
        self,
        frame: dict,
    ) -> float:

        left_ear = frame["left_ear"]
        right_ear = frame["right_ear"]
        nose = frame["nose"]

        ear_mid_x = (left_ear["x"] + right_ear["x"]) / 2
        ear_half_distance = abs(right_ear["x"] - left_ear["x"]) / 2

        if ear_half_distance == 0:
            return 0.0

        dx = nose["x"] - ear_mid_x

        return abs(
            math.degrees(
                math.atan2(
                    abs(dx),
                    ear_half_distance,
                )
            )
        )

```

- [ ] **Step 7: 구현 — `analyze_window`에 gaze 집계 추가**

`arm_frames`/`arm_ratio`/`arm_openness` 블록(245~265행, `_arm_openness_level(...)` 호출까지) 바로 뒤, `shoulder_tilt_avg = statistics.mean(shoulder_tilts)`(267행) 바로 앞에 삽입:

```python
        gaze_frames = [
            frame
            for frame in valid_frames
            if self._has_signal(frame, self.GAZE_LANDMARKS)
        ]

        gaze_ratio = (
            len(gaze_frames) / len(valid_frames)
            if valid_frames
            else 0.0
        )

        gaze_signal_sufficient = (
            gaze_ratio >= self.MIN_VALID_FRAME_RATIO
        )

        if gaze_signal_sufficient:
            gaze_away_degs = [
                self._gaze_away_deg(frame)
                for frame in gaze_frames
            ]

            gaze_away_avg = statistics.mean(gaze_away_degs)
            gaze_away_exceed_ratio = self._exceed_ratio(
                gaze_away_degs,
                self.GAZE_AWAY_THRESHOLD_DEG,
            )
        else:
            gaze_away_avg = 0.0
            gaze_away_exceed_ratio = 0.0

```

- [ ] **Step 8: 구현 — reasons에 통합, 응답에 필드 추가**

`reasons` 리스트에 상체 기울어짐 사유를 추가하는 블록(309~315행) 바로 뒤에 추가:

```python

        if (
            gaze_signal_sufficient
            and gaze_away_exceed_ratio >= self.REASON_EXCEED_RATIO_THRESHOLD
        ):
            reasons.append(
                f"시선 이탈 {gaze_away_exceed_ratio * 100:.0f}% 구간"
            )
```

`analyze_window`의 최종 반환 dict에서 `"arm_openness_level": arm_openness,` 줄 다음(`"reasons": reasons,` 줄 바로 앞)에 추가:

```python
            "gaze_signal_sufficient": gaze_signal_sufficient,
            "gaze_away_avg_deg": round(gaze_away_avg, 2),
            "gaze_away_exceed_ratio": round(gaze_away_exceed_ratio, 2),
```

- [ ] **Step 9: 스키마에 필드 추가**

`backend/app/schemas/analysis_response.py`의 `PostureWindow` 클래스에서 `arm_openness_level: str = "unknown"`(116행) 다음, `reasons` 필드(118행) 앞에 추가:

```python

    gaze_signal_sufficient: bool = False
    gaze_away_avg_deg: float = 0.0
    gaze_away_exceed_ratio: float = 0.0
```

- [ ] **Step 10: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py test_posture_frame_extractor.py -v`
Expected: PASS (전체)

- [ ] **Step 11: 커밋**

```bash
git add backend/app/services/posture_analyzer.py backend/app/schemas/analysis_response.py backend/test_posture_analyzer.py
git commit -m "feat: compute gaze-away signal from ear/nose landmarks"
```

---

### Task 3: `avatar_state` 판정

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Modify: `backend/app/schemas/analysis_response.py:94-123` (Task 2에서 수정한 `PostureWindow`)
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: Task 2까지의 `reasons` 리스트, `signal_sufficient` 플래그
- Produces: `analyze_window()` 반환 dict에 `avatar_state: "good" | "bad" | "unknown"` 추가 — Task 6(프론트)이 이 값을 그대로 소비함

- [ ] **Step 1: 기존 exact-equality 테스트 갱신 (먼저 실패하게 만듦)**

`test_analyze_window_signal_insufficient_when_too_many_invalid_frames`(155~165행)와 `test_analyze_window_empty_list_is_insufficient`(168~176행)의 기대 dict를 각각 아래로 교체:

```python
def test_analyze_window_signal_insufficient_when_too_many_invalid_frames():
    analyzer = PostureAnalyzer()

    frames = [None, None, None, _frame()]

    result = analyzer.analyze_window(frames)

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.25,
        "avatar_state": "unknown",
    }


def test_analyze_window_empty_list_is_insufficient():
    analyzer = PostureAnalyzer()

    result = analyzer.analyze_window([])

    assert result == {
        "signal_sufficient": False,
        "valid_frame_ratio": 0.0,
        "avatar_state": "unknown",
    }
```

- [ ] **Step 2: 신규 테스트 추가**

`test_analyze_window_all_level_frames_has_zero_tilt_and_low_activity` 근처에 추가:

```python
def test_analyze_window_avatar_state_good_when_no_reasons():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] == []
    assert result["avatar_state"] == "good"


def test_analyze_window_avatar_state_bad_when_reasons_present():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] != []
    assert result["avatar_state"] == "bad"
```

`test_analyze_window_result_is_compatible_with_posture_window_schema` 테스트에 아래 assertion 한 줄 추가:

```python
    assert window.avatar_state == "good"
```

- [ ] **Step 3: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py -v`
Expected: Step 1/2에서 만지거나 추가한 테스트들 FAIL (`avatar_state` 키 없음)

- [ ] **Step 4: 구현 — 신호 부족 분기에 `avatar_state` 추가**

`analyze_window`의 신호 부족 조기 반환문(181~185행)을 아래로 교체:

```python
        if valid_ratio < self.MIN_VALID_FRAME_RATIO:
            return {
                "signal_sufficient": False,
                "valid_frame_ratio": round(valid_ratio, 2),
                "avatar_state": "unknown",
            }
```

- [ ] **Step 5: 구현 — 정상 분기에 `avatar_state` 판정 추가**

`reasons` 리스트 계산이 끝난 직후(Task 2에서 추가한 시선 이탈 reason append 블록 바로 뒤), 최종 `return {` 문 바로 앞에 추가:

```python
        avatar_state = (
            "bad"
            if reasons
            else "good"
        )

```

최종 반환 dict에서 `"reasons": reasons,` 줄 다음에 추가:

```python
            "avatar_state": avatar_state,
```

- [ ] **Step 6: 스키마에 필드 추가**

`backend/app/schemas/analysis_response.py`의 `PostureWindow` 클래스에서 `reasons` 필드(Task 2에서 위치가 밀린 줄, `List[str] = []`) 다음에 추가:

```python

    avatar_state: str = "unknown"
```

- [ ] **Step 7: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py test_posture_frame_extractor.py -v`
Expected: PASS (전체)

- [ ] **Step 8: 전체 백엔드 테스트 스위트 실행 (회귀 확인)**

Run: `cd backend && .venv/bin/pytest -v`
Expected: PASS (전체 — 특히 `test_presentation_analysis_service_posture.py`, `test_posture_route.py`, `test_posture_session_store.py`가 새 필드로 인해 깨지지 않는지 확인)

- [ ] **Step 9: 커밋**

```bash
git add backend/app/services/posture_analyzer.py backend/app/schemas/analysis_response.py backend/test_posture_analyzer.py
git commit -m "feat: classify posture window as good/bad/unknown for avatar reaction"
```

---

### Task 4: 프론트 — window 업로드 응답 파싱

**Files:**
- Modify: `frontend/lib/posture_window_uploader.dart`
- Test: `frontend/test/posture_window_uploader_test.dart`

**Interfaces:**
- Consumes: 없음 (기존 HTTP 응답 body를 그냥 버리지 않고 읽는 것뿐)
- Produces: `PostureWindowUploader.uploadWindow(...)`의 반환 타입이 `Future<void>` → `Future<Map<String, dynamic>>`로 변경. 반환되는 맵은 백엔드 `/posture/window` 응답 JSON 그대로이며 `avatar_state` 키를 포함함 — Task 6이 이 키를 사용함

- [ ] **Step 1: 실패하는 테스트 추가**

`frontend/test/posture_window_uploader_test.dart`의 기존 두 테스트 사이 또는 뒤에 추가:

```dart
  test('uploadWindow returns the parsed JSON response body', () async {
    final mockClient = MockClient((request) async {
      return http.Response(
        '{"avatar_state": "good", "window_index": 3}',
        200,
      );
    });

    final uploader = PostureWindowUploader(
      baseUrl: 'http://127.0.0.1:8000',
      sessionId: 'test-session',
      client: mockClient,
    );

    final result = await uploader.uploadWindow(
      windowIndex: 3,
      frames: [
        [1, 2, 3],
      ],
    );

    expect(result['avatar_state'], 'good');
    expect(result['window_index'], 3);
  });
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd frontend && flutter test test/posture_window_uploader_test.dart`
Expected: FAIL (컴파일 에러 — `uploadWindow`가 `void`를 반환해서 `result['avatar_state']` 접근 불가)

- [ ] **Step 3: 구현**

`frontend/lib/posture_window_uploader.dart` 전체를 아래로 교체:

```dart
import 'dart:convert';

import 'package:http/http.dart' as http;

class PostureWindowUploader {
  PostureWindowUploader({
    required this.baseUrl,
    required this.sessionId,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final String sessionId;
  final http.Client _client;

  Future<Map<String, dynamic>> uploadWindow({
    required int windowIndex,
    required List<List<int>> frames,
  }) async {
    final uri = Uri.parse(baseUrl).replace(
      path: '/posture/window',
      queryParameters: {
        'session_id': sessionId,
        'window_index': '$windowIndex',
      },
    );

    final request = http.MultipartRequest('POST', uri);

    for (var i = 0; i < frames.length; i++) {
      request.files.add(
        http.MultipartFile.fromBytes(
          'frames',
          frames[i],
          filename: 'frame_$i.jpg',
        ),
      );
    }

    final streamedResponse = await _client.send(request);
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      throw Exception(
        'posture window upload failed: ${response.statusCode}',
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd frontend && flutter test test/posture_window_uploader_test.dart`
Expected: PASS (3개 테스트 전체)

- [ ] **Step 5: 커밋**

```bash
git add frontend/lib/posture_window_uploader.dart frontend/test/posture_window_uploader_test.dart
git commit -m "feat: return parsed response body from posture window upload"
```

---

### Task 5: 프론트 — `AvatarWidget`

**Files:**
- Create: `frontend/lib/avatar_widget.dart`
- Test: `frontend/test/avatar_widget_test.dart`

**Interfaces:**
- Consumes: `state`(String) — `"idle" | "good" | "bad" | "unknown"` 또는 인식 불가한 임의 문자열
- Produces: `AvatarWidget` (StatelessWidget) — `state` prop 하나만 받음. Task 6이 이 위젯을 `state: _avatarState`로 인스턴스화함

- [ ] **Step 1: 실패하는 위젯 테스트 작성**

`frontend/test/avatar_widget_test.dart` 새로 작성:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pr_front/avatar_widget.dart';

void main() {
  testWidgets('shows idle emoji by default', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'idle')),
    );

    expect(find.text('💤'), findsOneWidget);
  });

  testWidgets('shows good emoji for good state', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'good')),
    );

    expect(find.text('🙂'), findsOneWidget);
  });

  testWidgets('shows bad emoji for bad state', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AvatarWidget(state: 'bad')),
    );

    expect(find.text('😟'), findsOneWidget);
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

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `cd frontend && flutter test test/avatar_widget_test.dart`
Expected: FAIL (`avatar_widget.dart` 파일이 없어서 컴파일 에러)

- [ ] **Step 3: 구현**

`frontend/lib/avatar_widget.dart` 새로 작성:

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
    'good': '🙂',
    'bad': '😟',
    'unknown': '❔',
  };

  static const Map<String, Color> _colorByState = {
    'idle': Colors.grey,
    'good': Colors.green,
    'bad': Colors.red,
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
          color: color.withOpacity(0.12),
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

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `cd frontend && flutter test test/avatar_widget_test.dart`
Expected: PASS (5개 테스트 전체)

- [ ] **Step 5: 커밋**

```bash
git add frontend/lib/avatar_widget.dart frontend/test/avatar_widget_test.dart
git commit -m "feat: add AvatarWidget for posture reaction states"
```

---

### Task 6: 프론트 — 녹화 화면에 아바타 연동

**Files:**
- Modify: `frontend/lib/main.dart`

**Interfaces:**
- Consumes: Task 4의 `PostureWindowUploader.uploadWindow(...) -> Future<Map<String, dynamic>>`, Task 5의 `AvatarWidget({required String state})`
- Produces: 없음 (최종 UI 배선. 이후 태스크 없음)

이 태스크는 위젯 트리 배선이라 별도 자동화 테스트를 추가하지 않고, 수동 검증으로 마무리한다 (설계 문서 7절과 동일한 방침).

- [ ] **Step 1: 아바타 상태 필드 추가**

`frontend/lib/main.dart:95`(`PostureWindowUploader? _postureUploader;`) 다음 줄에 필드 추가:

```dart
  String _avatarState = 'idle';
```

- [ ] **Step 2: import 추가**

`frontend/lib/main.dart` 상단의 로컬 import 블록(`import 'posture_window_uploader.dart';` 다음 줄, 11~15행 부근)에 추가:

```dart
import 'avatar_widget.dart';
```

- [ ] **Step 3: 녹화 시작 시 상태 초기화**

`startRecording()` 안의 기존 `setState(() { isRecording = true; recordingSeconds = 0; })` 블록(134~137행)을 아래로 교체:

```dart
    setState(() {
      isRecording = true;
      recordingSeconds = 0;
      _avatarState = 'idle';
    });
```

- [ ] **Step 4: window 업로드 응답을 아바타 상태에 반영**

`_flushPostureWindow()`(255~272행)를 아래로 교체:

```dart
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
```

- [ ] **Step 5: 화면에 위젯 배치**

`build()`(603행부터) 안에서, 마이크 원형 버튼을 감싸는 `Center(child: Material(...))` 블록이 끝나는 지점(707행, `),` 다음) 바로 뒤 — `const SizedBox(height: 28,)`(709~711행) 앞에 삽입:

```dart

                  const SizedBox(
                    height: 20,
                  ),

                  Center(
                    child: AvatarWidget(
                      state: _avatarState,
                    ),
                  ),
```

- [ ] **Step 6: 정적 분석**

Run: `cd frontend && flutter analyze lib/main.dart lib/avatar_widget.dart lib/posture_window_uploader.dart`
Expected: `No issues found!`

- [ ] **Step 7: 전체 프론트 테스트 스위트 실행 (회귀 확인)**

Run: `cd frontend && flutter test`
Expected: PASS (전체)

- [ ] **Step 8: 수동 검증**

1. `cd backend && .venv/bin/uvicorn app.main:app --reload`로 백엔드 실행
2. `cd frontend && flutter run -d chrome`로 프론트 실행
3. 녹음 시작 → 아바타가 💤(idle) 상태로 나타나는지 확인
4. 카메라 앞에서 정면을 보고 바른 자세로 15초 이상 대기 → 🙂(good)로 바뀌는지 확인
5. 고개를 옆으로 돌리거나 어깨를 기울인 채로 15초 이상 유지 → 😟(bad)로 바뀌는지 확인
6. 카메라 프레임 밖으로 벗어난 채로 15초 이상 유지 → ❔(unknown)로 바뀌는지 확인

- [ ] **Step 9: 커밋**

```bash
git add frontend/lib/main.dart
git commit -m "feat: react avatar to live posture window results during recording"
```

---

## 스코프 밖 (이번 계획에 포함하지 않음)

- 음성 신호(추임새/속도) 기반 아바타 반응 — 설계 문서 8절 참고, 추후 별도 계획
- 최종 리포트(`ResultPage`)에 시선 처리 요약 반영
- good/bad 이진을 넘어선 세분화된 감정 상태(혼란/산만 등)
