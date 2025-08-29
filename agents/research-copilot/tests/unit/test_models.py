"""Unit tests for data models."""

import pytest
from pydantic import ValidationError
from src.models.research_config import (
    AnalysisRequest,
    AnalysisResult,
    ContentType,
    ImpactLevel,
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
        request = AnalysisRequest(
            content="Research organization releases new findings with major improvements",
            content_type=ContentType.ANNOUNCEMENT,
            organization_hint="Research Institute",
        )

        assert request.content_type == ContentType.ANNOUNCEMENT
        assert request.organization_hint == "Research Institute"
        assert "findings" in request.content

    def test_create_request_without_organization_hint(self):
        """Test creating a request without organization hint."""
        request = AnalysisRequest(
            content="New research developments in the industry",
            content_type=ContentType.BLOG_POST,
        )

        assert request.content_type == ContentType.BLOG_POST
        assert request.organization_hint is None


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_create_valid_result(self):
        """Test creating a valid analysis result."""
        result = AnalysisResult(
            content_type=ContentType.RELEASE,
            organization="Research Institute",
            product="Research Platform v2.0",
            key_points=["Improved methodology", "Better data analysis"],
            sentiment="positive",
            impact_assessment=ImpactLevel.HIGH,
            confidence_score=0.85,
        )

        assert result.content_type == ContentType.RELEASE
        assert result.organization == "Research Institute"
        assert result.product == "Research Platform v2.0"
        assert len(result.key_points) == 2
        assert result.sentiment == "positive"
        assert result.impact_assessment == ImpactLevel.HIGH
        assert result.confidence_score == 0.85

    def test_default_values(self):
        """Test default values for optional fields."""
        result = AnalysisResult(
            content_type=ContentType.ANNOUNCEMENT,
        )

        assert result.sentiment == "neutral"
        assert result.impact_assessment == ImpactLevel.LOW
        assert result.confidence_score == 0.0
        assert result.key_points == []

    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid confidence score
        result = AnalysisResult(
            content_type=ContentType.RELEASE,
            confidence_score=0.5,
        )
        assert result.confidence_score == 0.5

        # Invalid confidence score (should be clamped or raise error)
        with pytest.raises(ValidationError):
            AnalysisResult(
                content_type=ContentType.RELEASE,
                confidence_score=1.5,  # Above maximum
            )

        with pytest.raises(ValidationError):
            AnalysisResult(
                content_type=ContentType.RELEASE,
                confidence_score=-0.1,  # Below minimum
            )
