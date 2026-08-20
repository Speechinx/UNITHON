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

            # SenseVoice 감정은 참고 신호
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

                "speech_rate": (
                    speech.get(
                        "speech_rate",
                        0,
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

아래 데이터는 발표 음성을 이미 분석한 결과다.

중요 규칙:

1. 제공된 분석 결과를 근거로만 코칭하라.
2. 숫자나 이벤트를 새로 추측하지 마라.
3. speech_rate는 한국어 어절/분이다.
4. filler는 추임새다.
5. repetition은 반복 표현이다.
6. pause는 WAV 음량 분석으로 탐지된 발표 중 멈춤이다.
7. risk heatmap은 10초 단위 분석 결과다.
8. emotion_signal은 SenseVoice의 참고 신호일 뿐이다.
   발표자의 실제 감정을 단정하지 마라.
9. 발표 내용 자체보다는 전달 방식과 발표 습관을 코칭하라.
10. 문제를 나열하는 데서 끝내지 말고
    다음 연습에서 어떻게 바꿀지 구체적으로 제안하라.

다음 형식으로 한국어로 답하라.

[종합 평가]
2~3문장

[잘한 점]
- 최대 3개

[개선할 점]
- 최대 3개
- 가능한 경우 문제가 발생한 시간 구간 언급

[다음 연습 목표]
- 행동 중심으로 3개

[한 줄 코칭]
짧고 기억하기 쉬운 한 문장

분석 결과:

{data_json}
"""