# 아바타 4단계 표정 판정 로직 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PostureAnalyzer.analyze_window()`가 내려주는 `avatar_state`를 기존 `"good"/"bad"/"unknown"` 3단계에서 `"focused"/"engaged"/"confused"/"bored"/"unknown"` 5단계로 확장한다.

**Architecture:** 기존 `reasons`(안정성) 판정은 그대로 두고, 지금까지 판정에 쓰이지 않던 `gesture_activity_level`과 `arm_openness_level`을 조합한 "참여도" 축을 새로 추가해 2×2 규칙 테이블로 최종 상태를 결정한다. 새 엔드포인트·새 서비스 클래스·새 신호 없이 기존 함수 내부 로직만 바뀐다.

**Tech Stack:** Python/pytest (backend만, 프론트 변경 없음)

## Global Constraints

- `avatar_state` 값 집합은 정확히 `{"focused", "engaged", "confused", "bored", "unknown"}` 5개다. 다른 값이 나오면 안 된다.
- `signal_sufficient=False`일 때의 조기 반환 분기(`avatar_state: "unknown"`)는 변경하지 않는다.
- 참여도 축 규칙: `gesture_activity_level == "low"` **그리고** `arm_openness_level == "closed"`일 때만 "참여도 낮음". 그 외 모든 조합(`normal`/`high`/`open`/`unknown` 포함)은 "참여도 높음"으로 취급한다 (보수적 AND 규칙).
- 최종 매핑: `reasons` 없음 + 참여도 높음 → `"engaged"` / `reasons` 없음 + 참여도 낮음 → `"focused"` / `reasons` 있음 + 참여도 높음 → `"confused"` / `reasons` 있음 + 참여도 낮음 → `"bored"`.
- 새 임계값 상수, 새 클래스, 새 카메라/모델 입력을 추가하지 않는다.
- 프론트(`frontend/lib/avatar_widget.dart`, `frontend/lib/main.dart`)는 이번 스코프가 아니다 — 건드리지 않는다.
- `coaching_service.py`의 규칙 28-10 **문구만** 새 값 집합에 맞게 갱신한다. 규칙의 취지(avatar_state를 코칭 근거로 쓰지 말 것)와 다른 규칙(28-1~28-9)은 변경하지 않는다.

---

## 파일 구조

- Modify: `backend/app/services/posture_analyzer.py` — `analyze_window()`의 `avatar_state` 계산부만 교체
- Modify: `backend/test_posture_analyzer.py` — 기존 avatar_state 관련 테스트 3개 갱신 + 신규 2개 추가
- Modify: `backend/app/services/coaching_service.py` — 규칙 28-10 문구만 갱신

---

### Task 1: `avatar_state` 2×2 판정 로직

**Files:**
- Modify: `backend/app/services/posture_analyzer.py`
- Test: `backend/test_posture_analyzer.py`

**Interfaces:**
- Consumes: 기존 `reasons`(list), `gesture_activity`(str: `"low"|"normal"|"high"|"unknown"`), `arm_openness`(str: `"closed"|"normal"|"open"|"unknown"`) — 모두 `analyze_window()` 내부에 이미 계산되어 있는 지역 변수
- Produces: `analyze_window()` 반환 dict의 `avatar_state` 값이 `"focused"|"engaged"|"confused"|"bored"|"unknown"` 중 하나 — 이번 계획 안에서 이 값을 소비하는 다음 태스크(Task 2)는 없음. 문자열 계약 자체가 산출물.

이 태스크는 기존 테스트 3개의 기댓값을 먼저 바꿔서 실패시키고(RED), 새 테스트 2개를 추가해서 역시 실패시킨 뒤, 구현으로 전부 통과(GREEN)시키는 순서로 진행한다.

- [ ] **Step 1: 기존 테스트 갱신 (실패하게 만듦) — good/bad 이름과 기댓값을 engaged/confused로 교체**

`backend/test_posture_analyzer.py`의 200~224행(`test_analyze_window_avatar_state_good_when_no_reasons`, `test_analyze_window_avatar_state_bad_when_reasons_present`)을 아래로 통째로 교체:

