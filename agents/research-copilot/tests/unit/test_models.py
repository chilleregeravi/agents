"""Unit tests for data models."""

from datetime import datetime

import pytest
from pydantic import ValidationError
from src.models import (
    AnalysisRequest,
    AnalysisResult,
    Company,
    ContentType,
    FeatureAnnouncement,
    ImpactLevel,
    LLMRelease,
    ResearchPaper,
    SearchResult,
    WeeklyReport,
)


class TestEnums:
    """Test enum definitions."""

    def test_impact_level_values(self):
        """Test ImpactLevel enum values."""
        assert ImpactLevel.LOW == "low"
        assert ImpactLevel.MEDIUM == "medium"
        assert ImpactLevel.HIGH == "high"
        assert ImpactLevel.CRITICAL == "critical"

    def test_company_values(self):
        """Test Company enum values."""
        assert Company.OPENAI == "OpenAI"
        assert Company.GOOGLE == "Google"
        assert Company.MICROSOFT == "Microsoft"
        assert Company.ANTHROPIC == "Anthropic"

    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.RELEASE == "release"
        assert ContentType.ANNOUNCEMENT == "announcement"
        assert ContentType.RESEARCH_PAPER == "research_paper"


class TestLLMRelease:
    """Test LLMRelease model."""

    def test_create_valid_release(self):
        """Test creating a valid LLM release."""
        release = LLMRelease(
            company=Company.OPENAI,
            product="GPT-4.5",
            version="4.5.0",
            release_date=datetime(2024, 1, 15),
            key_features=["Improved reasoning", "Better code generation"],
            impact_level=ImpactLevel.HIGH,
            source_links=["https://openai.com/blog/gpt-4-5"],
            summary="OpenAI releases GPT-4.5 with major improvements",
        )

        assert release.company == Company.OPENAI
        assert release.product == "GPT-4.5"
        assert release.version == "4.5.0"
        assert len(release.key_features) == 2
        assert release.impact_level == ImpactLevel.HIGH

    def test_required_fields(self):
        """Test that required fields are validated."""
        with pytest.raises(ValidationError):
            LLMRelease()

        with pytest.raises(ValidationError):
            LLMRelease(company=Company.OPENAI)

    def test_json_serialization(self):
        """Test JSON serialization."""
        release = LLMRelease(
            company=Company.OPENAI,
            product="GPT-4.5",
            release_date=datetime(2024, 1, 15),
            impact_level=ImpactLevel.HIGH,
            summary="Test release",
        )

        json_data = release.dict()
        assert json_data["company"] == "OpenAI"
        assert json_data["impact_level"] == "high"
        assert json_data["release_date"].strftime("%Y-%m-%d") == "2024-01-15"


class TestFeatureAnnouncement:
    """Test FeatureAnnouncement model."""

    def test_create_valid_announcement(self):
        """Test creating a valid feature announcement."""
        announcement = FeatureAnnouncement(
            company=Company.GOOGLE,
            product="Gemini Pro",
            announcement_date=datetime(2024, 1, 10),
            features=["Faster inference", "Lower cost"],
            impact_level=ImpactLevel.MEDIUM,
            summary="Google announces Gemini Pro improvements",
        )

        assert announcement.company == Company.GOOGLE
        assert announcement.product == "Gemini Pro"
        assert len(announcement.features) == 2
        assert announcement.impact_level == ImpactLevel.MEDIUM


class TestResearchPaper:
    """Test ResearchPaper model."""

    def test_create_valid_paper(self):
        """Test creating a valid research paper."""
        paper = ResearchPaper(
            title="Advances in Large Language Models",
            authors=["Jane Doe", "John Smith"],
            publication="arXiv",
            publication_date=datetime(2024, 1, 5),
            summary="New techniques for LLM training",
            link="https://arxiv.org/abs/2024.01234",
            relevance_score=0.85,
        )

        assert paper.title == "Advances in Large Language Models"
        assert len(paper.authors) == 2
        assert paper.publication == "arXiv"
        assert paper.relevance_score == 0.85

    def test_relevance_score_validation(self):
        """Test relevance score validation."""
        # Valid score
        paper = ResearchPaper(
            title="Test Paper",
            publication="arXiv",
            publication_date=datetime(2024, 1, 5),
            summary="Test summary",
            link="https://example.com",
            relevance_score=0.5,
        )
        assert paper.relevance_score == 0.5

        # Invalid scores should raise validation error
        with pytest.raises(ValidationError):
            ResearchPaper(
                title="Test Paper",
                publication="arXiv",
                publication_date=datetime(2024, 1, 5),
                summary="Test summary",
                link="https://example.com",
                relevance_score=1.5,  # > 1.0
            )


