from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24 * 7

    # Storage
    data_dir: Path = BACKEND_DIR / "data"
    model_path: Path = BACKEND_DIR / "Model" / "plant-disease-model.pth"

    # LLM (Groq)
    groq_api_key: str = ""
    orchestrator_model: str = "openai/gpt-oss-120b"
    remedy_model: str = "openai/gpt-oss-120b"
    max_history_tokens: int = 8000

    # External services
    weather_api_key: str = ""
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    tavily_api_key: str = ""

    # Diagnosis
    confidence_threshold: float = 0.6
    outbreak_radius_km: float = 10.0
    outbreak_window_days: int = 14
    places_radius_km: float = 15.0

    # Knowledge base
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    kb_collection: str = "remedies"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "aurafarm.db"

    @property
    def checkpoint_db_path(self) -> Path:
        return self.data_dir / "checkpoints.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"


@lru_cache
def get_settings() -> Settings:
    return Settings()
