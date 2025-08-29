"""Unit tests for research configuration models."""

from datetime import datetime

import pytest
from pydantic import ValidationError
from src.models.research_config import (
    MARKET_RESEARCH_TEMPLATE,
    TECH_RESEARCH_TEMPLATE,
    AnalysisInsight,
    ContentProcessing,
    OutputFormat,
    OutputSchema,
    PageSection,
    PageStructure,
    ResearchConfiguration,
    ResearchDepth,
    ResearchRequest,
    ResearchResult,
    ResearchTopic,
    SearchResult,
    SearchStrategy,
    SectionConfiguration,
    SectionType,
    SourceType,
    SummaryLength,
)


class TestResearchTopic:
    """Test ResearchTopic model."""

    def test_valid_research_topic(self):
        """Test creating a valid research topic."""
        topic = ResearchTopic(
            name="AI Research",
            description="Research on AI developments",
            keywords=["AI", "machine learning"],
            focus_areas=["innovations", "trends"],
            time_range="past_month",
            depth=ResearchDepth.DETAILED,
        )

        assert topic.name == "AI Research"
        assert topic.description == "Research on AI developments"
        assert len(topic.keywords) == 2
        assert len(topic.focus_areas) == 2
        assert topic.depth == ResearchDepth.DETAILED

    def test_empty_name_validation(self):
        """Test validation of empty name."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchTopic(name="", description="Test description", keywords=["test"])

        assert "Topic name cannot be empty" in str(exc_info.value)

    def test_empty_keywords_validation(self):
        """Test validation of empty keywords."""
        with pytest.raises(ValidationError) as exc_info:
            ResearchTopic(
                name="Test Topic", description="Test description", keywords=[]
            )

        assert "Keywords list cannot be empty" in str(exc_info.value)

    def test_name_whitespace_trimming(self):
        """Test that name whitespace is trimmed."""
        topic = ResearchTopic(
            name="  AI Research  ",
            description="Test description",
            keywords=["AI"],
        )

        assert topic.name == "AI Research"


class TestSearchStrategy:
    """Test SearchStrategy model."""

    def test_valid_search_strategy(self):
        """Test creating a valid search strategy."""
        strategy = SearchStrategy(
            max_sources=20,
            source_types=[SourceType.NEWS, SourceType.BLOGS],
            credibility_threshold=0.7,
            max_search_depth=3,
            parallel_searches=5,
        )

        assert strategy.max_sources == 20
        assert len(strategy.source_types) == 2
        assert strategy.credibility_threshold == 0.7
        assert strategy.max_search_depth == 3
        assert strategy.parallel_searches == 5

    def test_default_source_types(self):
        """Test default source types when empty list provided."""
        strategy = SearchStrategy(source_types=[])

        assert len(strategy.source_types) == 3
        assert SourceType.NEWS in strategy.source_types
        assert SourceType.BLOGS in strategy.source_types
        assert SourceType.OFFICIAL_ANNOUNCEMENTS in strategy.source_types

    def test_max_sources_validation(self):
        """Test max_sources validation."""
        with pytest.raises(ValidationError):
            SearchStrategy(max_sources=0)

        with pytest.raises(ValidationError):
            SearchStrategy(max_sources=101)

    def test_credibility_threshold_validation(self):
        """Test credibility threshold validation."""
        with pytest.raises(ValidationError):
            SearchStrategy(credibility_threshold=-0.1)

        with pytest.raises(ValidationError):
            SearchStrategy(credibility_threshold=1.1)


class TestResearchRequest:
    """Test ResearchRequest model."""

    def test_valid_research_request(self):
        """Test creating a valid research request."""
        topic = ResearchTopic(
            name="AI Research", description="Test description", keywords=["AI"]
        )

        request = ResearchRequest(
            topic=topic, analysis_instructions="Test instructions", priority=8
        )

        assert request.topic.name == "AI Research"
        assert request.analysis_instructions == "Test instructions"
        assert request.priority == 8
        assert isinstance(request.search_strategy, SearchStrategy)

    def test_empty_analysis_instructions_validation(self):
        """Test validation of empty analysis instructions."""
        topic = ResearchTopic(
            name="AI Research", description="Test description", keywords=["AI"]
        )

        with pytest.raises(ValidationError) as exc_info:
            ResearchRequest(topic=topic, analysis_instructions="")

        assert "Analysis instructions cannot be empty" in str(exc_info.value)

    def test_priority_validation(self):
        """Test priority validation."""
        topic = ResearchTopic(
            name="AI Research", description="Test description", keywords=["AI"]
        )

        with pytest.raises(ValidationError):
            ResearchRequest(topic=topic, priority=0)

        with pytest.raises(ValidationError):
            ResearchRequest(topic=topic, priority=11)


class TestPageSection:
    """Test PageSection model."""

    def test_valid_page_section(self):
        """Test creating a valid page section."""
        section = PageSection(
            name="Executive Summary",
            type=SectionType.TEXT_BLOCK,
            content_source="summary",
            order=1,
        )

        assert section.name == "Executive Summary"
        assert section.type == SectionType.TEXT_BLOCK
        assert section.content_source == "summary"
        assert section.order == 1
        assert section.required is True
        assert isinstance(section.configuration, SectionConfiguration)

    def test_empty_name_validation(self):
        """Test validation of empty section name."""
        with pytest.raises(ValidationError) as exc_info:
            PageSection(name="", type=SectionType.TEXT_BLOCK, content_source="summary")

        assert "Section name cannot be empty" in str(exc_info.value)


class TestPageStructure:
    """Test PageStructure model."""

    def test_valid_page_structure(self):
        """Test creating a valid page structure."""
        sections = [
            PageSection(
                name="Summary",
                type=SectionType.TEXT_BLOCK,
                content_source="summary",
            ),
            PageSection(
                name="Findings",
                type=SectionType.BULLET_LIST,
                content_source="findings",
            ),
        ]

        structure = PageStructure(
            title_template="Research Report - {topic_name}",
            sections=sections,
            tags=["research", "analysis"],
        )

        assert structure.title_template == "Research Report - {topic_name}"
        assert len(structure.sections) == 2
        assert len(structure.tags) == 2

    def test_empty_sections_validation(self):
        """Test validation of empty sections list."""
        with pytest.raises(ValidationError) as exc_info:
            PageStructure(sections=[])

        assert "Page sections cannot be empty" in str(exc_info.value)

    def test_unique_section_names_validation(self):
        """Test validation of unique section names."""
        sections = [
            PageSection(
                name="Summary",
                type=SectionType.TEXT_BLOCK,
                content_source="summary",
            ),
            PageSection(
                name="Summary",
                type=SectionType.BULLET_LIST,
                content_source="findings",
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            PageStructure(sections=sections)

        assert "Section names must be unique" in str(exc_info.value)


class TestResearchConfiguration:
    """Test ResearchConfiguration model."""

    def test_valid_research_configuration(self):
        """Test creating a valid research configuration."""
        topic = ResearchTopic(
            name="AI Research", description="Test description", keywords=["AI"]
        )

        request = ResearchRequest(topic=topic)

        sections = [
            PageSection(
                name="Summary",
                type=SectionType.TEXT_BLOCK,
                content_source="summary",
            )
        ]

        page_structure = PageStructure(sections=sections)
        output_schema = OutputSchema(page_structure=page_structure)

        config = ResearchConfiguration(
            name="Test Config",
            research_request=request,
            output_schema=output_schema,
            tags=["test", "ai"],
        )

        assert config.name == "Test Config"
        assert config.version == "1.0"
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)
        assert len(config.tags) == 2

    def test_empty_name_validation(self):
        """Test validation of empty configuration name."""
        topic = ResearchTopic(
            name="AI Research", description="Test description", keywords=["AI"]
        )

        request = ResearchRequest(topic=topic)
        sections = [
            PageSection(
                name="Summary",
                type=SectionType.TEXT_BLOCK,
                content_source="summary",
            )
        ]
        page_structure = PageStructure(sections=sections)
        output_schema = OutputSchema(page_structure=page_structure)

        with pytest.raises(ValidationError) as exc_info:
            ResearchConfiguration(
                name="", research_request=request, output_schema=output_schema
            )

        assert "Configuration name cannot be empty" in str(exc_info.value)


class TestSearchResult:
    """Test SearchResult model."""

    def test_valid_search_result(self):
        """Test creating a valid search result."""
        result = SearchResult(
            title="AI Breakthrough",
            url="https://example.com/article",
            snippet="Recent AI developments...",
            source_type=SourceType.NEWS,
            credibility_score=0.8,
            relevance_score=0.9,
            domain="example.com",
            publication_date=datetime.now(),
            content_length=500,
            extracted_entities=["OpenAI", "GPT"],
            sentiment_score=0.2,
        )

        assert result.title == "AI Breakthrough"
        assert result.url == "https://example.com/article"
        assert result.credibility_score == 0.8
        assert result.relevance_score == 0.9
        assert len(result.extracted_entities) == 2

    def test_url_validation(self):
        """Test URL validation."""
        with pytest.raises(ValidationError) as exc_info:
            SearchResult(
                title="Test",
                url="invalid-url",
                snippet="Test snippet",
                source_type=SourceType.NEWS,
                credibility_score=0.8,
                relevance_score=0.9,
                domain="example.com",
            )

        assert "URL must start with http:// or https://" in str(exc_info.value)


class TestAnalysisInsight:
    """Test AnalysisInsight model."""

    def test_valid_analysis_insight(self):
        """Test creating a valid analysis insight."""
        insight = AnalysisInsight(
            title="Key Finding",
            content="This is an important insight...",
            confidence_score=0.9,
            supporting_sources=["https://example.com/source1"],
            category="innovation",
            impact_level="high",
            key_entities=["OpenAI", "GPT-4"],
        )

        assert insight.title == "Key Finding"
        assert insight.content == "This is an important insight..."
        assert insight.confidence_score == 0.9
        assert len(insight.supporting_sources) == 1
        assert insight.category == "innovation"
        assert len(insight.key_entities) == 2
        assert isinstance(insight.generated_at, datetime)

    def test_empty_title_validation(self):
        """Test validation of empty title."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisInsight(
                title="",
                content="Test content",
                confidence_score=0.9,
                category="test",
            )

        assert "Title and content cannot be empty" in str(exc_info.value)

    def test_empty_content_validation(self):
        """Test validation of empty content."""
        with pytest.raises(ValidationError) as exc_info:
            AnalysisInsight(
                title="Test Title",
                content="",
                confidence_score=0.9,
                category="test",
            )

        assert "Title and content cannot be empty" in str(exc_info.value)


