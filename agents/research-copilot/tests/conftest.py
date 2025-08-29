"""Shared test configuration and fixtures for Research Copilot Agent."""

import asyncio
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Mock LLM client for testing."""
    client = AsyncMock()
    client.generate.return_value = "Mocked LLM response"
    client.generate_response.return_value = "Mocked LLM response"
    client.health_check.return_value = {
        "status": "healthy",
        "model": "qwen2:7b",
        "response": "Mocked LLM response",
        "timestamp": 1704067200.0,
    }
    return client


@pytest.fixture
def mock_notion_client() -> AsyncMock:
    """Mock Notion client for testing."""
    client = AsyncMock()
    client.databases = AsyncMock()
    client.databases.query.return_value = {
        "results": [],
        "next_cursor": None,
        "has_more": False,
    }
    client.pages = AsyncMock()
    client.pages.create.return_value = {
        "id": "test-page-123",
        "created_time": "2024-01-01T00:00:00Z",
        "url": "https://notion.so/test-page-123",
    }
    return client


@pytest.fixture
def mock_http_session() -> AsyncMock:
    """Mock HTTP session for testing."""
    session = AsyncMock(spec=aiohttp.ClientSession)

    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.text.return_value = "<html><body>Mock content</body></html>"
    mock_response.json.return_value = {"mock": "data"}

    # Create a proper async context manager mock
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = mock_response
    context_manager.__aexit__.return_value = None

    session.get.return_value = context_manager
    session.post.return_value = context_manager

    return session


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "ollama_host": "localhost:11434",
        "ollama_model": "qwen2:7b",
        "notion_token": "test_token",
        "notion_database_id": "test_database_id",
        "search_api_key": "test_search_key",
        "log_level": "DEBUG",
        "max_retries": 3,
        "timeout": 30,
        "rate_limit_delay": 0.1,  # Faster for tests
    }


@pytest.fixture
def sample_web_content() -> str:
    """Sample web content for testing."""
    return """
    <html>
    <head><title>OpenAI Blog - GPT-4.5 Release</title></head>
    <body>
        <article>
            <h1>Introducing GPT-4.5: Our Most Capable Model Yet</h1>
            <p>Today, we're excited to announce GPT-4.5, our latest and most capable language model.</p>
            <p>Key improvements include:</p>
            <ul>
                <li>Enhanced reasoning capabilities</li>
                <li>Better code generation</li>
                <li>Improved multimodal understanding</li>
            </ul>
            <p>GPT-4.5 is now available through our API.</p>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def sample_search_results() -> Dict[str, Any]:
    """Sample search results for testing."""
    return {
        "organic_results": [
            {
                "position": 1,
                "title": "OpenAI Announces GPT-4.5 with Major Improvements",
                "link": "https://openai.com/blog/gpt-4-5-release",
                "snippet": "OpenAI today released GPT-4.5, featuring enhanced reasoning...",
                "date": "2024-01-12",
            },
            {
                "position": 2,
                "title": "Google's Gemini Pro 2.0 Delivers Better Performance",
                "link": "https://blog.google/technology/ai/gemini-pro-2-announcement",
                "snippet": "Google announces Gemini Pro 2.0 with faster inference...",
                "date": "2024-01-14",
            },
        ],
        "related_searches": [
            "LLM releases January 2024",
            "AI model announcements",
            "GPT-4.5 features",
        ],
    }


@pytest.fixture
async def agent_instance(mock_llm_client, mock_notion_client, sample_config):
    """Create agent instance for testing."""
    from src.agent.main import ResearchCopilotAgent

    agent = ResearchCopilotAgent(
        config=sample_config,
        llm_client=mock_llm_client,
        notion_client=mock_notion_client,
    )
    return agent


@pytest.fixture
def mock_kubernetes_client() -> AsyncMock:
    """Mock Kubernetes client for testing."""
    client = AsyncMock()
    client.list_namespaced_pod.return_value = Mock(items=[])
    client.create_namespaced_deployment.return_value = Mock(
        metadata=Mock(name="test-deployment")
    )
    return client


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test."""
    yield
    # Cleanup happens automatically with pytest


# Test markers
pytestmark = [
    pytest.mark.asyncio,
]


# Custom test utilities
class MockAsyncContextManager:
    """Mock async context manager for testing."""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def create_mock_response(status=200, json_data=None, text_data=None):
    """Create a mock HTTP response."""
    mock_response = AsyncMock()
    mock_response.status = status

    if json_data is not None:
        mock_response.json.return_value = json_data

    if text_data is not None:
        mock_response.text.return_value = text_data

    return MockAsyncContextManager(mock_response)


@pytest.fixture
def sample_research_data():
    """Sample research data for testing."""
    return {
        "topic": {"name": "AI Research"},
        "summary": "This is a comprehensive analysis of AI research trends.",
        "findings": [
            "AI adoption is increasing rapidly",
            "Large language models are becoming more sophisticated",
            "Ethical considerations are paramount",
        ],
        "sources": [
            {
                "title": "AI Research Paper",
                "url": "https://example.com/paper",
                "credibility": 0.9,
                "date": "2024-01-15",
                "source_type": "research",
            },
            {
                "title": "Tech News Article",
                "url": "https://example.com/news",
                "credibility": 0.8,
                "date": "2024-01-14",
                "source_type": "news",
            },
        ],
        "insights": [
            {
                "title": "Key Insight",
                "content": "AI models are becoming more efficient",
                "confidence": 0.85,
            }
        ],
        "content": "Detailed analysis content here...",
    }


@pytest.fixture
def sample_output_schema():
    """Sample output schema for testing."""
    from src.models.research_config import (
        ContentProcessing,
        OutputSchema,
        PageSection,
        PageStructure,
    )

    return OutputSchema(
        output_format="notion_page",
        template="research_report",
        page_structure=PageStructure(
            title_template="Research Report - {topic_name}",
            tags=["research", "test"],
            sections=[
                PageSection(
                    name="Summary",
                    type="text_block",
                    content_source="summary",
                    order=1,
                    required=True,
                    configuration={"max_length": 500},
                ),
                PageSection(
                    name="Key Findings",
                    type="bullet_list",
                    content_source="findings",
                    order=2,
                    required=True,
                    configuration={"max_items": 10},
                ),
                PageSection(
                    name="Sources",
                    type="table",
                    content_source="sources",
                    order=3,
                    required=True,
                    configuration={
                        "columns": ["Title", "URL", "Credibility", "Date"],
                        "sort_by": "credibility",
                    },
                ),
            ],
        ),
        content_processing=ContentProcessing(
            summary_length="detailed",
            include_confidence_scores=True,
            group_similar_findings=True,
        ),
    )
