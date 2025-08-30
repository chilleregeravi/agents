"""
Configuration Loader for Data Scraper Agent.

This module provides functionality to load API scraping configurations from
mounted ConfigMap files and environment variables.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import ValidationError

from ..models.api_config import ApiScrapingConfig, ScrapingJob

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised when configuration loading fails."""

    pass


class DataScraperConfigLoader:
    """
    Loader for API scraping configurations from mounted files.

    This approach leverages Kubernetes' native ConfigMap mounting instead
    of using the Kubernetes API client at runtime.
    """

    def __init__(self, config_base_path: str = "/app/config"):
        """
        Initialize the configuration loader.

        Args:
            config_base_path: Base path where ConfigMaps are mounted
        """
        self.config_base_path = Path(config_base_path)
        self.apis_path = self.config_base_path / "apis"
        self.jobs_path = self.config_base_path / "jobs"

        # Create directories if they don't exist
        self.apis_path.mkdir(parents=True, exist_ok=True)
        self.jobs_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Initialized data scraper config loader with base path: {self.config_base_path}"
        )

    def load_api_config(self, config_name: str) -> ApiScrapingConfig:
        """
        Load an API scraping configuration.

        Args:
            config_name: Name of the configuration file (without extension)

        Returns:
            ApiScrapingConfig: Loaded and validated configuration

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        logger.info(f"Loading API configuration: {config_name}")

        # Try to load from mounted files
        config_file = self.apis_path / f"{config_name}.yaml"

        if not config_file.exists():
            config_file = self.apis_path / f"{config_name}.yml"

        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_name}")

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Validate and create configuration
            config = ApiScrapingConfig(**config_data)

            logger.info(f"Successfully loaded API configuration: {config_name}")
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def load_job_config(self, job_name: str) -> ScrapingJob:
        """
        Load a scraping job configuration.

        Args:
            job_name: Name of the job configuration file (without extension)

        Returns:
            ScrapingJob: Loaded and validated job configuration

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        logger.info(f"Loading job configuration: {job_name}")

        # Try to load from mounted files
        job_file = self.jobs_path / f"{job_name}.yaml"

        if not job_file.exists():
            job_file = self.jobs_path / f"{job_name}.yml"

        if not job_file.exists():
            raise ConfigurationError(f"Job configuration file not found: {job_name}")

        try:
            with open(job_file, "r", encoding="utf-8") as f:
                job_data = yaml.safe_load(f)

            # Validate and create job configuration
            job = ScrapingJob(**job_data)

            logger.info(f"Successfully loaded job configuration: {job_name}")
            return job

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in job file: {e}")
        except ValidationError as e:
            raise ConfigurationError(f"Job configuration validation failed: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load job configuration: {e}")

    def list_available_configs(self) -> List[str]:
        """
        List all available API configurations.

        Returns:
            List[str]: List of configuration names
        """
        configs = []

        for file_path in self.apis_path.glob("*.yaml"):
            configs.append(file_path.stem)

        for file_path in self.apis_path.glob("*.yml"):
            if file_path.stem not in configs:
                configs.append(file_path.stem)

        return sorted(configs)

    def list_available_jobs(self) -> List[str]:
        """
        List all available job configurations.

        Returns:
            List[str]: List of job names
        """
        jobs = []

        for file_path in self.jobs_path.glob("*.yaml"):
            jobs.append(file_path.stem)

        for file_path in self.jobs_path.glob("*.yml"):
            if file_path.stem not in jobs:
                jobs.append(file_path.stem)

        return sorted(jobs)

    def validate_config(self, config_name: str) -> bool:
        """
        Validate a configuration without executing it.

        Args:
            config_name: Name of the configuration to validate

        Returns:
            bool: True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        try:
            config = self.load_api_config(config_name)

            # Additional validation checks
            if not config.enabled:
                logger.warning(f"Configuration {config_name} is disabled")

            # Validate authentication
            if config.authentication.type != "none":
                if (
                    config.authentication.type == "api_key"
                    and not config.authentication.api_key_value
                ):
                    raise ConfigurationError(
                        "API key value is required for api_key authentication"
                    )
                elif (
                    config.authentication.type == "bearer_token"
                    and not config.authentication.bearer_token
                ):
                    raise ConfigurationError(
                        "Bearer token is required for bearer_token authentication"
                    )
                elif config.authentication.type == "basic_auth" and (
                    not config.authentication.username
                    or not config.authentication.password
                ):
                    raise ConfigurationError(
                        "Username and password are required for basic_auth authentication"
                    )

            logger.info(f"Configuration {config_name} is valid")
            return True

        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")

    def get_config_info(self, config_name: str) -> Dict[str, Any]:
        """
        Get information about a configuration without loading the full config.

        Args:
            config_name: Name of the configuration

        Returns:
            Dict[str, any]: Configuration information
        """
        try:
            config = self.load_api_config(config_name)

            return {
                "name": config.name,
                "description": config.description,
                "base_url": str(config.base_url),
                "endpoints_count": len(config.endpoints),
                "authentication_type": config.authentication.type,
                "data_format": config.data_format,
                "enabled": config.enabled,
                "schedule": config.schedule,
                "rate_limit": {
                    "requests_per_minute": config.rate_limit.requests_per_minute,
                    "requests_per_hour": config.rate_limit.requests_per_hour,
                    "delay_between_requests": config.rate_limit.delay_between_requests,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get config info for {config_name}: {e}")
            return {"error": str(e)}
