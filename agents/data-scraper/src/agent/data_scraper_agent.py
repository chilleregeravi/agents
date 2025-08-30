"""
Data Scraper Agent - Complete API scraping workflow orchestrator.

This agent implements the complete API scraping flow:
1. Load API configuration from config files
2. Authenticate with APIs using environment variables
3. Scrape data from configured endpoints with rate limiting
4. Transform and validate the scraped data
5. Save results to configured output locations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..clients.api_client import (
    ApiClient,
    ApiClientError,
    DataProcessor,
    RateLimitExceededError,
)
from ..config.config_loader import DataScraperConfigLoader
from ..models.api_config import ApiScrapingConfig, ScrapingJob, ScrapingResult

logger = logging.getLogger(__name__)


class DataScraperAgentError(Exception):
    """Exception raised when data scraper agent execution fails."""

    pass


class DataScraperAgent:
    """
    Data Scraper Agent.

    This agent orchestrates the complete API scraping workflow:
    - Loads API configurations from mounted config files
    - Authenticates with APIs using environment variables
    - Scrapes data from configured endpoints with rate limiting
    - Transforms and validates the scraped data
    - Saves results to configured output locations
    """

    def __init__(
        self,
        config_base_path: str = "/app/config",
        output_base_path: str = "/app/output",
    ):
        """
        Initialize the data scraper agent.

        Args:
            config_base_path: Base path for configuration files
            output_base_path: Base path for output files
        """
        self.execution_id = (
            f"data_scraper_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        self.execution_start_time: Optional[datetime] = None
        self.current_config: Optional[ApiScrapingConfig] = None
        self.current_job: Optional[ScrapingJob] = None
        self.scraping_result: Optional[ScrapingResult] = None

        # Component clients
        self.config_loader: Optional[DataScraperConfigLoader] = None
        self.api_client: Optional[ApiClient] = None

        # Paths
        self.config_base_path = config_base_path
        self.output_base_path = Path(output_base_path)
        self.output_base_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Data Scraper Agent initialized - execution_id: {self.execution_id}, "
            f"config_base_path: {config_base_path}, output_base_path: {self.output_base_path}"
        )

    async def execute_scraping_job(
        self,
        config_name: str,
        job_id: Optional[str] = None,
        override_params: Optional[Dict[str, Any]] = None,
    ) -> ScrapingResult:
        """
        Execute complete API scraping workflow.

        Args:
            config_name: Name of API configuration to use
            job_id: Optional job ID for tracking
            override_params: Optional parameters to override in config

        Returns:
            ScrapingResult: Scraping execution result

        Raises:
            DataScraperAgentError: If scraping execution fails
        """
        self.execution_start_time = datetime.utcnow()
        job_id = job_id or f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        logger.info(
            f"Starting API scraping execution - config_name: {config_name}, "
            f"job_id: {job_id}, execution_id: {self.execution_id}"
        )

        try:
            # Phase 1: Load and validate configuration
            await self._load_configuration(config_name, override_params)

            # Phase 2: Initialize components
            await self._initialize_components()

            # Phase 3: Execute API scraping
            self.scraping_result = await self._execute_scraping_phase(job_id)

            # Phase 4: Process and save results
            await self._execute_output_phase()

            logger.info(
                f"API scraping execution completed successfully - execution_id: {self.execution_id}, "
                f"job_id: {job_id}, duration_seconds: {self.scraping_result.duration_seconds}, "
                f"endpoints_scraped: {self.scraping_result.endpoints_scraped}, "
                f"records_processed: {self.scraping_result.records_processed}"
            )

            return self.scraping_result

        except Exception as e:
            logger.error(
                f"API scraping execution failed - execution_id: {self.execution_id}, error: {str(e)}",
                exc_info=True,
            )

            raise DataScraperAgentError(f"Scraping execution failed: {e}") from e

    async def _load_configuration(
        self, config_name: str, override_params: Optional[Dict[str, Any]]
    ) -> None:
        """Load and validate API scraping configuration."""
        logger.info(f"Loading API scraping configuration: {config_name}")

        try:
            # Initialize config loader
            self.config_loader = DataScraperConfigLoader(self.config_base_path)

            # Load configuration
            self.current_config = self.config_loader.load_api_config(config_name)

            # Apply overrides if provided
            if override_params:
                self._apply_configuration_overrides(override_params)

            # Validate configuration
            self.config_loader.validate_config(config_name)

            logger.info(
                f"Configuration loaded successfully - config_name: {config_name}, "
                f"api_name: {self.current_config.name}, endpoints_count: {len(self.current_config.endpoints)}"
            )

        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise DataScraperAgentError(f"Configuration error: {e}")

    def _apply_configuration_overrides(self, override_params: Dict[str, Any]) -> None:
        """Apply parameter overrides to configuration."""
        if not self.current_config:
            return

        # Override rate limiting
        if "rate_limit" in override_params:
            rate_limit_params = override_params["rate_limit"]
            if "requests_per_minute" in rate_limit_params:
                self.current_config.rate_limit.requests_per_minute = rate_limit_params[
                    "requests_per_minute"
                ]
            if "requests_per_hour" in rate_limit_params:
                self.current_config.rate_limit.requests_per_hour = rate_limit_params[
                    "requests_per_hour"
                ]
            if "delay_between_requests" in rate_limit_params:
                self.current_config.rate_limit.delay_between_requests = (
                    rate_limit_params["delay_between_requests"]
                )

        # Override endpoint parameters
        if "endpoints" in override_params:
            for endpoint_override in override_params["endpoints"]:
                endpoint_name = endpoint_override.get("name")
                if endpoint_name:
                    for endpoint in self.current_config.endpoints:
                        if endpoint.name == endpoint_name:
                            if "params" in endpoint_override:
                                endpoint.params.update(endpoint_override["params"])
                            if "headers" in endpoint_override:
                                endpoint.headers.update(endpoint_override["headers"])
                            break

    async def _initialize_components(self) -> None:
        """Initialize all agent components."""
        logger.info("Initializing agent components")

        if not self.current_config:
            raise DataScraperAgentError("No configuration loaded")

        # Initialize API client
        self.api_client = ApiClient(self.current_config.rate_limit)

        logger.info("All components initialized successfully")

    async def _execute_scraping_phase(self, job_id: str) -> ScrapingResult:
        """Execute API scraping phase."""
        logger.info("Starting API scraping phase")

        if not self.current_config or not self.api_client:
            raise DataScraperAgentError("Components not initialized")

        endpoints_scraped = 0
        records_processed = 0
        total_data_size = 0
        scraped_data = {}

        try:
            async with self.api_client:
                for endpoint in self.current_config.endpoints:
                    try:
                        logger.info(f"Scraping endpoint: {endpoint.name}")

                        # Make API request
                        response = await self.api_client.make_request(
                            endpoint=endpoint,
                            authentication=self.current_config.authentication,
                            base_url=str(self.current_config.base_url),
                        )

                        # Process response data
                        data = response["data"]
                        if data:
                            # Transform data if transformation rules are configured
                            if self.current_config.transformation.field_mapping:
                                data = DataProcessor.transform_data(
                                    data=data,
                                    field_mapping=self.current_config.transformation.field_mapping,
                                    field_filters=self.current_config.transformation.field_filters,
                                    data_validation=self.current_config.transformation.data_validation,
                                )

                            # Count records
                            if isinstance(data, list):
                                records_processed += len(data)
                            else:
                                records_processed += 1

                            # Calculate data size
                            data_str = json.dumps(data)
                            total_data_size += len(data_str.encode("utf-8"))

                            # Store scraped data
                            scraped_data[endpoint.name] = {
                                "data": data,
                                "response_info": response,
                                "timestamp": datetime.utcnow().isoformat(),
                            }

                        endpoints_scraped += 1
                        logger.info(
                            f"Successfully scraped endpoint: {endpoint.name} - "
                            f"records_count: {records_processed if isinstance(data, list) else 1}"
                        )

                    except RateLimitExceededError as e:
                        logger.warning(
                            f"Rate limit exceeded for endpoint {endpoint.name}: {e}"
                        )
                        # Continue with next endpoint
                        continue

                    except ApiClientError as e:
                        logger.error(f"Failed to scrape endpoint {endpoint.name}: {e}")
                        # Continue with next endpoint
                        continue

            # Create scraping result
            end_time = datetime.utcnow()
            duration = (
                (end_time - self.execution_start_time).total_seconds()
                if self.execution_start_time
                else 0.0
            )

            result = ScrapingResult(
                job_id=job_id,
                config_name=self.current_config.name,
                execution_id=self.execution_id,
                status="completed",
                started_at=self.execution_start_time or end_time,
                completed_at=end_time,
                duration_seconds=duration,
                endpoints_scraped=endpoints_scraped,
                records_processed=records_processed,
                data_size_bytes=total_data_size,
                metadata={
                    "workflow_type": "api_scraping",
                    "scraped_endpoints": list(scraped_data.keys()),
                    "raw_data": scraped_data,
                },
            )

            logger.info(
                f"API scraping phase completed successfully - endpoints_scraped: {endpoints_scraped}, "
                f"records_processed: {records_processed}, data_size_bytes: {total_data_size}"
            )

            return result

        except Exception as e:
            raise DataScraperAgentError(f"API scraping phase failed: {e}")

    async def _execute_output_phase(self) -> None:
        """Execute output processing phase."""
        logger.info("Starting output processing phase")

        if not self.scraping_result or not self.current_config:
            raise DataScraperAgentError("No scraping result or configuration available")

        try:
            # Determine output format and location
            output_config = self.current_config.output_config
            output_format = output_config.get("format", "json")
            output_filename = output_config.get(
                "filename", f"{self.current_config.name}_{self.execution_id}"
            )

            # Create output file path
            output_file = self.output_base_path / f"{output_filename}.{output_format}"

            # Extract raw data from metadata
            raw_data = self.scraping_result.metadata.get("raw_data", {})

            # Save data based on format
            if output_format == "json":
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f, indent=2, ensure_ascii=False, default=str)

            elif output_format == "csv":
                import csv

                # Flatten data for CSV output
                flattened_data = []
                for endpoint_name, endpoint_data in raw_data.items():
                    data = endpoint_data["data"]
                    if isinstance(data, list):
                        for record in data:
                            if isinstance(record, dict):
                                record["_endpoint"] = endpoint_name
                                record["_timestamp"] = endpoint_data["timestamp"]
                                flattened_data.append(record)
                    else:
                        if isinstance(data, dict):
                            data["_endpoint"] = endpoint_name
                            data["_timestamp"] = endpoint_data["timestamp"]
                            flattened_data.append(data)

                if flattened_data:
                    fieldnames = set()
                    for record in flattened_data:
                        fieldnames.update(record.keys())

                    with open(output_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=sorted(fieldnames))
                        writer.writeheader()
                        writer.writerows(flattened_data)

            # Update result with output location
            self.scraping_result.output_location = str(output_file)

            logger.info(
                f"Output processing phase completed successfully - output_file: {output_file}, "
                f"output_format: {output_format}"
            )

        except Exception as e:
            raise DataScraperAgentError(f"Output processing phase failed: {e}")

    def _create_execution_result(
        self, status: str, job_id: str, error_message: Optional[str] = None
    ) -> ScrapingResult:
        """Create execution result for failed execution."""
        end_time = datetime.utcnow()
        duration = (
            (end_time - self.execution_start_time).total_seconds()
            if self.execution_start_time
            else 0.0
        )

        return ScrapingResult(
            job_id=job_id,
            config_name=self.current_config.name if self.current_config else "unknown",
            execution_id=self.execution_id,
            status=status,
            started_at=self.execution_start_time or datetime.utcnow(),
            completed_at=end_time,
            duration_seconds=duration,
            endpoints_scraped=0,
            records_processed=0,
            data_size_bytes=0,
            error_message=error_message,
            metadata={
                "workflow_type": "api_scraping",
                "error": error_message,
            },
        )

    async def list_available_configs(self) -> List[Dict[str, Any]]:
        """
        List all available API configurations.

        Returns:
            List[Dict[str, Any]]: List of configuration information
        """
        try:
            if not self.config_loader:
                self.config_loader = DataScraperConfigLoader(self.config_base_path)

            config_names = self.config_loader.list_available_configs()
            configs_info = []

            for config_name in config_names:
                try:
                    info = self.config_loader.get_config_info(config_name)
                    configs_info.append(info)
                except Exception as e:
                    logger.warning(f"Failed to get info for config {config_name}: {e}")
                    configs_info.append({"name": config_name, "error": str(e)})

            return configs_info

        except Exception as e:
            logger.error(f"Failed to list configurations: {e}")
            return []

    async def validate_config(self, config_name: str) -> Dict[str, Any]:
        """
        Validate a configuration without executing it.

        Args:
            config_name: Name of the configuration to validate

        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            if not self.config_loader:
                self.config_loader = DataScraperConfigLoader(self.config_base_path)

            is_valid = self.config_loader.validate_config(config_name)
            config_info = self.config_loader.get_config_info(config_name)

            return {
                "config_name": config_name,
                "valid": is_valid,
                "info": config_info,
            }

        except Exception as e:
            return {
                "config_name": config_name,
                "valid": False,
                "error": str(e),
            }
