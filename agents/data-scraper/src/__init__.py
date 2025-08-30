"""
Data Scraper Agent Package.

A comprehensive API scraping solution that can scrape data from APIs
using configuration files and environment variables for authentication.
"""

__version__ = "1.0.0"
__author__ = "Data Scraper Team"
__description__ = "API Data Scraper Agent"

from .agent.data_scraper_agent import DataScraperAgent, DataScraperAgentError
from .models.api_config import (
    ApiEndpoint,
    ApiScrapingConfig,
    Authentication,
    DataTransformation,
    RateLimit,
    ScrapingJob,
    ScrapingResult,
)

__all__ = [
    "DataScraperAgent",
    "DataScraperAgentError",
    "ApiScrapingConfig",
    "ScrapingJob",
    "ScrapingResult",
    "Authentication",
    "ApiEndpoint",
    "RateLimit",
    "DataTransformation",
]
