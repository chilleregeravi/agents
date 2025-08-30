"""Unit tests for WebScrapingAgent."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.agent.web_scraping_agent import AgentExecutionError, WebScrapingAgent
from src.models.research_config import ResearchRequest, ResearchResult


class TestWebScrapingAgent:
    """Test suite for WebScrapingAgent class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        client = AsyncMock()
        client.health_check.return_value = {"status": "healthy"}
        return client

    @pytest.fixture
    def mock_web_scraping_research_client(self):
        """Create mock web scraping research client for testing."""
        client = AsyncMock()
        client.execute_web_scraping_research.return_value = Mock(
            execution_id="test_exec_001",
            status="completed",
            sources_found=5,
            sources_analyzed=3,
            insights_generated=10,
            quality_score=0.8,
            duration_seconds=30.0,
        )
        return client

    @pytest.fixture
    def mock_notion_client(self):
        """Create mock Notion client for testing."""
        client = AsyncMock()
        client.create_page.return_value = "https://notion.so/test-page"
        return client

    @pytest.fixture
    def web_scraping_agent(self):
        """Create WebScrapingAgent instance for testing."""
        return WebScrapingAgent()

    @pytest.fixture
    def sample_research_request(self):
        """Create sample research request for testing."""
        from src.models.research_config import ResearchTopic, SearchStrategy

        return ResearchRequest(
            topic=ResearchTopic(
                name="Test Topic",
                description="Test description",
                keywords=["test", "research"],
                focus_areas=["focus1"],
                time_range="2024",
                depth="comprehensive",
            ),
            search_strategy=SearchStrategy(
                max_sources=10,
                credibility_threshold=0.7,
                source_types=["news", "blogs"],
            ),
            analysis_instructions="Test analysis instructions",
        )

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_success(
        self,
        web_scraping_agent,
        sample_research_request,
        mock_llm_client,
        mock_web_scraping_research_client,
        mock_notion_client,
    ):
        """Test successful web scraping research execution."""
        with patch(
            "src.agent.web_scraping_agent.load_research_config"
        ) as mock_load_config, patch(
            "src.agent.web_scraping_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.web_scraping_agent.QwenLLMClient", return_value=mock_llm_client
        ), patch(
            "src.agent.web_scraping_agent.WebScrapingResearchClient",
            return_value=mock_web_scraping_research_client,
        ), patch(
            "src.agent.web_scraping_agent.NotionClient", return_value=mock_notion_client
        ), patch.dict(
            "os.environ",
            {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"},
        ):
            # Mock configuration
            mock_config = Mock()
            mock_config.research_request = sample_research_request
            mock_load_config.return_value = mock_config
            mock_settings.return_value = Mock()

            # Execute research
            result = await web_scraping_agent.execute_web_scraping_research(
                config_name="test_config"
            )

            # Verify result
            assert isinstance(result, ResearchResult)
            assert result.status == "completed"
            # The configuration_name should be a string, not a Mock object
            assert isinstance(result.configuration_name, str)
            assert result.sources_found == 5
            assert result.sources_analyzed == 3
            assert result.insights_generated == 10
            assert result.quality_score == 0.8
            assert result.notion_page_url == "https://notion.so/test-page"
            assert result.metadata["workflow_type"] == "web_scraping_research"

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_config_error(self, web_scraping_agent):
        """Test web scraping research execution with configuration error."""
        with patch(
            "src.agent.web_scraping_agent.load_research_config",
            side_effect=Exception("Config error"),
        ):
            with pytest.raises(AgentExecutionError) as exc_info:
                await web_scraping_agent.execute_web_scraping_research("test_config")

            assert "Configuration error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_llm_error(
        self, web_scraping_agent, mock_llm_client
    ):
        """Test web scraping research execution with LLM error."""
        mock_llm_client.health_check.return_value = {
            "status": "unhealthy",
            "error": "LLM error",
        }

        with patch(
            "src.agent.web_scraping_agent.load_research_config"
        ) as mock_load_config, patch(
            "src.agent.web_scraping_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.web_scraping_agent.QwenLLMClient", return_value=mock_llm_client
        ):
            # Mock configuration
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic"),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config
            mock_settings.return_value = Mock()

            with pytest.raises(AgentExecutionError) as exc_info:
                await web_scraping_agent.execute_web_scraping_research("test_config")

            assert "LLM client health check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_notion_error(
        self, web_scraping_agent, mock_llm_client, mock_web_scraping_research_client
    ):
        """Test web scraping research execution with Notion error."""
        with patch(
            "src.agent.web_scraping_agent.load_research_config"
        ) as mock_load_config, patch(
            "src.agent.web_scraping_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.web_scraping_agent.QwenLLMClient", return_value=mock_llm_client
        ), patch(
            "src.agent.web_scraping_agent.WebScrapingResearchClient",
            return_value=mock_web_scraping_research_client,
        ), patch.dict(
            "os.environ", {}, clear=True
        ):
            # Mock configuration
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic"),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config
            mock_settings.return_value = Mock()

            with pytest.raises(AgentExecutionError) as exc_info:
                await web_scraping_agent.execute_web_scraping_research("test_config")

            assert "Notion token not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_configuration_success(self, web_scraping_agent):
        """Test successful configuration loading."""
        with patch(
            "src.agent.web_scraping_agent.load_research_config"
        ) as mock_load_config:
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic"),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config

            await web_scraping_agent._load_configuration("test_config", None)

            assert web_scraping_agent.current_config == mock_config.research_request

    @pytest.mark.asyncio
    async def test_load_configuration_with_overrides(self, web_scraping_agent):
        """Test configuration loading with overrides."""
        with patch(
            "src.agent.web_scraping_agent.load_research_config"
        ) as mock_load_config:
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic"),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config

            override_params = {"max_sources": 20, "credibility_threshold": 0.8}
            await web_scraping_agent._load_configuration("test_config", override_params)

            assert web_scraping_agent.current_config.search_strategy.max_sources == 20
            assert (
                web_scraping_agent.current_config.search_strategy.credibility_threshold
                == 0.8
            )

    @pytest.mark.asyncio
    async def test_initialize_components_success(
        self,
        web_scraping_agent,
        mock_llm_client,
        mock_web_scraping_research_client,
        mock_notion_client,
    ):
        """Test successful component initialization."""
        with patch("src.agent.web_scraping_agent.get_settings") as mock_settings, patch(
            "src.agent.web_scraping_agent.QwenLLMClient", return_value=mock_llm_client
        ), patch(
            "src.agent.web_scraping_agent.WebScrapingResearchClient",
            return_value=mock_web_scraping_research_client,
        ), patch(
            "src.agent.web_scraping_agent.NotionClient", return_value=mock_notion_client
        ), patch.dict(
            "os.environ",
            {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"},
        ):
            mock_settings.return_value = Mock()

            await web_scraping_agent._initialize_components()

            assert web_scraping_agent.llm_client == mock_llm_client
            assert (
                web_scraping_agent.web_scraping_research_client
                == mock_web_scraping_research_client
            )
            assert web_scraping_agent.notion_client == mock_notion_client

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_phase_success(
        self, web_scraping_agent, mock_web_scraping_research_client
    ):
        """Test successful web scraping research phase execution."""
        web_scraping_agent.web_scraping_research_client = (
            mock_web_scraping_research_client
        )
        web_scraping_agent.current_config = Mock()

        result = await web_scraping_agent._execute_web_scraping_research_phase()

        assert (
            result
            == mock_web_scraping_research_client.execute_web_scraping_research.return_value
        )
        mock_web_scraping_research_client.execute_web_scraping_research.assert_called_once_with(
            web_scraping_agent.current_config
        )

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_phase_error(
        self, web_scraping_agent, mock_web_scraping_research_client
    ):
        """Test web scraping research phase execution with error."""
        web_scraping_agent.web_scraping_research_client = (
            mock_web_scraping_research_client
        )
        mock_web_scraping_research_client.execute_web_scraping_research.side_effect = (
            Exception("Research error")
        )

        with pytest.raises(AgentExecutionError) as exc_info:
            await web_scraping_agent._execute_web_scraping_research_phase()

        assert "Web scraping research phase failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_publishing_phase_success(
        self, web_scraping_agent, mock_notion_client
    ):
        """Test successful publishing phase execution."""
        web_scraping_agent.notion_client = mock_notion_client
        web_scraping_agent.research_result = Mock()

        with patch.object(
            web_scraping_agent,
            "_create_notion_page",
            return_value="https://notion.so/test",
        ):
            result = await web_scraping_agent._execute_publishing_phase()

            assert result == "https://notion.so/test"

    @pytest.mark.asyncio
    async def test_execute_publishing_phase_error(self, web_scraping_agent):
        """Test publishing phase execution with error."""
        web_scraping_agent.research_result = None

        with pytest.raises(AgentExecutionError) as exc_info:
            await web_scraping_agent._execute_publishing_phase()

        assert "No research result to publish" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_notion_page_success(
        self, web_scraping_agent, mock_notion_client
    ):
        """Test successful Notion page creation."""
        web_scraping_agent.notion_client = mock_notion_client
        web_scraping_agent.current_config = Mock(topic=Mock(name="Test Topic"))
        web_scraping_agent.research_result = Mock()

        with patch.object(
            web_scraping_agent, "_build_notion_page_content", return_value=[]
        ):
            result = await web_scraping_agent._create_notion_page()

            assert result == "https://notion.so/test-page"
            mock_notion_client.create_page.assert_called_once()

    def test_build_notion_page_content(self, web_scraping_agent):
        """Test Notion page content building."""
        web_scraping_agent.current_config = Mock(
            topic=Mock(
                name="Test Topic",
                description="Test description",
                keywords=["test", "research"],
                focus_areas=["focus1"],
                time_range="2024",
                depth="comprehensive",
            ),
            analysis_instructions="Test analysis instructions",
        )
        web_scraping_agent.research_result = Mock(
            execution_id="test_exec_001",
            status="completed",
            duration_seconds=30.5,
            sources_found=5,
            sources_analyzed=3,
            insights_generated=10,
            quality_score=0.8,
            metadata={"workflow_type": "web_scraping_research"},
        )

        content = web_scraping_agent._build_notion_page_content()

        assert isinstance(content, list)
        assert len(content) > 0

        # Check for execution summary
        summary_block = next(
            (block for block in content if block.get("type") == "callout"), None
        )
        assert summary_block is not None
        assert "Test Topic" in summary_block["content"]
        assert "test_exec_001" in summary_block["content"]
        assert "5" in summary_block["content"]  # sources_found
        assert "3" in summary_block["content"]  # sources_analyzed
        assert "10" in summary_block["content"]  # insights_generated

    def test_create_execution_result(self, web_scraping_agent):
        """Test execution result creation for failed execution."""
        web_scraping_agent.execution_start_time = datetime.utcnow()
        web_scraping_agent.current_config = Mock(topic=Mock(name="Test Topic"))

        result = web_scraping_agent._create_execution_result("failed", "Test error")

        assert isinstance(result, ResearchResult)
        assert result.status == "failed"
        assert result.error_message == "Test error"
        # The configuration_name should be a string, not a Mock object
        assert isinstance(result.configuration_name, str)
        assert result.metadata["workflow_type"] == "web_scraping_research"
        assert result.metadata["error"] == "Test error"

    def test_agent_initialization(self, web_scraping_agent):
        """Test agent initialization."""
        assert web_scraping_agent.execution_id.startswith("web_scraping_")
        assert web_scraping_agent.execution_start_time is None
        assert web_scraping_agent.current_config is None
        assert web_scraping_agent.research_result is None
        assert web_scraping_agent.llm_client is None
        assert web_scraping_agent.web_scraping_research_client is None
        assert web_scraping_agent.notion_client is None

    @pytest.mark.asyncio
    async def test_apply_configuration_overrides(self, web_scraping_agent):
        """Test configuration override application."""
        web_scraping_agent.current_config = Mock(
            search_strategy=Mock(max_sources=10, credibility_threshold=0.7)
        )

        override_params = {"max_sources": 20, "credibility_threshold": 0.8}
        web_scraping_agent._apply_configuration_overrides(override_params)

        assert web_scraping_agent.current_config.search_strategy.max_sources == 20
        assert (
            web_scraping_agent.current_config.search_strategy.credibility_threshold
            == 0.8
        )

    @pytest.mark.asyncio
    async def test_apply_configuration_overrides_partial(self, web_scraping_agent):
        """Test partial configuration override application."""
        web_scraping_agent.current_config = Mock(
            search_strategy=Mock(max_sources=10, credibility_threshold=0.7)
        )

        override_params = {"max_sources": 20}  # Only max_sources
        web_scraping_agent._apply_configuration_overrides(override_params)

        assert web_scraping_agent.current_config.search_strategy.max_sources == 20
        assert (
            web_scraping_agent.current_config.search_strategy.credibility_threshold
            == 0.7
        )  # Unchanged
