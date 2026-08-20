from typing import List

from pydantic import BaseModel


class PauseItem(
    BaseModel
):
    start: float
    end: float
    duration: float


class SpeechResult(
    BaseModel
):
    word_count: int

    presentation_duration: float
    speech_time: float

    presentation_rate: float
    articulation_rate: float

    pace_level: str

    internal_pause_time: float
    internal_pause_ratio: float

    internal_pauses: List[
        PauseItem
    ]


class SpeechEvent(
    BaseModel
):
    type: str
    text: str
    start: float
    end: float
    confidence: float


class RiskWindow(
    BaseModel
):
    start: float
    end: float
    duration: float

    word_count: int

    presentation_time: float
    speech_time: float

    presentation_rate: float
    articulation_rate: float

    pace_level: str

    pause_time: float
    pause_count: int

    long_pause_count: int
    very_long_pause_count: int

    filler_count: int
    repetition_count: int

    emotion_signal: str

    score: int
    level: str

    reasons: List[
        str
    ]


class RiskResult(
    BaseModel
):
    overall_score: int
    overall_level: str

    heatmap: List[
        RiskWindow
    ]


class Improvement(
    BaseModel
):
    title: str
    time_range: str
    description: str


class CoachingResult(
    BaseModel
):
    summary: str

    strengths: List[
        str
    ]

    improvements: List[
        Improvement
    ]

    practice_goals: List[
        str
    ]

    one_line_coaching: str


class AnalysisResponse(
    BaseModel
):
    transcript: str

    duration: float

    speech: SpeechResult

    fillers: List[
        SpeechEvent
    ]

    risk: RiskResult

    coaching: CoachingResult