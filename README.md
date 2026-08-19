# 🎤 Presentation Coach AI

> AI 기반 발표 분석 및 발표 코칭 서비스

발표자의 음성을 분석하여  
말하기 속도, 침묵, 추임새, 반복 표현 등을 분석하고  
발표 중 개선이 필요한 구간을 시각화하는 AI Presentation Coach입니다.

---

## 🚀 Project Overview

발표 연습을 녹음한 음성 파일을 업로드하면  
음성 AI 모델을 이용하여 발표 내용을 분석합니다.

### 주요 분석 항목

- 🎙️ Speech-to-Text
- ⏱️ 발화 구간 및 타임스탬프
- 👤 화자 분석
- 🗣️ 말하기 속도(WPM)
- 🤫 침묵 분석
- 🧩 추임새 분석
- 🔁 반복 단어 분석
- 🔥 발표 위험 구간 분석
- 📊 시간대별 위험도 Heatmap
- 😊 감정 분석
- 🔊 음향 이벤트 분석

---

# 🏗️ Architecture

```text
                    🎙️ Audio
                       │
                       ▼
              ┌─────────────────┐
              │   SenseVoice    │
              │                 │
              │      STT        │
              │    Emotion      │
              │  Audio Event    │
              └────────┬────────┘
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
           FSMN-VAD   CAM++    Transcript
             │         │         │
             │         │         ▼
             │         │    Filler Analyzer
             │         │         │
             │         │         ├─ Known Fillers
             │         │         └─ Repetition
             │         │
             └─────────┼──────────────┐
                       │              │
                       ▼              ▼
                Speech Analyzer   Risk Analyzer
                       │              │
                       ├─ WPM         ├─ Risk Score
                       ├─ Silence     └─ Heatmap
                       └─ Speaking Time
                              │
                              ▼
                       📊 Analysis Result