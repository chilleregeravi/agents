"""Unit tests for LocalAnalysisClient."""

from unittest.mock import AsyncMock, Mock

import pytest
from src.clients.local_analysis_client import LocalAnalysisClient, LocalAnalysisError
from src.models.research_config import (
    AnalysisRequest,
    AnalysisResult,
    OutputSchema,
    PageSection,
    PageStructure,
    ResearchConfiguration,
    ResearchData,
    SectionType,
)


class TestLocalAnalysisClient:
    """Test suite for LocalAnalysisClient class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        client = AsyncMock()
        client.generate_response.return_value = '{"insights": []}'
        return client

    @pytest.fixture
    def local_analysis_client(self, mock_llm_client):
        """Create LocalAnalysisClient instance for testing."""
        return LocalAnalysisClient(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_research_data(self):
        """Create sample research data for testing."""
        return ResearchData(
            topic_name="Test Topic",
            data_sources=["https://example.com"],
            web_pages=[
                {
                    "title": "Test Article",
                    "content": "This is test content for analysis.",
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

    @pytest.fixture
    def sample_analysis_request(self, sample_research_data):
        """Create sample analysis request for testing."""
        config = ResearchConfiguration(
            name="Test Config",
            description="Test configuration",
            research_request=Mock(),
            output_schema=OutputSchema(
                output_format="notion_page",
                template="research_report",
                page_structure=PageStructure(
                    title_template="Test - {date}",
                    sections=[
                        PageSection(
                            name="Executive Summary",
                            type=SectionType.TEXT_BLOCK,
                            content_source="analysis_result",
                        ),
                        PageSection(
                            name="Key Insights",
                            type=SectionType.BULLET_LIST,
                            content_source="insights",
                        ),
                        PageSection(
                            name="Analysis",
                            type=SectionType.TEXT_BLOCK,
                            content_source="analysis_result",
                        ),
                    ],
                ),
            ),
        )

        return AnalysisRequest(
            research_data=sample_research_data,
            analysis_config=config,
            analysis_focus=["focus1", "focus2"],
            output_requirements={"format": "notion_page"},
            include_confidence_scores=True,
            include_source_citations=True,
            group_similar_findings=True,
            trend_analysis=True,
            summary_length="detailed",
            include_quantitative_data=True,
            include_qualitative_insights=True,
        )

    @pytest.mark.asyncio
    async def test_analyze_research_data_success(
        self, local_analysis_client, sample_analysis_request, mock_llm_client
    ):
        """Test successful analysis of research data."""
        # Mock LLM responses
        mock_llm_client.generate_response.side_effect = [
            '{"insights": [{"title": "Test Insight", "description": "Test description", "category": "finding", "confidence": 0.8, "sources": [], "impact": "medium", "evidence": "test"}]}',
            '{"cross_content_insights": []}',
            '{"trends": [], "summary": "Test trend summary"}',
            '{"quantitative_findings": []}',
            "Test executive summary",
        ]

        # Execute analysis
        result = await local_analysis_client.analyze_research_data(
            sample_analysis_request
        )

        # Verify result
        assert isinstance(result, AnalysisResult)
        assert result.analysis_id.startswith("local_analysis_")
        assert result.executive_summary == "Test executive summary"
        assert len(result.key_insights) == 1
        assert result.key_insights[0].title == "Test Insight"
        assert result.analysis_confidence > 0
        assert result.processing_time_seconds > 0

    @pytest.mark.asyncio
    async def test_analyze_research_data_llm_error(
        self, local_analysis_client, sample_analysis_request, mock_llm_client
    ):
        """Test analysis with LLM error."""
        mock_llm_client.generate_response.side_effect = Exception("LLM error")

        with pytest.raises(LocalAnalysisError) as exc_info:
            await local_analysis_client.analyze_research_data(sample_analysis_request)

        assert "Analysis failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_preprocess_research_data(
        self, local_analysis_client, sample_research_data
    ):
        """Test preprocessing of research data."""
        processed = await local_analysis_client._preprocess_research_data(
            sample_research_data
        )

        assert processed["topic_name"] == "Test Topic"
        assert processed["total_content_length"] == 100
        assert processed["source_diversity"] == 0.8
        assert processed["content_freshness"] == 0.9
        assert processed["relevance_score"] == 0.7
        assert "web_pages" in processed["content_by_type"]
        assert len(processed["content_by_type"]["web_pages"]) == 1

    @pytest.mark.asyncio
    async def test_generate_insights(
        self,
        local_analysis_client,
        sample_research_data,
        sample_analysis_request,
        mock_llm_client,
    ):
        """Test insight generation."""
        mock_llm_client.generate_response.return_value = '{"insights": [{"title": "Test", "description": "Test", "category": "finding", "confidence": 0.8, "sources": [], "impact": "medium", "evidence": "test"}]}'

        processed_data = await local_analysis_client._preprocess_research_data(
            sample_research_data
        )
        insights = await local_analysis_client._generate_insights(
            processed_data, sample_analysis_request
        )

        assert len(insights) > 0
        assert insights[0].title == "Test"
        assert insights[0].confidence_score == 0.8

    @pytest.mark.asyncio
    async def test_analyze_content_type(
        self, local_analysis_client, sample_analysis_request, mock_llm_client
    ):
        """Test content type analysis."""
        mock_llm_client.generate_response.return_value = '{"insights": [{"title": "Test", "description": "Test", "category": "finding", "confidence": 0.8, "sources": [], "impact": "medium", "evidence": "test"}]}'

        content_items = [
            {
                "title": "Test Article",
                "content": "Test content",
                "url": "https://example.com",
            }
        ]

        insights = await local_analysis_client._analyze_content_type(
            "web_pages", content_items, sample_analysis_request
        )

        assert len(insights) > 0
        assert insights[0].title == "Test"

    @pytest.mark.asyncio
    async def test_analyze_content_batch(
        self, local_analysis_client, sample_analysis_request, mock_llm_client
    ):
        """Test content batch analysis."""
        mock_llm_client.generate_response.return_value = '{"insights": [{"title": "Test", "description": "Test", "category": "finding", "confidence": 0.8, "sources": [], "impact": "medium", "evidence": "test"}]}'

        content_batch = [
            {
                "title": "Test Article",
                "content": "Test content",
                "url": "https://example.com",
            }
        ]

        insights = await local_analysis_client._analyze_content_batch(
            "web_pages", content_batch, sample_analysis_request
        )

        assert len(insights) > 0
        assert insights[0].title == "Test"

    @pytest.mark.asyncio
    async def test_generate_cross_content_insights(
        self,
        local_analysis_client,
        sample_research_data,
        sample_analysis_request,
        mock_llm_client,
    ):
        """Test cross-content insight generation."""
        mock_llm_client.generate_response.return_value = '{"cross_content_insights": [{"title": "Cross Test", "description": "Cross test", "confidence": 0.8, "sources": [], "impact": "medium", "evidence": "test"}]}'

        processed_data = await local_analysis_client._preprocess_research_data(
            sample_research_data
        )
        insights = await local_analysis_client._generate_cross_content_insights(
            processed_data, sample_analysis_request
        )

        assert len(insights) > 0
        assert insights[0].title == "Cross Test"
        assert insights[0].category == "cross_content"

    @pytest.mark.asyncio
    async def test_analyze_trends(
        self,
        local_analysis_client,
        sample_research_data,
        sample_analysis_request,
        mock_llm_client,
    ):
        """Test trend analysis."""
        mock_llm_client.generate_response.return_value = '{"trends": [{"trend_name": "Test Trend", "direction": "increasing", "confidence": 0.8, "evidence": "test"}], "summary": "Test trend summary"}'

        processed_data = await local_analysis_client._preprocess_research_data(
            sample_research_data
        )
        trends = await local_analysis_client._analyze_trends(
            processed_data, sample_analysis_request
        )

        assert trends is not None
        assert "trends" in trends
        assert "summary" in trends
        assert trends["summary"] == "Test trend summary"

    @pytest.mark.asyncio
    async def test_extract_quantitative_data(
        self,
        local_analysis_client,
        sample_research_data,
        sample_analysis_request,
        mock_llm_client,
    ):
        """Test quantitative data extraction."""
        mock_llm_client.generate_response.return_value = '{"quantitative_findings": [{"metric": "Test Metric", "value": "100", "unit": "units", "source": "test", "confidence": 0.8}]}'

        processed_data = await local_analysis_client._preprocess_research_data(
            sample_research_data
        )
        findings = await local_analysis_client._extract_quantitative_data(
            processed_data, sample_analysis_request
        )

        assert len(findings) > 0
        assert findings[0]["metric"] == "Test Metric"
        assert findings[0]["value"] == "100"

    @pytest.mark.asyncio
    async def test_generate_executive_summary(
        self, local_analysis_client, sample_analysis_request, mock_llm_client
    ):
        """Test executive summary generation."""
        mock_llm_client.generate_response.return_value = "Test executive summary"

        insights = []
        trend_analysis = {"summary": "Test trend summary"}
        quantitative_findings = []

        summary = await local_analysis_client._generate_executive_summary(
            insights, trend_analysis, quantitative_findings, sample_analysis_request
        )

        assert summary == "Test executive summary"

    def test_filter_and_rank_insights(
        self, local_analysis_client, sample_analysis_request
    ):
        """Test insight filtering and ranking."""
        from src.models.research_config import AnalysisInsight

        insights = [
            AnalysisInsight(
                insight_id="1",
                title="High Confidence",
                description="High confidence insight",
                category="finding",
                confidence_score=0.9,
                source_references=[],
                impact_level="high",
                supporting_evidence="test",
            ),
            AnalysisInsight(
                insight_id="2",
                title="Low Confidence",
                description="Low confidence insight",
                category="finding",
                confidence_score=0.3,
                source_references=[],
                impact_level="low",
                supporting_evidence="test",
            ),
        ]

        filtered = local_analysis_client._filter_and_rank_insights(
            insights, sample_analysis_request
        )

        # Should filter out low confidence insight
        assert len(filtered) == 1
        assert filtered[0].title == "High Confidence"

    def test_impact_score(self, local_analysis_client):
        """Test impact score calculation."""
        assert local_analysis_client._impact_score("high") == 3.0
        assert local_analysis_client._impact_score("medium") == 2.0
        assert local_analysis_client._impact_score("low") == 1.0
        assert local_analysis_client._impact_score("unknown") == 1.0

    def test_calculate_quality_metrics(
        self, local_analysis_client, sample_analysis_request
    ):
        """Test quality metrics calculation."""
        from src.models.research_config import AnalysisInsight

        insights = [
            AnalysisInsight(
                insight_id="1",
                title="Test",
                description="Test",
                category="finding",
                confidence_score=0.8,
                source_references=[],
                impact_level="medium",
                supporting_evidence="test",
            )
        ]

        processed_data = {
            "source_diversity": 0.8,
            "total_content_length": 5000,
            "relevance_score": 0.7,
        }

        metrics = local_analysis_client._calculate_quality_metrics(
            insights, processed_data, sample_analysis_request
        )

        assert "confidence" in metrics
        assert "coverage" in metrics
        assert "quality" in metrics
        assert metrics["confidence"] == 0.8
        assert 0 <= metrics["coverage"] <= 1
        assert 0 <= metrics["quality"] <= 1

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_llm_client):
        """Test async context manager functionality."""
        async with LocalAnalysisClient(mock_llm_client) as client:
            assert isinstance(client, LocalAnalysisClient)
            assert client.llm_client == mock_llm_client
