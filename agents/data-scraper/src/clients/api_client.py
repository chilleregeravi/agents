"""
API Client for Data Scraper Agent.

This module provides functionality to make HTTP requests to APIs with
authentication, rate limiting, and error handling.
"""

import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError

from ..models.api_config import (
    ApiEndpoint,
    Authentication,
    AuthType,
    HttpMethod,
    RateLimit,
)

logger = logging.getLogger(__name__)


class ApiClientError(Exception):
    """Exception raised when API client operations fail."""

    pass


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


class ApiClient:
    """
    Client for making HTTP requests to APIs with authentication and rate limiting.
    """

    def __init__(self, rate_limit: RateLimit):
        """
        Initialize the API client.

        Args:
            rate_limit: Rate limiting configuration
        """
        self.rate_limit = rate_limit
        self.request_times: List[float] = []
        self.session: Optional[ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        timeout = ClientTimeout(total=30)
        self.session = ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def make_request(
        self,
        endpoint: ApiEndpoint,
        authentication: Authentication,
        base_url: str,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to an API endpoint.

        Args:
            endpoint: Endpoint configuration
            authentication: Authentication configuration
            base_url: Base URL for the API

        Returns:
            Dict[str, Any]: Response data

        Raises:
            ApiClientError: If request fails
            RateLimitExceededError: If rate limit is exceeded
        """
        # Check rate limiting
        await self._check_rate_limit()

        # Build full URL
        url = urljoin(base_url, str(endpoint.url))

        # Prepare headers
        headers = endpoint.headers.copy()
        headers.update(self._build_auth_headers(authentication))

        # Prepare request parameters
        request_kwargs = {
            "url": url,
            "headers": headers,
            "timeout": ClientTimeout(total=endpoint.timeout),
        }

        # Add method-specific parameters
        if endpoint.method in [HttpMethod.GET, HttpMethod.DELETE]:
            if endpoint.params:
                request_kwargs["params"] = endpoint.params
        else:
            if endpoint.body:
                request_kwargs["json"] = endpoint.body
            if endpoint.params:
                request_kwargs["params"] = endpoint.params

        # Make request with retries
        for attempt in range(endpoint.retry_attempts + 1):
            try:
                logger.info(
                    f"Making {endpoint.method} request to {url} (attempt {attempt + 1})"
                )

                if not self.session:
                    raise ApiClientError("Session not initialized")

                # Extract URL and other parameters
                url = str(request_kwargs.pop("url"))
                headers = request_kwargs.pop("headers", {})  # type: ignore
                timeout_obj = request_kwargs.pop("timeout", None)
                params = request_kwargs.pop("params", None)
                json_data = request_kwargs.pop("json", None)

                async with self.session.request(
                    endpoint.method, url, headers=headers, timeout=timeout_obj, params=params, json=json_data  # type: ignore
                ) as response:
                    # Record request time for rate limiting
                    self.request_times.append(time.time())

                    # Check response status
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ApiClientError(f"HTTP {response.status}: {error_text}")

                    # Parse response based on content type
                    content_type = response.headers.get("content-type", "")
                    data = await self._parse_response(response, content_type)

                    # Extract data using JSON path if specified
                    if endpoint.data_path:
                        data = self._extract_data_path(data, endpoint.data_path)

                    logger.info(
                        f"Successfully made request to {url} - status: {response.status}, data_size: {len(str(data))}"
                    )

                    return {
                        "status_code": response.status,
                        "data": data,
                        "headers": dict(response.headers),
                        "url": str(response.url),
                    }

            except ClientError as e:
                if attempt == endpoint.retry_attempts:
                    raise ApiClientError(
                        f"Request failed after {endpoint.retry_attempts + 1} attempts: {e}"
                    )

                logger.warning(f"Request attempt {attempt + 1} failed, retrying: {e}")
                await asyncio.sleep(2**attempt)  # Exponential backoff

            except Exception as e:
                raise ApiClientError(f"Unexpected error during request: {e}")

        # This should never be reached due to the retry logic above
        raise ApiClientError("Request failed after all retry attempts")

    def _build_auth_headers(self, authentication: Authentication) -> Dict[str, str]:
        """
        Build authentication headers based on authentication type.

        Args:
            authentication: Authentication configuration

        Returns:
            Dict[str, str]: Authentication headers
        """
        headers = {}

        if authentication.type == AuthType.API_KEY:
            if authentication.api_key_name and authentication.api_key_value:
                headers[authentication.api_key_name] = authentication.api_key_value

        elif authentication.type == AuthType.BEARER_TOKEN:
            if authentication.bearer_token:
                headers["Authorization"] = f"Bearer {authentication.bearer_token}"

        elif authentication.type == AuthType.BASIC_AUTH:
            if authentication.username and authentication.password:
                import base64

                credentials = base64.b64encode(
                    f"{authentication.username}:{authentication.password}".encode()
                ).decode()
                headers["Authorization"] = f"Basic {credentials}"

        return headers

    async def _parse_response(
        self, response: aiohttp.ClientResponse, content_type: str
    ) -> Any:
        """
        Parse response based on content type.

        Args:
            response: HTTP response
            content_type: Content type header

        Returns:
            Any: Parsed response data
        """
        if "application/json" in content_type:
            return await response.json()
        elif "application/xml" in content_type or "text/xml" in content_type:
            text = await response.text()
            return ET.fromstring(text)
        elif "text/csv" in content_type:
            return await response.text()
        else:
            return await response.text()

    def _extract_data_path(self, data: Any, data_path: str) -> Any:
        """
        Extract data from response using JSON path.

        Args:
            data: Response data
            data_path: JSON path expression

        Returns:
            Any: Extracted data
        """
        try:
            # Simple JSON path implementation for common cases
            if data_path.startswith("$."):
                path_parts = data_path[2:].split(".")
                current = data

                for part in path_parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    elif isinstance(current, list) and part.isdigit():
                        current = current[int(part)]
                    else:
                        logger.warning(f"Could not extract path {data_path}")
                        return data

                return current
            else:
                logger.warning(f"Unsupported JSON path format: {data_path}")
                return data

        except Exception as e:
            logger.warning(f"Failed to extract data path {data_path}: {e}")
            return data

    async def _check_rate_limit(self) -> None:  # type: ignore
        """
        Check if rate limit is exceeded and wait if necessary.

        Raises:
            RateLimitExceededError: If rate limit is exceeded
        """
        current_time = time.time()

        # Remove old request times (older than 1 hour)
        self.request_times = [t for t in self.request_times if current_time - t < 3600]

        # Check hourly rate limit
        if len(self.request_times) >= self.rate_limit.requests_per_hour:
            oldest_time = min(self.request_times)
            wait_time = 3600 - (current_time - oldest_time)
            if wait_time > 0:
                raise RateLimitExceededError(
                    f"Hourly rate limit exceeded. Wait {wait_time:.1f} seconds"
                )

        # Check per-minute rate limit
        recent_requests = [t for t in self.request_times if current_time - t < 60]
        if len(recent_requests) >= self.rate_limit.requests_per_minute:
            oldest_time = min(recent_requests)
            wait_time = 60 - (current_time - oldest_time)
            if wait_time > 0:
                raise RateLimitExceededError(
                    f"Per-minute rate limit exceeded. Wait {wait_time:.1f} seconds"
                )

        # Apply delay between requests
        if self.request_times and self.rate_limit.delay_between_requests > 0:
            time_since_last = current_time - self.request_times[-1]
            if time_since_last < self.rate_limit.delay_between_requests:
                wait_time = self.rate_limit.delay_between_requests - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)

        return None  # type: ignore


class DataProcessor:
    """
    Process and transform scraped data.
    """

    @staticmethod
    def transform_data(
        data: Any,
        field_mapping: Dict[str, str],
        field_filters: Dict[str, Any],
        data_validation: Dict[str, Any],
    ) -> Any:
        """
        Transform scraped data according to configuration.

        Args:
            data: Raw scraped data
            field_mapping: Field mapping configuration
            field_filters: Field filter configuration
            data_validation: Data validation configuration

        Returns:
            Any: Transformed data
        """
        if isinstance(data, list):
            return [
                DataProcessor._transform_record(
                    item, field_mapping, field_filters, data_validation
                )
                for item in data
            ]
        else:
            return DataProcessor._transform_record(
                data, field_mapping, field_filters, data_validation
            )

    @staticmethod
    def _transform_record(
        record: Any,
        field_mapping: Dict[str, str],
        field_filters: Dict[str, Any],
        data_validation: Dict[str, Any],
    ) -> Any:
        """
        Transform a single record.

        Args:
            record: Single record to transform
            field_mapping: Field mapping configuration
            field_filters: Field filter configuration
            data_validation: Data validation configuration

        Returns:
            Any: Transformed record
        """
        if not isinstance(record, dict):
            return record

        # Apply field mapping
        transformed = {}
        for source_field, target_field in field_mapping.items():
            if source_field in record:
                transformed[target_field] = record[source_field]

        # Apply field filters
        for field, filter_config in field_filters.items():
            if field in transformed:
                transformed[field] = DataProcessor._apply_filter(
                    transformed[field], filter_config
                )

        # Apply data validation
        for field, validation_config in data_validation.items():
            if field in transformed:
                if not DataProcessor._validate_field(
                    transformed[field], validation_config
                ):
                    logger.warning(
                        f"Field {field} failed validation: {validation_config}"
                    )
                    # Remove invalid field or set to None based on configuration
                    transformed[field] = None

        return transformed

    @staticmethod
    def _apply_filter(value: Any, filter_config: Any) -> Any:
        """
        Apply filter to a field value.

        Args:
            value: Field value
            filter_config: Filter configuration

        Returns:
            Any: Filtered value
        """
        if isinstance(filter_config, dict):
            if "type" in filter_config:
                filter_type = filter_config["type"]

                if filter_type == "string" and isinstance(value, str):
                    if "lowercase" in filter_config and filter_config["lowercase"]:
                        value = value.lower()
                    if "uppercase" in filter_config and filter_config["uppercase"]:
                        value = value.upper()
                    if "strip" in filter_config and filter_config["strip"]:
                        value = value.strip()

                elif filter_type == "number" and isinstance(value, (int, float)):
                    if "min" in filter_config and value < filter_config["min"]:
                        value = filter_config["min"]
                    if "max" in filter_config and value > filter_config["max"]:
                        value = filter_config["max"]

                elif filter_type == "date" and isinstance(value, str):
                    # Basic date parsing and formatting
                    try:
                        from datetime import datetime

                        parsed_date = datetime.fromisoformat(
                            value.replace("Z", "+00:00")
                        )
                        if "format" in filter_config:
                            value = parsed_date.strftime(filter_config["format"])
                        else:
                            value = parsed_date.isoformat()
                    except ValueError:
                        logger.warning(f"Failed to parse date: {value}")

        return value

    @staticmethod
    def _validate_field(value: Any, validation_config: Any) -> bool:
        """
        Validate a field value.

        Args:
            value: Field value
            validation_config: Validation configuration

        Returns:
            bool: True if validation passes
        """
        if isinstance(validation_config, dict):
            if "required" in validation_config and validation_config["required"]:
                if value is None or value == "":
                    return False

            if "type" in validation_config:
                expected_type = validation_config["type"]
                if expected_type == "string" and not isinstance(value, str):
                    return False
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False

            if "pattern" in validation_config and isinstance(value, str):
                import re

                if not re.match(validation_config["pattern"], value):
                    return False

            if "min_length" in validation_config and isinstance(value, str):
                if len(value) < validation_config["min_length"]:
                    return False

            if "max_length" in validation_config and isinstance(value, str):
                if len(value) > validation_config["max_length"]:
                    return False

        return True
