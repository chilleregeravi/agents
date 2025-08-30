"""
Pytest configuration for Data Scraper Agent tests.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_config_dir():
    """Create a temporary configuration directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "config" / "apis"
        config_dir.mkdir(parents=True, exist_ok=True)
        yield str(Path(temp_dir) / "config")


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        yield str(output_dir)


@pytest.fixture
def sample_api_config():
    """Sample API configuration for testing."""
    return {
        "name": "Test API",
        "description": "Test configuration for unit tests",
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


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    original_env = os.environ.copy()

    # Set test environment variables
    os.environ.update(
        {
            "API_TOKEN": "test-token",
            "API_KEY": "test-key",
            "API_USERNAME": "test-user",
            "API_PASSWORD": "test-pass",
        }
    )

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
