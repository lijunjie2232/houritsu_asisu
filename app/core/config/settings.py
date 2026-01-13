from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from shutil import copy


class Settings(BaseSettings):

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Japanese Law AI Agent"

    # Database Configuration
    POSTGRES_SERVER: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # Vector Database Configuration
    MILVUS_HOST: str = ""
    MILVUS_PORT: int = 0
    MILVUS_USER: str = ""
    MILVUS_PASSWORD: str = ""
    COLLECTION_NAME: str = ""

    # LLM Configuration
    OPENAI_API_KEY: str = ""
    MODEL_NAME: str = ""

    # Ollama Configuration
    OLLAMA_IP: str = ""
    OLLAMA_PORT: int = 0
    OLLAMA_MODEL: str = ""

    # Application Configuration
    DEBUG: bool = False
    MAX_HISTORY_LENGTH: int = 0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


if not Path(".env").is_file():
    copy(".env.example", ".env")

env_list = (
    ".env",
    ".env.local",
    ".env.prod",
    ".env.dev",
    ".env.test",
)
settings = Settings(
    _env_file=filter(
        lambda env: Path(env).is_file(),
        env_list,
    ),
    _env_file_encoding="utf-8",
)
