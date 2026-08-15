from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multi-Tenant RAG API"
    VERSION: str = "0.1.0"
    
    # Database Settings
    DATABASE_URI: Optional[str] = None
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "rag_platform"

    @property
    def DATABASE_URL(self) -> str:
        # If a full URI is provided (e.g. from Render/Supabase), use it.
        if self.DATABASE_URI:
            # Ensure it uses asyncpg for SQLAlchemy async operations
            if self.DATABASE_URI.startswith("postgres://") or self.DATABASE_URI.startswith("postgresql://"):
                return self.DATABASE_URI.replace("postgres://", "postgresql+asyncpg://").replace("postgresql://", "postgresql+asyncpg://")
            return self.DATABASE_URI
        # Otherwise fallback to local docker connection
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Celery / Redis Settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Qdrant Vector DB Settings
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # Gemini AI Settings
    GEMINI_API_KEY: str = "" # To be provided in .env

    # Langfuse Observability
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"
    
    # CORS
    CORS_ORIGINS: str = ""

    # We load settings from a .env file if it exists
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

