"""Application configuration."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "PatentAI"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/patentai"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 3600  # 1 hour
    
    # AI/Embeddings
    ollama_base_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    embed_dimensions: int = 768
    
    # LLM (via OpenRouter)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openai/gpt-4o-mini"
    
    # Search
    similarity_threshold: float = 0.7
    max_results: int = 20
    fuzzy_threshold: int = 80  # RapidFuzz score threshold
    
    # Prometheus
    metrics_enabled: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
