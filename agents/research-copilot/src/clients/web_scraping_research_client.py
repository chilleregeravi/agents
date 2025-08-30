"""
Web Scraping Research Client for complete research workflow.

This module implements the complete research flow:
1. Research Request → Scrape internet by agent based on what sites should be scraped
2. Collect data by agent and provide to LLM with context of research request
3. LLM generates output based on the data
4. Send data to Notion
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.research_config import (
    AnalysisRequest,
    AnalysisResult,
    ResearchData,
    ResearchRequest,
    ResearchResult,
)

logger = logging.getLogger(__name__)


class WebScrapingResearchError(Exception):
    """Exception raised for web scraping research workflow errors."""

    pass


class WebSource(BaseModel):
    """Represents a web source to be scraped."""

    url: str
    domain: str
    source_type: str  # "news", "blog", "research", "official", "documentation"
    credibility_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    description: str
    priority: int = Field(default=1, ge=1, le=5)  # Priority for scraping order


class ScrapingStrategy(BaseModel):
    """Strategy for web scraping and data collection."""

    target_sources: List[WebSource]
    search_queries: List[str]
    content_keywords: List[str]
    quality_indicators: List[str]
    max_sources_to_scrape: int = Field(default=20, ge=1, le=100)
    scraping_timeout: int = Field(default=30, ge=10, le=120)
    content_filters: List[str] = Field(default_factory=list)


class WebScrapingResearchClient:
    """
    Web scraping research client that handles the complete workflow.

    Flow:
    1. Research Request → Generate scraping strategy
    2. Scrape internet based on strategy
    3. Collect and organize data
    4. Provide data to LLM with research context
    5. Generate analysis output
    6. Prepare for Notion publishing
    """

    def __init__(self, llm_client, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize web scraping research client.

        Args:
            llm_client: Local LLM client (Qwen via Ollama)
            session: Optional HTTP session for web requests
        """
        self.llm_client = llm_client
        self.session = session
        self._should_close_session = session is None

        # Scraping parameters
        self.max_content_length = 50000
        self.min_content_length = 100
        self.user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        # Analysis parameters
        self.analysis_id_counter = 0

    async def __aenter__(self):
        """Async context manager entry."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {"User-Agent": self.user_agent}
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._should_close_session and self.session:
            await self.session.close()

    async def execute_web_scraping_research(
        self, research_request: ResearchRequest
    ) -> ResearchResult:
        """
        Execute complete web scraping research workflow.

        Args:
            research_request: Research configuration and requirements

        Returns:
            Complete research result with analysis
        """
        start_time = datetime.utcnow()
        execution_id = f"web_scraping_research_{start_time.strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting web scraping research: {execution_id}")

        try:
            # Phase 1: Generate scraping strategy
            scraping_strategy = await self._generate_scraping_strategy(research_request)
            logger.info(
                f"Generated scraping strategy with {len(scraping_strategy.target_sources)} sources"
            )

            # Phase 2: Scrape internet based on strategy
            scraped_data = await self._scrape_internet_data(
                scraping_strategy, research_request
            )
            logger.info(f"Scraped {len(scraped_data)} content items")

            # Phase 3: Organize collected data
            research_data = await self._organize_scraped_data(
                scraped_data, research_request
            )
            logger.info(
                f"Organized data into {len(research_data.data_sources)} sources"
            )

            # Phase 4: Create analysis request with context
            analysis_request = self._create_analysis_request(
                research_data, research_request
            )

            # Phase 5: Generate analysis using LLM
            analysis_result = await self._generate_analysis(analysis_request)
            logger.info(f"Generated {len(analysis_result.key_insights)} insights")

            # Phase 6: Create research result
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = ResearchResult(
                configuration_name=research_request.topic.name,
                execution_id=execution_id,
                status="completed",
                started_at=start_time,
                completed_at=end_time,
                duration_seconds=duration,
                sources_found=len(scraping_strategy.target_sources),
                sources_analyzed=len(research_data.data_sources),
                insights_generated=len(analysis_result.key_insights),
                quality_score=analysis_result.analysis_confidence,
                metadata={
                    "workflow_type": "web_scraping_research",
                    "llm_model": "qwen-local",
                    "scraping_strategy": scraping_strategy.dict(),
                    "analysis_id": analysis_result.analysis_id,
                },
            )

            logger.info(f"Web scraping research completed: {execution_id}")
            return result

        except Exception as e:
            logger.error(f"Web scraping research failed: {e}", exc_info=True)
            raise WebScrapingResearchError(f"Research failed: {e}") from e

    async def _generate_scraping_strategy(
        self, research_request: ResearchRequest
    ) -> ScrapingStrategy:
        """
        Generate scraping strategy using LLM.

        Args:
            research_request: Research configuration

        Returns:
            Scraping strategy with target sources and queries
        """
        prompt = self._construct_strategy_prompt(research_request)

        try:
            response = await self.llm_client.generate_response(
                prompt, max_tokens=3000, temperature=0.4
            )

            strategy_data = json.loads(response.strip())

            # Convert to structured objects
            target_sources = [
                WebSource(**source)
                for source in strategy_data.get("target_sources", [])
            ]

            strategy = ScrapingStrategy(
                target_sources=target_sources,
                search_queries=strategy_data.get("search_queries", []),
                content_keywords=strategy_data.get("content_keywords", []),
                quality_indicators=strategy_data.get("quality_indicators", []),
                max_sources_to_scrape=research_request.search_strategy.max_sources,
                scraping_timeout=30,
                content_filters=strategy_data.get("content_filters", []),
            )

            return strategy

        except Exception as e:
            logger.error(f"Failed to generate scraping strategy: {e}")
            # Fallback to basic strategy
            return self._create_fallback_strategy(research_request)

    def _construct_strategy_prompt(self, research_request: ResearchRequest) -> str:
        """Construct prompt for generating scraping strategy."""
        prompt_parts = [
            f"Generate a comprehensive web scraping strategy for research on: {research_request.topic.name}",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {research_request.topic.name}",
            f"Description: {research_request.topic.description}",
            f"Keywords: {', '.join(research_request.topic.keywords)}",
            f"Focus Areas: {', '.join(research_request.topic.focus_areas)}",
            f"Time Range: {research_request.topic.time_range}",
            f"Research Depth: {research_request.topic.depth}",
            "",
            "ANALYSIS INSTRUCTIONS:",
            research_request.analysis_instructions,
            "",
            "Generate a scraping strategy that includes:",
            "1. Specific websites and URLs to scrape",
            "2. Search queries to find relevant content",
            "3. Keywords to look for in content",
            "4. Quality indicators for content filtering",
            "5. Content filters to apply",
            "",
            "Respond with JSON:",
            "{",
            '  "target_sources": [',
            "    {",
            '      "url": "https://specific-url.com/relevant-section",',
            '      "domain": "specific-url.com",',
            '      "source_type": "news|blog|research|official|documentation",',
            '      "credibility_score": 0.8,',
            '      "relevance_score": 0.9,',
            '      "description": "Why this source is relevant",',
            '      "priority": 1',
            "    }",
            "  ],",
            '  "search_queries": ["query1", "query2", ...],',
            '  "content_keywords": ["keyword1", "keyword2", ...],',
            '  "quality_indicators": ["peer reviewed", "official", ...],',
            '  "content_filters": ["filter1", "filter2", ...]',
            "}",
            "",
            "Focus on high-quality, authoritative sources that would contain "
            "relevant information for the research topic.",
        ]

        return "\n".join(prompt_parts)

    def _create_fallback_strategy(
        self, research_request: ResearchRequest
    ) -> ScrapingStrategy:
        """Create a basic fallback strategy if LLM generation fails."""
        topic_keywords = research_request.topic.keywords

        # Basic target sources
        target_sources = [
            WebSource(
                url="https://techcrunch.com",
                domain="techcrunch.com",
                source_type="news",
                credibility_score=0.8,
                relevance_score=0.7,
                description="Technology news and announcements",
                priority=1,
            ),
            WebSource(
                url="https://www.reuters.com",
                domain="reuters.com",
                source_type="news",
                credibility_score=0.9,
                relevance_score=0.6,
                description="General news and business updates",
                priority=2,
            ),
        ]

        # Basic search queries
        search_queries = [
            f"{research_request.topic.name} {research_request.topic.time_range}",
            f"{' '.join(topic_keywords[:3])} latest developments",
            f"{research_request.topic.name} announcements news",
        ]

        return ScrapingStrategy(
            target_sources=target_sources,
            search_queries=search_queries,
            content_keywords=topic_keywords,
            quality_indicators=["official", "announcement", "research", "study"],
            max_sources_to_scrape=research_request.search_strategy.max_sources,
            scraping_timeout=30,
        )

    async def _scrape_internet_data(
        self, scraping_strategy: ScrapingStrategy, research_request: ResearchRequest
    ) -> List[Dict[str, Any]]:
        """
        Scrape internet data based on the strategy.

        Args:
            scraping_strategy: Strategy for web scraping
            research_request: Research configuration

        Returns:
            List of scraped content items
        """
        scraped_data = []

        # Scrape target sources
        for source in scraping_strategy.target_sources[
            : scraping_strategy.max_sources_to_scrape
        ]:
            try:
                content = await self._scrape_web_source(source, scraping_strategy)
                if content:
                    scraped_data.append(content)

                # Small delay between requests
                await asyncio.sleep(1)

            except Exception as e:
                logger.warning(f"Failed to scrape {source.url}: {e}")

        # Use search queries to find additional sources
        for query in scraping_strategy.search_queries[:5]:  # Limit queries
            try:
                additional_sources = await self._discover_sources_from_query(
                    query, scraping_strategy, research_request
                )

                for source in additional_sources:
                    if len(scraped_data) >= scraping_strategy.max_sources_to_scrape:
                        break

                    try:
                        content = await self._scrape_web_source(
                            source, scraping_strategy
                        )
                        if content:
                            scraped_data.append(content)

                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.warning(
                            f"Failed to scrape discovered source {source.url}: {e}"
                        )

            except Exception as e:
                logger.warning(f"Failed to discover sources for query '{query}': {e}")

        return scraped_data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    async def _scrape_web_source(
        self, source: WebSource, scraping_strategy: ScrapingStrategy
    ) -> Optional[Dict[str, Any]]:
        """
        Scrape content from a specific web source.

        Args:
            source: Web source to scrape
            scraping_strategy: Scraping strategy for filtering

        Returns:
            Scraped content or None if failed
        """
        try:
            async with self.session.get(
                source.url, timeout=scraping_strategy.scraping_timeout
            ) as response:
                if response.status != 200:
                    return None

                html_content = await response.text()

                # Parse and clean HTML
                soup = BeautifulSoup(html_content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "aside"]):
                    script.decompose()

                # Extract title
                title = soup.find("title")
                title_text = title.get_text().strip() if title else source.description

                # Extract main content
                main_content = (
                    soup.find("main") or soup.find("article") or soup.find("body")
                )
                if main_content:
                    text_content = main_content.get_text()
                else:
                    text_content = soup.get_text()

                # Clean up text
                lines = (line.strip() for line in text_content.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                cleaned_text = " ".join(chunk for chunk in chunks if chunk)

                # Apply content filters
                if not self._passes_content_filters(cleaned_text, scraping_strategy):
                    return None

                # Limit content length
                cleaned_text = cleaned_text[: self.max_content_length]

                if len(cleaned_text) < self.min_content_length:
                    return None

                return {
                    "title": title_text,
                    "content": cleaned_text,
                    "url": source.url,
                    "source_type": source.source_type,
                    "domain": source.domain,
                    "credibility_score": source.credibility_score,
                    "relevance_score": source.relevance_score,
                    "publication_date": datetime.utcnow().isoformat(),
                    "scraped_at": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            logger.warning(f"Failed to scrape {source.url}: {e}")
            return None

    def _passes_content_filters(
        self, content: str, scraping_strategy: ScrapingStrategy
    ) -> bool:
        """
        Check if content passes the defined filters.

        Args:
            content: Content to check
            scraping_strategy: Strategy with filters

        Returns:
            True if content passes filters
        """
        content_lower = content.lower()

        # Check for required keywords
        if scraping_strategy.content_keywords:
            has_keywords = any(
                keyword.lower() in content_lower
                for keyword in scraping_strategy.content_keywords
            )
            if not has_keywords:
                return False

        # Check for quality indicators
        if scraping_strategy.quality_indicators:
            has_quality = any(
                indicator.lower() in content_lower
                for indicator in scraping_strategy.quality_indicators
            )
            if not has_quality:
                return False

        # Apply custom filters
        for filter_term in scraping_strategy.content_filters:
            if filter_term.lower() in content_lower:
                return False

        return True

    async def _discover_sources_from_query(
        self,
        query: str,
        scraping_strategy: ScrapingStrategy,
        research_request: ResearchRequest,
    ) -> List[WebSource]:
        """
        Discover additional sources using search queries.

        Args:
            query: Search query
            scraping_strategy: Current scraping strategy
            research_request: Research configuration

        Returns:
            List of discovered web sources
        """
        discovery_prompt = f"""
        For the search query "{query}" related to "{research_request.topic.name}",
        suggest 3-5 specific, real web sources that would likely contain relevant information.

        Consider:
        - Official websites and documentation
        - News sites with relevant coverage
        - Industry blogs and publications
        - Research institutions and academic sources

        Focus on sources that would have information from the {research_request.topic.time_range} timeframe.

        Respond with JSON:
        {{
            "sources": [
                {{
                    "url": "https://specific-real-url.com/relevant-section",
                    "domain": "specific-real-url.com",
                    "source_type": "news|blog|research|official|documentation",
                    "credibility_score": 0.8,
                    "relevance_score": 0.9,
                    "description": "Why this source is relevant for the query",
                    "priority": 3
                }}
            ]
        }}
        """

        try:
            response = await self.llm_client.generate_response(
                discovery_prompt, max_tokens=1500, temperature=0.6
            )

            data = json.loads(response.strip())
            return [WebSource(**source) for source in data.get("sources", [])]

        except Exception as e:
            logger.warning(f"Failed to discover sources for query '{query}': {e}")
            return []

    async def _organize_scraped_data(
        self, scraped_data: List[Dict[str, Any]], research_request: ResearchRequest
    ) -> ResearchData:
        """
        Organize scraped data into ResearchData structure.

        Args:
            scraped_data: List of scraped content items
            research_request: Research configuration

        Returns:
            Organized research data
        """
        # Organize by content type
        content_by_type = {
            "web_pages": [],
            "documents": [],
            "news_articles": [],
            "social_media": [],
        }

        total_content_length = 0
        data_sources = []

        for item in scraped_data:
            source_type = item.get("source_type", "web_pages")
            if source_type not in content_by_type:
                source_type = "web_pages"

            content_by_type[source_type].append(item)
            total_content_length += len(item.get("content", ""))
            data_sources.append(item.get("url", ""))

        # Calculate quality metrics
        source_diversity = min(1.0, len(set(data_sources)) / 10.0)
        content_freshness = 0.8  # Default for scraped content
        relevance_score = 0.7  # Default for scraped content

        return ResearchData(
            topic_name=research_request.topic.name,
            data_sources=data_sources,
            web_pages=content_by_type["web_pages"],
            documents=content_by_type["documents"],
            news_articles=content_by_type["news_articles"],
            social_media=content_by_type["social_media"],
            collection_method="web_scraping",
            collection_notes=f"Scraped from {len(scraped_data)} sources based on research strategy",
            total_content_length=total_content_length,
            source_diversity=source_diversity,
            content_freshness=content_freshness,
            relevance_score=relevance_score,
        )

    def _create_analysis_request(
        self, research_data: ResearchData, research_request: ResearchRequest
    ) -> AnalysisRequest:
        """
        Create analysis request with research context.

        Args:
            research_data: Collected research data
            research_request: Original research request

        Returns:
            Analysis request with context
        """
        # Create a mock configuration for analysis
        from ..models.research_config import (
            OutputSchema,
            PageSection,
            PageStructure,
            ResearchConfiguration,
            SectionType,
        )

        analysis_config = ResearchConfiguration(
            name=f"Analysis for {research_request.topic.name}",
            description=f"Analysis configuration for {research_request.topic.name}",
            research_request=research_request,
            output_schema=OutputSchema(
                output_format="notion_page",
                template="research_report",
                page_structure=PageStructure(
                    title_template=f"{research_request.topic.name} - {{date}}",
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
            research_data=research_data,
            analysis_config=analysis_config,
            analysis_focus=research_request.topic.focus_areas,
            output_requirements={
                "format": "notion_page",
                "include_summary": True,
                "include_insights": True,
                "include_recommendations": True,
            },
            include_confidence_scores=True,
            include_source_citations=True,
            group_similar_findings=True,
            trend_analysis=True,
            summary_length="detailed",
            include_quantitative_data=True,
            include_qualitative_insights=True,
        )

    async def _generate_analysis(
        self, analysis_request: AnalysisRequest
    ) -> AnalysisResult:
        """
        Generate analysis using the local analysis client logic.

        Args:
            analysis_request: Analysis request with research data and context

        Returns:
            Analysis result
        """
        # Reuse the logic from LocalAnalysisClient
        from .local_analysis_client import LocalAnalysisClient

        local_client = LocalAnalysisClient(self.llm_client)
        return await local_client.analyze_research_data(analysis_request)
