from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router


app = FastAPI(
    title="AI Presentation Coach API",
    description="발표 음성을 분석하고 AI 코칭 결과를 반환합니다.",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    # `flutter run -d chrome`는 매번 임의의 포트에서 뜨므로 고정 목록만으로는
    # 막힌다. 로컬 개발 환경(localhost/127.0.0.1)의 모든 포트를 추가로 허용한다.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    router
)


@app.get("/")
def root():
    return {
        "message": "AI Presentation Coach API is running."
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }