import pytest

from app.config import Settings, get_settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="test-model",
        token_limit=64,
        context_window=2048,
        ollama_connect_timeout_seconds=1.0,
        ollama_read_timeout_seconds=2.0,
        max_concurrent_asks=2,
        cors_origins="http://localhost:5173",
    )


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
