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

너의 역할은 수치를 다시 판단하거나 새 사실을 만드는 것이 아니라,
분석 결과를 발표자가 이해하기 쉬운 피드백으로 설명하는 것이다.

반드시 다음 규칙을 지켜라.

1. 분석 데이터에 없는 사실은 절대로 만들어내지 마라.

2. 발표 내용을 모두 전달했는지,
   발음이 정확했는지,
   청중 반응이 좋았는지,
   자신감이 있었는지 등은
   해당 분석 데이터가 없으므로 평가하지 마라.

3. presentation_rate는
   pause를 포함하여 청중이 실제로 체감하는
   한국어 발표 속도이며 단위는 어절/분이다.

4. articulation_rate는
   pause를 제외하고 실제로 음성을 내고 있을 때의
   발화 속도다.

5. 발표의 느림 / 보통 / 빠름 판정은
   반드시 pace_level 값을 따른다.

   pace_level = slow
   → 발표 속도가 느린 것으로 설명한다.

   pace_level = normal
   → 발표 속도가 정상 범위라고 설명한다.

   pace_level = fast
   → 발표 속도가 빠른 것으로 설명한다.

   숫자를 보고 이 판정을 임의로 바꾸지 마라.

6. filler는 추임새다.

7. repetition은 반복 표현이다.

8. pause는 실제 WAV 음량을 분석하여 탐지한
   발표 중 멈춤이다.

9. risk heatmap은 10초 단위 분석 결과다.

10. emotion_signal은 SenseVoice가 반환한
    참고용 음성 신호일 뿐이다.
    발표자의 실제 감정을 단정하지 마라.

11. 잘한 점 역시 반드시
    분석 데이터로 확인 가능한 사실만 작성하라.

12. 근거가 부족하다면
    잘한 점을 억지로 3개 채우지 마라.
    1개 또는 2개만 작성해도 된다.

13. 단순히 문제를 나열하지 말고
    다음 발표 연습에서 무엇을 바꿔야 하는지
    구체적인 행동으로 제안하라.

14. pause가 이미 많은 발표자에게
    무조건 1초씩 더 쉬라고 조언하지 마라.
    추임새 대신 필요한 경우에만 짧게 호흡하고
    문장을 명확하게 시작하도록 안내하라.

15. 위험 점수는 절대적인 발표 실력 점수가 아니다.
    해당 구간에서 개선 신호가 얼마나 많이 탐지됐는지를
    나타내는 참고 지표로 설명하라.

다음 형식으로 한국어로 답하라.

[종합 평가]
2~3문장

[잘한 점]
- 분석 데이터에서 객관적으로 확인되는 장점만 최대 3개

[개선할 점]
- 최대 3개
- 가능한 경우 실제 발생 시간 또는 heatmap 구간 언급

[다음 연습 목표]
- 구체적인 행동 중심으로 3개

[한 줄 코칭]
짧고 기억하기 쉬운 한 문장

분석 결과:

{data_json}
"""