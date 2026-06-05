"""Core configuration — reads from environment variables, falls back to local Docker defaults."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "test123"
    db_name: str = "vectordb"

    # Embeddings & vector store
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_collection: str = "garmin_health"

    # LLM (Gemini)
    google_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    # JWT auth (Task 4)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 30

    # Google OAuth (Task 4)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Read-only DB URL for sql_retriever (Task 10); defaults to main DB if not set
    readonly_db_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
