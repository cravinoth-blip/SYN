from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Competitor Analysis"
    app_env: str = Field(default="local", validation_alias="APP_ENV")
    local_data_dir: Path = Field(default=Path("outputs/local_store"), validation_alias="LOCAL_DATA_DIR")
    generation_output_dir: Path = Field(
        default=Path("outputs/generation_runs"), validation_alias="GENERATION_OUTPUT_DIR"
    )

    snowflake_account: str | None = Field(default=None, validation_alias="SNOWFLAKE_ACCOUNT")
    snowflake_user: str | None = Field(default=None, validation_alias="SNOWFLAKE_USER")
    snowflake_password: str | None = Field(default=None, validation_alias="SNOWFLAKE_PASSWORD")
    snowflake_private_key_path: str | None = Field(
        default=None, validation_alias="SNOWFLAKE_PRIVATE_KEY_PATH"
    )
    snowflake_warehouse: str | None = Field(default=None, validation_alias="SNOWFLAKE_WAREHOUSE")
    snowflake_database: str = Field(
        default="COMMUNICATIONS__EU__DER__DEV", validation_alias="SNOWFLAKE_DATABASE"
    )
    snowflake_schema: str = Field(default="DEV", validation_alias="SNOWFLAKE_SCHEMA")
    strategic_workspace_table: str = Field(
        default="STRATEGIC_WORKSPACE", validation_alias="STRATEGIC_WORKSPACE_TABLE"
    )

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias="OPENAI_MODEL")
    ncbi_email: str | None = Field(default=None, validation_alias="NCBI_EMAIL")
    ncbi_api_key: str | None = Field(default=None, validation_alias="NCBI_API_KEY")
    live_connectors_enabled: bool = Field(
        default=False, validation_alias="LIVE_CONNECTORS_ENABLED"
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.local_data_dir.mkdir(parents=True, exist_ok=True)
    settings.generation_output_dir.mkdir(parents=True, exist_ok=True)
    return settings