class TestResearchResult:
    """Test ResearchResult model."""

    def test_valid_research_result(self):
        """Test creating a valid research result."""
        result = ResearchResult(
            configuration_name="test-config",
            execution_id="test-123",
            status="completed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_seconds=120.5,
            sources_found=25,
            sources_analyzed=20,
            insights_generated=15,
            notion_page_url="https://notion.so/page-123",
            quality_score=0.85,
        )

        assert result.configuration_name == "test-config"
        assert result.execution_id == "test-123"
        assert result.status == "completed"
        assert result.duration_seconds == 120.5
        assert result.sources_found == 25
        assert result.sources_analyzed == 20
        assert result.insights_generated == 15
        assert result.quality_score == 0.85

    def test_quality_score_validation(self):
        """Test quality score validation."""
        with pytest.raises(ValidationError):
            ResearchResult(
                configuration_name="test",
                execution_id="test-123",
                status="completed",
                started_at=datetime.now(),
                quality_score=1.5,
            )


class TestBuiltinTemplates:
    """Test built-in configuration templates."""

    def test_tech_research_template(self):
        """Test technology research template."""
        config = TECH_RESEARCH_TEMPLATE

        assert config.name == "Technology Research Template"
        assert config.research_request.topic.name == "Technology Research"
        assert len(config.research_request.topic.keywords) > 0
        assert len(config.output_schema.page_structure.sections) > 0
        assert config.output_schema.output_format == OutputFormat.NOTION_PAGE

    def test_market_research_template(self):
        """Test market research template."""
        config = MARKET_RESEARCH_TEMPLATE

        assert config.name == "Market Research Template"
        assert config.research_request.topic.name == "Market Research"
        assert len(config.research_request.topic.keywords) > 0
        assert len(config.output_schema.page_structure.sections) > 0
        assert config.output_schema.output_format == OutputFormat.NOTION_PAGE

    def test_template_validation(self):
        """Test that templates are valid configurations."""
        templates = [TECH_RESEARCH_TEMPLATE, MARKET_RESEARCH_TEMPLATE]

        for template in templates:
            # Should not raise validation errors
            assert isinstance(template, ResearchConfiguration)
            assert template.name
            assert template.research_request
            assert template.output_schema


