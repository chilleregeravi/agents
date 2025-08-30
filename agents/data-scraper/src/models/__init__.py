"""
Models module for Data Scraper.

Contains Pydantic models for configuration and data structures.
"""

from .api_config import (
    ApiEndpoint,
    ApiScrapingConfig,
    Authentication,
    AuthType,
    DataFormat,
    DataTransformation,
    HttpMethod,
    RateLimit,
    ScrapingJob,
    ScrapingResult,
)

__all__ = [
    "ApiScrapingConfig",
    "ScrapingJob",
    "ScrapingResult",
    "Authentication",
    "ApiEndpoint",
    "RateLimit",
    "DataTransformation",
    "HttpMethod",
    "AuthType",
    "DataFormat",
]
