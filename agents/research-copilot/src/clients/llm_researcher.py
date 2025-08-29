"""
LLM-powered research client for autonomous web research.

This module implements a fully LLM-driven research approach that:
1. Uses LLM to identify relevant sources and search strategies
2. Performs intelligent web content analysis
3. Synthesizes findings autonomously without hardcoded APIs
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from ..models.research_config import ResearchRequest, SearchResult

logger = logging.getLogger(__name__)


class ResearchError(Exception):
    """Exception raised for research-related errors."""

    pass


class WebSource(BaseModel):
    """Represents a web source discovered by LLM."""

    url: str
    domain: str
    source_type: str  # "news", "blog", "research", "official", "documentation"
    credibility_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    description: str


class ResearchStrategy(BaseModel):
    """LLM-generated research strategy."""

    search_queries: List[str]
    target_sources: List[WebSource]
    content_keywords: List[str]
    quality_indicators: List[str]
    analysis_focus: str


class LLMResearcher:
    """
    Fully autonomous LLM-powered researcher.

    Uses LLM to:
    1. Generate research strategies
    2. Discover relevant web sources
    3. Extract and analyze content
    4. Synthesize findings
    """

    def __init__(self, llm_client, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize LLM researcher.

        Args:
            llm_client: LLM client for research orchestration
            session: Optional HTTP session for web requests
        """
        self.llm_client = llm_client
        self.session = session
        self._should_close_session = session is None

        # Research parameters
        self.max_sources_per_query = 10
        self.content_timeout = 30
        self.max_content_length = 50000  # Max content to analyze per page
        self.min_credibility_threshold = 0.6

        # User agent for web requests
        self.user_agent = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.content_timeout)
            headers = {"User-Agent": self.user_agent}
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._should_close_session and self.session:
            await self.session.close()

    async def conduct_research(
        self, research_request: ResearchRequest
    ) -> List[SearchResult]:
        """
        Conduct autonomous research based on the request.

        Args:
            research_request: Research configuration

        Returns:
            List of research results with analysis
        """
        logger.info(f"Starting LLM-driven research for: {research_request.topic.name}")

        # Phase 1: Generate research strategy
        strategy = await self._generate_research_strategy(research_request)
        logger.info(
            f"Generated strategy with {len(strategy.search_queries)} queries and {len(strategy.target_sources)} target sources"
        )

        # Phase 2: Discover and analyze web sources
        search_results = await self._discover_and_analyze_sources(
            strategy, research_request
        )
        logger.info(f"Discovered and analyzed {len(search_results)} sources")

        # Phase 3: Filter and rank results
        filtered_results = self._filter_and_rank_results(
            search_results, research_request
        )
        logger.info(f"Filtered to {len(filtered_results)} high-quality results")

        return filtered_results

    async def _generate_research_strategy(
        self, research_request: ResearchRequest
    ) -> ResearchStrategy:
        """Generate comprehensive research strategy using LLM."""
        strategy_prompt = f"""
        You are a research strategist tasked with creating a comprehensive research plan.

        Research Topic: {research_request.topic.name}
        Description: {research_request.topic.description}
        Keywords: {', '.join(research_request.topic.keywords)}
        Focus Areas: {', '.join(research_request.topic.focus_areas)}
        Time Range: {research_request.topic.time_range}
        Research Depth: {research_request.topic.depth}

        Analysis Instructions: {research_request.analysis_instructions}

        Generate a research strategy that includes:
        1. 8-12 diverse search queries to find relevant information
        2. 15-20 high-quality web sources likely to contain relevant information
        3. Key content keywords to look for in sources
        4. Quality indicators that suggest credible, authoritative content
        5. Analysis focus for this specific research topic

        For web sources, identify:
        - News sites (reuters.com, techcrunch.com, etc.)
        - Official company/organization sites
        - Research institutions and academic sources
        - Industry blogs and expert publications
        - Documentation and technical resources

        Consider the time range and focus on sources that would have recent, relevant information.

        Respond with valid JSON in this exact format:
        {{
            "search_queries": ["query1", "query2", ...],
            "target_sources": [
                {{
                    "url": "https://example.com",
                    "domain": "example.com",
                    "source_type": "news|blog|research|official|documentation",
                    "credibility_score": 0.8,
                    "relevance_score": 0.9,
                    "description": "Why this source is relevant"
                }}
            ],
            "content_keywords": ["keyword1", "keyword2", ...],
            "quality_indicators": ["peer reviewed", "official announcement", ...],
            "analysis_focus": "What to focus on when analyzing content"
        }}
        """

        try:
            response = await self.llm_client.generate_response(
                strategy_prompt, max_tokens=4000, temperature=0.7
            )

            # Parse JSON response
            strategy_data = json.loads(response.strip())

            # Convert to structured objects
            target_sources = [
                WebSource(**source)
                for source in strategy_data.get("target_sources", [])
            ]

            strategy = ResearchStrategy(
                search_queries=strategy_data.get("search_queries", []),
                target_sources=target_sources,
                content_keywords=strategy_data.get("content_keywords", []),
                quality_indicators=strategy_data.get("quality_indicators", []),
                analysis_focus=strategy_data.get("analysis_focus", "General analysis"),
            )

            return strategy

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM strategy response: {e}")
            # Fallback to basic strategy
            return self._create_fallback_strategy(research_request)

    def _create_fallback_strategy(
        self, research_request: ResearchRequest
    ) -> ResearchStrategy:
        """Create a basic fallback strategy if LLM generation fails."""
        topic_keywords = research_request.topic.keywords

        # Generate basic queries
        search_queries = [
            f"{research_request.topic.name} {research_request.topic.time_range}",
            f"{' '.join(topic_keywords[:3])} latest developments",
            f"{research_request.topic.name} announcements news",
        ]

        # Basic target sources
        target_sources = [
            WebSource(
                url="https://techcrunch.com",
                domain="techcrunch.com",
                source_type="news",
                credibility_score=0.8,
                relevance_score=0.7,
                description="Technology news and announcements",
            ),
            WebSource(
                url="https://www.reuters.com",
                domain="reuters.com",
                source_type="news",
                credibility_score=0.9,
                relevance_score=0.6,
                description="General news and business updates",
            ),
        ]

        return ResearchStrategy(
            search_queries=search_queries,
            target_sources=target_sources,
            content_keywords=topic_keywords,
            quality_indicators=[
                "official",
                "announcement",
                "research",
                "study",
            ],
            analysis_focus="General topic analysis",
        )

    async def _discover_and_analyze_sources(
        self, strategy: ResearchStrategy, research_request: ResearchRequest
    ) -> List[SearchResult]:
        """Discover web sources and analyze their content."""
        discovered_urls: Set[str] = set()
        search_results: List[SearchResult] = []

        # Start with target sources from strategy
        for web_source in strategy.target_sources:
            if web_source.url not in discovered_urls:
                discovered_urls.add(web_source.url)

                try:
                    result = await self._analyze_web_source(
                        web_source, strategy, research_request
                    )
                    if result:
                        search_results.append(result)
                except Exception as e:
                    logger.warning(f"Failed to analyze {web_source.url}: {e}")

        # Use LLM to discover additional sources based on queries
        for query in strategy.search_queries[:5]:  # Limit to avoid overload
            try:
                additional_sources = await self._discover_sources_from_query(
                    query, strategy, research_request
                )

                for source in additional_sources:
                    if source.url not in discovered_urls:
                        discovered_urls.add(source.url)
                        try:
                            result = await self._analyze_web_source(
                                source, strategy, research_request
                            )
                            if result:
                                search_results.append(result)
                        except Exception as e:
                            logger.warning(
                                f"Failed to analyze discovered source {source.url}: {e}"
                            )

            except Exception as e:
                logger.warning(f"Failed to discover sources for query '{query}': {e}")

        return search_results

    async def _discover_sources_from_query(
        self,
        query: str,
        strategy: ResearchStrategy,
        research_request: ResearchRequest,
    ) -> List[WebSource]:
        """Use LLM to suggest relevant web sources for a query."""
        discovery_prompt = f"""
        You are a web research expert. For the search query "{query}" related to the topic "{research_request.topic.name}",
        suggest 5-8 specific, real web sources that would likely contain relevant, up-to-date information.

        Consider:
        - Official websites and documentation
        - News sites with technology/business coverage
        - Industry blogs and publications
        - Research institutions and academic sources
        - Company blogs and announcement pages

        Focus on sources that would have information from the {research_request.topic.time_range} timeframe.

        Respond with valid JSON:
        {{
            "sources": [
                {{
                    "url": "https://specific-real-url.com/relevant-section",
                    "domain": "specific-real-url.com",
                    "source_type": "news|blog|research|official|documentation",
                    "credibility_score": 0.8,
                    "relevance_score": 0.9,
                    "description": "Why this specific source is relevant for the query"
                }}
            ]
        }}
        """

        try:
            response = await self.llm_client.generate_response(
                discovery_prompt, max_tokens=2000, temperature=0.6
            )

            data = json.loads(response.strip())
            return [WebSource(**source) for source in data.get("sources", [])]

        except Exception as e:
            logger.warning(f"Failed to discover sources for query '{query}': {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
    )
    async def _analyze_web_source(
        self,
        web_source: WebSource,
        strategy: ResearchStrategy,
        research_request: ResearchRequest,
    ) -> Optional[SearchResult]:
        """Analyze a specific web source for relevant content."""
        try:
            # Fetch content
            content = await self._fetch_web_content(web_source.url)
            if not content:
                return None

            # Use LLM to analyze content relevance and extract information
            analysis = await self._llm_analyze_content(
                content, web_source, strategy, research_request
            )

            if not analysis or analysis.get("relevance_score", 0) < 0.3:
                return None

            # Create SearchResult
            search_result = SearchResult(
                title=analysis.get("title", web_source.description),
                url=web_source.url,
                snippet=analysis.get("summary", "")[:500],
                source_type=web_source.source_type,
                credibility_score=web_source.credibility_score,
                relevance_score=analysis.get(
                    "relevance_score", web_source.relevance_score
                ),
                domain=web_source.domain,
                extracted_entities=analysis.get("entities", []),
                quality_score=None,  # Will be calculated later
            )

            # Add publication date if available
            if analysis.get("publication_date"):
                try:
                    search_result.publication_date = datetime.fromisoformat(
                        analysis["publication_date"].replace("Z", "+00:00")
                    )
                except Exception:
                    pass

            return search_result

        except Exception as e:
            logger.error(f"Failed to analyze web source {web_source.url}: {e}")
            return None

    async def _fetch_web_content(self, url: str) -> Optional[str]:
        """Fetch and clean web content."""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None

                html_content = await response.text()

                # Parse and clean HTML
                soup = BeautifulSoup(html_content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "aside"]):
                    script.decompose()

                # Get text content
                text_content = soup.get_text()

                # Clean up text
                lines = (line.strip() for line in text_content.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                text = " ".join(chunk for chunk in chunks if chunk)

                # Limit content length
                return text[: self.max_content_length]

        except Exception as e:
            logger.warning(f"Failed to fetch content from {url}: {e}")
            return None

    async def _llm_analyze_content(
        self,
        content: str,
        web_source: WebSource,
        strategy: ResearchStrategy,
        research_request: ResearchRequest,
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to analyze web content for relevance and extract key information."""
        analysis_prompt = f"""
        Analyze the following web content for relevance to the research topic.

        Research Topic: {research_request.topic.name}
        Research Focus: {strategy.analysis_focus}
        Target Keywords: {', '.join(strategy.content_keywords)}
        Quality Indicators: {', '.join(strategy.quality_indicators)}

        Web Source: {web_source.url} ({web_source.source_type})

        Content (first 8000 chars):
        {content[:8000]}

        Analyze and extract:
        1. Relevance score (0.0-1.0) - how relevant is this content to the research topic?
        2. Title - main title or headline
        3. Summary - 2-3 sentence summary of key points relevant to the research
        4. Key entities mentioned (people, companies, products, technologies)
        5. Publication date if identifiable (ISO format)
        6. Key insights that relate to the research topic

        Respond with valid JSON:
        {{
            "relevance_score": 0.8,
            "title": "Article title or main topic",
            "summary": "Key points summary",
            "entities": ["entity1", "entity2", ...],
            "publication_date": "2024-01-15T00:00:00Z",
            "key_insights": ["insight1", "insight2", ...]
        }}

        If the content is not relevant to the research topic, set relevance_score to 0.0.
        """

        try:
            response = await self.llm_client.generate_response(
                analysis_prompt, max_tokens=1500, temperature=0.3
            )

            return json.loads(response.strip())

        except Exception as e:
            logger.warning(f"Failed to analyze content from {web_source.url}: {e}")
            return None

    def _filter_and_rank_results(
        self,
        search_results: List[SearchResult],
        research_request: ResearchRequest,
    ) -> List[SearchResult]:
        """Filter and rank results based on quality and relevance."""
        # Filter by minimum thresholds
        filtered_results = [
            result
            for result in search_results
            if (
                result.relevance_score >= 0.4
                and result.credibility_score >= self.min_credibility_threshold
            )
        ]

        # Calculate quality scores
        for result in filtered_results:
            result.quality_score = (
                result.relevance_score * 0.6 + result.credibility_score * 0.4
            )

        # Sort by quality score
        filtered_results.sort(key=lambda x: x.quality_score, reverse=True)

        # Limit results based on research configuration
        max_results = research_request.search_strategy.max_sources
        return filtered_results[:max_results]
