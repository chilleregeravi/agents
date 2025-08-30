"""
Unit tests for Data Scraper Agent configuration loader.
"""

from pathlib import Path

import pytest
import yaml
from src.config.config_loader import ConfigurationError, DataScraperConfigLoader


class TestDataScraperConfigLoader:
    """Test DataScraperConfigLoader."""

    def test_initialization(self, temp_config_dir):
        """Test config loader initialization."""
        loader = DataScraperConfigLoader(temp_config_dir)
        assert loader.config_base_path == Path(temp_config_dir)
        assert loader.apis_path == Path(temp_config_dir) / "apis"
        assert loader.jobs_path == Path(temp_config_dir) / "jobs"

    def test_load_api_config_success(self, temp_config_dir, sample_api_config):
        """Test successful API configuration loading."""
        # Create config file
        config_file = Path(temp_config_dir) / "apis" / "test-api.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        # Load configuration
        loader = DataScraperConfigLoader(temp_config_dir)
        config = loader.load_api_config("test-api")

        assert config.name == "Test API"
        assert config.description == "Test configuration for unit tests"
        assert str(config.base_url).rstrip("/") == "https://httpbin.org"

    def test_load_api_config_not_found(self, temp_config_dir):
        """Test loading non-existent configuration."""
        loader = DataScraperConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            loader.load_api_config("non-existent")

    def test_load_api_config_invalid_yaml(self, temp_config_dir):
        """Test loading configuration with invalid YAML."""
        # Create invalid YAML file
        config_file = Path(temp_config_dir) / "apis" / "invalid.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        loader = DataScraperConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            loader.load_api_config("invalid")

    def test_load_api_config_validation_error(self, temp_config_dir):
        """Test loading configuration with validation errors."""
        # Create invalid config (missing required fields)
        invalid_config = {
            "name": "Test API",
            # Missing required fields
        }

        config_file = Path(temp_config_dir) / "apis" / "invalid-config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(invalid_config, f)

        loader = DataScraperConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError, match="Configuration validation failed"):
            loader.load_api_config("invalid-config")

    def test_list_available_configs(self, temp_config_dir, sample_api_config):
        """Test listing available configurations."""
        # Create multiple config files
        configs = ["api1", "api2", "api3"]

        for config_name in configs:
            config_file = Path(temp_config_dir) / "apis" / f"{config_name}.yaml"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Modify config for each file
            config_data = sample_api_config.copy()
            config_data["name"] = f"Test API {config_name}"

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

        loader = DataScraperConfigLoader(temp_config_dir)
        available_configs = loader.list_available_configs()

        assert len(available_configs) == 3
        assert "api1" in available_configs
        assert "api2" in available_configs
        assert "api3" in available_configs

    def test_list_available_configs_empty(self, temp_config_dir):
        """Test listing configurations when none exist."""
        loader = DataScraperConfigLoader(temp_config_dir)
        configs = loader.list_available_configs()

        assert configs == []

    def test_validate_config_success(self, temp_config_dir, sample_api_config):
        """Test successful configuration validation."""
        # Create valid config file
        config_file = Path(temp_config_dir) / "apis" / "valid-api.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        loader = DataScraperConfigLoader(temp_config_dir)
        is_valid = loader.validate_config("valid-api")

        assert is_valid is True

    def test_validate_config_disabled(self, temp_config_dir, sample_api_config):
        """Test validation of disabled configuration."""
        # Create disabled config
        sample_api_config["enabled"] = False

        config_file = Path(temp_config_dir) / "apis" / "disabled-api.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        loader = DataScraperConfigLoader(temp_config_dir)
        is_valid = loader.validate_config("disabled-api")

        assert is_valid is True  # Should still be valid, just disabled

    def test_validate_config_missing_auth(self, temp_config_dir, sample_api_config):
        """Test validation with missing authentication credentials."""
        # Create config with bearer token but no token value
        sample_api_config["authentication"] = {
            "type": "bearer_token",
            "bearer_token": None,
        }

        config_file = Path(temp_config_dir) / "apis" / "missing-auth.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        loader = DataScraperConfigLoader(temp_config_dir)

        with pytest.raises(ConfigurationError, match="Bearer token is required"):
            loader.validate_config("missing-auth")

    def test_get_config_info(self, temp_config_dir, sample_api_config):
        """Test getting configuration information."""
        # Create config file
        config_file = Path(temp_config_dir) / "apis" / "info-api.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(config_file, "w") as f:
            yaml.dump(sample_api_config, f)

        loader = DataScraperConfigLoader(temp_config_dir)
        info = loader.get_config_info("info-api")

        assert info["name"] == "Test API"
        assert info["description"] == "Test configuration for unit tests"
        assert info["base_url"] == "https://httpbin.org/"
        assert info["endpoints_count"] == 1
        assert info["authentication_type"] == "none"
        assert info["data_format"] == "json"
        assert info["enabled"] is True

    def test_get_config_info_error(self, temp_config_dir):
        """Test getting config info for non-existent configuration."""
        loader = DataScraperConfigLoader(temp_config_dir)
        info = loader.get_config_info("non-existent")

        assert "error" in info
        assert "Configuration file not found" in info["error"]
