from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "7Cs Disease Intelligence Platform"
    app_env: str = "local"

    database_url: str = Field(
        default="postgresql+psycopg://stratergic:stratergic@localhost:5432/stratergic_mapping",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="OPENAI_EMBEDDING_MODEL"
    )
    live_connectors_enabled: bool = Field(
        default=False, validation_alias="LIVE_CONNECTORS_ENABLED"
    )

    vector_db_path: str = Field(default="chroma_db", validation_alias="VECTOR_DB_PATH")
    vector_collection_name: str = Field(
        default="stratergic_upload_chunks", validation_alias="VECTOR_COLLECTION_NAME"
    )
    vector_embedding_dimensions: int = Field(
        default=1536, validation_alias="VECTOR_EMBEDDING_DIMENSIONS"
    )

    object_storage_endpoint: str = Field(
        default="http://localhost:9000", validation_alias="OBJECT_STORAGE_ENDPOINT"
    )
    object_storage_access_key: str = Field(
        default="minioadmin", validation_alias="OBJECT_STORAGE_ACCESS_KEY"
    )
    object_storage_secret_key: str = Field(
        default="minioadmin", validation_alias="OBJECT_STORAGE_SECRET_KEY"
    )
    object_storage_bucket: str = Field(
        default="stratergic-mapping", validation_alias="OBJECT_STORAGE_BUCKET"
    )
    object_storage_public_url: str = Field(
        default="http://localhost:9000", validation_alias="OBJECT_STORAGE_PUBLIC_URL"
    )

    ncbi_email: str | None = Field(default=None, validation_alias="NCBI_EMAIL")
    ncbi_api_key: str | None = Field(default=None, validation_alias="NCBI_API_KEY")
    ncbi_retmax: int = Field(default=100, ge=1, le=200, validation_alias="NCBI_RETMAX")
    ncbi_request_delay_seconds: float = Field(
        default=0.5, ge=0, validation_alias="NCBI_REQUEST_DELAY_SECONDS"
    )
    clinical_trials_page_size: int = Field(
        default=100, ge=1, le=1000, validation_alias="CLINICAL_TRIALS_PAGE_SIZE"
    )
    web_search_results_per_source: int = Field(
        default=100, ge=1, le=100, validation_alias="WEB_SEARCH_RESULTS_PER_SOURCE"
    )
    web_request_delay_seconds: float = Field(
        default=0.5, ge=0, validation_alias="WEB_REQUEST_DELAY_SECONDS"
    )
    internal_upload_top_k: int = Field(
        default=50, ge=1, le=500, validation_alias="INTERNAL_UPLOAD_TOP_K"
    )
    external_request_timeout_seconds: float = Field(
        default=30.0, gt=0, validation_alias="EXTERNAL_REQUEST_TIMEOUT_SECONDS"
    )
    external_request_retries: int = Field(
        default=4, ge=0, le=10, validation_alias="EXTERNAL_REQUEST_RETRIES"
    )
    bing_search_api_key: str | None = Field(default=None, validation_alias="BING_SEARCH_API_KEY")
    serpapi_api_key: str | None = Field(default=None, validation_alias="SERPAPI_API_KEY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
