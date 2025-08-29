"""Tests for ConfigMap-driven content analyzer."""

import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from src.clients.content_analyzer import ContentAnalyzer
from src.models.research_config import (
    AnalysisInsight,
    ResearchRequest,
    ResearchTopic,
    SearchResult,
    SearchStrategy,
)


class TestContentAnalyzer:
    """Test ConfigMap-driven content analyzer functionality."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        client = AsyncMock()
        client.generate_response.return_value = json.dumps(
            {
                "title": "AI Model Performance Improvement",
                "content": "Analysis shows significant improvements in model efficiency",
                "confidence_score": 0.85,
                "key_entities": ["GPT-4", "OpenAI", "performance"],
                "relevance_to_topic": 0.9,
                "significance": "high",
                "actionable_insights": [
                    "Model optimization techniques",
                    "Performance benchmarks",
                ],
                "supporting_evidence": [
                    "Test results",
                    "Benchmark comparisons",
                ],
                "related_concepts": ["machine learning", "optimization"],
                "temporal_context": "recent development",
                "implications": "This indicates major progress in AI efficiency",
            }
        )
        return client

    @pytest.fixture
    def research_request(self):
        """Sample research request."""
        topic = ResearchTopic(
            name="AI Performance Research",
            description="Research on AI model performance improvements",
            keywords=["AI", "performance", "optimization"],
            focus_areas=["efficiency", "benchmarks"],
            time_range="past_month",
            depth="detailed",
        )

        search_strategy = SearchStrategy(max_sources=10, credibility_threshold=0.7)

        return ResearchRequest(
            topic=topic,
            search_strategy=search_strategy,
            analysis_instructions="Analyze performance improvements and efficiency gains in AI models",
        )

    @pytest.fixture
    def search_results(self):
        """Sample search results."""
        return [
            SearchResult(
                title="GPT-4 Performance Improvements",
                url="https://openai.com/research/gpt-4-improvements",
                snippet="New optimizations show 40% performance improvement",
                source_type="official_announcements",
                credibility_score=0.9,
                relevance_score=0.8,
                domain="openai.com",
                publication_date=datetime(2024, 1, 15),
            ),
            SearchResult(
                title="AI Benchmark Results",
                url="https://arxiv.org/abs/2024.01234",
                snippet="Comprehensive benchmarking of latest AI models",
                source_type="research_papers",
                credibility_score=0.85,
                relevance_score=0.9,
                domain="arxiv.org",
                publication_date=datetime(2024, 1, 10),
            ),
        ]

    def test_init(self, mock_llm_client):
        """Test analyzer initialization."""
        analyzer = ContentAnalyzer(mock_llm_client)

        assert analyzer.llm_client == mock_llm_client

    async def test_analyze_research_results_success(
        self, mock_llm_client, research_request, search_results
    ):
        """Test successful analysis of research results."""
        analyzer = ContentAnalyzer(mock_llm_client)

        insights = await analyzer.analyze_research_results(
            search_results, research_request
        )

        assert len(insights) == 2
        assert all(isinstance(insight, AnalysisInsight) for insight in insights)

        # Check first insight
        insight = insights[0]
        assert insight.title == "AI Model Performance Improvement"
        assert insight.confidence_score == 0.85
        assert (
            "https://openai.com/research/gpt-4-improvements"
            in insight.supporting_sources
        )
        assert "GPT-4" in insight.key_entities

    async def test_analyze_research_results_empty_list(
        self, mock_llm_client, research_request
    ):
        """Test analysis with empty search results."""
        analyzer = ContentAnalyzer(mock_llm_client)

        insights = await analyzer.analyze_research_results([], research_request)

        assert insights == []

    async def test_analyze_single_result_success(
        self, mock_llm_client, research_request, search_results
    ):
        """Test successful analysis of single result."""
        analyzer = ContentAnalyzer(mock_llm_client)

        insight = await analyzer._analyze_single_result(
            search_results[0], research_request
        )

        assert insight is not None
        assert isinstance(insight, AnalysisInsight)
        assert insight.title == "AI Model Performance Improvement"
        assert insight.confidence_score == 0.85
        assert search_results[0].url in insight.supporting_sources

        # Verify LLM was called with ConfigMap-driven prompt
        mock_llm_client.generate_response.assert_called_once()
        call_args = mock_llm_client.generate_response.call_args[0]
        prompt = call_args[0]
        assert "AI Performance Research" in prompt
        assert (
            "Analyze performance improvements" in prompt
        )  # From ConfigMap analysis_instructions
        assert search_results[0].title in prompt
        assert (
            "Focus specifically on: efficiency, benchmarks" in prompt
        )  # ConfigMap focus areas

    async def test_configmap_driven_prompt_construction(
        self, mock_llm_client, research_request, search_results
    ):
        """Test that prompts are constructed from ConfigMap data."""
        analyzer = ContentAnalyzer(mock_llm_client)

        # Test the prompt construction method directly
        content = "Test content about AI performance"
        prompt = analyzer._construct_analysis_prompt(
            content, search_results[0], research_request
        )

        # Verify ConfigMap elements are used in prompt
        assert research_request.topic.name in prompt
        assert research_request.topic.description in prompt
        assert research_request.analysis_instructions in prompt
        assert "efficiency" in prompt  # focus area from ConfigMap
        assert "benchmarks" in prompt  # focus area from ConfigMap
        assert "AI" in prompt  # keyword from ConfigMap
        assert "performance" in prompt  # keyword from ConfigMap
        assert "optimization" in prompt  # keyword from ConfigMap

        # Verify no hardcoded analysis patterns
        assert (
            "You are a research analyst specializing in AI Performance Research"
            in prompt
        )
        assert "ANALYSIS INSTRUCTIONS:" in prompt
        assert "RESEARCH CONTEXT:" in prompt

    async def test_dynamic_json_schema_construction(
        self, mock_llm_client, research_request
    ):
        """Test dynamic JSON schema construction based on ConfigMap."""
        analyzer = ContentAnalyzer(mock_llm_client)

        schema = analyzer._construct_dynamic_json_schema(research_request)

        # Verify schema includes ConfigMap-based fields
        assert "focus_area_insights" in schema
        assert "efficiency" in schema  # from focus areas
        assert "benchmarks" in schema  # from focus areas
        assert "keyword_relevance" in schema
        assert "ai" in schema.lower()  # from keywords
        assert "performance" in schema.lower()  # from keywords

        # Verify base fields are present
        assert "title" in schema
        assert "content" in schema
        assert "confidence_score" in schema
        assert "relevance_to_topic" in schema

    async def test_analyze_single_result_low_relevance(
        self, mock_llm_client, research_request, search_results
    ):
        """Test analysis with low relevance content."""
        # Mock LLM to return low relevance
        mock_llm_client.generate_response.return_value = json.dumps(
            {
                "title": "Irrelevant Content",
                "content": "This content is not relevant",
                "confidence_score": 0.2,
                "relevance_to_topic": 0.1,  # Low relevance
                "key_entities": [],
                "significance": "low",
            }
        )

        analyzer = ContentAnalyzer(mock_llm_client)

        insight = await analyzer._analyze_single_result(
            search_results[0], research_request
        )

        # Should return None for low relevance content
        assert insight is None

    async def test_analyze_single_result_llm_failure(
        self, mock_llm_client, research_request, search_results
    ):
        """Test handling of LLM analysis failure."""
        # Mock LLM to return invalid JSON
        mock_llm_client.generate_response.return_value = "invalid json response"

        analyzer = ContentAnalyzer(mock_llm_client)

        insight = await analyzer._analyze_single_result(
            search_results[0], research_request
        )

        # Should return None when LLM analysis fails
        assert insight is None

    async def test_fetch_full_content_long_snippet(
        self, mock_llm_client, search_results
    ):
        """Test content fetching with long snippet."""
        # Create result with long snippet
        search_result = SearchResult(
            title="Test Article",
            url="https://example.com/article",
            snippet="A" * 600,  # Long snippet
            source_type="news",
            credibility_score=0.8,
            relevance_score=0.7,
            domain="example.com",
        )

        analyzer = ContentAnalyzer(mock_llm_client)

        content = await analyzer._fetch_full_content(search_result)

        # Should use the existing snippet
        assert content == "A" * 600

    async def test_fetch_full_content_short_snippet(
        self, mock_llm_client, search_results
    ):
        """Test content fetching with short snippet."""
        analyzer = ContentAnalyzer(mock_llm_client)

        content = await analyzer._fetch_full_content(search_results[0])

        # Should use the snippet (in real implementation would fetch full content)
        assert content == search_results[0].snippet

    async def test_synthesize_research_findings_success(
        self, mock_llm_client, research_request
    ):
        """Test successful synthesis of research findings using ConfigMap instructions."""
        # Mock synthesis response
        synthesis_response = {
            "executive_summary": "Research shows significant AI performance improvements",
            "key_findings": [
                {
                    "finding": "40% performance improvement in GPT-4",
                    "supporting_evidence": ["benchmark results", "test data"],
                    "confidence": 0.9,
                    "significance": "high",
                }
            ],
            "efficiency_analysis": "Major efficiency gains observed",  # ConfigMap focus area
            "benchmarks_analysis": "Comprehensive benchmark improvements",  # ConfigMap focus area
            "key_themes": ["performance", "optimization", "efficiency"],
            "confidence_assessment": "high",
            "research_quality": "Comprehensive analysis with strong evidence",
        }

        mock_llm_client.generate_response.return_value = json.dumps(synthesis_response)

        # Create sample insights
        insights = [
            AnalysisInsight(
                title="Performance Improvement",
                content="GPT-4 shows 40% improvement",
                confidence_score=0.9,
                category="performance",
                supporting_sources=["https://example.com/1"],
                key_entities=["GPT-4", "performance"],
                impact_level="high",
            ),
            AnalysisInsight(
                title="Optimization Techniques",
                content="New optimization methods developed",
                confidence_score=0.8,
                category="optimization",
                supporting_sources=["https://example.com/2"],
                key_entities=["optimization", "methods"],
                impact_level="medium",
            ),
        ]

        analyzer = ContentAnalyzer(mock_llm_client)

        synthesis = await analyzer.synthesize_research_findings(
            insights, research_request
        )

        assert (
            synthesis["executive_summary"]
            == "Research shows significant AI performance improvements"
        )
        assert len(synthesis["key_findings"]) == 1
        assert (
            synthesis["key_findings"][0]["finding"]
            == "40% performance improvement in GPT-4"
        )
        assert "performance" in synthesis["key_themes"]
        assert synthesis["confidence_assessment"] == "high"

        # Verify ConfigMap focus areas are included
        assert "efficiency_analysis" in synthesis
        assert "benchmarks_analysis" in synthesis

    async def test_synthesize_research_findings_empty_insights(
        self, mock_llm_client, research_request
    ):
        """Test synthesis with no insights."""
        analyzer = ContentAnalyzer(mock_llm_client)

        synthesis = await analyzer.synthesize_research_findings([], research_request)

        assert "No significant insights found" in synthesis["summary"]
        assert synthesis["findings"] == []
        assert synthesis["confidence_assessment"] == "low"

    async def test_synthesize_research_findings_llm_failure(
        self, mock_llm_client, research_request
    ):
        """Test synthesis when LLM fails."""
        # Mock LLM to return invalid JSON
        mock_llm_client.generate_response.return_value = "invalid json"

        insights = [
            AnalysisInsight(
                title="Test Insight",
                content="Test content",
                confidence_score=0.8,
                category="test",
                supporting_sources=["https://example.com"],
                key_entities=["test"],
                impact_level="medium",
            )
        ]

        analyzer = ContentAnalyzer(mock_llm_client)

        synthesis = await analyzer.synthesize_research_findings(
            insights, research_request
        )

        # Should return basic synthesis as fallback
        assert "Analysis of 1 insights" in synthesis["executive_summary"]
        assert len(synthesis["key_findings"]) == 1
        assert synthesis["key_findings"][0]["finding"] == "Test Insight"
        assert "test" in synthesis["key_themes"]
        assert synthesis["confidence_assessment"] == "medium"

    async def test_configmap_synthesis_prompt_construction(
        self, mock_llm_client, research_request
    ):
        """Test that synthesis prompts use ConfigMap research instructions."""
        insights = [
            AnalysisInsight(
                title="Test Insight",
                content="Test content",
                confidence_score=0.8,
                category="test",
                supporting_sources=["https://example.com"],
                key_entities=["test"],
                impact_level="medium",
            )
        ]

        analyzer = ContentAnalyzer(mock_llm_client)

        # Test the synthesis prompt construction
        prompt = analyzer._construct_synthesis_prompt(insights, research_request)

        # Verify ConfigMap elements are used
        assert research_request.topic.name in prompt
        assert research_request.topic.description in prompt
        assert research_request.analysis_instructions in prompt  # Key ConfigMap element
        assert "efficiency" in prompt  # focus area
        assert "benchmarks" in prompt  # focus area
        assert "AI" in prompt  # keyword
        assert "performance" in prompt  # keyword

        # Verify ConfigMap-driven instructions are primary
        assert "Based on the research instructions and individual insights" in prompt
        assert (
            "Follows the analysis instructions provided in the research configuration"
            in prompt
        )
