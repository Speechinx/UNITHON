import json
import os

from google import genai


class CoachingService:
    def __init__(self):
        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY가 설정되지 않았습니다."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.1-flash-lite",
        )

    def generate(
        self,
        analysis_result: dict,
    ) -> str:

        coaching_data = (
            self._build_coaching_data(
                analysis_result
            )
        )

        prompt = self._build_prompt(
            coaching_data
        )

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
        )

        if not response.text:
            return (
                "코칭 결과를 생성하지 못했습니다."
            )

        return response.text.strip()

    def _build_coaching_data(
        self,
        analysis_result: dict,
    ) -> dict:

        speech = analysis_result.get(
            "speech",
            {},
        )

        risk = analysis_result.get(
            "risk",
            {},
        )

        fillers = analysis_result.get(
            "fillers",
            [],
        )

        return {
            "transcript": (
                analysis_result.get(
                    "transcript",
                    "",
                )
            ),

            # 참고 신호일 뿐 실제 감정으로 단정 금지
            "emotion_signal": (
                analysis_result.get(
                    "emotion",
                    "unknown",
                )
            ),

            "speech": {
                "word_count": (
                    speech.get(
                        "word_count",
                        0,
                    )
                ),

                "presentation_duration": (
                    speech.get(
                        "presentation_duration",
                        0,
                    )
                ),

                "speech_time": (
                    speech.get(
                        "speech_time",
                        0,
                    )
                ),

                # 청중이 체감하는 발표 템포
                "presentation_rate": (
                    speech.get(
                        "presentation_rate",
                        0,
                    )
                ),

                # 실제 음성을 낼 때의 발화 속도
                "articulation_rate": (
                    speech.get(
                        "articulation_rate",
                        0,
                    )
                ),

                # 우리 분석 엔진이 이미 판정한 값
                "pace_level": (
                    speech.get(
                        "pace_level",
                        "unknown",
                    )
                ),

                "internal_pause_time": (
                    speech.get(
                        "internal_pause_time",
                        0,
                    )
                ),

                "internal_pause_ratio": (
                    speech.get(
                        "internal_pause_ratio",
                        0,
                    )
                ),

                "internal_pauses": (
                    speech.get(
                        "internal_pauses",
                        [],
                    )
                ),
            },

            "speech_events": fillers,

            "risk": {
                "overall_score": (
                    risk.get(
                        "overall_score",
                        0,
                    )
                ),

                "overall_level": (
                    risk.get(
                        "overall_level",
                        "low",
                    )
                ),

                "heatmap": (
                    risk.get(
                        "heatmap",
                        [],
                    )
                ),
            },
        }

    def _build_prompt(
        self,
        coaching_data: dict,
    ) -> str:

        data_json = json.dumps(
            coaching_data,
            ensure_ascii=False,
            indent=2,
        )

        return f"""
너는 한국어 발표 코칭 AI다.

아래 데이터는 발표 음성을 별도의 분석 엔진이
이미 분석한 결과다.

너의 역할은 새로운 분석을 수행하는 것이 아니라,
주어진 분석 결과를 발표자가 이해하기 쉬운
코칭 문장으로 변환하는 것이다.

반드시 아래 규칙을 지켜라.


[핵심 원칙]

1. 분석 데이터에 없는 사실은 절대로 만들어내지 마라.

2. 수치를 보고 새로운 사실을 추측하지 마라.

3. 아래 항목들은 분석 데이터가 없으므로
   절대로 평가하거나 추론하지 마라.

   - 발음 정확도
   - 발성의 명확성
   - 자신감
   - 발표자의 노력
   - 청중의 이해도
   - 청중의 반응
   - 발표 내용의 완성도
   - 준비 정도
   - 발표 내용을 모두 전달했는지 여부
   - 발표자의 실제 감정

4. transcript는
   반복 표현이나 추임새 등
   이미 탐지된 이벤트의 문맥을 확인하는 용도로만 사용하라.

   transcript만 보고
   발표 내용의 품질이나 논리성을 평가하지 마라.


[말하기 속도]

5. presentation_rate는
   pause를 포함하여 청중이 실제로 체감하는
   발표 속도이며 단위는 '어절/분'이다.

6. articulation_rate는
   pause를 제외하고 실제 음성을 내고 있을 때의
   발화 속도다.

7. 발표 속도의 최종 판정은
   반드시 pace_level을 따른다.

   pace_level = slow
   → 발표 속도가 느린 편이라고 설명한다.

   pace_level = normal
   → 발표 속도가 정상 범위라고 설명한다.

   pace_level = fast
   → 발표 속도가 빠른 편이라고 설명한다.

8. presentation_rate나 articulation_rate 숫자를 보고
   pace_level 판정을 임의로 변경하지 마라.

9. articulation_rate가 정상적으로 보이더라도
   presentation_rate가 느리고 pace_level이 slow라면
   "실제로 말을 할 때의 속도와 달리,
   잦은 pause 때문에 전체 발표 템포가 느려졌다"
   정도로 설명할 수 있다.


[Pause]

10. pause는 WAV 음량 분석으로 탐지된
    발표 중 실제 멈춤 구간이다.

11. internal_pause_ratio는
    전체 발표 구간 중 내부 pause가 차지하는 비율이다.

12. pause가 많다고 해서
    모든 pause가 나쁘다고 단정하지 마라.

13. pause 횟수와 비율이 높거나
    위험 구간에 집중되어 있을 때만
    발표 흐름이 끊길 가능성이 있다고 설명하라.

14. pause가 이미 많은 발표자에게
    "1초씩 더 쉬어라"와 같은 조언을 하지 마라.

15. 추임새 대신 pause를 활용하라고 조언할 경우에도
    "필요한 경우에만 짧게 호흡한 뒤
    다음 문장을 명확하게 시작하라"
    정도로 표현하라.


[추임새와 반복]

16. filler는 추임새다.

17. repetition은 반복 표현이다.

18. 실제 탐지된 filler와 repetition만 언급하라.

19. 문제가 발생한 시간이 제공되어 있다면
    가능한 한 시간 구간을 함께 설명하라.

20. 단순히 "추임새가 많다"고 말하지 말고
    실제 탐지된 단어 예시를 사용할 수 있다.


[Risk]

21. risk heatmap은 10초 단위 분석 결과다.

22. risk score는 발표 실력 점수가 아니다.

23. risk score는 해당 구간에서
    개선이 필요한 신호가 얼마나 많이 탐지됐는지를
    나타내는 참고 지표다.

24. high / medium / low를
    발표자의 능력이나 실력 수준으로 표현하지 마라.

25. 위험도가 높은 구간에서는
    reasons에 기록된 실제 원인을 중심으로 설명하라.


[Emotion]

26. emotion_signal은 SenseVoice가 제공한
    참고용 음성 신호일 뿐이다.

27. emotion_signal이 sad, happy, angry 등으로 나오더라도
    발표자의 실제 감정이라고 단정하지 마라.

28. 특별한 이유가 없다면
    emotion_signal을 코칭에서 굳이 언급하지 않아도 된다.


[잘한 점]

29. 잘한 점 역시 반드시
    분석 데이터에서 객관적으로 확인 가능한 사실만 작성하라.

30. "노력했다", "정보 전달을 잘했다",
    "발음이 명확했다", "준비가 잘 되어 있다" 등의 표현은
    현재 데이터만으로 확인할 수 없으므로 사용하지 마라.

31. 객관적으로 확인 가능한 장점이 없다면
    억지로 장점을 만들지 마라.

32. 명확한 장점이 없는 경우에는 다음과 같이 작성할 수 있다.

    - 현재 분석 데이터에서는 뚜렷한 강점을 판단하기 어렵습니다.

33. 잘한 점은 반드시 3개를 채울 필요가 없다.
    0~3개까지 작성할 수 있다.


[개선 조언]

34. 개선할 점은 최대 3개만 제시하라.

35. 가장 중요한 문제부터 우선순위를 정하라.

36. 같은 원인을 표현만 바꾸어
    여러 항목으로 반복하지 마라.

37. 개선 조언은 다음 연습에서
    실제로 수행할 수 있는 행동이어야 한다.

좋은 예:
- 문장 첫 단어를 반복하지 않고 한 번만 말하는 연습
- 추임새가 나오려 할 때 문장을 잠시 정리한 뒤 바로 다음 문장 시작
- 의미 단위로 호흡 위치를 미리 표시하고 연습

나쁜 예:
- 더 자신감 있게 발표하세요.
- 발표를 더 잘하세요.
- 자연스럽게 말하세요.


[출력 형식]

반드시 다음 형식으로 한국어로 답하라.

[종합 평가]
2~3문장.
가장 중요한 발표 특성을 요약한다.

[잘한 점]
- 객관적으로 확인 가능한 내용만 작성
- 최대 3개
- 없다면 "현재 분석 데이터에서는 뚜렷한 강점을 판단하기 어렵습니다."라고 작성

[개선할 점]
- 최대 3개
- 가능하면 실제 시간 구간을 함께 언급
- 분석 데이터에 있는 근거를 중심으로 설명

[다음 연습 목표]
- 구체적인 행동 중심으로 정확히 3개

[한 줄 코칭]
- 짧고 기억하기 쉬운 한 문장
- 분석 결과와 직접 연결된 조언


분석 결과:

{data_json}
"""