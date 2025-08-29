"""
Pydantic models for research configuration management.

This module defines the data structures used to configure research requests,
search strategies, and output formatting for the Research Copilot Agent.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ResearchDepth(str, Enum):
    """Enumeration of research depth levels."""

    BASIC = "basic"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class SourceType(str, Enum):
    """Enumeration of source types for research."""

    NEWS = "news"
    RESEARCH_PAPERS = "research_papers"
    BLOGS = "blogs"
    OFFICIAL_ANNOUNCEMENTS = "official_announcements"
    SOCIAL_MEDIA = "social_media"
    FORUMS = "forums"
    DOCUMENTATION = "documentation"
    REPORTS = "reports"
    INTERVIEWS = "interviews"
    PODCASTS = "podcasts"


class OutputFormat(str, Enum):
    """Enumeration of output formats."""

    NOTION_PAGE = "notion_page"
    MARKDOWN = "markdown"
    JSON = "json"
    PDF = "pdf"


class SectionType(str, Enum):
    """Enumeration of section types for output structure."""

    TEXT_BLOCK = "text_block"
    BULLET_LIST = "bullet_list"
    NUMBERED_LIST = "numbered_list"
    TABLE = "table"
    TOGGLE_BLOCKS = "toggle_blocks"
    CALLOUT = "callout"
    QUOTE = "quote"
    CODE_BLOCK = "code_block"
    DIVIDER = "divider"
    IMAGE = "image"
    VIDEO = "video"


class SummaryLength(str, Enum):
    """Enumeration of summary length options."""

    SHORT = "short"
    MEDIUM = "medium"
    DETAILED = "detailed"


class ResearchTopic(BaseModel):
    """Configuration for research topic definition."""

    name: str = Field(..., description="Name of the research topic")
    description: str = Field(
        ..., description="Detailed description of what to research"
    )
    keywords: List[str] = Field(
        default_factory=list, description="Key terms and phrases"
    )
    focus_areas: List[str] = Field(
        default_factory=list, description="Specific areas to focus on"
    )
    time_range: str = Field(default="past_month", description="Time range for research")
    depth: ResearchDepth = Field(
        default=ResearchDepth.DETAILED, description="Research depth level"
    )
    exclude_terms: List[str] = Field(
        default_factory=list, description="Terms to exclude from search"
    )

    @validator("keywords")
    def keywords_not_empty(cls, v):
        """Validate that keywords list is not empty."""
        if not v:
            raise ValueError("Keywords list cannot be empty")
        return v

    @validator("name")
    def name_not_empty(cls, v):
        """Validate that name is not empty."""
        if not v.strip():
            raise ValueError("Topic name cannot be empty")
        return v.strip()


class SearchStrategy(BaseModel):
    """Configuration for search strategy parameters."""

    max_sources: int = Field(
        default=20, ge=1, le=100, description="Maximum number of sources to search"
    )
    source_types: List[SourceType] = Field(
        default_factory=list, description="Types of sources to include"
    )
    credibility_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum credibility score"
    )
    max_search_depth: int = Field(
        default=3, ge=1, le=5, description="Maximum search depth for follow-ups"
    )
    parallel_searches: int = Field(
        default=5, ge=1, le=10, description="Number of parallel search threads"
    )
    search_timeout: int = Field(
        default=300, ge=30, le=600, description="Search timeout in seconds"
    )
    enable_follow_up: bool = Field(
        default=True, description="Enable follow-up searches"
    )
    language_preference: List[str] = Field(
        default=["en"], description="Preferred languages for sources"
    )

    @validator("source_types")
    def source_types_not_empty(cls, v):
        """Validate that source types list is not empty."""
        if not v:
            return [
                SourceType.NEWS,
                SourceType.BLOGS,
                SourceType.OFFICIAL_ANNOUNCEMENTS,
            ]
        return v


class ResearchRequest(BaseModel):
    """Complete research request configuration."""

    topic: ResearchTopic = Field(..., description="Research topic configuration")
    search_strategy: SearchStrategy = Field(
        default_factory=SearchStrategy, description="Search strategy parameters"
    )
    analysis_instructions: str = Field(
        default="Analyze the collected information and provide comprehensive insights with supporting evidence.",
        description="Instructions for content analysis",
    )
    priority: int = Field(default=5, ge=1, le=10, description="Research priority level")
    deadline: Optional[datetime] = Field(
        None, description="Research completion deadline"
    )
    requester: Optional[str] = Field(
        None, description="Person or system requesting research"
    )

    @validator("analysis_instructions")
    def analysis_instructions_not_empty(cls, v):
        """Validate that analysis instructions are not empty."""
        if not v.strip():
            raise ValueError("Analysis instructions cannot be empty")
        return v.strip()


class SectionConfiguration(BaseModel):
    """Configuration for individual output sections."""

    max_length: Optional[int] = Field(None, ge=1, description="Maximum content length")
    max_items: Optional[int] = Field(None, ge=1, description="Maximum number of items")
    include_sources: bool = Field(default=True, description="Include source references")
    include_confidence_scores: bool = Field(
        default=False, description="Include confidence scores"
    )
    group_by: Optional[str] = Field(None, description="Grouping criteria")
    sort_by: Optional[str] = Field(None, description="Sorting criteria")
    columns: Optional[List[str]] = Field(None, description="Table column definitions")
    format_numbers: bool = Field(default=False, description="Format numeric values")
    highlight_key_points: bool = Field(
        default=False, description="Highlight important points"
    )
    prioritize_by_impact: bool = Field(
        default=False, description="Prioritize by impact level"
    )
    include_metrics: bool = Field(
        default=False, description="Include quantitative metrics"
    )
    include_market_share: bool = Field(
        default=False, description="Include market share data"
    )
    include_key_points: bool = Field(
        default=False, description="Include key point summaries"
    )


class PageSection(BaseModel):
    """Configuration for output page sections."""

    name: str = Field(..., description="Section name")
    type: SectionType = Field(..., description="Section type")
    content_source: str = Field(..., description="Source of content for this section")
    configuration: SectionConfiguration = Field(
        default_factory=SectionConfiguration,
        description="Section-specific configuration",
    )
    order: int = Field(default=0, description="Section display order")
    required: bool = Field(default=True, description="Whether section is required")

    @validator("name")
    def name_not_empty(cls, v):
        """Validate that section name is not empty."""
        if not v.strip():
            raise ValueError("Section name cannot be empty")
        return v.strip()


class PageStructure(BaseModel):
    """Configuration for output page structure."""

    title_template: str = Field(
        default="Research Report - {topic_name} - {date}",
        description="Template for page title",
    )
    sections: List[PageSection] = Field(..., description="Page sections configuration")
    header_content: Optional[str] = Field(None, description="Optional header content")
    footer_content: Optional[str] = Field(None, description="Optional footer content")
    tags: List[str] = Field(default_factory=list, description="Page tags")

    @validator("sections")
    def sections_not_empty(cls, v):
        """Validate that sections list is not empty."""
        if not v:
            raise ValueError("Page sections cannot be empty")
        return v

    @validator("sections")
    def unique_section_names(cls, v):
        """Validate that section names are unique."""
        names = [section.name for section in v]
        if len(names) != len(set(names)):
            raise ValueError("Section names must be unique")
        return v


class ContentProcessing(BaseModel):
    """Configuration for content processing options."""

    summary_length: SummaryLength = Field(
        default=SummaryLength.DETAILED, description="Summary length preference"
    )
    include_confidence_scores: bool = Field(
        default=True, description="Include confidence scores in output"
    )
    group_similar_findings: bool = Field(
        default=True, description="Group similar findings together"
    )
    extract_key_quotes: bool = Field(
        default=True, description="Extract important quotes"
    )
    generate_insights: bool = Field(
        default=True, description="Generate analytical insights"
    )
    fact_check: bool = Field(default=False, description="Enable fact-checking")
    sentiment_analysis: bool = Field(
        default=False, description="Include sentiment analysis"
    )
    entity_extraction: bool = Field(default=True, description="Extract named entities")
    relationship_mapping: bool = Field(
        default=False, description="Map entity relationships"
    )
    trend_analysis: bool = Field(default=False, description="Analyze trends over time")


class OutputSchema(BaseModel):
    """Complete output schema configuration."""

    output_format: OutputFormat = Field(
        default=OutputFormat.NOTION_PAGE, description="Output format type"
    )
    template: str = Field(default="research_report", description="Output template name")
    page_structure: PageStructure = Field(
        ..., description="Page structure configuration"
    )
    content_processing: ContentProcessing = Field(
        default_factory=ContentProcessing, description="Content processing options"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ResearchConfiguration(BaseModel):
    """Complete research configuration combining request and output schema."""

    version: str = Field(default="1.0", description="Configuration schema version")
    name: str = Field(..., description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    research_request: ResearchRequest = Field(
        ..., description="Research request configuration"
    )
    output_schema: OutputSchema = Field(..., description="Output schema configuration")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Configuration creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update time"
    )
    created_by: Optional[str] = Field(None, description="Configuration creator")
    tags: List[str] = Field(default_factory=list, description="Configuration tags")

    @validator("name")
    def name_not_empty(cls, v):
        """Validate that configuration name is not empty."""
        if not v.strip():
            raise ValueError("Configuration name cannot be empty")
        return v.strip()

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class ResearchResult(BaseModel):
    """Model for research execution results."""

    configuration_name: str = Field(..., description="Name of configuration used")
    execution_id: str = Field(..., description="Unique execution identifier")
    status: str = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(
        None, description="Execution completion time"
    )
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    sources_found: int = Field(default=0, description="Number of sources found")
    sources_analyzed: int = Field(default=0, description="Number of sources analyzed")
    insights_generated: int = Field(
        default=0, description="Number of insights generated"
    )
    notion_page_url: Optional[str] = Field(
        None, description="URL of created Notion page"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Research quality score"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional result metadata"
    )


class SearchResult(BaseModel):
    """Model for individual search results."""

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Source URL")
    snippet: str = Field(..., description="Content snippet")
    source_type: SourceType = Field(..., description="Type of source")
    credibility_score: float = Field(
        ..., ge=0.0, le=1.0, description="Credibility assessment"
    )
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance to topic"
    )
    publication_date: Optional[datetime] = Field(None, description="Publication date")
    author: Optional[str] = Field(None, description="Content author")
    domain: str = Field(..., description="Source domain")
    language: str = Field(default="en", description="Content language")
    content_length: int = Field(
        default=0, ge=0, description="Content length in characters"
    )
    extracted_entities: List[str] = Field(
        default_factory=list, description="Extracted named entities"
    )
    quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Overall quality score"
    )
    sentiment_score: Optional[float] = Field(
        None, ge=-1.0, le=1.0, description="Sentiment analysis score"
    )

    @validator("url")
    def valid_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class AnalysisInsight(BaseModel):
    """Model for analytical insights generated from research."""

    title: str = Field(..., description="Insight title")
    content: str = Field(..., description="Insight content")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in insight"
    )
    supporting_sources: List[str] = Field(
        default_factory=list, description="URLs of supporting sources"
    )
    category: str = Field(..., description="Insight category")
    impact_level: str = Field(default="medium", description="Estimated impact level")
    key_entities: List[str] = Field(
        default_factory=list, description="Key entities mentioned"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Generation timestamp"
    )

    @validator("title", "content")
    def not_empty(cls, v):
        """Validate that title and content are not empty."""
        if not v.strip():
            raise ValueError("Title and content cannot be empty")
        return v.strip()


# Template configurations for common research types
TECH_RESEARCH_TEMPLATE = ResearchConfiguration(
    name="Technology Research Template",
    description="Comprehensive analysis of emerging technology trends",
    research_request=ResearchRequest(
        topic=ResearchTopic(
            name="Technology Research",
            description="Comprehensive analysis of emerging technology trends",
            keywords=["AI", "machine learning", "blockchain", "cloud computing"],
            focus_areas=["innovations", "market impact", "adoption trends"],
            time_range="past_month",
            depth=ResearchDepth.DETAILED,
        ),
        search_strategy=SearchStrategy(
            max_sources=20,
            source_types=[
                SourceType.NEWS,
                SourceType.RESEARCH_PAPERS,
                SourceType.BLOGS,
                SourceType.OFFICIAL_ANNOUNCEMENTS,
            ],
            credibility_threshold=0.7,
        ),
        analysis_instructions="""
        Analyze the collected information to identify:
        1. Key technological breakthroughs and innovations
        2. Market trends and adoption patterns
        3. Industry impact and future implications
        4. Competitive landscape changes

        Provide detailed analysis with supporting evidence and credible sources.
        """,
    ),
    output_schema=OutputSchema(
        output_format=OutputFormat.NOTION_PAGE,
        template="research_report",
        page_structure=PageStructure(
            title_template="Technology Research Report - {topic_name} - {date}",
            sections=[
                PageSection(
                    name="Executive Summary",
                    type=SectionType.TEXT_BLOCK,
                    content_source="summary",
                    configuration=SectionConfiguration(
                        max_length=500, include_key_points=True
                    ),
                    order=1,
                ),
                PageSection(
                    name="Key Findings",
                    type=SectionType.BULLET_LIST,
                    content_source="findings",
                    configuration=SectionConfiguration(
                        max_items=10, include_sources=True
                    ),
                    order=2,
                ),
                PageSection(
                    name="Detailed Analysis",
                    type=SectionType.TOGGLE_BLOCKS,
                    content_source="analysis",
                    configuration=SectionConfiguration(
                        group_by="category", include_confidence_scores=True
                    ),
                    order=3,
                ),
                PageSection(
                    name="Sources",
                    type=SectionType.TABLE,
                    content_source="sources",
                    configuration=SectionConfiguration(
                        columns=["Title", "URL", "Credibility", "Date"],
                        sort_by="credibility",
                    ),
                    order=4,
                ),
            ],
        ),
        content_processing=ContentProcessing(
            summary_length=SummaryLength.DETAILED,
            include_confidence_scores=True,
            group_similar_findings=True,
        ),
    ),
)

MARKET_RESEARCH_TEMPLATE = ResearchConfiguration(
    name="Market Research Template",
    description="Market analysis and competitive intelligence",
    research_request=ResearchRequest(
        topic=ResearchTopic(
            name="Market Research",
            description="Market analysis and competitive intelligence",
            keywords=[
                "market size",
                "competition",
                "growth trends",
                "consumer behavior",
            ],
            focus_areas=["market dynamics", "competitive analysis", "opportunities"],
            time_range="past_quarter",
            depth=ResearchDepth.COMPREHENSIVE,
        ),
        search_strategy=SearchStrategy(
            max_sources=25,
            source_types=[
                SourceType.REPORTS,
                SourceType.NEWS,
                SourceType.OFFICIAL_ANNOUNCEMENTS,
            ],
            credibility_threshold=0.8,
        ),
        analysis_instructions="""
        Conduct comprehensive market analysis focusing on:
        1. Market size, growth, and segmentation
        2. Competitive landscape and key players
        3. Consumer trends and preferences
        4. Market opportunities and threats
        5. Financial performance and projections

        Provide quantitative data where available and cite all sources.
        """,
    ),
    output_schema=OutputSchema(
        output_format=OutputFormat.NOTION_PAGE,
        template="market_report",
        page_structure=PageStructure(
            title_template="Market Research - {topic_name} - {date}",
            sections=[
                PageSection(
                    name="Market Overview",
                    type=SectionType.TEXT_BLOCK,
                    content_source="overview",
                    configuration=SectionConfiguration(
                        include_metrics=True, highlight_key_stats=True
                    ),
                    order=1,
                ),
                PageSection(
                    name="Market Metrics",
                    type=SectionType.TABLE,
                    content_source="metrics",
                    configuration=SectionConfiguration(
                        columns=["Metric", "Value", "Change", "Source"],
                        format_numbers=True,
                    ),
                    order=2,
                ),
                PageSection(
                    name="Competitive Analysis",
                    type=SectionType.TOGGLE_BLOCKS,
                    content_source="competitors",
                    configuration=SectionConfiguration(
                        group_by="company", include_market_share=True
                    ),
                    order=3,
                ),
                PageSection(
                    name="Key Insights",
                    type=SectionType.BULLET_LIST,
                    content_source="insights",
                    configuration=SectionConfiguration(
                        prioritize_by_impact=True, include_confidence_scores=True
                    ),
                    order=4,
                ),
            ],
        ),
        content_processing=ContentProcessing(
            summary_length=SummaryLength.DETAILED,
            include_confidence_scores=True,
            group_similar_findings=True,
            trend_analysis=True,
        ),
    ),
)
