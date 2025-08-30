"""
Pydantic models for data scraper API configuration management.

This module defines the data structures used to configure API scraping requests,
authentication, and data processing for the Data Scraper Agent.
"""

import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class HttpMethod(str, Enum):
    """Enumeration of HTTP methods."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class AuthType(str, Enum):
    """Enumeration of authentication types."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"


class DataFormat(str, Enum):
    """Enumeration of data formats."""

    JSON = "json"
    XML = "xml"
    CSV = "csv"
    HTML = "html"
    TEXT = "text"


class RateLimit(BaseModel):
    """Configuration for API rate limiting."""

    requests_per_minute: int = Field(default=60, description="Requests per minute")
    requests_per_hour: int = Field(default=1000, description="Requests per hour")
    delay_between_requests: float = Field(
        default=1.0, description="Delay between requests in seconds"
    )


class ApiEndpoint(BaseModel):
    """Configuration for a single API endpoint."""

    name: str = Field(..., description="Name of the endpoint")
    url: str = Field(..., description="API endpoint URL (can be relative)")
    method: HttpMethod = Field(default=HttpMethod.GET, description="HTTP method")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    params: Dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    body: Optional[Dict[str, Any]] = Field(
        default=None, description="Request body for POST/PUT"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    data_path: Optional[str] = Field(
        default=None, description="JSON path to extract data from response"
    )
    pagination: Optional[Dict[str, Any]] = Field(
        default=None, description="Pagination configuration"
    )


class Authentication(BaseModel):
    """Configuration for API authentication."""

    type: AuthType = Field(..., description="Authentication type")
    api_key_name: Optional[str] = Field(
        default=None, description="API key parameter name"
    )
    api_key_value: Optional[str] = Field(
        default=None, description="API key value (from env var)"
    )
    bearer_token: Optional[str] = Field(
        default=None, description="Bearer token (from env var)"
    )
    username: Optional[str] = Field(
        default=None, description="Username for basic auth (from env var)"
    )
    password: Optional[str] = Field(
        default=None, description="Password for basic auth (from env var)"
    )
    oauth2_config: Optional[Dict[str, Any]] = Field(
        default=None, description="OAuth2 configuration"
    )

    @validator("api_key_value", "bearer_token", "username", "password", pre=True)
    def resolve_env_vars(cls, v):
        """Resolve environment variables if value starts with $."""
        if isinstance(v, str) and v.startswith("$"):
            env_var = v[1:]
            return os.getenv(env_var)
        return v


class DataTransformation(BaseModel):
    """Configuration for data transformation."""

    field_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Map source fields to target fields"
    )
    field_filters: Dict[str, Any] = Field(
        default_factory=dict, description="Filter conditions for fields"
    )
    data_validation: Dict[str, Any] = Field(
        default_factory=dict, description="Data validation rules"
    )
    data_enrichment: Dict[str, Any] = Field(
        default_factory=dict, description="Data enrichment rules"
    )


class ApiScrapingConfig(BaseModel):
    """Configuration for API scraping job."""

    name: str = Field(..., description="Name of the scraping configuration")
    description: str = Field(..., description="Description of the scraping job")
    base_url: HttpUrl = Field(..., description="Base URL for the API")
    authentication: Authentication = Field(
        ..., description="Authentication configuration"
    )
    endpoints: List[ApiEndpoint] = Field(..., description="List of endpoints to scrape")
    rate_limit: RateLimit = Field(
        default_factory=RateLimit, description="Rate limiting configuration"
    )
    data_format: DataFormat = Field(
        default=DataFormat.JSON, description="Expected data format"
    )
    transformation: DataTransformation = Field(
        default_factory=DataTransformation, description="Data transformation rules"
    )
    output_config: Dict[str, Any] = Field(
        default_factory=dict, description="Output configuration"
    )
    schedule: Optional[str] = Field(
        default=None, description="Cron schedule for periodic scraping"
    )
    enabled: bool = Field(
        default=True, description="Whether this configuration is enabled"
    )

    @validator("endpoints")
    def validate_endpoints(cls, v):
        """Validate that at least one endpoint is provided."""
        if not v:
            raise ValueError("At least one endpoint must be configured")
        return v


class ScrapingJob(BaseModel):
    """Configuration for a scraping job execution."""

    job_id: str = Field(..., description="Unique job identifier")
    config_name: str = Field(..., description="Name of the API configuration to use")
    execution_time: datetime = Field(
        default_factory=datetime.utcnow, description="Job execution time"
    )
    status: str = Field(default="pending", description="Job status")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Job-specific parameters"
    )
    override_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Configuration overrides"
    )


class ScrapingResult(BaseModel):
    """Result of a scraping job execution."""

    job_id: str = Field(..., description="Job identifier")
    config_name: str = Field(..., description="Configuration name used")
    execution_id: str = Field(..., description="Execution identifier")
    status: str = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Start time")
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion time"
    )
    duration_seconds: float = Field(default=0.0, description="Execution duration")
    endpoints_scraped: int = Field(default=0, description="Number of endpoints scraped")
    records_processed: int = Field(default=0, description="Number of records processed")
    data_size_bytes: int = Field(default=0, description="Size of scraped data")
    error_message: Optional[str] = Field(
        default=None, description="Error message if failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    output_location: Optional[str] = Field(
        default=None, description="Output file location"
    )
