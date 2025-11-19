from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field

# Load .env file from project root
# _project_root = Path(__file__).parent.parent.parent
# _env_file = _project_root / ".env"
load_dotenv()


class Settings(BaseSettings):
    """Base settings for the application."""

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    
    # Application settings
    APP_NAME: str = "RJM Backend Core"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "RJM MIRA backend core API"
    APP_AUTHOR: str = "CorpusAI Development Team"

    DATABASE_URL: str = ""
    LOCAL_SQLITE_PATH: str = "sqlite+aiosqlite:///./local.db"
    
    SUPABASE_DATABASE_NAME: str = "postgres"
    SUPABASE_DATABASE_USER: str = "postgres"
    SUPABASE_DATABASE_PASSWORD: str = ""
    SUPABASE_DATABASE_HOST: str = ""
    SUPABASE_DATABASE_PORT: int = 5432
    
    # Supabase Auth settings
    SUPABASE_URL: str = Field(default="", description="Supabase project URL (https://xxx.supabase.co)")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase anonymous/public key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="", description="Supabase service role key (for admin operations)")

    # Local auth fallback (dev only)
    LOCAL_AUTH_SECRET: str = "JWT_SECRET_KEY"
    LOCAL_AUTH_TOKEN_EXP_SECONDS: int = 3600

    @computed_field
    @property
    def effective_database_url(self) -> str:
        """Resolve the database URL for the application.

        Priority:
        1. Explicit DATABASE_URL (Postgres, SQLite, etc.)
        2. Supabase Postgres URL built from SUPABASE_* components
        3. Local SQLite fallback for development: LOCAL_SQLITE_PATH
        """
        # Check if DATABASE_URL is set and not empty/whitespace
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            return self.DATABASE_URL.strip()
        # Fallback to SUPABASE_* components
        if self.SUPABASE_DATABASE_HOST and self.SUPABASE_DATABASE_HOST.strip() and self.SUPABASE_DATABASE_PASSWORD and self.SUPABASE_DATABASE_PASSWORD.strip():
            return (
                f"postgresql://{self.SUPABASE_DATABASE_USER}:{self.SUPABASE_DATABASE_PASSWORD}@"
                f"{self.SUPABASE_DATABASE_HOST}:{self.SUPABASE_DATABASE_PORT}/{self.SUPABASE_DATABASE_NAME}?sslmode=require"
            )
        # Final fallback: local SQLite DB for development
        if self.LOCAL_SQLITE_PATH and self.LOCAL_SQLITE_PATH.strip():
            return self.LOCAL_SQLITE_PATH.strip()
        return "sqlite+aiosqlite:///./local.db"


    # OpenAI settings
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TOP_P: float = 1.0
    OPENAI_FREQUENCY_PENALTY: float = 0.0
    OPENAI_PRESENCE_PENALTY: float = 0.0
    OPENAI_STOP: str = ""
    OPENAI_N: int = 1

    # OpenAI embedding settings
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_EMBEDDING_TEMPERATURE: float = 0.7
    OPENAI_EMBEDDING_MAX_TOKENS: int = 1000
    OPENAI_EMBEDDING_TOP_P: float = 1.0
    OPENAI_EMBEDDING_FREQUENCY_PENALTY: float = 0.0
    OPENAI_EMBEDDING_PRESENCE_PENALTY: float = 0.0
    OPENAI_EMBEDDING_STOP: str = ""
    OPENAI_EMBEDDING_N: int = 1

    # Pinecone / vector store settings
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "rjm-mira-docs"
    PINECONE_REGION: str = "us-east-1"

    # RJM document corpus settings
    RJM_DOCS_DIR: str = "rjm_docs"  # Directory (relative to project root) containing RJM *.txt docs


settings = Settings()