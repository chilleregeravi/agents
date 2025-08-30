"""Unit tests for data models."""

from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from src.models.research_config import (
    AnalysisRequest,
    AnalysisResult,
    ContentType,
    ImpactLevel,
    OutputSchema,
    PageSection,
    PageStructure,
    ResearchConfiguration,
    ResearchData,
    SectionType,
)


class TestEnums:
    """Test enum definitions."""

    def test_impact_level_values(self):
        """Test ImpactLevel enum values."""
        assert ImpactLevel.LOW == "low"
        assert ImpactLevel.MEDIUM == "medium"
        assert ImpactLevel.HIGH == "high"
        assert ImpactLevel.CRITICAL == "critical"

    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.RELEASE == "release"
        assert ContentType.ANNOUNCEMENT == "announcement"
        assert ContentType.RESEARCH_PAPER == "research_paper"
        assert ContentType.BLOG_POST == "blog_post"
        assert ContentType.REPORT == "report"
        assert ContentType.WHITEPAPER == "whitepaper"


class TestAnalysisRequest:
    """Test AnalysisRequest model."""

    def test_create_valid_request(self):
        """Test creating a valid analysis request."""
        research_data = ResearchData(
            topic_name="Test Topic",
            data_sources=["https://example.com"],
            web_pages=[],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="test",
            total_content_length=100,
            source_diversity=0.8,
            content_freshness=0.9,
            relevance_score=0.7,
        )

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
                    ],
                ),
            ),
        )

        request = AnalysisRequest(
            research_data=research_data,
            analysis_config=config,
            analysis_focus=["focus1", "focus2"],
            output_requirements={"format": "notion_page"},
        )

        assert request.research_data.topic_name == "Test Topic"
        assert request.analysis_config.name == "Test Config"
        assert "focus1" in request.analysis_focus

    def test_create_request_without_organization_hint(self):
        """Test creating a request with minimal parameters."""
        research_data = ResearchData(
            topic_name="Test Topic",
            data_sources=[],
            web_pages=[],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="test",
            total_content_length=0,
            source_diversity=0.0,
            content_freshness=0.0,
            relevance_score=0.0,
        )

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
                        PageSection(name="Executive Summary", content_type="text"),
                    ],
                ),
            ),
        )

        request = AnalysisRequest(
            research_data=research_data,
            analysis_config=config,
        )

        assert request.research_data.topic_name == "Test Topic"
        assert request.analysis_config.name == "Test Config"


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_create_valid_result(self):
        """Test creating a valid analysis result."""
        research_data = ResearchData(
            topic_name="Test Topic",
            data_sources=[],
            web_pages=[],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="test",
            total_content_length=100,
            source_diversity=0.8,
            content_freshness=0.9,
            relevance_score=0.7,
        )

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
                        PageSection(name="Executive Summary", content_type="text"),
                    ],
                ),
            ),
        )

        analysis_request = AnalysisRequest(
            research_data=research_data,
            analysis_config=config,
        )

        result = AnalysisResult(
            analysis_id="test_analysis_001",
            analysis_request=analysis_request,
            executive_summary="Test executive summary",
            key_insights=[],
            analysis_confidence=0.85,
            coverage_score=0.8,
            insight_quality=0.9,
            processing_time_seconds=10.5,
            llm_model_used="qwen2.5",
        )

        assert result.analysis_id == "test_analysis_001"
        assert result.executive_summary == "Test executive summary"
        assert result.analysis_confidence == 0.85
        assert result.processing_time_seconds == 10.5
        assert result.llm_model_used == "qwen2.5"

    def test_default_values(self):
        """Test default values for optional fields."""
        research_data = ResearchData(
            topic_name="Test Topic",
            data_sources=[],
            web_pages=[],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="test",
            total_content_length=0,
            source_diversity=0.0,
            content_freshness=0.0,
            relevance_score=0.0,
        )

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
                        PageSection(name="Executive Summary", content_type="text"),
                    ],
                ),
            ),
        )

        analysis_request = AnalysisRequest(
            research_data=research_data,
            analysis_config=config,
        )

        result = AnalysisResult(
            analysis_id="test_analysis_002",
            analysis_request=analysis_request,
            executive_summary="Test summary",
            analysis_confidence=0.5,
            coverage_score=0.5,
            insight_quality=0.5,
            processing_time_seconds=5.0,
            llm_model_used="qwen2.5",
        )

        assert result.trend_analysis is None
        assert result.quantitative_findings == []
        assert result.analysis_notes is None

    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        research_data = ResearchData(
            topic_name="Test Topic",
            data_sources=[],
            web_pages=[],
            documents=[],
            news_articles=[],
            social_media=[],
            collection_method="test",
            total_content_length=0,
            source_diversity=0.0,
            content_freshness=0.0,
            relevance_score=0.0,
        )

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
                        PageSection(name="Executive Summary", content_type="text"),
                    ],
                ),
            ),
        )

        analysis_request = AnalysisRequest(
            research_data=research_data,
            analysis_config=config,
        )

        # Valid confidence score
        result = AnalysisResult(
            analysis_id="test_analysis_003",
            analysis_request=analysis_request,
            executive_summary="Test summary",
            analysis_confidence=0.5,
            coverage_score=0.5,
            insight_quality=0.5,
            processing_time_seconds=5.0,
            llm_model_used="qwen2.5",
        )
        assert result.analysis_confidence == 0.5

        # Invalid confidence score (should raise error)
        with pytest.raises(ValidationError):
            AnalysisResult(
                analysis_id="test_analysis_004",
                analysis_request=analysis_request,
                executive_summary="Test summary",
                analysis_confidence=1.5,  # Above maximum
                coverage_score=0.5,
                insight_quality=0.5,
                processing_time_seconds=5.0,
                llm_model_used="qwen2.5",
            )

        with pytest.raises(ValidationError):
            AnalysisResult(
                analysis_id="test_analysis_005",
                analysis_request=analysis_request,
                executive_summary="Test summary",
                analysis_confidence=-0.1,  # Below minimum
                coverage_score=0.5,
                insight_quality=0.5,
                processing_time_seconds=5.0,
                llm_model_used="qwen2.5",
            )
