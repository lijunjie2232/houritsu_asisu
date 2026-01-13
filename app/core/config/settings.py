import os

import tomli  # Need to install tomli for reading TOML files
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_var_value(value_str):
    """
    Parse a string like '${VAR_NAME:-default}' and return the environment variable value or default
    """
    if value_str.startswith("${") and "}" in value_str:
        # Extract the variable part like VAR_NAME:-default
        env_part = value_str[2:-1]  # Remove ${ and }
        if ":-" in env_part:
            var_name, default_val = env_part.split(":-", 1)
            return os.getenv(var_name, default_val)
        else:
            return os.getenv(env_part, "")
    return value_str


# Ensure config.toml exists by importing the config module
from . import config  # This triggers the initialization

# Load configuration from config.toml
config_path = os.path.join(os.path.dirname(__file__), "config.toml")
with open(config_path, "rb") as f:
    config_data = tomli.load(f)


class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = get_env_var_value(config_data["api"]["api_v1_str"])
    PROJECT_NAME: str = get_env_var_value(config_data["api"]["project_name"])

    # Database settings
    POSTGRES_SERVER: str = get_env_var_value(config_data["database"]["postgres_server"])
    POSTGRES_USER: str = get_env_var_value(config_data["database"]["postgres_user"])
    POSTGRES_PASSWORD: str = get_env_var_value(
        config_data["database"]["postgres_password"]
    )
    POSTGRES_DB: str = get_env_var_value(config_data["database"]["postgres_db"])

    # Vector database settings
    MILVUS_HOST: str = get_env_var_value(config_data["vector_database"]["milvus_host"])
    MILVUS_PORT: int = int(
        get_env_var_value(config_data["vector_database"]["milvus_port"])
    )
    MILVUS_USER: str = get_env_var_value(config_data["vector_database"]["milvus_user"])
    MILVUS_PASSWORD: str = get_env_var_value(
        config_data["vector_database"]["milvus_password"]
    )
    COLLECTION_NAME: str = get_env_var_value(
        config_data["vector_database"]["collection_name"]
    )

    # LLM settings
    OPENAI_API_KEY: str = get_env_var_value(config_data["llm"]["openai_api_key"])
    MODEL_NAME: str = get_env_var_value(config_data["llm"]["model_name"])

    # Application settings
    DEBUG: bool = (
        get_env_var_value(config_data["application"]["debug"]).lower() == "true"
    )
    MAX_HISTORY_LENGTH: int = int(
        get_env_var_value(config_data["application"]["max_history_length"])
    )

    model_config = SettingsConfigDict(case_sensitive=True)

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"


settings = Settings()
