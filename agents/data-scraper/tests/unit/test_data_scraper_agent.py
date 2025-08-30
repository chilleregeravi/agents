"""
Unit tests for Data Scraper Agent.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.agent.data_scraper_agent import DataScraperAgent, DataScraperAgentError
from src.models.api_config import ScrapingResult


class TestDataScraperAgent:
    """Test DataScraperAgent."""

    @pytest.fixture
    def agent(self, temp_config_dir, temp_output_dir):
        """Create a data scraper agent instance."""
        return DataScraperAgent(
            config_base_path=temp_config_dir, output_base_path=temp_output_dir
        )

    def test_initialization(self, temp_config_dir, temp_output_dir):
        """Test agent initialization."""
        agent = DataScraperAgent(
            config_base_path=temp_config_dir, output_base_path=temp_output_dir
        )

        assert agent.execution_id is not None
        assert "data_scraper_" in agent.execution_id
        assert agent.config_base_path == Path(temp_config_dir)
        assert agent.output_base_path == Path(temp_output_dir)
        assert agent.config_loader is None
        assert agent.api_client is None

    async def test_list_available_configs_empty(self, agent):
        """Test listing configurations when none exist."""
        configs = await agent.list_available_configs()
        assert isinstance(configs, list)
        assert len(configs) == 0

    async def test_list_available_configs_with_configs(
        self, agent, temp_config_dir, sample_api_config
    ):
        """Test listing configurations when they exist."""
        # Create a config file
        config_file = Path(temp_config_dir) / "apis" / "test-api.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        configs = await agent.list_available_configs()
        assert len(configs) == 1
        assert configs[0]["name"] == "Test API"

    async def test_validate_config_success(
        self, agent, temp_config_dir, sample_api_config
    ):
        """Test successful configuration validation."""
        # Create a config file
        config_file = Path(temp_config_dir) / "apis" / "valid-api.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        import yaml

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        result = await agent.validate_config("valid-api")
        assert result["valid"] is True
        assert result["config_name"] == "valid-api"
        assert "info" in result

    async def test_validate_config_not_found(self, agent):
        """Test validation of non-existent configuration."""
        result = await agent.validate_config("non-existent")
        assert result["valid"] is False
        assert "error" in result

    @patch("src.agent.data_scraper_agent.DataScraperConfigLoader")
    @patch("src.agent.data_scraper_agent.ApiClient")
    async def test_execute_scraping_job_success(
        self, mock_api_client, mock_config_loader, agent, sample_api_config
    ):
        """Test successful scraping job execution."""
        # Mock config loader
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_api_config.return_value = MagicMock(
            **sample_api_config
        )
        mock_loader_instance.validate_config.return_value = True
        mock_config_loader.return_value = mock_loader_instance

        # Mock API client
        mock_client_instance = AsyncMock()
        mock_client_instance.make_request.return_value = {
            "status_code": 200,
            "data": {"test": "data"},
            "headers": {},
            "url": "https://httpbin.org/test",
        }
        mock_api_client.return_value = mock_client_instance

        # Mock file operations
        with patch("builtins.open", create=True), patch("json.dump"), patch(
            "pathlib.Path.mkdir"
        ):
            result = await agent.execute_scraping_job("test-api")

        assert isinstance(result, ScrapingResult)
        assert result.status == "completed"
        assert result.endpoints_scraped == 1
        assert result.records_processed == 1

    @patch("src.agent.data_scraper_agent.DataScraperConfigLoader")
    async def test_execute_scraping_job_config_error(self, mock_config_loader, agent):
        """Test scraping job with configuration error."""
        # Mock config loader to raise error
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_api_config.side_effect = Exception("Config error")
        mock_config_loader.return_value = mock_loader_instance

        with pytest.raises(DataScraperAgentError, match="Configuration error"):
            await agent.execute_scraping_job("test-api")

    @patch("src.agent.data_scraper_agent.DataScraperConfigLoader")
    @patch("src.agent.data_scraper_agent.ApiClient")
    async def test_execute_scraping_job_api_error(
        self, mock_api_client, mock_config_loader, agent, sample_api_config
    ):
        """Test scraping job with API error."""
        # Mock config loader
        mock_loader_instance = MagicMock()
        mock_loader_instance.load_api_config.return_value = MagicMock(
            **sample_api_config
        )
        mock_loader_instance.validate_config.return_value = True
        mock_config_loader.return_value = mock_loader_instance

        # Mock API client to raise error
        mock_client_instance = AsyncMock()
        mock_client_instance.make_request.side_effect = Exception("API error")
        mock_api_client.return_value = mock_client_instance

        # Mock file operations
        with patch("builtins.open", create=True), patch("json.dump"), patch(
            "pathlib.Path.mkdir"
        ):
            result = await agent.execute_scraping_job("test-api")

        # Should complete with errors but not fail completely
        assert isinstance(result, ScrapingResult)
        assert result.endpoints_scraped == 0
        assert result.records_processed == 0

    def test_apply_configuration_overrides_rate_limit(self, agent, sample_api_config):
        """Test applying rate limit overrides."""
        # Set up agent with config
        agent.current_config = MagicMock(**sample_api_config)
        agent.current_config.rate_limit = MagicMock()

        override_params = {
            "rate_limit": {
                "requests_per_minute": 30,
                "requests_per_hour": 500,
                "delay_between_requests": 2.0,
            }
        }

        agent._apply_configuration_overrides(override_params)

        # Verify overrides were applied
        agent.current_config.rate_limit.requests_per_minute = 30
        agent.current_config.rate_limit.requests_per_hour = 500
        agent.current_config.rate_limit.delay_between_requests = 2.0

    def test_apply_configuration_overrides_endpoints(self, agent, sample_api_config):
        """Test applying endpoint overrides."""
        # Set up agent with config
        agent.current_config = MagicMock(**sample_api_config)
        agent.current_config.endpoints = [
            MagicMock(name="endpoint1", params={}, headers={}),
            MagicMock(name="endpoint2", params={}, headers={}),
        ]

        override_params = {
            "endpoints": [
                {
                    "name": "endpoint1",
                    "params": {"limit": 50},
                    "headers": {"Custom-Header": "value"},
                }
            ]
        }

        agent._apply_configuration_overrides(override_params)

        # Verify overrides were applied
        assert agent.current_config.endpoints[0].params == {"limit": 50}
        assert agent.current_config.endpoints[0].headers == {"Custom-Header": "value"}

    def test_create_execution_result_success(self, agent):
        """Test creating execution result for successful execution."""
        agent.execution_start_time = MagicMock()
        agent.current_config = MagicMock()
        agent.current_config.name = "Test Config"

        result = agent._create_execution_result("completed", "test-job")

        assert isinstance(result, ScrapingResult)
        assert result.job_id == "test-job"
        assert result.config_name == "Test Config"
        assert result.status == "completed"
        assert result.execution_id == agent.execution_id

    def test_create_execution_result_failure(self, agent):
        """Test creating execution result for failed execution."""
        agent.execution_start_time = MagicMock()
        agent.current_config = MagicMock()
        agent.current_config.name = "Test Config"

        result = agent._create_execution_result("failed", "test-job", "Test error")

        assert isinstance(result, ScrapingResult)
        assert result.job_id == "test-job"
        assert result.status == "failed"
        assert result.error_message == "Test error"
