"""
Clients module for Data Scraper.

Contains API client and data processing utilities.
"""

from .api_client import ApiClient, ApiClientError, DataProcessor, RateLimitExceededError

__all__ = [
    "ApiClient",
    "DataProcessor",
    "ApiClientError",
    "RateLimitExceededError",
]
