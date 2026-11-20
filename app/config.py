"""Configuración centralizada. Todo valor sensible viene de variables de entorno / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "nvidia/nemotron-3.5-super-vl:free"
    llm_timeout_seconds: float = 45.0
    # Reintentos extra cuando el LLM responde con un JSON inválido o incompleto.
    llm_max_retries: int = 2


@lru_cache
def get_settings() -> Settings:
    return Settings()
