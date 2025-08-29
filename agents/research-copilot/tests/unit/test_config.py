"""Unit tests for configuration management."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from src.config import (
    LLMSettings,
    MonitoringSettings,
    NotionSettings,
    ScrapingSettings,
    SearchSettings,
    Settings,
    get_settings,
    reload_settings,
)


class TestLLMSettings:
    """Test LLM configuration settings."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = LLMSettings(
            host="localhost:11434",
            model="qwen2:7b",
            timeout=60,
            max_retries=3,
            temperature=0.1,
            max_tokens=4000,
        )

        assert settings.host == "localhost:11434"
        assert settings.model == "qwen2:7b"
        assert settings.timeout == 60
        assert settings.max_retries == 3
        assert settings.temperature == 0.1
        assert settings.max_tokens == 4000

    def test_custom_values(self):
        """Test custom configuration values."""
        settings = LLMSettings(
            host="test-host:8080",
            model="test-model",
            timeout=30,
            max_retries=5,
            temperature=0.5,
            max_tokens=2000,
        )

        assert settings.host == "test-host:8080"
        assert settings.model == "test-model"
        assert settings.timeout == 30
        assert settings.max_retries == 5
        assert settings.temperature == 0.5
        assert settings.max_tokens == 2000


class TestNotionSettings:
    """Test Notion configuration settings."""

    def test_valid_configuration(self):
        """Test valid Notion configuration."""
        settings = NotionSettings(
            token="secret_test_token",
            database_id="test_database_id",
            page_size=100,
            timeout=30,
        )

        assert settings.token == "secret_test_token"
        assert settings.database_id == "test_database_id"
        assert settings.page_size == 100
        assert settings.timeout == 30

    def test_missing_required_fields(self):
        """Test validation of required fields."""
        with pytest.raises(ValidationError):
            NotionSettings()

    def test_invalid_token_format(self):
        """Test validation of token format."""
        with pytest.raises(ValidationError, match="must start with 'secret_'"):
            NotionSettings(token="invalid_token", database_id="test_database_id")


class TestSearchSettings:
    """Test search configuration settings."""

    def test_valid_configuration(self):
        """Test valid search configuration."""
        settings = SearchSettings(
            api_key="test_api_key",
            engine="serpapi",
            results_limit=20,
            timeout=30,
        )

        assert settings.api_key == "test_api_key"
        assert settings.engine == "serpapi"
        assert settings.results_limit == 20
        assert settings.timeout == 30

    def test_missing_api_key(self):
        """Test validation when API key is missing."""
        with pytest.raises(ValidationError):
            SearchSettings()


class TestScrapingSettings:
    """Test scraping configuration settings."""

    def test_default_values(self):
        """Test default scraping configuration."""
        settings = ScrapingSettings(
            user_agent="ResearchCopilot/1.0",
            request_timeout=30,
            max_concurrent_requests=5,
            rate_limit_delay=1.0,
            max_retries=3,
        )

        assert "ResearchCopilot" in settings.user_agent
        assert settings.request_timeout == 30
        assert settings.max_concurrent_requests == 5
        assert settings.rate_limit_delay == 1.0
        assert settings.max_retries == 3

    def test_custom_values(self):
        """Test custom scraping configuration."""
        settings = ScrapingSettings(
            user_agent="CustomAgent/1.0",
            request_timeout=60,
            max_concurrent_requests=10,
            rate_limit_delay=0.5,
            max_retries=5,
        )

        assert settings.user_agent == "CustomAgent/1.0"
        assert settings.request_timeout == 60
        assert settings.max_concurrent_requests == 10
        assert settings.rate_limit_delay == 0.5
        assert settings.max_retries == 5


class TestMonitoringSettings:
    """Test monitoring configuration settings."""

    def test_default_values(self):
        """Test default monitoring configuration."""
        settings = MonitoringSettings(
            log_level="INFO",
            log_format="json",
            metrics_port=8080,
            health_check_port=8081,
        )

        assert settings.log_level == "INFO"
        assert settings.log_format == "json"
        assert settings.metrics_port == 8080
        assert settings.health_check_port == 8081

    def test_valid_log_levels(self):
        """Test valid log level values."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = MonitoringSettings(
                log_level=level,
                log_format="json",
                metrics_port=8080,
                health_check_port=8081,
            )
            assert settings.log_level == level

    def test_invalid_log_level(self):
        """Test validation of invalid log level."""
        with pytest.raises(ValidationError, match="Log level must be one of"):
            MonitoringSettings(
                log_level="INVALID",
                log_format="json",
                metrics_port=8080,
                health_check_port=8081,
            )

    def test_log_level_case_normalization(self):
        """Test log level is normalized to uppercase."""
        settings = MonitoringSettings(
            log_level="info",
            log_format="json",
            metrics_port=8080,
            health_check_port=8081,
        )
        assert settings.log_level == "INFO"


class TestSettings:
    """Test main Settings class."""

    def test_complete_configuration(self):
        """Test complete configuration setup."""
        settings = Settings(
            environment="development",
            debug=False,
            testing=False,
            notion=NotionSettings(token="secret_test_token", database_id="test_db_id"),
            search=SearchSettings(api_key="test_search_key"),
        )

        assert settings.environment == "development"
        assert settings.debug is False
        assert settings.testing is False

        # Test nested settings
        assert settings.llm.host == "localhost:11434"
        assert settings.notion.token == "secret_test_token"
        assert settings.search.api_key == "test_search_key"

    def test_environment_validation(self):
        """Test environment validation."""
        valid_environments = ["development", "staging", "production"]

        for env in valid_environments:
            settings = Settings(
                environment=env,
                notion=NotionSettings(token="secret_test", database_id="test_db"),
                search=SearchSettings(api_key="test_key"),
            )
            assert settings.environment == env

    def test_invalid_environment(self):
        """Test validation of invalid environment."""
        with pytest.raises(ValidationError, match="Environment must be one of"):
            Settings(
                environment="invalid",
                notion=NotionSettings(token="secret_test", database_id="test_db"),
                search=SearchSettings(api_key="test_key"),
            )

    def test_boolean_fields(self):
        """Test boolean field parsing."""
        settings = Settings(
            debug=True,
            testing=True,
            notion=NotionSettings(token="secret_test_token", database_id="test_db_id"),
            search=SearchSettings(api_key="test_search_key"),
        )

        assert settings.debug is True
        assert settings.testing is True


class TestSettingsFunctions:
    """Test settings utility functions."""

    @patch("src.config.settings.Settings")
    def test_get_settings(self, mock_settings_class):
        """Test get_settings function."""
        mock_settings = MagicMock()
        mock_settings_class.return_value = mock_settings

        # Reset global settings to ensure fresh test
        import src.config.settings

        src.config.settings._settings = None

        settings = get_settings()

        assert settings == mock_settings
        mock_settings_class.assert_called_once()

    @patch("src.config.settings.Settings")
    def test_reload_settings(self, mock_settings_class):
        """Test reload_settings function."""
        mock_settings = MagicMock()
        mock_settings_class.return_value = mock_settings

        # Reset global settings to ensure fresh test
        import src.config.settings

        src.config.settings._settings = None

        settings = reload_settings()

        assert settings == mock_settings
        mock_settings_class.assert_called_once()
