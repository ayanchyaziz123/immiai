from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Immigration AI API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./immigration_ai.db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # ML model
    base_model: str = "google/flan-t5-base"
    adapter_path: str = "backend/models/lora_adapter"
    onnx_path: str = "backend/models/onnx"
    use_onnx: bool = False
    max_input_tokens: int = 512
    max_new_tokens: int = 350
    num_beams: int = 4

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
