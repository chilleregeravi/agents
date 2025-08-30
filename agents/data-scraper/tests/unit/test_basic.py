#!/usr/bin/env python3
"""
Basic test script for Data Scraper Agent.

This script tests the basic functionality of the data scraper agent
without requiring actual API credentials.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Import after path setup
from src.agent.data_scraper_agent import DataScraperAgent  # noqa: E402
from src.config.config_loader import DataScraperConfigLoader  # noqa: E402


async def test_config_loader():
    """Test configuration loader functionality."""
    print("Testing configuration loader...")

    # Create temporary config directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config" / "apis"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create a test configuration
        test_config = {
            "name": "Test API",
            "description": "Test configuration",
            "base_url": "https://httpbin.org",
            "authentication": {"type": "none"},
            "endpoints": [
                {
                    "name": "test_endpoint",
                    "url": "/json",
                    "method": "GET",
                    "timeout": 30,
                    "retry_attempts": 3,
                }
            ],
            "rate_limit": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "delay_between_requests": 1.0,
            },
            "data_format": "json",
            "transformation": {
                "field_mapping": {},
                "field_filters": {},
                "data_validation": {},
            },
            "output_config": {"format": "json", "filename": "test_output"},
            "enabled": True,
        }

        # Write test configuration
        config_file = config_dir / "test-api.yaml"

        with open(config_file, "w") as f:
            yaml.dump(test_config, f)

        # Test config loader
        loader = DataScraperConfigLoader(str(Path(temp_dir) / "config"))

        # Test loading configuration
        config = loader.load_api_config("test-api")
        # Remove debug prints for clean test output
        assert config.name == "Test API"
        assert str(config.base_url).rstrip("/") == "https://httpbin.org"
        assert len(config.endpoints) == 1
        assert config.endpoints[0].name == "test_endpoint"

        # Test listing configurations
        configs = loader.list_available_configs()
        assert "test-api" in configs

        # Test validation
        is_valid = loader.validate_config("test-api")
        assert is_valid

        print("✅ Configuration loader tests passed!")


async def test_agent_initialization():
    """Test agent initialization."""
    print("Testing agent initialization...")

    with tempfile.TemporaryDirectory() as temp_dir:
        agent = DataScraperAgent(
            config_base_path=str(Path(temp_dir) / "config"),
            output_base_path=str(Path(temp_dir) / "output"),
        )

        assert agent.execution_id is not None
        assert "data_scraper_" in agent.execution_id
        assert agent.config_loader is None  # Not initialized yet

        print("✅ Agent initialization tests passed!")


async def test_list_configs():
    """Test listing configurations."""
    print("Testing list configurations...")

    with tempfile.TemporaryDirectory() as temp_dir:
        agent = DataScraperAgent(
            config_base_path=str(Path(temp_dir) / "config"),
            output_base_path=str(Path(temp_dir) / "output"),
        )

        # Should return empty list when no configs exist
        configs = await agent.list_available_configs()
        assert isinstance(configs, list)
        assert len(configs) == 0

        print("✅ List configurations tests passed!")


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        # Test that imports work
        print("✅ All imports successful!")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

    return True


async def main():
    """Run all tests."""
    print("🧪 Running Data Scraper Agent Tests")
    print("=" * 50)

    # Test imports first
    if not test_imports():
        return 1

    # Run async tests
    try:
        await test_config_loader()
        await test_agent_initialization()
        await test_list_configs()

        print("\n" + "=" * 50)
        print("🎉 All tests passed!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
