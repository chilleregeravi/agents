"""Unit tests for WebScrapingResearchClient."""

from unittest.mock import AsyncMock

import pytest
from src.clients.web_scraping_research_client import (
    ScrapingStrategy,
    WebScrapingResearchClient,
    WebScrapingResearchError,
    WebSource,
)
from src.models.research_config import ResearchRequest, ResearchResult


class TestWebScrapingResearchClient:
    """Test suite for WebScrapingResearchClient class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        client = AsyncMock()
        client.generate_response.return_value = '{"target_sources": []}'
        return client

    @pytest.fixture
    def mock_session(self):
        """Create mock HTTP session for testing."""
        session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.text.return_value = "<html><body>Test content</body></html>"
        session.get.return_value.__aenter__.return_value = response
        return session

    @pytest.fixture
    def web_scraping_client(self, mock_llm_client, mock_session):
        """Create WebScrapingResearchClient instance for testing."""
        return WebScrapingResearchClient(
            llm_client=mock_llm_client, session=mock_session
        )

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

    @pytest.fixture
    def sample_web_source(self):
        """Create sample web source for testing."""
        return WebSource(
            url="https://example.com/test",
            domain="example.com",
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.9,
            description="Test source",
            priority=1,
        )

    @pytest.fixture
    def sample_scraping_strategy(self, sample_web_source):
        """Create sample scraping strategy for testing."""
        return ScrapingStrategy(
            target_sources=[sample_web_source],
            search_queries=["test query"],
            content_keywords=["test"],
            quality_indicators=["official"],
            max_sources_to_scrape=5,
            scraping_timeout=30,
            content_filters=[],
        )

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_success(
        self, web_scraping_client, sample_research_request, mock_llm_client
    ):
        """Test successful web scraping research execution."""
        # Mock LLM responses
        mock_llm_client.generate_response.side_effect = [
            '{"target_sources": [{"url": "https://example.com", "domain": "example.com", "source_type": "news", "credibility_score": 0.8, "relevance_score": 0.9, "description": "Test", "priority": 1}], "search_queries": [], "content_keywords": [], "quality_indicators": [], "content_filters": []}',
            '{"sources": []}',
            '{"insights": []}',
        ]

        # Execute research
        result = await web_scraping_client.execute_web_scraping_research(
            sample_research_request
        )

        # Verify result
        assert isinstance(result, ResearchResult)
        assert result.execution_id.startswith("web_scraping_research_")
        assert result.status == "completed"
        assert result.configuration_name == "Test Topic"
        assert result.duration_seconds > 0
        assert result.metadata["workflow_type"] == "web_scraping_research"

    @pytest.mark.asyncio
    async def test_execute_web_scraping_research_error(
        self, web_scraping_client, sample_research_request, mock_llm_client
    ):
        """Test web scraping research with error."""
        mock_llm_client.generate_response.side_effect = Exception("LLM error")

        with pytest.raises(WebScrapingResearchError) as exc_info:
            await web_scraping_client.execute_web_scraping_research(
                sample_research_request
            )

        assert "Research failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_scraping_strategy(
        self, web_scraping_client, sample_research_request, mock_llm_client
    ):
        """Test scraping strategy generation."""
        mock_llm_client.generate_response.return_value = '{"target_sources": [{"url": "https://example.com", "domain": "example.com", "source_type": "news", "credibility_score": 0.8, "relevance_score": 0.9, "description": "Test", "priority": 1}], "search_queries": ["test"], "content_keywords": ["test"], "quality_indicators": ["official"], "content_filters": []}'

        strategy = await web_scraping_client._generate_scraping_strategy(
            sample_research_request
        )

        assert isinstance(strategy, ScrapingStrategy)
        assert len(strategy.target_sources) == 1
        assert strategy.target_sources[0].url == "https://example.com"
        assert strategy.search_queries == ["test"]
        assert strategy.content_keywords == ["test"]

    @pytest.mark.asyncio
    async def test_generate_scraping_strategy_fallback(
        self, web_scraping_client, sample_research_request, mock_llm_client
    ):
        """Test scraping strategy generation with fallback."""
        mock_llm_client.generate_response.side_effect = Exception("LLM error")

        strategy = await web_scraping_client._generate_scraping_strategy(
            sample_research_request
        )

        assert isinstance(strategy, ScrapingStrategy)
        assert len(strategy.target_sources) > 0
        assert len(strategy.search_queries) > 0

    def test_construct_strategy_prompt(
        self, web_scraping_client, sample_research_request
    ):
        """Test strategy prompt construction."""
        prompt = web_scraping_client._construct_strategy_prompt(sample_research_request)

        assert "Test Topic" in prompt
        assert "Test description" in prompt
        assert "test, research" in prompt
        assert "focus1" in prompt
        assert "2024" in prompt
        assert "comprehensive" in prompt
        assert "Test analysis instructions" in prompt
        assert "target_sources" in prompt

    def test_create_fallback_strategy(
        self, web_scraping_client, sample_research_request
    ):
        """Test fallback strategy creation."""
        strategy = web_scraping_client._create_fallback_strategy(
            sample_research_request
        )

        assert isinstance(strategy, ScrapingStrategy)
        assert len(strategy.target_sources) == 2  # techcrunch and reuters
        assert len(strategy.search_queries) == 3
        assert strategy.content_keywords == ["test", "research"]

    @pytest.mark.asyncio
    async def test_scrape_internet_data(
        self, web_scraping_client, sample_scraping_strategy, sample_research_request
    ):
        """Test internet data scraping."""
        scraped_data = await web_scraping_client._scrape_internet_data(
            sample_scraping_strategy, sample_research_request
        )

        assert isinstance(scraped_data, list)
        # Should have scraped data from the target source
        assert len(scraped_data) > 0

    @pytest.mark.asyncio
    async def test_scrape_web_source_success(
        self, web_scraping_client, sample_web_source, sample_scraping_strategy
    ):
        """Test successful web source scraping."""
        content = await web_scraping_client._scrape_web_source(
            sample_web_source, sample_scraping_strategy
        )

        assert content is not None
        assert content["title"] == "Test source"  # Uses description as fallback
        assert "Test content" in content["content"]
        assert content["url"] == "https://example.com/test"
        assert content["source_type"] == "news"
        assert content["credibility_score"] == 0.8
        assert content["relevance_score"] == 0.9

    @pytest.mark.asyncio
    async def test_scrape_web_source_failure(
        self,
        web_scraping_client,
        sample_web_source,
        sample_scraping_strategy,
        mock_session,
    ):
        """Test web source scraping failure."""
        # Mock failed response
        response = AsyncMock()
        response.status = 404
        mock_session.get.return_value.__aenter__.return_value = response

        content = await web_scraping_client._scrape_web_source(
            sample_web_source, sample_scraping_strategy
        )

        assert content is None

    def test_passes_content_filters(
        self, web_scraping_client, sample_scraping_strategy
    ):
        """Test content filter checking."""
        # Test content that passes filters
        content = "This is test content with official information"
        assert web_scraping_client._passes_content_filters(
            content, sample_scraping_strategy
        )

        # Test content that fails keyword filter
        strategy_no_keywords = ScrapingStrategy(
            target_sources=[],
            search_queries=[],
            content_keywords=["required_keyword"],
            quality_indicators=[],
            max_sources_to_scrape=5,
            scraping_timeout=30,
            content_filters=[],
        )
        content_no_keywords = "This content doesn't have the required keyword"
        assert not web_scraping_client._passes_content_filters(
            content_no_keywords, strategy_no_keywords
        )

        # Test content that fails quality filter
        strategy_no_quality = ScrapingStrategy(
            target_sources=[],
            search_queries=[],
            content_keywords=[],
            quality_indicators=["official"],
            max_sources_to_scrape=5,
            scraping_timeout=30,
            content_filters=[],
        )
        content_no_quality = "This content doesn't have official information"
        assert not web_scraping_client._passes_content_filters(
            content_no_quality, strategy_no_quality
        )

    @pytest.mark.asyncio
    async def test_discover_sources_from_query(
        self,
        web_scraping_client,
        sample_scraping_strategy,
        sample_research_request,
        mock_llm_client,
    ):
        """Test source discovery from query."""
        mock_llm_client.generate_response.return_value = '{"sources": [{"url": "https://discovered.com", "domain": "discovered.com", "source_type": "news", "credibility_score": 0.7, "relevance_score": 0.8, "description": "Discovered source", "priority": 2}]}'

        sources = await web_scraping_client._discover_sources_from_query(
            "test query", sample_scraping_strategy, sample_research_request
        )

        assert len(sources) == 1
        assert sources[0].url == "https://discovered.com"
        assert sources[0].domain == "discovered.com"

    @pytest.mark.asyncio
    async def test_discover_sources_from_query_error(
        self,
        web_scraping_client,
        sample_scraping_strategy,
        sample_research_request,
        mock_llm_client,
    ):
        """Test source discovery with error."""
        mock_llm_client.generate_response.side_effect = Exception("Discovery error")

        sources = await web_scraping_client._discover_sources_from_query(
            "test query", sample_scraping_strategy, sample_research_request
        )

        assert sources == []

    @pytest.mark.asyncio
    async def test_organize_scraped_data(
        self, web_scraping_client, sample_research_request
    ):
        """Test scraped data organization."""
        scraped_data = [
            {
                "title": "Test Article",
                "content": "Test content",
                "url": "https://example.com/test",
                "source_type": "news",
                "domain": "example.com",
                "credibility_score": 0.8,
                "relevance_score": 0.9,
                "publication_date": "2024-01-01T00:00:00",
                "scraped_at": "2024-01-01T00:00:00",
            }
        ]

        research_data = await web_scraping_client._organize_scraped_data(
            scraped_data, sample_research_request
        )

        assert research_data.topic_name == "Test Topic"
        assert len(research_data.data_sources) == 1
        assert len(research_data.news_articles) == 1
        assert research_data.collection_method == "web_scraping"
        assert research_data.total_content_length > 0
        assert research_data.source_diversity > 0

    def test_create_analysis_request(
        self, web_scraping_client, sample_research_request
    ):
        """Test analysis request creation."""
        from src.models.research_config import ResearchData

        research_data = ResearchData(
            topic_name="Test Topic",
            data_sources=["https://example.com"],
            web_pages=[],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="web_scraping",
            total_content_length=100,
            source_diversity=0.8,
            content_freshness=0.9,
            relevance_score=0.7,
        )

        analysis_request = web_scraping_client._create_analysis_request(
            research_data, sample_research_request
        )

        assert analysis_request.research_data == research_data
        assert analysis_request.analysis_focus == ["focus1"]
        assert analysis_request.include_confidence_scores is True
        assert analysis_request.trend_analysis is True

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_llm_client):
        """Test async context manager functionality."""
        async with WebScrapingResearchClient(mock_llm_client) as client:
            assert isinstance(client, WebScrapingResearchClient)
            assert client.llm_client == mock_llm_client

    def test_web_source_model(self):
        """Test WebSource model validation."""
        source = WebSource(
            url="https://example.com",
            domain="example.com",
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.9,
            description="Test source",
            priority=1,
        )

        assert source.url == "https://example.com"
        assert source.domain == "example.com"
        assert source.source_type == "news"
        assert source.credibility_score == 0.8
        assert source.relevance_score == 0.9
        assert source.description == "Test source"
        assert source.priority == 1

    def test_scraping_strategy_model(self):
        """Test ScrapingStrategy model validation."""
        strategy = ScrapingStrategy(
            target_sources=[],
            search_queries=["test"],
            content_keywords=["test"],
            quality_indicators=["official"],
            max_sources_to_scrape=10,
            scraping_timeout=30,
            content_filters=[],
        )

        assert strategy.search_queries == ["test"]
        assert strategy.content_keywords == ["test"]
        assert strategy.quality_indicators == ["official"]
        assert strategy.max_sources_to_scrape == 10
        assert strategy.scraping_timeout == 30
        assert strategy.content_filters == []