class TestEnumValues:
    """Test enum values and validation."""

    def test_research_depth_values(self):
        """Test ResearchDepth enum values."""
        assert ResearchDepth.BASIC == "basic"
        assert ResearchDepth.DETAILED == "detailed"
        assert ResearchDepth.COMPREHENSIVE == "comprehensive"

    def test_source_type_values(self):
        """Test SourceType enum values."""
        assert SourceType.NEWS == "news"
        assert SourceType.BLOGS == "blogs"
        assert SourceType.RESEARCH_PAPERS == "research_papers"
        assert SourceType.OFFICIAL_ANNOUNCEMENTS == "official_announcements"

    def test_output_format_values(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.NOTION_PAGE == "notion_page"
        assert OutputFormat.MARKDOWN == "markdown"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.PDF == "pdf"

    def test_section_type_values(self):
        """Test SectionType enum values."""
        assert SectionType.TEXT_BLOCK == "text_block"
        assert SectionType.BULLET_LIST == "bullet_list"
        assert SectionType.TABLE == "table"
        assert SectionType.TOGGLE_BLOCKS == "toggle_blocks"

    def test_summary_length_values(self):
        """Test SummaryLength enum values."""
        assert SummaryLength.SHORT == "short"
        assert SummaryLength.MEDIUM == "medium"
        assert SummaryLength.DETAILED == "detailed"


class TestSectionConfiguration:
    """Test SectionConfiguration model."""

    def test_default_section_configuration(self):
        """Test default section configuration."""
        config = SectionConfiguration()

        assert config.include_sources is True
        assert config.include_confidence_scores is False
        assert config.format_numbers is False
        assert config.highlight_key_points is False

    def test_section_configuration_with_values(self):
        """Test section configuration with custom values."""
        config = SectionConfiguration(
            max_length=500,
            max_items=10,
            include_sources=False,
            include_confidence_scores=True,
            columns=["Title", "URL", "Date"],
        )

        assert config.max_length == 500
        assert config.max_items == 10
        assert config.include_sources is False
        assert config.include_confidence_scores is True
        assert len(config.columns) == 3


class TestContentProcessing:
    """Test ContentProcessing model."""

    def test_default_content_processing(self):
        """Test default content processing configuration."""
        processing = ContentProcessing()

        assert processing.summary_length == SummaryLength.DETAILED
        assert processing.include_confidence_scores is True
        assert processing.group_similar_findings is True
        assert processing.extract_key_quotes is True
        assert processing.generate_insights is True
        assert processing.fact_check is False
        assert processing.sentiment_analysis is False
        assert processing.entity_extraction is True

    def test_custom_content_processing(self):
        """Test custom content processing configuration."""
        processing = ContentProcessing(
            summary_length=SummaryLength.SHORT,
            include_confidence_scores=False,
            fact_check=True,
            sentiment_analysis=True,
            trend_analysis=True,
        )

        assert processing.summary_length == SummaryLength.SHORT
        assert processing.include_confidence_scores is False
        assert processing.fact_check is True
        assert processing.sentiment_analysis is True
        assert processing.trend_analysis is True
