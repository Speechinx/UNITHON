# 설계: 자세 기반 실시간 반응형 아바타

> 작성일: 2026-08-25
> 관련 문서: `구현계획서_자세추적.md`(자세 추적 원설계), `backend/docs/superpowers/specs/2026-08-25-posture-upper-body-landmarks-design.md`, `frontend/docs/superpowers/specs/2026-08-25-posture-timeline-merge-design.md`

---

## 1. 목표 & 원칙

- 녹화 중인 발표자가 실시간으로 "지금 내 자세가 괜찮은지"를 직관적으로 알 수 있도록, 카메라 프리뷰 옆에 **단일 캐릭터 아바타**를 두고 자세 신호에 따라 표정을 바꾼다.
- "실시간"은 프레임 단위 초저지연이 아니라, 이미 검증된 posture window 주기(15초)마다 즉시 반응하는 것을 의미한다. 새로운 지연 요구사항을 만들지 않는다.
- **이번 스코프는 자세(어깨 기울기/고개 숙임/상체 기울어짐/시선 이탈) 신호만** 사용한다. 음성 기반 반응(추임새/속도 등)은 이번 스코프에서 제외한다 — 추후 별도 설계로 확장 가능하도록 인터페이스만 열어둔다(8절 참고).
- 기존 `구현계획서_자세추적.md`의 원칙을 그대로 계승한다: **측정된 기하학적 사실만 다룬다.** "긴장해 보였다" 같은 해석은 하지 않는다. 시선 관련 지표도 "고개가 정면 대비 N도 돌아감" 같은 기하학적 사실로만 표현하고, "시선을 피했다/집중하지 않았다" 같은 심리적 해석은 판정 로직 밖(문구/문서 수준)에서만 완곡하게 사용한다.
- 랜드마크 신뢰도가 낮은 구간은 기존 패턴과 동일하게 "신호 부족"으로 처리하고 억지로 판정하지 않는다.

---

## 2. 아키텍처 (변경 최소화)

새 엔드포인트, 새 모델, 새 통신 계층(WebSocket 등)을 도입하지 않는다. 기존 `/posture/window` 파이프라인을 확장하는 것만으로 구현한다.

```
[기존 파이프라인 — 변경 없음]
프론트: camera로 2~5fps JPEG 캡처 → 15초 버퍼 → POST /posture/window

[백엔드 — 확장]
PostureFrameExtractor: 귀 랜드마크(7, 8) 2개 추가 추출  (새 모델 불필요, 같은 Pose Landmarker 사용)
        ↓
PostureAnalyzer.analyze_window():
  - 기존: shoulder_tilt, head_down, torso_lean, arm_openness, gesture_activity, reasons
  - 신규: gaze_away_deg / gaze_away_exceed_ratio → reasons에 통합
  - 신규: avatar_state 판정 ('good' | 'bad' | 'unknown')  ← 서버가 판정 (프론트는 그대로 렌더링만)
        ↓
응답(JSON)에 avatar_state 필드 추가 (기존 응답 스키마에 필드만 추가, breaking change 없음)

[프론트 — 신규]
posture window 응답을 받는 콜백에서 avatar_state를 읽어
AvatarWidget의 상태를 갱신 → 표정 전환
```

---

## 3. 백엔드 상세

### 3.1 `posture_frame_extractor.py`

`LANDMARK_INDICES`에 추가:

```python
"left_ear": 7,
"right_ear": 8,
```

같은 `PoseLandmarker` 인스턴스에서 이미 계산되는 33개 랜드마크 중 2개를 더 꺼내는 것뿐이라 성능 영향 없음.

### 3.2 `posture_analyzer.py`

**`gaze_away_deg` 계산** (기존 `_head_down_deg`와 같은 스타일):

- 양 귀 중점 x좌표와 코 x좌표의 편차를, 귀 간 거리(정규화 기준)로 나눈 값을 각도로 환산
- 귀 visibility가 둘 다 충분한 프레임에서만 계산 (`_has_signal`로 신뢰도 체크 — 기존 `GESTURE_LANDMARKS`/`TORSO_LANDMARKS` 처리와 동일 패턴)
- 신뢰도 부족 시 해당 window의 시선 지표는 `"신호 부족"`으로 빠지고 전체 판정에서 제외 (기존 `torso_signal_sufficient` 패턴 재사용)

새 상수:
```python
GAZE_AWAY_THRESHOLD_DEG = 20.0  # 시작값 — 데모 리허설 중 실측 기반으로 조정
GAZE_LANDMARKS = ["left_ear", "right_ear"]
```

`reasons` 리스트에 기존 패턴대로 추가:
```python
if gaze_signal_sufficient and gaze_away_exceed_ratio >= REASON_EXCEED_RATIO_THRESHOLD:
    reasons.append(f"시선 이탈 {gaze_away_exceed_ratio * 100:.0f}% 구간")
```

