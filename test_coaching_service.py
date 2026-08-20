from dotenv import load_dotenv

from app.services.analysis_service import (
    AnalysisService
)

from app.services.coaching_service import (
    CoachingService
)


load_dotenv()


audio_path = "audio/test.wav"


print("Loading AnalysisService...")

analysis_service = AnalysisService()

print("Starting analysis...")

analysis_result = (
    analysis_service.analyze(
        audio_path
    )
)

print(
    "Analysis complete!"
)


print("\nLoading CoachingService...")

coaching_service = CoachingService()

print("Generating coaching...")

coaching = (
    coaching_service.generate(
        analysis_result
    )
)


print(
    "\n===== AI COACHING ====="
)

print(
    coaching
)