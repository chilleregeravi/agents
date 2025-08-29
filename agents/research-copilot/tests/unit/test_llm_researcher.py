"""Tests for LLM-driven research client."""

import json
from unittest.mock import AsyncMock

import pytest
from src.clients.llm_researcher import LLMResearcher, ResearchStrategy, WebSource
from src.models.research_config import (
    ResearchRequest,
    ResearchTopic,
    SearchResult,
    SearchStrategy,
)


class TestLLMResearcher:
    """Test LLM researcher functionality."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = AsyncMock()
        client.generate_response.return_value = json.dumps(
            {
                "search_queries": [
                    "AI research 2024",
                    "machine learning developments",
                ],
                "target_sources": [
                    {
                        "url": "https://techcrunch.com/ai",
                        "domain": "techcrunch.com",
                        "source_type": "news",
                        "credibility_score": 0.8,
                        "relevance_score": 0.9,
                        "description": "Technology news and AI updates",
                    }
                ],
                "content_keywords": ["AI", "machine learning", "research"],
                "quality_indicators": [
                    "peer reviewed",
                    "official announcement",
                ],
                "analysis_focus": "AI research developments",
            }
        )
        return client

    @pytest.fixture
    def research_request(self):
        """Sample research request."""
        topic = ResearchTopic(
            name="AI Research",
            description="Research on AI developments",
            keywords=["AI", "machine learning"],
            focus_areas=["research", "developments"],
            time_range="past_month",
            depth="detailed",
        )

        search_strategy = SearchStrategy(max_sources=10, credibility_threshold=0.7)

        return ResearchRequest(
            topic=topic,
            search_strategy=search_strategy,
            analysis_instructions="Analyze AI research trends",
        )

    def test_init_default(self, mock_llm_client):
        """Test researcher initialization with defaults."""
        researcher = LLMResearcher(mock_llm_client)

        assert researcher.llm_client == mock_llm_client
        assert researcher.session is None
        assert researcher._should_close_session is True
        assert researcher.max_sources_per_query == 10
        assert researcher.min_credibility_threshold == 0.6

    def test_init_with_session(self, mock_llm_client, mock_http_session):
        """Test researcher initialization with provided session."""
        researcher = LLMResearcher(mock_llm_client, session=mock_http_session)

        assert researcher.session == mock_http_session
        assert researcher._should_close_session is False

    async def test_context_manager(self, mock_llm_client):
        """Test async context manager."""
        researcher = LLMResearcher(mock_llm_client)

        async with researcher:
            assert researcher.session is not None

    async def test_generate_research_strategy_success(
        self, mock_llm_client, research_request
    ):
        """Test successful research strategy generation."""
        researcher = LLMResearcher(mock_llm_client)

        strategy = await researcher._generate_research_strategy(research_request)

        assert isinstance(strategy, ResearchStrategy)
        assert len(strategy.search_queries) == 2
        assert len(strategy.target_sources) == 1
        assert strategy.target_sources[0].domain == "techcrunch.com"
        assert strategy.analysis_focus == "AI research developments"

        # Verify LLM was called with appropriate prompt
        mock_llm_client.generate_response.assert_called_once()
        call_args = mock_llm_client.generate_response.call_args[0]
        assert "AI Research" in call_args[0]
        assert "research strategy" in call_args[0].lower()

    async def test_generate_research_strategy_fallback(
        self, mock_llm_client, research_request
    ):
        """Test fallback strategy when LLM fails."""
        # Mock LLM to return invalid JSON
        mock_llm_client.generate_response.return_value = "invalid json"

        researcher = LLMResearcher(mock_llm_client)

        strategy = await researcher._generate_research_strategy(research_request)

        assert isinstance(strategy, ResearchStrategy)
        assert len(strategy.search_queries) > 0
        assert len(strategy.target_sources) > 0
        # Should contain basic fallback sources
        assert any(
            "techcrunch.com" in source.domain for source in strategy.target_sources
        )

    async def test_fetch_web_content_success(self, mock_llm_client, mock_http_session):
        """Test successful web content fetching."""
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text.return_value = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <script>console.log('remove me');</script>
                <h1>Main Content</h1>
                <p>This is the main content of the article.</p>
                <nav>Navigation</nav>
                <footer>Footer</footer>
            </body>
        </html>
        """

        mock_http_session.get.return_value.__aenter__.return_value = mock_response

        researcher = LLMResearcher(mock_llm_client, session=mock_http_session)

        content = await researcher._fetch_web_content("https://example.com/article")

        assert content is not None
        assert "Main Content" in content
        assert "This is the main content" in content
        # Should remove script, nav, and footer
        assert "console.log" not in content
        assert "Navigation" not in content
        assert "Footer" not in content

    async def test_fetch_web_content_failure(self, mock_llm_client, mock_http_session):
        """Test web content fetching failure."""
        # Mock HTTP response with error
        mock_response = AsyncMock()
        mock_response.status = 404

        mock_http_session.get.return_value.__aenter__.return_value = mock_response

        researcher = LLMResearcher(mock_llm_client, session=mock_http_session)

        content = await researcher._fetch_web_content("https://example.com/not-found")

        assert content is None

    async def test_llm_analyze_content_success(self, mock_llm_client, research_request):
        """Test successful LLM content analysis."""
        # Mock LLM analysis response
        mock_llm_client.generate_response.return_value = json.dumps(
            {
                "relevance_score": 0.8,
                "title": "AI Research Breakthrough",
                "summary": "New developments in AI research",
                "entities": ["OpenAI", "GPT-4", "machine learning"],
                "publication_date": "2024-01-15T00:00:00Z",
                "key_insights": ["AI models improving", "New architecture"],
            }
        )

        researcher = LLMResearcher(mock_llm_client)

        web_source = WebSource(
            url="https://example.com",
            domain="example.com",
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.7,
            description="Test source",
        )

        strategy = ResearchStrategy(
            search_queries=["test query"],
            target_sources=[web_source],
            content_keywords=["AI", "research"],
            quality_indicators=["peer reviewed"],
            analysis_focus="AI research",
        )

        analysis = await researcher._llm_analyze_content(
            "Sample content about AI research",
            web_source,
            strategy,
            research_request,
        )

        assert analysis is not None
        assert analysis["relevance_score"] == 0.8
        assert analysis["title"] == "AI Research Breakthrough"
        assert "OpenAI" in analysis["entities"]

    async def test_llm_analyze_content_irrelevant(
        self, mock_llm_client, research_request
    ):
        """Test LLM analysis of irrelevant content."""
        # Mock LLM to return low relevance score
        mock_llm_client.generate_response.return_value = json.dumps(
            {
                "relevance_score": 0.1,
                "title": "Irrelevant Article",
                "summary": "Not related to research topic",
                "entities": [],
                "key_insights": [],
            }
        )

        researcher = LLMResearcher(mock_llm_client)

        web_source = WebSource(
            url="https://example.com",
            domain="example.com",
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.7,
            description="Test source",
        )

        strategy = ResearchStrategy(
            search_queries=["test query"],
            target_sources=[web_source],
            content_keywords=["AI", "research"],
            quality_indicators=["peer reviewed"],
            analysis_focus="AI research",
        )

        analysis = await researcher._llm_analyze_content(
            "Content about cooking recipes",
            web_source,
            strategy,
            research_request,
        )

        assert analysis is not None
        assert analysis["relevance_score"] == 0.1

    async def test_filter_and_rank_results(self, mock_llm_client, research_request):
        """Test filtering and ranking of results."""
        researcher = LLMResearcher(mock_llm_client)

        # Create test results with different scores
        results = [
            SearchResult(
                title="High Quality Result",
                url="https://example1.com",
                snippet="Relevant content",
                source_type="research_papers",
                credibility_score=0.9,
                relevance_score=0.8,
                domain="example1.com",
            ),
            SearchResult(
                title="Low Quality Result",
                url="https://example2.com",
                snippet="Less relevant",
                source_type="blogs",
                credibility_score=0.5,  # Below threshold
                relevance_score=0.6,
                domain="example2.com",
            ),
            SearchResult(
                title="Medium Quality Result",
                url="https://example3.com",
                snippet="Somewhat relevant",
                source_type="news",
                credibility_score=0.7,
                relevance_score=0.7,
                domain="example3.com",
            ),
        ]

        filtered = researcher._filter_and_rank_results(results, research_request)

        # Should filter out low credibility result
        assert len(filtered) == 2

        # Should be sorted by quality score (relevance * 0.6 + credibility * 0.4)
        assert filtered[0].title == "High Quality Result"
        assert filtered[1].title == "Medium Quality Result"

        # Quality scores should be calculated
        assert filtered[0].quality_score is not None
        assert filtered[1].quality_score is not None
        assert filtered[0].quality_score > filtered[1].quality_score


