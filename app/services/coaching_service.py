import json
import os

from openai import OpenAI


class CoachingService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv(
                "OPENAI_API_KEY"
            )
        )

        self.model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna",
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
            self.client.responses.create(
                model=self.model,
                input=prompt,
            )
        )

        return response.output_text.strip()

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

        # GPT에게 불필요하게 거대한
        # normalized_words / timestamp 원본까지
        # 전부 넘기지 않는다.
        return {
            "transcript": (
                analysis_result.get(
                    "transcript",
                    "",
                )
            ),

            # 감정은 보조 신호일 뿐
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

아래 데이터는 음성을 이미 분석한 결과다.
숫자나 이벤트를 새로 추측하지 말고
제공된 분석 결과를 근거로만 코칭하라.

중요 규칙:

1. speech_rate는 한국어 '어절/분'이다.
2. filler는 추임새다.
3. repetition은 반복 표현이다.
4. pause는 실제 WAV 음량 분석으로 탐지된 발표 중 멈춤이다.
5. risk heatmap은 10초 단위 발표 위험 분석이다.
6. emotion_signal은 SenseVoice의 보조 신호일 뿐이다.
   사용자의 실제 감정을 단정하지 마라.
7. 단순히 점수를 나열하지 말고
   발표자가 다음 연습에서 무엇을 바꾸면 되는지 설명하라.
8. 과도하게 부정적인 표현은 피하고,
   구체적이고 실행 가능한 피드백을 제공하라.
9. 분석 데이터에 없는 사실은 만들지 마라.
10. transcript의 발표 내용 자체를 비판하기보다
    전달 방식과 발표 습관을 중심으로 코칭하라.

다음 형식으로 한국어로 답하라.

[종합 평가]
2~3문장

[잘한 점]
- 최대 3개

[개선할 점]
- 최대 3개
- 가능하면 문제가 발생한 시간 구간을 언급

[다음 연습 목표]
- 가장 중요한 행동 3개

[한 줄 코칭]
짧고 기억하기 쉬운 한 문장

분석 결과:

{data_json}
"""