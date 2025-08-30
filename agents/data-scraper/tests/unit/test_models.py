"""
Unit tests for Data Scraper Agent models.
"""

import pytest
from pydantic import ValidationError
from src.models.api_config import (
    ApiEndpoint,
    ApiScrapingConfig,
    Authentication,
    AuthType,
    DataFormat,
    DataTransformation,
    HttpMethod,
    RateLimit,
)


class TestApiEndpoint:
    """Test ApiEndpoint model."""

    def test_valid_endpoint(self):
        """Test creating a valid endpoint."""
        endpoint = ApiEndpoint(
            name="test_endpoint",
            url="/api/test",
            method=HttpMethod.GET,
            timeout=30,
            retry_attempts=3,
        )

        assert endpoint.name == "test_endpoint"
        assert endpoint.url == "/api/test"
        assert endpoint.method == HttpMethod.GET
        assert endpoint.timeout == 30
        assert endpoint.retry_attempts == 3

    def test_endpoint_with_headers_and_params(self):
        """Test endpoint with headers and parameters."""
        endpoint = ApiEndpoint(
            name="test_endpoint",
            url="/api/test",
            headers={"Accept": "application/json"},
            params={"limit": 100, "offset": 0},
        )

        assert endpoint.headers == {"Accept": "application/json"}
        assert endpoint.params == {"limit": 100, "offset": 0}

    def test_endpoint_with_body(self):
        """Test endpoint with request body."""
        endpoint = ApiEndpoint(
            name="test_endpoint",
            url="/api/test",
            method=HttpMethod.POST,
            body={"key": "value"},
        )

        assert endpoint.method == HttpMethod.POST
        assert endpoint.body == {"key": "value"}


class TestAuthentication:
    """Test Authentication model."""

    def test_no_auth(self):
        """Test no authentication configuration."""
        auth = Authentication(type=AuthType.NONE)
        assert auth.type == AuthType.NONE

    def test_bearer_token_auth(self):
        """Test bearer token authentication."""
        auth = Authentication(type=AuthType.BEARER_TOKEN, bearer_token="test-token")
        assert auth.type == AuthType.BEARER_TOKEN
        assert auth.bearer_token == "test-token"

    def test_api_key_auth(self):
        """Test API key authentication."""
        auth = Authentication(
            type=AuthType.API_KEY, api_key_name="X-API-Key", api_key_value="test-key"
        )
        assert auth.type == AuthType.API_KEY
        assert auth.api_key_name == "X-API-Key"
        assert auth.api_key_value == "test-key"

    def test_basic_auth(self):
        """Test basic authentication."""
        auth = Authentication(
            type=AuthType.BASIC_AUTH, username="test-user", password="test-pass"
        )
        assert auth.type == AuthType.BASIC_AUTH
        assert auth.username == "test-user"
        assert auth.password == "test-pass"


class TestRateLimit:
    """Test RateLimit model."""

    def test_default_rate_limit(self):
        """Test default rate limit values."""
        rate_limit = RateLimit()
        assert rate_limit.requests_per_minute == 60
        assert rate_limit.requests_per_hour == 1000
        assert rate_limit.delay_between_requests == 1.0

    def test_custom_rate_limit(self):
        """Test custom rate limit values."""
        rate_limit = RateLimit(
            requests_per_minute=30, requests_per_hour=500, delay_between_requests=2.0
        )
        assert rate_limit.requests_per_minute == 30
        assert rate_limit.requests_per_hour == 500
        assert rate_limit.delay_between_requests == 2.0


class TestDataTransformation:
    """Test DataTransformation model."""

    def test_empty_transformation(self):
        """Test empty transformation configuration."""
        transformation = DataTransformation()
        assert transformation.field_mapping == {}
        assert transformation.field_filters == {}
        assert transformation.data_validation == {}

    def test_field_mapping(self):
        """Test field mapping configuration."""
        transformation = DataTransformation(
            field_mapping={"id": "user_id", "name": "user_name"}
        )
        assert transformation.field_mapping == {"id": "user_id", "name": "user_name"}

    def test_field_filters(self):
        """Test field filters configuration."""
        transformation = DataTransformation(
            field_filters={
                "name": {"type": "string", "lowercase": True},
                "age": {"type": "number", "min": 0, "max": 120},
            }
        )
        assert "name" in transformation.field_filters
        assert "age" in transformation.field_filters

    def test_data_validation(self):
        """Test data validation configuration."""
        transformation = DataTransformation(
            data_validation={
                "email": {"required": True, "type": "string"},
                "age": {"type": "number", "min": 0},
            }
        )
        assert "email" in transformation.data_validation
        assert "age" in transformation.data_validation


class TestApiScrapingConfig:
    """Test ApiScrapingConfig model."""

    def test_valid_config(self, sample_api_config):
        """Test creating a valid configuration."""
        config = ApiScrapingConfig(**sample_api_config)

        assert config.name == "Test API"
        assert config.description == "Test configuration for unit tests"
        assert str(config.base_url).rstrip("/") == "https://httpbin.org"
        assert config.authentication.type == AuthType.NONE
        assert len(config.endpoints) == 1
        assert config.endpoints[0].name == "test_endpoint"
        assert config.data_format == DataFormat.JSON
        assert config.enabled is True

    def test_config_without_endpoints(self):
        """Test that config without endpoints raises validation error."""
        config_data = {
            "name": "Test API",
            "description": "Test configuration",
            "base_url": "https://httpbin.org",
            "authentication": {"type": "none"},
            "endpoints": [],
        }

        with pytest.raises(ValidationError, match="endpoints"):
            ApiScrapingConfig(**config_data)

    def test_config_with_disabled_flag(self, sample_api_config):
        """Test configuration with disabled flag."""
        sample_api_config["enabled"] = False
        config = ApiScrapingConfig(**sample_api_config)
        assert config.enabled is False

    def test_config_with_schedule(self, sample_api_config):
        """Test configuration with schedule."""
        sample_api_config["schedule"] = "0 */6 * * *"
        config = ApiScrapingConfig(**sample_api_config)
        assert config.schedule == "0 */6 * * *"

    def test_config_with_transformation(self, sample_api_config):
        """Test configuration with data transformation."""
        sample_api_config["transformation"] = {
            "field_mapping": {"id": "user_id"},
            "field_filters": {"name": {"type": "string", "lowercase": True}},
            "data_validation": {"email": {"required": True}},
        }
        config = ApiScrapingConfig(**sample_api_config)

        assert config.transformation.field_mapping == {"id": "user_id"}
        assert "name" in config.transformation.field_filters
        assert "email" in config.transformation.data_validation
