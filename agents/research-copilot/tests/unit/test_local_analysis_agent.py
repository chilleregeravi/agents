"""Unit tests for LocalAnalysisAgent."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.agent.local_analysis_agent import AgentExecutionError, LocalAnalysisAgent
from src.models.research_config import ResearchData, ResearchResult


class TestLocalAnalysisAgent:
    """Test suite for LocalAnalysisAgent class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        client = AsyncMock()
        client.health_check.return_value = {"status": "healthy"}
        return client

    @pytest.fixture
    def mock_local_analysis_client(self):
        """Create mock local analysis client for testing."""
        client = AsyncMock()
        client.analyze_research_data.return_value = Mock(
            analysis_id="test_analysis_001",
            key_insights=[Mock(title="Test Insight")],
            analysis_confidence=0.8,
            processing_time_seconds=10.0,
            executive_summary="Test summary",
            trend_analysis={"summary": "Test trends"},
            quantitative_findings=[{"metric": "Test", "value": "100"}],
        )
        return client

    @pytest.fixture
    def mock_notion_client(self):
        """Create mock Notion client for testing."""
        client = AsyncMock()
        client.create_page.return_value = "https://notion.so/test-page"
        return client

    @pytest.fixture
    def local_analysis_agent(self):
        """Create LocalAnalysisAgent instance for testing."""
        return LocalAnalysisAgent()

    @pytest.fixture
    def sample_research_data(self):
        """Create sample research data for testing."""
        return ResearchData(
            topic_name="Test Topic",
            data_sources=["https://example.com"],
            web_pages=[
                {
                    "title": "Test Article",
                    "content": "Test content",
                    "url": "https://example.com/test",
                    "source_type": "web_pages",
                }
            ],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="test",
            total_content_length=100,
            source_diversity=0.8,
            content_freshness=0.9,
            relevance_score=0.7,
        )

    @pytest.mark.asyncio
    async def test_execute_analysis_success(
        self,
        local_analysis_agent,
        sample_research_data,
        mock_llm_client,
        mock_local_analysis_client,
        mock_notion_client,
    ):
        """Test successful analysis execution."""
        with patch(
            "src.agent.local_analysis_agent.load_research_config"
        ) as mock_load_config, patch(
            "src.agent.local_analysis_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.local_analysis_agent.QwenLLMClient", return_value=mock_llm_client
        ), patch(
            "src.agent.local_analysis_agent.LocalAnalysisClient",
            return_value=mock_local_analysis_client,
        ), patch(
            "src.agent.local_analysis_agent.NotionClient",
            return_value=mock_notion_client,
        ), patch.dict(
            "os.environ",
            {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"},
        ):
            # Mock configuration
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic", focus_areas=["focus1"]),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config
            mock_settings.return_value = Mock()

            # Execute analysis
            result = await local_analysis_agent.execute_analysis(
                research_data=sample_research_data, config_name="test_config"
            )

            # Verify result
            assert isinstance(result, ResearchResult)
            assert result.status == "completed"
            assert result.configuration_name == "test_config"
            assert result.sources_analyzed == 1
            assert result.insights_generated == 1
            assert result.quality_score == 0.8
            assert result.notion_page_url == "https://notion.so/test-page"
            assert result.metadata["workflow_type"] == "local_analysis"

    @pytest.mark.asyncio
    async def test_execute_analysis_config_error(
        self, local_analysis_agent, sample_research_data
    ):
        """Test analysis execution with configuration error."""
        with patch(
            "src.agent.local_analysis_agent.load_research_config",
            side_effect=Exception("Config error"),
        ):
            with pytest.raises(AgentExecutionError) as exc_info:
                await local_analysis_agent.execute_analysis(
                    research_data=sample_research_data, config_name="test_config"
                )

            assert "Configuration error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_analysis_llm_error(
        self, local_analysis_agent, sample_research_data, mock_llm_client
    ):
        """Test analysis execution with LLM error."""
        mock_llm_client.health_check.return_value = {
            "status": "unhealthy",
            "error": "LLM error",
        }

        with patch(
            "src.agent.local_analysis_agent.load_research_config"
        ) as mock_load_config, patch(
            "src.agent.local_analysis_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.local_analysis_agent.QwenLLMClient", return_value=mock_llm_client
        ):
            # Mock configuration
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic", focus_areas=["focus1"]),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config
            mock_settings.return_value = Mock()

            with pytest.raises(AgentExecutionError) as exc_info:
                await local_analysis_agent.execute_analysis(
                    research_data=sample_research_data, config_name="test_config"
                )

            assert "LLM client health check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_analysis_notion_error(
        self,
        local_analysis_agent,
        sample_research_data,
        mock_llm_client,
        mock_local_analysis_client,
    ):
        """Test analysis execution with Notion error."""
        with patch(
            "src.agent.local_analysis_agent.load_research_config"
        ) as mock_load_config, patch(
            "src.agent.local_analysis_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.local_analysis_agent.QwenLLMClient", return_value=mock_llm_client
        ), patch(
            "src.agent.local_analysis_agent.LocalAnalysisClient",
            return_value=mock_local_analysis_client,
        ), patch.dict(
            "os.environ", {}, clear=True
        ):
            # Mock configuration
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic", focus_areas=["focus1"]),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config
            mock_settings.return_value = Mock()

            with pytest.raises(AgentExecutionError) as exc_info:
                await local_analysis_agent.execute_analysis(
                    research_data=sample_research_data, config_name="test_config"
                )

            assert "Notion token not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_load_configuration_success(self, local_analysis_agent):
        """Test successful configuration loading."""
        with patch(
            "src.agent.local_analysis_agent.load_research_config"
        ) as mock_load_config:
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic"),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config

            await local_analysis_agent._load_configuration("test_config", None)

            assert local_analysis_agent.current_config == mock_config.research_request

    @pytest.mark.asyncio
    async def test_load_configuration_with_overrides(self, local_analysis_agent):
        """Test configuration loading with overrides."""
        with patch(
            "src.agent.local_analysis_agent.load_research_config"
        ) as mock_load_config:
            mock_config = Mock()
            mock_config.research_request = Mock(
                topic=Mock(name="Test Topic"),
                search_strategy=Mock(max_sources=10, credibility_threshold=0.7),
            )
            mock_load_config.return_value = mock_config

            override_params = {"max_sources": 20, "credibility_threshold": 0.8}
            await local_analysis_agent._load_configuration(
                "test_config", override_params
            )

            assert local_analysis_agent.current_config.search_strategy.max_sources == 20
            assert (
                local_analysis_agent.current_config.search_strategy.credibility_threshold
                == 0.8
            )

    @pytest.mark.asyncio
    async def test_initialize_components_success(
        self,
        local_analysis_agent,
        mock_llm_client,
        mock_local_analysis_client,
        mock_notion_client,
    ):
        """Test successful component initialization."""
        with patch(
            "src.agent.local_analysis_agent.get_settings"
        ) as mock_settings, patch(
            "src.agent.local_analysis_agent.QwenLLMClient", return_value=mock_llm_client
        ), patch(
            "src.agent.local_analysis_agent.LocalAnalysisClient",
            return_value=mock_local_analysis_client,
        ), patch(
            "src.agent.local_analysis_agent.NotionClient",
            return_value=mock_notion_client,
        ), patch.dict(
            "os.environ",
            {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"},
        ):
            mock_settings.return_value = Mock()

            await local_analysis_agent._initialize_components()

            assert local_analysis_agent.llm_client == mock_llm_client
            assert (
                local_analysis_agent.local_analysis_client == mock_local_analysis_client
            )
            assert local_analysis_agent.notion_client == mock_notion_client

    def test_create_analysis_request(self, local_analysis_agent, sample_research_data):
        """Test analysis request creation."""
        # Set up current config
        local_analysis_agent.current_config = Mock(
            topic=Mock(focus_areas=["focus1", "focus2"])
        )

        analysis_request = local_analysis_agent._create_analysis_request(
            sample_research_data
        )

        assert analysis_request.research_data == sample_research_data
        assert analysis_request.analysis_focus == ["focus1", "focus2"]
        assert analysis_request.include_confidence_scores is True
        assert analysis_request.trend_analysis is True
        assert analysis_request.summary_length == "detailed"

    @pytest.mark.asyncio
    async def test_execute_analysis_phase_success(
        self, local_analysis_agent, mock_local_analysis_client
    ):
        """Test successful analysis phase execution."""
        local_analysis_agent.local_analysis_client = mock_local_analysis_client

        analysis_request = Mock()
        result = await local_analysis_agent._execute_analysis_phase(analysis_request)

        assert result == mock_local_analysis_client.analyze_research_data.return_value
        mock_local_analysis_client.analyze_research_data.assert_called_once_with(
            analysis_request
        )

    @pytest.mark.asyncio
    async def test_execute_analysis_phase_error(
        self, local_analysis_agent, mock_local_analysis_client
    ):
        """Test analysis phase execution with error."""
        local_analysis_agent.local_analysis_client = mock_local_analysis_client
        mock_local_analysis_client.analyze_research_data.side_effect = Exception(
            "Analysis error"
        )

        analysis_request = Mock()

        with pytest.raises(AgentExecutionError) as exc_info:
            await local_analysis_agent._execute_analysis_phase(analysis_request)

        assert "Analysis phase failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_publishing_phase_success(
        self, local_analysis_agent, mock_notion_client
    ):
        """Test successful publishing phase execution."""
        local_analysis_agent.notion_client = mock_notion_client
        local_analysis_agent.current_config = Mock(topic=Mock(name="Test Topic"))

        analysis_result = Mock()

        with patch.object(
            local_analysis_agent,
            "_create_notion_page",
            return_value="https://notion.so/test",
        ):
            result = await local_analysis_agent._execute_publishing_phase(
                analysis_result
            )

            assert result == "https://notion.so/test"

    @pytest.mark.asyncio
    async def test_execute_publishing_phase_error(self, local_analysis_agent):
        """Test publishing phase execution with error."""
        local_analysis_agent.research_result = None

        with pytest.raises(AgentExecutionError) as exc_info:
            await local_analysis_agent._execute_publishing_phase(Mock())

        assert "Missing analysis result or configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_notion_page_success(
        self, local_analysis_agent, mock_notion_client
    ):
        """Test successful Notion page creation."""
        local_analysis_agent.notion_client = mock_notion_client
        local_analysis_agent.current_config = Mock(topic=Mock(name="Test Topic"))
        local_analysis_agent.research_result = Mock()

        with patch.object(
            local_analysis_agent, "_build_notion_page_content", return_value=[]
        ):
            result = await local_analysis_agent._create_notion_page(Mock())

            assert result == "https://notion.so/test-page"
            mock_notion_client.create_page.assert_called_once()

    def test_build_notion_page_content(self, local_analysis_agent):
        """Test Notion page content building."""
        local_analysis_agent.current_config = Mock(topic=Mock(name="Test Topic"))
        local_analysis_agent.research_result = Mock(
            execution_id="test_exec_001",
            status="completed",
            duration_seconds=10.5,
            insights_generated=5,
            quality_score=0.8,
        )

        analysis_result = Mock(
            processing_time_seconds=10.0,
            analysis_confidence=0.8,
            executive_summary="Test summary",
            key_insights=[
                Mock(title="Test Insight", confidence_score=0.8, description="Test")
            ],
            trend_analysis={"summary": "Test trends"},
            quantitative_findings=[{"metric": "Test", "value": "100", "unit": "units"}],
        )

        content = local_analysis_agent._build_notion_page_content(analysis_result)

        assert isinstance(content, list)
        assert len(content) > 0

        # Check for execution summary
        summary_block = next(
            (block for block in content if block.get("type") == "callout"), None
        )
        assert summary_block is not None
        assert "Test Topic" in summary_block["content"]
        # The execution ID should be in the content
        assert "test_exec_001" in summary_block["content"]

    def test_create_execution_result(self, local_analysis_agent):
        """Test execution result creation for failed execution."""
        local_analysis_agent.execution_start_time = datetime.utcnow()
        local_analysis_agent.current_config = Mock(topic=Mock(name="Test Topic"))

        result = local_analysis_agent._create_execution_result("failed", "Test error")

        assert isinstance(result, ResearchResult)
        assert result.status == "failed"
        assert result.error_message == "Test error"
        # The configuration_name should be a string, not a Mock object
        assert isinstance(result.configuration_name, str)
        assert result.metadata["workflow_type"] == "local_analysis"
        assert result.metadata["error"] == "Test error"

    def test_agent_initialization(self, local_analysis_agent):
        """Test agent initialization."""
        assert local_analysis_agent.execution_id.startswith("local_analysis_")
        assert local_analysis_agent.execution_start_time is None
        assert local_analysis_agent.current_config is None
        assert local_analysis_agent.research_result is None
        assert local_analysis_agent.llm_client is None
        assert local_analysis_agent.local_analysis_client is None
        assert local_analysis_agent.notion_client is None
