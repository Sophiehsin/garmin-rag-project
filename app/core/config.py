"""Core configuration — reads from environment variables, falls back to local Docker defaults."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "test123"
    db_name: str = "vectordb"
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_collection: str = "garmin_health"
    google_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