class TestWebSource:
    """Test WebSource model."""

    def test_create_valid_web_source(self):
        """Test creating a valid web source."""
        source = WebSource(
            url="https://example.com",
            domain="example.com",
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.9,
            description="Test news source",
        )

        assert source.url == "https://example.com"
        assert source.domain == "example.com"
        assert source.source_type == "news"
        assert source.credibility_score == 0.8
        assert source.relevance_score == 0.9
        assert source.description == "Test news source"

    def test_invalid_credibility_score(self):
        """Test validation of credibility score range."""
        with pytest.raises(ValueError):
            WebSource(
                url="https://example.com",
                domain="example.com",
                source_type="news",
                credibility_score=1.5,  # Invalid: > 1.0
                relevance_score=0.9,
                description="Test source",
            )


class TestResearchStrategy:
    """Test ResearchStrategy model."""

    def test_create_valid_strategy(self):
        """Test creating a valid research strategy."""
        web_source = WebSource(
            url="https://example.com",
            domain="example.com",
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.9,
            description="Test source",
        )

        strategy = ResearchStrategy(
            search_queries=["query1", "query2"],
            target_sources=[web_source],
            content_keywords=["keyword1", "keyword2"],
            quality_indicators=["indicator1", "indicator2"],
            analysis_focus="Test analysis focus",
        )

        assert len(strategy.search_queries) == 2
        assert len(strategy.target_sources) == 1
        assert strategy.target_sources[0] == web_source
        assert len(strategy.content_keywords) == 2
        assert len(strategy.quality_indicators) == 2
        assert strategy.analysis_focus == "Test analysis focus"
