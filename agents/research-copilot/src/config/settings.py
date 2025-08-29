"""Configuration management for LLM Release Radar Agent."""
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """LLM server configuration."""

    host: str = Field(
        default="localhost:11434",
        description="Environment variable: OLLAMA_HOST",
    )
    model: str = Field(
        default="qwen2:7b", description="Environment variable: OLLAMA_MODEL"
    )
    timeout: int = Field(default=60, description="Environment variable: LLM_TIMEOUT")
    max_retries: int = Field(
        default=3, description="Environment variable: LLM_MAX_RETRIES"
    )
    temperature: float = Field(
        default=0.1, description="Environment variable: LLM_TEMPERATURE"
    )
    max_tokens: int = Field(
        default=4000, description="Environment variable: LLM_MAX_TOKENS"
    )


class NotionSettings(BaseSettings):
    """Notion API configuration."""

    token: str = Field(..., description="Environment variable: NOTION_TOKEN")
    database_id: str = Field(
        ..., description="Environment variable: NOTION_DATABASE_ID"
    )
    page_size: int = Field(
        default=100, description="Environment variable: NOTION_PAGE_SIZE"
    )
    timeout: int = Field(default=30, description="Environment variable: NOTION_TIMEOUT")

    @field_validator("token")
    @classmethod
    def validate_token(cls, v):
        """Validate Notion token format."""
        if not v.startswith("secret_"):
            raise ValueError("Notion token must start with 'secret_'")
        return v


class SearchSettings(BaseSettings):
    """Web search configuration."""

    api_key: str = Field(..., description="Environment variable: SEARCH_API_KEY")
    engine: str = Field(
        default="serpapi", description="Environment variable: SEARCH_ENGINE"
    )
    results_limit: int = Field(
        default=20, description="Environment variable: SEARCH_RESULTS_LIMIT"
    )
    timeout: int = Field(default=30, description="Environment variable: SEARCH_TIMEOUT")


class ScrapingSettings(BaseSettings):
    """Web scraping configuration."""

    user_agent: str = Field(
        default="LLMReleaseRadar/1.0 (+https://github.com/your-username/agents)",
        env="USER_AGENT",
    )
    request_timeout: int = Field(
        default=30, description="Environment variable: REQUEST_TIMEOUT"
    )
    max_concurrent_requests: int = Field(
        default=5, description="Environment variable: MAX_CONCURRENT_REQUESTS"
    )
    rate_limit_delay: float = Field(
        default=1.0, description="Environment variable: RATE_LIMIT_DELAY"
    )
    max_retries: int = Field(
        default=3, description="Environment variable: SCRAPING_MAX_RETRIES"
    )


class MonitoringSettings(BaseSettings):
    """Monitoring and logging configuration."""

    log_level: str = Field(
        default="INFO", description="Environment variable: LOG_LEVEL"
    )
    log_format: str = Field(
        default="json", description="Environment variable: LOG_FORMAT"
    )
    metrics_port: int = Field(
        default=8080, description="Environment variable: METRICS_PORT"
    )
    health_check_port: int = Field(
        default=8081, description="Environment variable: HEALTH_CHECK_PORT"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class KubernetesSettings(BaseSettings):
    """Kubernetes deployment configuration."""

    namespace: str = Field(
        default="agents", description="Environment variable: K8S_NAMESPACE"
    )
    service_account: str = Field(
        default="llm-release-radar",
        description="Environment variable: K8S_SERVICE_ACCOUNT",
    )


class CacheSettings(BaseSettings):
    """Caching configuration."""

    ttl: int = Field(
        default=3600, description="Environment variable: CACHE_TTL"
    )  # 1 hour
    max_size: int = Field(
        default=1000, description="Environment variable: CACHE_MAX_SIZE"
    )


class SourceConfig(BaseSettings):
    """Source monitoring configuration."""

    enable_github_monitoring: bool = Field(
        default=True,
        description="Environment variable: ENABLE_GITHUB_MONITORING",
    )
    enable_google_monitoring: bool = Field(
        default=True,
        description="Environment variable: ENABLE_GOOGLE_MONITORING",
    )
    enable_microsoft_monitoring: bool = Field(
        default=True, env="ENABLE_MICROSOFT_MONITORING"
    )
    enable_openai_monitoring: bool = Field(
        default=True,
        description="Environment variable: ENABLE_OPENAI_MONITORING",
    )
    enable_anthropic_monitoring: bool = Field(
        default=True, env="ENABLE_ANTHROPIC_MONITORING"
    )
    enable_huggingface_monitoring: bool = Field(
        default=True, env="ENABLE_HUGGINGFACE_MONITORING"
    )


class SchedulingSettings(BaseSettings):
    """Scheduling configuration."""

    cron_schedule: str = Field(
        default="0 9 * * 1", description="Environment variable: CRON_SCHEDULE"
    )  # Monday 9 AM
    timezone: str = Field(default="UTC", description="Environment variable: TIMEZONE")


class ErrorHandlingSettings(BaseSettings):
    """Error handling configuration."""

    max_retry_attempts: int = Field(
        default=3, description="Environment variable: MAX_RETRY_ATTEMPTS"
    )
    retry_backoff_factor: float = Field(
        default=2.0, description="Environment variable: RETRY_BACKOFF_FACTOR"
    )
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Environment variable: CIRCUIT_BREAKER_THRESHOLD",
    )


class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    environment: str = Field(
        default="development", description="Environment variable: ENVIRONMENT"
    )
    debug: bool = Field(default=False, description="Environment variable: DEBUG")
    testing: bool = Field(default=False, description="Environment variable: TESTING")

    # Component settings
    llm: LLMSettings = Field(default_factory=LLMSettings)
    notion: NotionSettings = Field(default_factory=NotionSettings)
    search: SearchSettings = Field(default_factory=SearchSettings)
    scraping: ScrapingSettings = Field(default_factory=ScrapingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    kubernetes: KubernetesSettings = Field(default_factory=KubernetesSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    sources: SourceConfig = Field(default_factory=SourceConfig)
    scheduling: SchedulingSettings = Field(default_factory=SchedulingSettings)
    error_handling: ErrorHandlingSettings = Field(default_factory=ErrorHandlingSettings)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Note: Hardcoded source URLs and search queries have been removed.
# The new LLM-driven research approach dynamically discovers sources and generates
# queries based on the research topic and LLM intelligence.

# Global settings instance - initialized lazily
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
