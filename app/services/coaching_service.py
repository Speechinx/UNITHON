import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


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
    ) -> dict:

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
                config=types.GenerateContentConfig(
                    response_mime_type=(
                        "application/json"
                    ),
                    response_schema={
                        "type": "object",
                        "properties": {
                            "summary": {
                                "type": "string"
                            },

                            "strengths": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            },

                            "improvements": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {
                                            "type": "string"
                                        },

                                        "time_range": {
                                            "type": "string"
                                        },

                                        "description": {
                                            "type": "string"
                                        },
                                    },

                                    "required": [
                                        "title",
                                        "time_range",
                                        "description",
                                    ],
                                },
                            },

                            "practice_goals": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                            },

                            "one_line_coaching": {
                                "type": "string"
                            },
                        },

                        "required": [
                            "summary",
                            "strengths",
                            "improvements",
                            "practice_goals",
                            "one_line_coaching",
                        ],
                    },
                ),
            )
        )

        if not response.text:
            return self._empty_result(
                "코칭 결과를 생성하지 못했습니다."
            )

        try:
            result = json.loads(
                response.text
            )

        except json.JSONDecodeError:
            return self._empty_result(
                "Gemini 응답을 JSON으로 변환하지 못했습니다."
            )

        return self._validate_result(
            result
        )

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

            "emotion_signal": (
                analysis_result.get(
                    "emotion",
                    "unknown",
                )
            ),

            "strength_signals": (
                analysis_result.get(
                    "strength_signals",
                    [],
                )
            ),

            "posture_signals": (
                analysis_result.get(
                    "posture",
                    {},
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

                "presentation_rate": (
                    speech.get(
                        "presentation_rate",
                        0,
                    )
                ),

                "articulation_rate": (
                    speech.get(
                        "articulation_rate",
                        0,
                    )
                ),

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
   → 발표 속도가 "느림"이라고 판단한다.
   
   pace_level = slightly_slow
   → 발표 속도가 "약간 느림"이라고 판단한다.
   
   pace_level = normal
   → 발표 속도가 "적절"하다고 판단한다.
   
   pace_level = slightly_fast
   → 발표 속도가 "약간 빠름"이라고 판단한다.
   
   pace_level = fast
   → 발표 속도가 "빠름"이라고 판단한다.

8. presentation_rate나 articulation_rate 숫자를 보고
   pace_level 판정을 임의로 변경하지 마라.

9. articulation_rate와 presentation_rate의 판정이 다르게 보이더라도 
발표 속도의 최종 판정은 반드시 pace_level을 따른다.
예를 들어 articulation_rate가 상대적으로 높더라도
presentation_rate가 낮고 pace_level이 slow라면
잦은 pause로 인해 전체 발표 템포가 느려졌다고 설명할 수 있다.


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


[자세]

28-1. posture_signals는 카메라 프레임에서 측정한 신체 자세 신호
    (어깨 기울기, 고개 숙임, 좌우 흔들림, 손 제스처 활동성)일 뿐이다.

28-2. posture_signals의 신호로 발표자의 자신감, 긴장 정도,
    실제 심리 상태를 단정하지 마라.

28-3. 각 구간의 signal_sufficient가 false라면
    해당 구간의 자세는 언급하지 마라.

28-4. shoulder_tilt_exceed_ratio나 head_down_exceed_ratio가 낮으면
    굳이 자세를 언급하지 않아도 된다.

28-5. reasons에 기록된 구체적인 수치·구간을 근거로만
    자세 피드백을 작성하라.

28-6. gesture_activity_level은 좋고 나쁨을 판단하는 지표가 아니라
    활동성 수준(낮음/보통/높음)일 뿐이다.
    "low"라고 해서 무조건 개선이 필요하다고 말하지 마라.


[잘한 점]

29. 잘한 점은 반드시 strength_signals를
    최우선 근거로 작성하라.

30. strength_signals는 별도의 분석 엔진이
    발표 속도, risk, 추임새, 반복, 멈춤 데이터를
    기반으로 계산한 객관적인 긍정 신호다.

31. strengths에 작성하는 내용은 원칙적으로
    strength_signals에 포함된 사실을 기반으로 해야 한다.

32. strength_signals에 없는 긍정적인 사실을
    임의로 추측하거나 만들어내지 마라.

33. "노력했다", "정보 전달을 잘했다",
    "발음이 명확했다", "준비가 잘 되어 있다",
    "자신감 있게 발표했다" 등의 표현은
    현재 데이터로 확인할 수 없으므로 사용하지 마라.

34. strength_signals에 여러 신호가 있더라도
    동일한 의미를 반복하지 마라.

35. 같은 시간 구간에서 여러 긍정 신호가 겹친 경우에는
    자연스럽게 하나의 장점으로 통합할 수 있다.

예:

strength_signals:
- 0~30초 안정 구간
- 0~30초 적절한 발표 속도
- 0~30초 추임새 없음

좋은 출력:
- 0~30초 구간에서는 적절한 속도를 유지하면서
  추임새 없이 안정적인 발표 흐름을 유지했습니다.

나쁜 출력:
- 0~30초 구간이 안정적이었습니다.
- 0~30초 속도가 적절했습니다.
- 0~30초 추임새가 없었습니다.

36. strength_signals가 없다면
    억지로 잘한 점을 생성하지 마라.

37. strength_signals가 없는 경우
    strengths에는 다음 문장 하나만 작성할 수 있다.

"현재 분석 데이터에서는 뚜렷한 강점을 판단하기 어렵습니다."

38. strengths는 최대 3개만 작성하라.

39. strength_signals가 2개 이상 존재한다면,
    의미가 중복되지 않는 범위에서 가능한 한 각 신호를
    strengths에 반영하라.

40. stable_delivery 신호는
    연속적으로 안정된 발표 구간을 나타내므로,
    다른 strength_signals와 의미가 중복되지 않는다면
    strengths에 우선적으로 반영하라.

41. 단순히 strengths의 개수를 채우기 위해
    서로 같은 의미의 긍정 평가를 반복하지 마라.   

42. 강점을 표현할 때 "매우 훌륭하다", "매우 좋다",
    "완벽하다", "탁월하다"처럼 데이터 근거보다
    강한 정도의 평가 표현은 사용하지 마라.

    strength_signals의 사실을 그대로 설명하고,
    필요한 경우 "안정적이었다", "적절했다",
    "탐지되지 않았다" 정도의 표현을 사용하라. 


[개선 조언]

43. improvements는 최대 3개만 작성하라.

44. 가장 중요한 문제부터 우선순위를 정하라.

45. 같은 원인을 표현만 바꾸어
    여러 항목으로 반복하지 마라.

46. 개선 조언은 다음 연습에서
    실제로 수행할 수 있는 행동이어야 한다.

좋은 예:
- 문장 첫 단어를 반복하지 않고 한 번만 말하는 연습
- 추임새가 나오려 할 때 문장을 잠시 정리한 뒤 바로 다음 문장 시작
- 의미 단위로 호흡 위치를 미리 표시하고 연습

나쁜 예:
- 더 자신감 있게 발표하세요.
- 발표를 더 잘하세요.
- 자연스럽게 말하세요.


[JSON 출력 규칙]

47. 반드시 JSON 객체 하나만 반환하라.

48. Markdown 코드블록을 사용하지 마라.

49. JSON 앞뒤에 설명 문장을 붙이지 마라.

50. 다음 필드를 반드시 포함하라.

- summary
- strengths
- improvements
- practice_goals
- one_line_coaching

51. summary는 문자열이며
    종합 평가를 2~3문장으로 작성한다.

52. strengths는 문자열 배열이다.
    객관적으로 확인 가능한 장점만 최대 3개 작성한다.

53. improvements는 객체 배열이며
    최대 3개 작성한다.

각 improvement는 반드시 다음 필드를 가진다.

- title
- time_range
- description

54. title은 짧은 문제 제목이다.

예:
"반복 표현 줄이기"
"추임새 줄이기"
"발표 템포 개선"

55. time_range는
    문제가 발생한 시간을 표현한다.

예:
"0~10초"
"13~16초"

정확한 시간 범위를 판단하기 어렵다면
빈 문자열 ""로 작성한다.

56. description은
    문제의 근거와 개선 방법을 함께 설명한다.

57. practice_goals는 문자열 배열이며
    실제 수행 가능한 연습 행동을 정확히 3개 작성한다.

58. one_line_coaching은
    짧고 기억하기 쉬운 한 문장으로 작성한다.

59. 모든 문자열은 한국어로 작성한다.


반환 JSON 형태는 반드시 다음 구조를 따른다.

{{
    "summary": "종합 평가",
    "strengths": [
        "객관적으로 확인 가능한 강점"
    ],
    "improvements": [
        {{
            "title": "개선 항목 제목",
            "time_range": "0~10초",
            "description": "문제의 근거와 구체적인 개선 방법"
        }}
    ],
    "practice_goals": [
        "연습 목표 1",
        "연습 목표 2",
        "연습 목표 3"
    ],
    "one_line_coaching": "한 줄 코칭"
}}


분석 결과:

{data_json}
"""

    def _validate_result(
        self,
        result: dict,
    ) -> dict:

        return {
            "summary": (
                result.get(
                    "summary",
                    "",
                )
            ),

            "strengths": (
                result.get(
                    "strengths",
                    [],
                )
            ),

            "improvements": (
                result.get(
                    "improvements",
                    [],
                )
            ),

            "practice_goals": (
                result.get(
                    "practice_goals",
                    [],
                )
            ),

            "one_line_coaching": (
                result.get(
                    "one_line_coaching",
                    "",
                )
            ),
        }

    def _empty_result(
        self,
        message: str,
    ) -> dict:

        return {
            "summary": message,
            "strengths": [],
            "improvements": [],
            "practice_goals": [],
            "one_line_coaching": "",
        }