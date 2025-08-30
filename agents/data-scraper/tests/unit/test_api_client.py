"""
Unit tests for Data Scraper Agent API client.
"""

from unittest.mock import AsyncMock, patch

import pytest
from src.clients.api_client import (
    ApiClient,
    ApiClientError,
    DataProcessor,
    RateLimitExceededError,
)
from src.models.api_config import (
    ApiEndpoint,
    Authentication,
    AuthType,
    HttpMethod,
    RateLimit,
)


class TestApiClient:
    """Test ApiClient."""

    @pytest.fixture
    def rate_limit(self):
        """Create a rate limit configuration."""
        return RateLimit(
            requests_per_minute=60, requests_per_hour=1000, delay_between_requests=1.0
        )

    @pytest.fixture
    def api_client(self, rate_limit):
        """Create an API client instance."""
        return ApiClient(rate_limit)

    @pytest.fixture
    def endpoint(self):
        """Create a test endpoint."""
        return ApiEndpoint(
            name="test_endpoint",
            url="/test",
            method=HttpMethod.GET,
            timeout=30,
            retry_attempts=3,
        )

    @pytest.fixture
    def auth_none(self):
        """Create no authentication configuration."""
        return Authentication(type=AuthType.NONE)

    @pytest.fixture
    def auth_bearer(self):
        """Create bearer token authentication."""
        return Authentication(type=AuthType.BEARER_TOKEN, bearer_token="test-token")

    @pytest.fixture
    def auth_api_key(self):
        """Create API key authentication."""
        return Authentication(
            type=AuthType.API_KEY, api_key_name="X-API-Key", api_key_value="test-key"
        )

    @pytest.fixture
    def auth_basic(self):
        """Create basic authentication."""
        return Authentication(
            type=AuthType.BASIC_AUTH, username="test-user", password="test-pass"
        )

    async def test_context_manager(self, api_client):
        """Test API client context manager."""
        async with api_client as client:
            assert client.session is not None
        assert api_client.session is None

    def test_build_auth_headers_none(self, api_client, auth_none):
        """Test building headers with no authentication."""
        headers = api_client._build_auth_headers(auth_none)
        assert headers == {}

    def test_build_auth_headers_bearer(self, api_client, auth_bearer):
        """Test building headers with bearer token."""
        headers = api_client._build_auth_headers(auth_bearer)
        assert headers == {"Authorization": "Bearer test-token"}

    def test_build_auth_headers_api_key(self, api_client, auth_api_key):
        """Test building headers with API key."""
        headers = api_client._build_auth_headers(auth_api_key)
        assert headers == {"X-API-Key": "test-key"}

    def test_build_auth_headers_basic(self, api_client, auth_basic):
        """Test building headers with basic auth."""
        headers = api_client._build_auth_headers(auth_basic)
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    @patch("aiohttp.ClientSession.request")
    async def test_make_request_success(
        self, mock_request, api_client, endpoint, auth_none
    ):
        """Test successful API request."""
        # Mock response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json = AsyncMock(return_value={"data": "test"})
        mock_response.text = AsyncMock(return_value='{"data": "test"}')
        mock_response.url = "https://httpbin.org/test"

        mock_request.return_value.__aenter__.return_value = mock_response

        async with api_client:
            result = await api_client.make_request(
                endpoint, auth_none, "https://httpbin.org"
            )

        assert result["status_code"] == 200
        assert result["data"] == {"data": "test"}
        assert "url" in result

    @patch("aiohttp.ClientSession.request")
    async def test_make_request_http_error(
        self, mock_request, api_client, endpoint, auth_none
    ):
        """Test API request with HTTP error."""
        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")

        mock_request.return_value.__aenter__.return_value = mock_response

        async with api_client:
            with pytest.raises(ApiClientError, match="HTTP 404"):
                await api_client.make_request(
                    endpoint, auth_none, "https://httpbin.org"
                )

    @patch("aiohttp.ClientSession.request")
    async def test_make_request_with_retry(
        self, mock_request, api_client, endpoint, auth_none
    ):
        """Test API request with retry logic."""
        # Mock first request to fail, second to succeed
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.text = AsyncMock(return_value="Internal Server Error")

        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.headers = {"content-type": "application/json"}
        mock_response_success.json = AsyncMock(return_value={"data": "test"})
        mock_response_success.text = AsyncMock(return_value='{"data": "test"}')
        mock_response_success.url = "https://httpbin.org/test"

        mock_request.return_value.__aenter__.side_effect = [
            mock_response_fail,
            mock_response_success,
        ]

        async with api_client:
            result = await api_client.make_request(
                endpoint, auth_none, "https://httpbin.org"
            )

        assert result["status_code"] == 200
        assert mock_request.call_count == 2

    @patch("aiohttp.ClientSession.request")
    async def test_make_request_rate_limit_exceeded(
        self, mock_request, api_client, endpoint, auth_none
    ):
        """Test API request with rate limit exceeded."""
        # Set up rate limiting to be exceeded
        api_client.request_times = [0] * 100  # More than hourly limit

        async with api_client:
            with pytest.raises(RateLimitExceededError):
                await api_client.make_request(
                    endpoint, auth_none, "https://httpbin.org"
                )

    def test_extract_data_path_simple(self, api_client):
        """Test simple JSON path extraction."""
        data = {"user": {"name": "John", "age": 30}}
        result = api_client._extract_data_path(data, "$.user")
        assert result == {"name": "John", "age": 30}

    def test_extract_data_path_nested(self, api_client):
        """Test nested JSON path extraction."""
        data = {"user": {"name": "John", "age": 30}}
        result = api_client._extract_data_path(data, "$.user.name")
        assert result == "John"

    def test_extract_data_path_array(self, api_client):
        """Test array JSON path extraction."""
        data = {"users": [{"name": "John"}, {"name": "Jane"}]}
        result = api_client._extract_data_path(data, "$.users.0")
        assert result == {"name": "John"}

    def test_extract_data_path_invalid(self, api_client):
        """Test invalid JSON path extraction."""
        data = {"user": {"name": "John"}}
        result = api_client._extract_data_path(data, "$.user.invalid")
        assert result == data  # Should return original data


