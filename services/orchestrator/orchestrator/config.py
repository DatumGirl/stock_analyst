from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    supabase_url: str = ""
    supabase_service_role_key: str = ""

    quant_service_url: str = "http://localhost:8001"
    graph_service_url: str = "http://localhost:8003"

    host: str = "0.0.0.0"
    port: int = 8002
    log_level: str = "info"

    # Safety: never run autonomous analysis on more than this many tickers in one call
    max_compare_tickers: int = 4


settings = Settings()
