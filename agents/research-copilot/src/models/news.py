"""Data models for LLM news and announcements."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class ImpactLevel(str, Enum):
    """Impact level of LLM releases and announcements."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Company(str, Enum):
    """Major companies in the LLM space."""

    OPENAI = "OpenAI"
    GOOGLE = "Google"
    MICROSOFT = "Microsoft"
    ANTHROPIC = "Anthropic"
    META = "Meta"
    HUGGINGFACE = "Hugging Face"
    GITHUB = "GitHub"
    OTHER = "Other"


class ContentType(str, Enum):
    """Type of content being analyzed."""

    RELEASE = "release"
    ANNOUNCEMENT = "announcement"
    RESEARCH_PAPER = "research_paper"
    BLOG_POST = "blog_post"
    DOCUMENTATION = "documentation"
    NEWS_ARTICLE = "news_article"


class LLMRelease(BaseModel):
    """Model for LLM release information."""

    company: Company
    product: str = Field(..., description="Name of the LLM or product")
    version: Optional[str] = Field(None, description="Version number if available")
    release_date: datetime = Field(..., description="Date of release")
    key_features: List[str] = Field(
        default_factory=list,
        description="List of key features or improvements",
    )
    impact_level: ImpactLevel = Field(..., description="Assessed impact level")
    source_links: List[HttpUrl] = Field(
        default_factory=list, description="Links to official announcements"
    )
    summary: str = Field(..., description="Brief summary of the release")
    technical_details: Optional[Dict[str, Any]] = Field(
        None, description="Technical specifications if available"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class FeatureAnnouncement(BaseModel):
    """Model for feature announcements and updates."""

    company: Company
    product: str = Field(..., description="Product or service name")
    announcement_date: datetime = Field(..., description="Date of announcement")
    features: List[str] = Field(
        default_factory=list, description="List of new features"
    )
    impact_level: ImpactLevel = Field(..., description="Assessed impact level")
    source_links: List[HttpUrl] = Field(
        default_factory=list, description="Links to announcements"
    )
    summary: str = Field(..., description="Brief summary of the announcement")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class ResearchPaper(BaseModel):
    """Model for research papers and publications."""

    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of authors")
    publication: str = Field(..., description="Publication venue (arXiv, etc.)")
    publication_date: datetime = Field(..., description="Publication date")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    summary: str = Field(..., description="AI-generated summary")
    link: HttpUrl = Field(..., description="Link to the paper")
    relevance_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Relevance score for LLM developments"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class WeeklyReport(BaseModel):
    """Model for weekly LLM news report."""

    week_of: datetime = Field(..., description="Start date of the week")
    generation_date: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this report was generated",
    )
    major_releases: List[LLMRelease] = Field(
        default_factory=list, description="Major LLM releases this week"
    )
    feature_announcements: List[FeatureAnnouncement] = Field(
        default_factory=list, description="Feature announcements this week"
    )
    research_papers: List[ResearchPaper] = Field(
        default_factory=list, description="Relevant research papers this week"
    )
    summary: str = Field(..., description="Executive summary of the week")
    trends: List[str] = Field(
        default_factory=list, description="Identified trends and patterns"
    )

    @validator("week_of")
    def validate_week_start(cls, v):
        """Ensure week_of is a Monday."""
        if v.weekday() != 0:  # Monday is 0
            # Adjust to the Monday of that week
            days_since_monday = v.weekday()
            v = v.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                days=days_since_monday
            )
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class SearchResult(BaseModel):
    """Model for web search results."""

    title: str = Field(..., description="Title of the search result")
    url: HttpUrl = Field(..., description="URL of the result")
    snippet: str = Field(..., description="Search result snippet")
    date: Optional[datetime] = Field(None, description="Publication date if available")
    source: str = Field(..., description="Source domain or publication")
    relevance_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Relevance score for the search query"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            HttpUrl: str,
        }


class AnalysisRequest(BaseModel):
    """Model for content analysis requests."""

    content: str = Field(..., description="Content to analyze")
    content_type: ContentType = Field(..., description="Type of content")
    source_url: Optional[HttpUrl] = Field(None, description="Source URL")
    company_hint: Optional[Company] = Field(
        None, description="Hint about which company this relates to"
    )
    analysis_focus: List[str] = Field(
        default_factory=list,
        description="Specific aspects to focus analysis on",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {HttpUrl: str}


class AnalysisResult(BaseModel):
    """Model for content analysis results."""

    content_type: ContentType
    company: Optional[Company] = Field(None, description="Identified company")
    product: Optional[str] = Field(None, description="Identified product")
    key_points: List[str] = Field(
        default_factory=list, description="Key points extracted from content"
    )
    sentiment: str = Field("neutral", description="Overall sentiment")
    impact_assessment: ImpactLevel = Field(
        ImpactLevel.LOW, description="Assessed impact level"
    )
    structured_data: Optional[Dict[str, Any]] = Field(
        None, description="Structured data extracted from content"
    )
    confidence_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence in the analysis"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