```python
def test_analyze_window_avatar_state_engaged_when_no_reasons_and_default_engagement():
    analyzer = PostureAnalyzer()

    frames = [_frame() for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] == []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "normal"
    assert result["avatar_state"] == "engaged"


def test_analyze_window_avatar_state_confused_when_reasons_present_and_default_engagement():
    analyzer = PostureAnalyzer()

    tilted_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
    )

    frames = [tilted_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] != []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "normal"
    assert result["avatar_state"] == "confused"
```

이 두 테스트는 기본 `_frame()` 픽스처가 `gesture_activity_level == "low"`이면서(손목이 프레임마다 그대로라 이동량 0) `arm_openness_level == "normal"`(팔꿈치/어깨 비율이 닫힘 임계값 0.8보다 큼)이 되는, **이미 확립된 픽스처 특성**을 이용한다 — 즉 "제스처는 적지만 팔은 안 오므려서 참여도는 높음" 케이스를 검증한다.

- [ ] **Step 2: 신규 테스트 추가 (실패함) — focused/bored: 참여도 낮음(팔 오므림) 케이스**

같은 파일에서, 방금 교체한 두 테스트 바로 뒤에 추가:

```python
def test_analyze_window_avatar_state_focused_when_no_reasons_and_low_engagement():
    analyzer = PostureAnalyzer()

    closed_arm_frame = _frame(
        left_elbow=(0.44, 0.55),
        right_elbow=(0.56, 0.55),
    )

    frames = [closed_arm_frame for _ in range(5)]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] == []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "closed"
    assert result["avatar_state"] == "focused"


def test_analyze_window_avatar_state_bored_when_reasons_present_and_low_engagement():
    analyzer = PostureAnalyzer()

    tilted_closed_frame = _frame(
        left_shoulder=(0.4, 0.35),
        right_shoulder=(0.6, 0.55),
        left_elbow=(0.44, 0.55),
        right_elbow=(0.56, 0.55),
    )

    frames = [tilted_closed_frame] * 4 + [_frame()]

    result = analyzer.analyze_window(frames)

    assert result["reasons"] != []
    assert result["gesture_activity_level"] == "low"
    assert result["arm_openness_level"] == "closed"
    assert result["avatar_state"] == "bored"
```

`closed_arm_frame`은 팔꿈치를 어깨 폭보다 훨씬 좁게 만들어 `arm_openness_ratio`(팔꿈치 간 거리 ÷ 어깨 너비)를 0.8 미만(닫힘 임계값 미만)으로 떨어뜨린다: 어깨 너비 0.2, 팔꿈치 너비 0.12 → 비율 0.6. `tilted_closed_frame`은 여기에 기존 `test_analyze_window_flags_shoulder_tilt_reason_when_exceed_ratio_high`와 동일한 어깨 기울기를 더해 `reasons`를 채운다.

- [ ] **Step 3: 스키마 호환성 테스트 갱신**

384~398행의 `test_analyze_window_result_is_compatible_with_posture_window_schema`에서 마지막 줄을 교체:

```python
    assert window.avatar_state == "engaged"
```

(기존 `assert window.avatar_state == "good"` 대체 — 이 테스트도 기본 `_frame()` 픽스처를 쓰므로 Step 1과 같은 이유로 `"engaged"`가 된다.)

- [ ] **Step 4: 테스트 실행해서 실패 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py -v`
Expected: Step 1~3에서 갱신/추가한 5개 테스트(`..._engaged_when...`, `..._confused_when...`, `..._focused_when...`, `..._bored_when...`, `..._compatible_with_posture_window_schema`)가 FAIL. 나머지 기존 테스트는 그대로 PASS.

- [ ] **Step 5: 구현 — 참여도 축 + 2×2 매핑**

`backend/app/services/posture_analyzer.py`에서 기존 `avatar_state` 계산부:

```python
        avatar_state = (
            "bad"
            if reasons
            else "good"
        )
```

를 아래로 교체:

```python
        low_engagement = (
            gesture_activity == "low"
            and arm_openness == "closed"
        )

        if reasons:
            avatar_state = (
                "bored"
                if low_engagement
                else "confused"
            )
        else:
            avatar_state = (
                "focused"
                if low_engagement
                else "engaged"
            )