class TestWeeklyReport:
    """Test WeeklyReport model."""

    def test_create_valid_report(self):
        """Test creating a valid weekly report."""
        week_start = datetime(2024, 1, 15)  # Monday

        report = WeeklyReport(
            week_of=week_start,
            summary="This week saw major releases from OpenAI and Google",
            trends=[
                "Increased focus on efficiency",
                "More multimodal capabilities",
            ],
        )

        assert report.week_of == week_start
        assert len(report.trends) == 2
        assert report.generation_date is not None

    def test_week_validation(self):
        """Test week_of validation adjusts to Monday."""
        # Wednesday should be adjusted to Monday
        wednesday = datetime(2024, 1, 17)
        expected_monday = datetime(2024, 1, 15)

        report = WeeklyReport(
            week_of=wednesday,
            summary="Test summary",
        )

        assert report.week_of == expected_monday

    def test_empty_lists_default(self):
        """Test that list fields default to empty lists."""
        report = WeeklyReport(
            week_of=datetime(2024, 1, 15),
            summary="Test summary",
        )

        assert report.major_releases == []
        assert report.feature_announcements == []
        assert report.research_papers == []
        assert report.trends == []


class TestSearchResult:
    """Test SearchResult model."""

    def test_create_valid_search_result(self):
        """Test creating a valid search result."""
        result = SearchResult(
            title="OpenAI Announces GPT-4.5",
            url="https://openai.com/blog/gpt-4-5",
            snippet="OpenAI today announced GPT-4.5...",
            source="openai.com",
            relevance_score=0.9,
        )

        assert result.title == "OpenAI Announces GPT-4.5"
        assert result.relevance_score == 0.9
        assert result.date is None  # Optional field

    def test_with_date(self):
        """Test search result with date."""
        result = SearchResult(
            title="Test Article",
            url="https://example.com",
            snippet="Test snippet",
            source="example.com",
            date=datetime(2024, 1, 15),
            relevance_score=0.8,
        )

        assert result.date == datetime(2024, 1, 15)


class TestAnalysisRequest:
    """Test AnalysisRequest model."""

    def test_create_valid_request(self):
        """Test creating a valid analysis request."""
        request = AnalysisRequest(
            content="OpenAI today announced GPT-4.5 with improved capabilities...",
            content_type=ContentType.ANNOUNCEMENT,
            source_url="https://openai.com/blog/gpt-4-5",
            company_hint=Company.OPENAI,
            analysis_focus=["features", "impact"],
        )

        assert request.content_type == ContentType.ANNOUNCEMENT
        assert request.company_hint == Company.OPENAI
        assert len(request.analysis_focus) == 2

    def test_minimal_request(self):
        """Test creating minimal analysis request."""
        request = AnalysisRequest(
            content="Test content",
            content_type=ContentType.BLOG_POST,
        )

        assert request.content == "Test content"
        assert request.content_type == ContentType.BLOG_POST
        assert request.source_url is None
        assert request.company_hint is None
        assert request.analysis_focus == []


class TestAnalysisResult:
    """Test AnalysisResult model."""

    def test_create_valid_result(self):
        """Test creating a valid analysis result."""
        result = AnalysisResult(
            content_type=ContentType.RELEASE,
            company=Company.OPENAI,
            product="GPT-4.5",
            key_points=["Improved reasoning", "Better performance"],
            sentiment="positive",
            impact_assessment=ImpactLevel.HIGH,
            confidence_score=0.85,
        )

        assert result.content_type == ContentType.RELEASE
        assert result.company == Company.OPENAI
        assert result.product == "GPT-4.5"
        assert len(result.key_points) == 2
        assert result.confidence_score == 0.85

    def test_defaults(self):
        """Test default values."""
        result = AnalysisResult(
            content_type=ContentType.BLOG_POST,
        )

        assert result.company is None
        assert result.product is None
        assert result.key_points == []
        assert result.sentiment == "neutral"
        assert result.impact_assessment == ImpactLevel.LOW
        assert result.confidence_score == 0.0

    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid score
        result = AnalysisResult(
            content_type=ContentType.BLOG_POST,
            confidence_score=0.75,
        )
        assert result.confidence_score == 0.75

        # Invalid score should raise validation error
        with pytest.raises(ValidationError):
            AnalysisResult(
                content_type=ContentType.BLOG_POST,
                confidence_score=1.5,  # > 1.0
            )
