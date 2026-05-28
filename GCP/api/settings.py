"""Configuración de la API por variables de entorno."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores configurables para ejecutar la API en Cloud Run o localmente."""

    model_config = SettingsConfigDict(env_prefix="MSMX_API_", env_file=".env", extra="ignore")

    app_name: str = "Movilidad Social MX API"
    app_version: str = "0.1.0"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    model_path: Path = Field(default=Path("models/modelo_entrenado.joblib"))
    model_cache_ttl_seconds: int = 12 * 60 * 60
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve settings cacheados para evitar relecturas de entorno por request."""

    return Settings()
