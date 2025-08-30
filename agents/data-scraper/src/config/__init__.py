"""
Configuration module for Data Scraper.

Contains configuration loading and validation utilities.
"""

from .config_loader import ConfigurationError, DataScraperConfigLoader

__all__ = [
    "DataScraperConfigLoader",
    "ConfigurationError",
]
