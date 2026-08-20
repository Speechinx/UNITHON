from dotenv import load_dotenv

# .env 파일을 먼저 로드
load_dotenv()

from fastapi import FastAPI

from app.api.routes import router


app = FastAPI(
    title="AI Presentation Coach API",
    description="발표 음성을 분석하고 AI 코칭 결과를 반환합니다.",
    version="1.0.0",
)


app.include_router(
    router
)


@app.get("/")
def root():
    return {
        "message": "AI Presentation Coach API is running."
    }