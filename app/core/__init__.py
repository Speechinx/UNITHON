from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Presentation Coach AI"
    app_version: str = "0.1.0"

    sensevoice_device: str = "cpu"

    max_audio_size_mb: int = 100

    class Config:
        env_file = ".env"


settings = Settings()