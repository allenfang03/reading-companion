from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: Optional[str] = None
    database_path: str = "reading_companion.db"
    llm_model: str = "claude-sonnet-5"
    llm_timeout: int = 60
    fuzzy_match_threshold: int = 85
    offset_bucket_size: int = 500
    context_snippet_chars: int = 50
    max_tokens_recap: int = 600
    max_tokens_sub_recap: int = 300
    max_tokens_per_chunk: int = 12000
    use_llm_for_extraction: bool = False  # Set to True only if you want LLM-based character extraction

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        env_file_encoding = "utf-8"


settings = Settings()
