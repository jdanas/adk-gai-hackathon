from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="FlowMind API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")

    google_cloud_project: str = Field(default="", alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_region: str = Field(default="asia-southeast1", alias="GOOGLE_CLOUD_REGION")
    vertex_ai_location: str = Field(default="asia-southeast1", alias="VERTEX_AI_LOCATION")
    vertex_ai_model: str = Field(default="gemini-2.5-pro", alias="VERTEX_AI_MODEL")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")

    alloydb_host: str = Field(default="127.0.0.1", alias="ALLOYDB_HOST")
    alloydb_port: int = Field(default=5432, alias="ALLOYDB_PORT")
    alloydb_database: str = Field(default="flowmind", alias="ALLOYDB_DATABASE")
    alloydb_user: str = Field(default="postgres", alias="ALLOYDB_USER")
    alloydb_password: str = Field(default="", alias="ALLOYDB_PASSWORD")
    alloydb_ssl: str = Field(default="prefer", alias="ALLOYDB_SSL")
    alloydb_dsn: str | None = Field(default=None, alias="ALLOYDB_DSN")

    notes_embedding_dim: int = Field(default=768, alias="NOTES_EMBEDDING_DIM")
    flowmind_notes_default_limit: int = Field(default=5, alias="FLOWMIND_NOTES_DEFAULT_LIMIT")

    mcp_server_name: str = Field(default="flowmind-mcp", alias="MCP_SERVER_NAME")
    mcp_transport: str = Field(default="streamable-http", alias="MCP_TRANSPORT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def database_url(self) -> str:
        if self.alloydb_dsn:
            return self.alloydb_dsn
        return (
            f"postgresql://{self.alloydb_user}:{self.alloydb_password}"
            f"@{self.alloydb_host}:{self.alloydb_port}/{self.alloydb_database}"
            f"?ssl={self.alloydb_ssl}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
