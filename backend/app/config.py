"""All configuration lives here, read from environment variables (see .env.example)."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Infrastructure
    database_url: str = "postgresql+psycopg2://documind:documind_pw@localhost:5432/documind"
    elasticsearch_url: str = "http://localhost:9200"
    es_index: str = "chunks"
    log_dir: str = "logs"
    sample_corpus_dir: str = "sample_corpus"

    # Gemini
    gemini_api_key: str = ""
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_llm_model: str = "gemini-2.5-flash"
    embedding_dimensions: int = 768

    # Security
    session_secret: str = "dev-secret-change-me"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    max_upload_mb: int = 10
    max_message_chars: int = 2000

    # RAG knobs
    chunk_size: int = 800
    chunk_overlap: int = 100
    retrieve_k: int = 20
    top_k: int = 5
    rrf_k: int = 60
    rewrite_followups: bool = True
    history_turns: int = 6  # how many previous messages are shown to the LLM

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