**`avatar_state` 판정** (신규, 순수 규칙 기반):

```python
if not signal_sufficient:
    avatar_state = "unknown"   # 카메라 밖 이탈 등 — 중립 표정
elif reasons:                  # 기존 reasons 리스트가 하나라도 채워지면
    avatar_state = "bad"
else:
    avatar_state = "good"
```

`reasons`는 이미 shoulder_tilt/head_down/torso_lean/gaze_away를 모두 취합한 리스트이므로, 이 세 줄만 추가하면 판정 로직이 끝난다 — 별도 서비스 클래스 불필요.

### 3.3 응답 스키마

`/posture/window` 응답(현재 `analyze_window()`의 반환 dict)에 `avatar_state` 필드만 추가. `AnalysisResponse`(`analysis_response.py`)의 `posture` 필드는 이 window 결과를 그대로 리스트로 담고 있으므로 스키마 변경 없이 필드가 함께 실려간다 (최종 코칭 프롬프트에서는 무시해도 무방 — 코칭 텍스트 생성 로직은 건드리지 않음).

---

## 4. 프론트 상세

- posture window 응답 파싱하는 지점(현재 `posture_timeline.dart` / `main.dart`의 업로드 콜백)에서 `avatar_state` 필드를 읽어온다.
- 신규 `AvatarWidget`: 백엔드가 내려주는 `good`/`bad`/`unknown` 3가지 상태 + 녹화 시작 전에만 쓰이는 프론트 로컬 상태 `idle`(백엔드 응답과 무관, 초기값)까지 총 4가지 표정(정적 이미지 또는 아이콘)을 `AnimatedSwitcher`로 전환. 약간의 `AnimatedScale`/`AnimatedRotation`을 곁들여 "반응하는" 느낌을 준다. 외부 애니메이션 라이브러리 불필요.
- `ValueNotifier<String>`(또는 동등한 상태 홀더)을 두고, 매 window 응답 도착 시 갱신 → 위젯이 자동 리빌드.
- 배치 위치: 카메라 프리뷰 옆(또는 위) — 기존 녹화 화면 레이아웃에 자연스럽게 추가.

---

## 5. MVP 범위

**이번 스코프 (전부 필수)**
- 귀 랜드마크 추가
- `gaze_away` 계산 + `reasons` 통합
- `avatar_state` 판정 (good/bad/unknown)
- 프론트 `AvatarWidget` + window 응답 연동

**이번 스코프 제외 (문서만 남김, 구현 안 함)**
- 음성 신호 연동 (10~15초 윈도잉으로 추임새/속도 반영) — 추후 별도 설계
- 다중 청중 캐릭터
- good/bad 이진을 넘어선 세분화된 감정 상태(혼란/산만 등)
- 최종 리포트에 시선 처리 요약 반영

---

## 6. 리스크 및 대응

| 리스크 | 대응 |
|---|---|
| 2D 랜드마크만으로는 고개 회전(yaw) 추정이 근사치 (depth 정보 없음) | "시선"이 아니라 "고개가 정면 대비 회전한 정도"라는 기하학적 사실로만 계산·표현 (1절 원칙과 동일) |
| 완전 옆모습 등 극단적 각도에서 귀 visibility 저하 | 기존 신뢰도 부족 처리 패턴(`_has_signal`)으로 해당 프레임/지표를 신호 부족 처리 — 전체 판정은 죽지 않음 |
| `avatar_state` 이진 판정이 데모 중 너무 민감하거나 둔감할 수 있음 | threshold를 클래스 상수로 분리해 리허설 중 즉시 튜닝 가능하게 함 |
| 표정 전환이 너무 자주/급격하게 바뀌면 산만해 보일 수 있음 | `AnimatedSwitcher` 전환 시간을 충분히 주고, 연속 같은 상태면 리빌드 스킵 (프론트 구현 시 고려) |

---

## 7. 테스트 전략

- `posture_analyzer.py`: 정면/좌우로 고개 돌린 정적 테스트 랜드마크로 `gaze_away_deg` 단위 테스트 (기존 `test_posture_analyzer.py` 패턴 재사용)
- `avatar_state` 판정 단위 테스트: reasons 없음 → good, reasons 있음 → bad, signal_sufficient=False → unknown
- 프론트: mock window 응답으로 `AvatarWidget`이 상태 전환 시 올바른 표정으로 바뀌는지 수동 검증

---

## 8. 향후 확장 여지 (이번 스코프 아님)

음성 신호를 나중에 추가할 경우, `avatar_state` 판정 지점(3.2절)에 posture 신호와 함께 speech window 신호를 입력으로 받는 형태로 자연스럽게 확장 가능하도록, 판정 로직을 별도 함수로 분리해두는 것을 권장한다(단, 이번 스코프에서 서비스 클래스로 분리할 필요는 없음 — 3줄짜리 로직을 굳이 추상화하지 않는다. 나중에 실제로 확장할 때 리팩터링).