class TestDataProcessor:
    """Test DataProcessor."""

    def test_transform_data_list(self):
        """Test transforming list data."""
        data = [{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]

        field_mapping = {"id": "user_id", "name": "user_name"}
        field_filters = {}
        data_validation = {}

        result = DataProcessor.transform_data(
            data, field_mapping, field_filters, data_validation
        )

        assert len(result) == 2
        assert result[0]["user_id"] == 1
        assert result[0]["user_name"] == "John"
        assert result[1]["user_id"] == 2
        assert result[1]["user_name"] == "Jane"

    def test_transform_data_single_record(self):
        """Test transforming single record."""
        data = {"id": 1, "name": "John"}

        field_mapping = {"id": "user_id", "name": "user_name"}
        field_filters = {}
        data_validation = {}

        result = DataProcessor.transform_data(
            data, field_mapping, field_filters, data_validation
        )

        assert result["user_id"] == 1
        assert result["user_name"] == "John"

    def test_transform_data_with_filters(self):
        """Test data transformation with filters."""
        data = {"name": "  JOHN  ", "age": 25}

        field_mapping = {"name": "user_name", "age": "user_age"}
        field_filters = {
            "user_name": {"type": "string", "lowercase": True, "strip": True},
            "user_age": {"type": "number", "min": 0, "max": 120},
        }
        data_validation = {}

        result = DataProcessor.transform_data(
            data, field_mapping, field_filters, data_validation
        )

        assert result["user_name"] == "john"
        assert result["user_age"] == 25

    def test_transform_data_with_validation(self):
        """Test data transformation with validation."""
        data = {"email": "test@example.com", "age": 25}

        field_mapping = {"email": "user_email", "age": "user_age"}
        field_filters = {}
        data_validation = {
            "user_email": {"required": True, "type": "string"},
            "user_age": {"type": "number", "min": 0},
        }

        result = DataProcessor.transform_data(
            data, field_mapping, field_filters, data_validation
        )

        assert result["user_email"] == "test@example.com"
        assert result["user_age"] == 25

    def test_transform_data_validation_failure(self):
        """Test data transformation with validation failure."""
        data = {"email": "", "age": -5}

        field_mapping = {"email": "user_email", "age": "user_age"}
        field_filters = {}
        data_validation = {
            "user_email": {"required": True, "type": "string"},
            "user_age": {"type": "number", "min": 0},
        }

        result = DataProcessor.transform_data(
            data, field_mapping, field_filters, data_validation
        )

        # Email should be None due to validation failure
        assert result["user_email"] is None
        # Age should be None due to validation failure
        assert result["user_age"] is None

    def test_apply_filter_string(self):
        """Test string filter application."""
        value = "  TEST  "
        filter_config = {"type": "string", "lowercase": True, "strip": True}

        result = DataProcessor._apply_filter(value, filter_config)
        assert result == "test"

    def test_apply_filter_number(self):
        """Test number filter application."""
        value = 150
        filter_config = {"type": "number", "min": 0, "max": 100}

        result = DataProcessor._apply_filter(value, filter_config)
        assert result == 100  # Should be capped at max

    def test_validate_field_success(self):
        """Test successful field validation."""
        value = "test@example.com"
        validation_config = {
            "required": True,
            "type": "string",
            "pattern": r"^[^@]+@[^@]+\.[^@]+$",
        }

        result = DataProcessor._validate_field(value, validation_config)
        assert result is True

    def test_validate_field_failure(self):
        """Test field validation failure."""
        value = "invalid-email"
        validation_config = {
            "required": True,
            "type": "string",
            "pattern": r"^[^@]+@[^@]+\.[^@]+$",
        }

        result = DataProcessor._validate_field(value, validation_config)
        assert result is False
