"""
Application Settings using Pydantic Settings
"""

from functools import lru_cache
from typing import List

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    APP_NAME: str = Field(default="MAX Flowstudio")
    APP_VERSION: str = Field(default="0.1.0")
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    
    # Backend Server
    BACKEND_HOST: str = Field(default="localhost")
    BACKEND_PORT: int = Field(default=8005)
    
    # Frontend
    FRONTEND_URL: str = Field(default="http://localhost:3005")
    
    # Authentication
    AUTH_SERVER_URL: str = Field(default="http://localhost:8000")
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_MINUTES: int = Field(default=30)
    
    # OAuth 2.0 Configuration
    OAUTH_CLIENT_ID: str = Field(default="maxflowstudio")
    OAUTH_CLIENT_SECRET: str | None = Field(default=None)
    OAUTH_REDIRECT_URI: str = Field(default="http://localhost:3005/oauth/callback")
    OAUTH_SCOPES: List[str] = Field(default=[
        "read:profile", 
        "read:groups", 
        "manage:workflows"
    ])
    
    # Database
    DB_HOST: str = Field(default="172.28.32.1")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="2300")
    DB_NAME: str = Field(default="max_flowstudio")
    
    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> PostgresDsn:
        """Construct database URL from components."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            path=self.DB_NAME,
        )
    
    # RabbitMQ
    RABBITMQ_HOST: str = Field(default="localhost")
    RABBITMQ_PORT: int = Field(default=5672)
    RABBITMQ_USER: str = Field(default="guest")
    RABBITMQ_PASSWORD: str = Field(default="guest")
    RABBITMQ_VHOST: str = Field(default="/")
    
    @computed_field  # type: ignore[misc]
    @property
    def RABBITMQ_URL(self) -> str:
        """Construct RabbitMQ URL from components."""
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@"
            f"{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"
        )
    
    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    
    # LLM API Keys
    OPENAI_API_KEY: str | None = Field(default=None)
    ANTHROPIC_API_KEY: str | None = Field(default=None)
    GOOGLE_API_KEY: str | None = Field(default=None)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    
    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3005", "http://localhost:3006", "http://localhost:8000", "http://localhost:8005"]
    )
     
    # File Storage
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_UPLOAD_SIZE: int = Field(default=10485760)  # 10MB
    
    # RAG Configuration
    RAG_UPLOAD_DIR: str = Field(default="./uploads/rag")
    RAG_MAX_FILE_SIZE: int = Field(default=52428800)  # 50MB
    
    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    RAG_EMBEDDING_MODEL: str = Field(default="bge-m3")
    RAG_LLM_MODEL: str = Field(default="gemma3:1b")
    
    # Qdrant Configuration  
    QDRANT_URL: str = Field(default="http://172.28.36.241:6333")
    QDRANT_API_KEY: str = Field(default="my-super-secret-key-12345dsfmdw_efjdsfjkhqjksdhfmq_amn21984mnbfnmcvx9a0r")
    
    # RAG Processing Parameters
    RAG_CHUNK_SIZE: int = Field(default=1000)
    RAG_CHUNK_OVERLAP: int = Field(default=200)
    RAG_RETRIEVER_K: int = Field(default=10)
    RAG_RERANK_TOP_N: int = Field(default=3)
    
    # Re-ranker Configuration
    RAG_RERANKER_MODEL: str = Field(default="ms-marco-MiniLM-L-12-v2")
    RAG_RERANKER_CACHE_DIR: str = Field(default="/tmp/flashrank_cache")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()