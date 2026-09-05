from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    host: str = "0.0.0.0"
    port: int = 8001
    log_level: str = "info"

    # Risk-free rate for Sharpe / Sortino (annualised)
    risk_free_rate: float = 0.05


settings = Settings()
