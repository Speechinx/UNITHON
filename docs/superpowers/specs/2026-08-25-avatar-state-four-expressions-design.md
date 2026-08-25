# 설계: 아바타 4단계 표정 판정 로직 (백엔드)

> 작성일: 2026-08-25
> 관련 문서: `docs/superpowers/specs/2026-08-25-posture-avatar-reaction-design.md`(기존 good/bad/unknown 판정 설계), `docs/superpowers/plans/2026-08-25-posture-avatar-reaction.md`(1차 구현 계획)

---

## 1. 목표 & 원칙

- 기존 `avatar_state`(`"good"` / `"bad"` / `"unknown"`) 판정을 4단계 표정 + 신호부족으로 확장한다:
  - `"focused"` (집중) — 잘하고 있음
  - `"engaged"` (공감) — 더 좋음
  - `"confused"` (혼란) — 설명 방식 수정 필요
  - `"bored"` (지루함) — 템포/전달력 개선 필요
  - `"unknown"` (신호부족, 기존과 동일하게 유지)
- **이번 스코프는 백엔드 판정 로직만이다.** 프론트(`avatar_widget.dart`)는 손대지 않는다 — 프론트는 별도로 진행 중인 커스텀 애니메이션 작업이 끝난 뒤, 이 문서가 정의하는 `avatar_state` 문자열 값을 그대로 받아쓰는 계약(contract)만 지키면 된다. 프론트 쪽 수동 검증은 그쪽 작업이 끝난 뒤 사용자가 직접 진행한다.
- 새 신호나 새 카메라/모델 입력을 추가하지 않는다. 이미 계산되지만 지금은 어떤 판정에도 쓰이지 않는 `gesture_activity_level`(제스처 활동성)과 `arm_openness_level`(팔 벌어짐)에 처음으로 판정 역할을 부여한다.
- 판정은 순수 규칙 기반(2×2 표)이다. 새 서비스 클래스나 ML 모델을 도입하지 않는다.
- **원칙 구분**: 코칭 리포트 텍스트는 "측정된 사실만" 다뤄야 하지만(기존 원칙 유지), 아바타 표정 자체는 UI 연출이므로 "혼란처럼 보이는 자세" 같은 해석적 라벨을 붙이는 것을 허용한다. `coaching_service.py` 규칙 28-10이 이미 "avatar_state는 UI 힌트일 뿐 코칭 근거로 쓰지 마라"고 못박아두었으므로, 아바타의 해석적 라벨과 리포트의 사실 기반 서술은 서로 충돌하지 않는다.

---

## 2. 판정 로직 (`backend/app/services/posture_analyzer.py`)

### 2.1 안정성 축 (기존 로직 재사용)

기존 `reasons` 리스트(어깨 기울기·고개 숙임·상체 기울기·시선 이탈 중 하나라도 임계값 초과 시 채워짐)를 그대로 안정성 축으로 쓴다. 변경 없음.

### 2.2 참여도 축 (신규)

```python
low_engagement = (
    gesture_activity_level == "low"
    and arm_openness_level == "closed"
)
```

- `gesture_activity_level`과 `arm_openness_level`이 **둘 다** 가장 낮은 값(`"low"`, `"closed"`)일 때만 "참여도 낮음"으로 판정한다 (보수적 기준).
- 그 외 모든 조합(`normal`/`high`/`open`/`unknown` 포함, 둘 중 하나라도 낮음이 아니거나 신호 부족인 경우)은 "참여도 높음"으로 취급한다. 신호가 애매하거나 부족할 때 좋은 쪽을 기본값으로 주는 것은 기존 "신호 부족 시 억지 판정 안 함" 철학과 같은 방향이다.

### 2.3 최종 매핑

| 안정성(reasons) \ 참여도 | 높음 | 낮음 |
|---|---|---|
| 안정적 (reasons 없음) | `"engaged"` (공감) | `"focused"` (집중) |
| 불안정 (reasons 있음) | `"confused"` (혼란) | `"bored"` (지루함) |

```python
if reasons:
    avatar_state = "bored" if low_engagement else "confused"
else:
    avatar_state = "focused" if low_engagement else "engaged"
```

`signal_sufficient=False`(카메라 밖 이탈 등, 조기 반환 분기)일 때는 지금처럼 `avatar_state = "unknown"`을 그대로 유지한다 — 이 분기는 변경하지 않는다.

### 2.4 스키마 영향 (`backend/app/schemas/analysis_response.py`)

`PostureWindow.avatar_state`는 `str` 타입 그대로 두고 필드 자체는 바꾸지 않는다. 값 집합만 5개로 늘어난다.

---

## 3. 코칭 프롬프트 규칙 갱신 (`backend/app/services/coaching_service.py`)

규칙 28-10이 `"good"/"bad"/"unknown"`을 문자 그대로 나열하고 있으므로, 값이 바뀐 만큼 나열만 갱신한다:

- 기존: `avatar_state의 "good"/"bad"/"unknown" 값을 인용하거나 코칭 근거로 삼지 마라.`
- 변경: `avatar_state의 "focused"/"engaged"/"confused"/"bored"/"unknown" 값을 인용하거나 코칭 근거로 삼지 마라.`

규칙의 취지(코칭 근거로 쓰지 말 것)는 그대로 유지한다. 다른 규칙(28-1~28-9)은 변경하지 않는다.

---

## 4. 스코프 밖 (이번에 구현하지 않음)

- `frontend/lib/avatar_widget.dart`의 이모지/색상 매핑 확장 — 사용자가 직접 제작 중인 애니메이션으로 대체될 예정
- `frontend/lib/main.dart` — 이미 `avatar_state` 문자열을 그대로 `AvatarWidget`에 전달하고 있어 변경이 필요 없으며, 프론트 위젯 자체도 이번 스코프가 아니므로 손대지 않는다
- 최종 리포트 UI에 4단계 표정 관련 요약 반영

---

## 5. 테스트 전략

- `posture_analyzer.py`: 2×2 표의 4가지 조합(안정적+높음, 안정적+낮음, 불안정+높음, 불안정+낮음) 각각에 대해 `avatar_state`가 올바른 값인지 단위 테스트 (기존 `test_analyze_window_avatar_state_good_when_no_reasons` / `..._bad_when_reasons_present` 패턴을 4가지로 확장)
- `gesture_activity_level`/`arm_openness_level`이 `"unknown"`인 경우 "참여도 낮음" 조건을 만족하지 못해 항상 "참여도 높음" 쪽으로 판정되는지 확인하는 테스트
- `signal_sufficient=False` 조기 반환 분기가 여전히 `"unknown"`을 반환하는지 확인하는 기존 테스트가 깨지지 않는지 회귀 확인
- `coaching_service.py`: 규칙 28-10 문구 갱신은 `_build_coaching_data`의 동작을 바꾸지 않으므로 기존 `test_coaching_service_posture.py`가 그대로 통과해야 함 (프롬프트 텍스트 내용 자체를 단정하는 테스트는 없음 — 기존 패턴과 동일)
