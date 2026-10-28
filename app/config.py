from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Signal Lab Research Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_chat_path: str = "/api/chat"
    ollama_model: str = "qwen2.5:7b"
    # Split timeouts: fail fast on connect, allow long generation
    ollama_connect_timeout_seconds: float = 10.0
    ollama_read_timeout_seconds: float = 180.0
    # Soft concurrency hint for single-process deploys (not a global rate limiter)
    max_concurrent_asks: int = 4

    # Generation / metrics
    token_limit: int = 512
    context_window: int = 32768

    # CORS — comma-separated origins in .env
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173"
    )

    @property
    def ollama_chat_url(self) -> str:
        return f"{self.ollama_base_url.rstrip('/')}{self.ollama_chat_path}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