```

(이 블록은 `reasons` 리스트 계산이 모두 끝난 직후, 최종 `return {` 문 바로 앞에 위치한다 — `gesture_activity`와 `arm_openness`는 이미 그 위에서 계산되어 있는 지역 변수이므로 새로 가져올 필요 없다.)

`signal_sufficient=False` 조기 반환 분기(`return {"signal_sufficient": False, "valid_frame_ratio": ..., "avatar_state": "unknown"}`)는 건드리지 않는다.

- [ ] **Step 6: 테스트 실행해서 통과 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py -v`
Expected: PASS (전체)

- [ ] **Step 7: 회귀 확인 — 자세 관련 나머지 파일도 함께**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py test_posture_frame_extractor.py test_posture_route.py test_posture_session_store.py test_presentation_analysis_service_posture.py -v`
Expected: PASS (전체)

- [ ] **Step 8: 커밋**

```bash
git add backend/app/services/posture_analyzer.py backend/test_posture_analyzer.py
git commit -m "feat: expand avatar_state to four expressions via engagement axis"
```

---

### Task 2: 코칭 프롬프트 규칙 28-10 문구 갱신

**Files:**
- Modify: `backend/app/services/coaching_service.py`
- Test: `backend/test_coaching_service_posture.py` (회귀 확인용, 새 테스트 추가 없음)

**Interfaces:**
- Consumes: Task 1에서 `avatar_state`가 낼 수 있는 값 집합 `{"focused", "engaged", "confused", "bored", "unknown"}` — 프롬프트 규칙 문구에 이 값들을 정확히 나열해야 함
- Produces: 없음 (프롬프트 텍스트 갱신으로 끝나는 태스크)

이 태스크는 프롬프트 문자열 리터럴 하나만 바꾸는 것이라 자동 테스트로 텍스트 내용 자체를 검증하지는 않는다 (기존 `test_coaching_service_posture.py`도 프롬프트의 리터럴 문구를 assert하지 않고 `_build_coaching_data`의 동작만 검증하는 패턴이다 — 이 패턴을 유지한다). 회귀 테스트로 기존 동작이 안 깨졌는지만 확인한다.

- [ ] **Step 1: 규칙 28-10 문구 갱신**

`backend/app/services/coaching_service.py`에서 아래 블록을 찾는다 (`[자세]` 규칙 섹션의 마지막, `28-9` 다음):

```python
28-10. avatar_state는 녹음 화면의 아바타 이모지를 그리기 위한
    UI 표시용 힌트일 뿐이다.
    avatar_state의 "good"/"bad"/"unknown" 값을 인용하거나
    코칭 근거로 삼지 마라. reasons와 수치 신호만 근거로 삼아라.
```

이 블록의 두 번째 문장만 아래로 교체 (나머지 문장은 그대로 유지):

```python
28-10. avatar_state는 녹음 화면의 아바타 이모지를 그리기 위한
    UI 표시용 힌트일 뿐이다.
    avatar_state의 "focused"/"engaged"/"confused"/"bored"/"unknown" 값을
    인용하거나 코칭 근거로 삼지 마라. reasons와 수치 신호만 근거로 삼아라.
```

- [ ] **Step 2: 회귀 테스트 실행**

Run: `cd backend && .venv/bin/pytest test_coaching_service.py test_coaching_service_posture.py -v`
Expected: PASS (전체 — 프롬프트 문구만 바뀌고 `_build_coaching_data`의 동작은 그대로이므로 기존 테스트가 깨지지 않아야 한다)

- [ ] **Step 3: 전체 백엔드 posture/coaching 관련 회귀 확인**

Run: `cd backend && .venv/bin/pytest test_posture_analyzer.py test_posture_frame_extractor.py test_posture_route.py test_posture_session_store.py test_presentation_analysis_service_posture.py test_coaching_service.py test_coaching_service_posture.py -v`
Expected: PASS (전체)

- [ ] **Step 4: 커밋**

```bash
git add backend/app/services/coaching_service.py
git commit -m "docs: update coaching prompt rule 28-10 for four-state avatar_state"
```

---

## 스코프 밖 (이번 계획에 포함하지 않음)

- `frontend/lib/avatar_widget.dart`의 이모지/색상 매핑 확장 — 사용자가 별도로 제작 중인 애니메이션으로 대체될 예정, 프론트 완성 후 수동 검증
- `frontend/lib/main.dart` — 이미 `avatar_state` 문자열을 그대로 전달하고 있어 변경 불필요
- 최종 리포트 UI에 4단계 표정 관련 요약 반영
