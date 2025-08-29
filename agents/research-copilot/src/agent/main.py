"""Main agent orchestrator for Research Copilot."""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from ..clients.content_analyzer import ContentAnalyzer
from ..clients.llm_client import QwenLLMClient
from ..clients.llm_researcher import LLMResearcher
from ..clients.notion_client import NotionClient, format_research_data_for_notion
from ..config.config_loader import ConfigurationError, load_research_config
from ..config.settings import get_settings
from ..models.research_config import (
    AnalysisInsight,
    ResearchConfiguration,
    ResearchResult,
    SearchResult,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails."""

    pass


class ResearchCopilotAgent:
    """
    Main agent orchestrator for Research Copilot.

    Coordinates the entire research workflow from configuration loading
    to final report generation and publishing.
    """

    def __init__(self):
        """
        Initialize the Research Copilot Agent.

        Configuration is now loaded from environment variables and mounted files,
        eliminating the need for Kubernetes API client.
        """
        self.execution_id = str(uuid.uuid4())

        # Component instances (initialized during execution)
        self.llm_client: Optional[QwenLLMClient] = None
        self.llm_researcher: Optional[LLMResearcher] = None
        self.content_analyzer: Optional[ContentAnalyzer] = None
        self.notion_client: Optional[NotionClient] = None

        # Execution state
        self.current_config: Optional[ResearchConfiguration] = None
        self.execution_start_time: Optional[datetime] = None
        self.search_results: List[SearchResult] = []
        self.analysis_insights: List[AnalysisInsight] = []

        logger.info(
            "Research Copilot Agent initialized", execution_id=self.execution_id
        )

    async def execute_research(
        self, config_name: str, override_params: Optional[Dict[str, Any]] = None
    ) -> ResearchResult:
        """
        Execute complete research workflow.

        Args:
            config_name: Name of research configuration to use
            override_params: Optional parameters to override in config

        Returns:
            Research execution result

        Raises:
            AgentExecutionError: If research execution fails
        """
        self.execution_start_time = datetime.utcnow()

        logger.info(
            "Starting research execution",
            config_name=config_name,
            execution_id=self.execution_id,
        )

        try:
            # Phase 1: Load and validate configuration
            await self._load_configuration(config_name, override_params)

            # Phase 2: Initialize components
            await self._initialize_components()

            # Phase 3: Execute intelligent search
            await self._execute_search_phase()

            # Phase 4: Analyze content and generate insights
            await self._execute_analysis_phase()

            # Phase 5: Generate and publish report
            notion_result = await self._execute_publishing_phase()

            # Phase 6: Create execution result
            result = self._create_execution_result("completed", notion_result)

            logger.info(
                "Research execution completed successfully",
                execution_id=self.execution_id,
                duration_seconds=result.duration_seconds,
                sources_analyzed=result.sources_analyzed,
                insights_generated=result.insights_generated,
            )

            return result

        except Exception as e:
            logger.error(
                "Research execution failed",
                execution_id=self.execution_id,
                error=str(e),
                exc_info=True,
            )

            result = self._create_execution_result("failed", error_message=str(e))
            raise AgentExecutionError(f"Research execution failed: {e}") from e

    async def _load_configuration(
        self, config_name: str, override_params: Optional[Dict[str, Any]]
    ) -> None:
        """Load and validate research configuration."""
        logger.info("Loading research configuration", config_name=config_name)

        try:
            # Load configuration from mounted files or environment
            self.current_config = load_research_config(config_name)

            # Apply overrides if provided
            if override_params:
                self._apply_configuration_overrides(override_params)

            logger.info(
                "Configuration loaded successfully",
                config_name=config_name,
                topic_name=self.current_config.research_request.topic.name,
                search_depth=self.current_config.research_request.topic.depth,
                max_sources=self.current_config.research_request.search_strategy.max_sources,
            )

        except ConfigurationError as e:
            raise AgentExecutionError(
                f"Failed to load configuration '{config_name}': {e}"
            )
        except Exception as e:
            logger.error("Unexpected error loading configuration", error=str(e))
            raise AgentExecutionError(f"Unexpected configuration error: {e}")

    def _apply_configuration_overrides(self, override_params: Dict[str, Any]) -> None:
        """Apply parameter overrides to configuration."""
        logger.info("Applying configuration overrides", overrides=override_params)

        # Apply topic overrides
        if "topic_name" in override_params:
            self.current_config.research_request.topic.name = override_params[
                "topic_name"
            ]

        if "keywords" in override_params:
            self.current_config.research_request.topic.keywords = override_params[
                "keywords"
            ]

        if "focus_areas" in override_params:
            self.current_config.research_request.topic.focus_areas = override_params[
                "focus_areas"
            ]

        # Apply search strategy overrides
        if "max_sources" in override_params:
            self.current_config.research_request.search_strategy.max_sources = (
                override_params["max_sources"]
            )

        if "credibility_threshold" in override_params:
            threshold = override_params["credibility_threshold"]
            self.current_config.research_request.search_strategy.credibility_threshold = (
                threshold
            )

    async def _initialize_components(self) -> None:
        """Initialize all agent components."""
        logger.info("Initializing agent components")

        # Initialize LLM client
        settings = get_settings()
        self.llm_client = QwenLLMClient(settings)

        # Test LLM connection
        try:
            health_status = await self.llm_client.health_check()
            if health_status["status"] != "healthy":
                raise AgentExecutionError(
                    f"LLM client health check failed: {health_status.get('error', 'Unknown error')}"
                )
            logger.info("LLM client initialized successfully")
        except Exception as e:
            raise AgentExecutionError(f"Failed to initialize LLM client: {e}")

        # Initialize LLM researcher (no external API keys required)
        self.llm_researcher = LLMResearcher(llm_client=self.llm_client)

        # Initialize ConfigMap-driven content analyzer
        self.content_analyzer = ContentAnalyzer(llm_client=self.llm_client)

        # Initialize Notion client
        notion_token = os.getenv("NOTION_TOKEN")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        if not notion_token:
            raise AgentExecutionError("Notion token not configured")

        self.notion_client = NotionClient(
            notion_token=notion_token, database_id=notion_database_id
        )

        logger.info("All components initialized successfully")

    async def _execute_search_phase(self) -> None:
        """Execute LLM-driven research phase."""
        logger.info("Starting LLM-driven research phase")

        try:
            async with self.llm_researcher:
                self.search_results = await self.llm_researcher.conduct_research(
                    self.current_config.research_request
                )

            avg_credibility = (
                sum(r.credibility_score for r in self.search_results)
                / len(self.search_results)
                if self.search_results
                else 0
            )
            avg_relevance = (
                sum(r.relevance_score for r in self.search_results)
                / len(self.search_results)
                if self.search_results
                else 0
            )

            logger.info(
                "LLM research phase completed",
                total_results=len(self.search_results),
                avg_credibility=avg_credibility,
                avg_relevance=avg_relevance,
            )

            if not self.search_results:
                raise AgentExecutionError("No research results found")

        except Exception as e:
            raise AgentExecutionError(f"LLM research phase failed: {e}")

    async def _execute_analysis_phase(self) -> None:
        """Execute ConfigMap-driven content analysis phase."""
        logger.info("Starting ConfigMap-driven analysis phase")

        try:
            # Use ConfigMap-driven content analyzer to analyze search results
            self.analysis_insights = (
                await self.content_analyzer.analyze_research_results(
                    self.search_results, self.current_config.research_request
                )
            )

            avg_confidence = (
                sum(i.confidence_score for i in self.analysis_insights)
                / len(self.analysis_insights)
                if self.analysis_insights
                else 0
            )

            logger.info(
                "Analysis phase completed",
                total_insights=len(self.analysis_insights),
                avg_confidence=avg_confidence,
            )

            if not self.analysis_insights:
                logger.warning("No insights generated from analysis")

        except Exception as e:
            raise AgentExecutionError(f"Analysis phase failed: {e}")

    async def _execute_publishing_phase(self) -> Dict[str, Any]:
        """Execute report generation and publishing phase."""
        logger.info("Starting publishing phase")

        try:
            # Format research data for Notion
            research_data = format_research_data_for_notion(
                search_results=self.search_results,
                insights=self.analysis_insights,
                metadata={
                    "topic": {
                        "name": self.current_config.research_request.topic.name,
                        "description": self.current_config.research_request.topic.description,
                        "keywords": self.current_config.research_request.topic.keywords,
                        "focus_areas": self.current_config.research_request.topic.focus_areas,
                    },
                    "execution_id": self.execution_id,
                    "execution_date": self.execution_start_time.isoformat(),
                    "config_name": self.current_config.name,
                    "summary": await self._generate_executive_summary(),
                    "key_points": await self._extract_key_points(),
                },
            )

            # Create Notion page
            async with self.notion_client:
                notion_result = await self.notion_client.create_research_page(
                    output_schema=self.current_config.output_schema,
                    research_data=research_data,
                )

            logger.info(
                "Publishing phase completed",
                page_id=notion_result["page_id"],
                page_url=notion_result["url"],
            )

            return notion_result

        except Exception as e:
            raise AgentExecutionError(f"Publishing phase failed: {e}")

    async def _generate_executive_summary(self) -> str:
        """Generate executive summary using ConfigMap-driven approach."""
        if not self.analysis_insights:
            return "No insights available for summary generation."

        # Use the research instructions from ConfigMap to guide summary generation
        insights_text = "\n".join(
            [
                f"- {insight.title}: {insight.content}"
                for insight in self.analysis_insights[:10]  # Top 10 insights
            ]
        )

        focus_areas = ", ".join(self.current_config.research_request.topic.focus_areas)

        summary_prompt = f"""
        Based on the following research about "{self.current_config.research_request.topic.name}",
        generate a concise executive summary following the research instructions:

        Research Instructions:
        {self.current_config.research_request.analysis_instructions}

        Research Context:
        - Topic: {self.current_config.research_request.topic.name}
        - Description: {self.current_config.research_request.topic.description}
        - Focus Areas: {focus_areas}
        - Keywords: {', '.join(self.current_config.research_request.topic.keywords)}

        Key Insights:
        {insights_text}

        Generate a professional executive summary (200-300 words) that follows the research instructions
        and highlights the most important findings related to the specified focus areas and keywords.
        """

        try:
            summary = await self.llm_client.generate(
                summary_prompt, max_tokens=500, temperature=0.3
            )
            return summary.strip()
        except Exception as e:
            logger.warning(f"Failed to generate executive summary: {e}")
            insight_count = len(self.analysis_insights)
            topic_name = self.current_config.research_request.topic.name
            return f"Research on {topic_name} completed with {insight_count} key insights identified."

    async def _extract_key_points(self) -> List[str]:
        """Extract key points from research findings."""
        if not self.analysis_insights:
            return []

        # Sort insights by confidence and impact
        sorted_insights = sorted(
            self.analysis_insights,
            key=lambda x: (x.confidence_score, len(x.supporting_sources)),
            reverse=True,
        )

        key_points = []
        for insight in sorted_insights[:8]:  # Top 8 key points
            point = insight.title
            if insight.confidence_score > 0.8:
                point += " (High confidence)"
            key_points.append(point)

        return key_points

    def _create_execution_result(
        self,
        status: str,
        notion_result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> ResearchResult:
        """Create execution result summary."""
        completed_at = datetime.utcnow()
        duration = (
            (completed_at - self.execution_start_time).total_seconds()
            if self.execution_start_time
            else 0
        )

        # Calculate quality score
        quality_score = None
        if self.search_results and self.analysis_insights:
            avg_credibility = sum(
                r.credibility_score for r in self.search_results
            ) / len(self.search_results)
            avg_confidence = sum(
                i.confidence_score for i in self.analysis_insights
            ) / len(self.analysis_insights)
            quality_score = (avg_credibility + avg_confidence) / 2

        avg_credibility = (
            sum(r.credibility_score for r in self.search_results)
            / len(self.search_results)
            if self.search_results
            else 0
        )
        avg_relevance = (
            sum(r.relevance_score for r in self.search_results)
            / len(self.search_results)
            if self.search_results
            else 0
        )

        return ResearchResult(
            configuration_name=self.current_config.name
            if self.current_config
            else "unknown",
            execution_id=self.execution_id,
            status=status,
            started_at=self.execution_start_time or completed_at,
            completed_at=completed_at,
            duration_seconds=duration,
            sources_found=len(self.search_results),
            sources_analyzed=len(
                [r for r in self.search_results if r.credibility_score > 0.5]
            ),
            insights_generated=len(self.analysis_insights),
            notion_page_url=notion_result.get("url") if notion_result else None,
            error_message=error_message,
            quality_score=quality_score,
            metadata={
                "search_results_count": len(self.search_results),
                "insights_count": len(self.analysis_insights),
                "avg_credibility": avg_credibility,
                "avg_relevance": avg_relevance,
                "categories": list(set(i.category for i in self.analysis_insights))
                if self.analysis_insights
                else [],
            },
        )


# Utility functions for common operations
async def execute_research_workflow(
    config_name: str, override_params: Optional[Dict[str, Any]] = None
) -> ResearchResult:
    """
    Convenience function to execute complete research workflow.

    Args:
        config_name: Name of research configuration
        override_params: Optional parameter overrides

    Returns:
        Research execution result
    """
    agent = ResearchCopilotAgent()
    return await agent.execute_research(config_name, override_params)


# Main execution entry point
async def main():
    """Main entry point for agent execution."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.agent.main <config_name> [override_params_json]")
        sys.exit(1)

    config_name = sys.argv[1]
    override_params = None

    if len(sys.argv) > 2:
        import json

        try:
            override_params = json.loads(sys.argv[2])
        except json.JSONDecodeError as e:
            print(f"Invalid JSON for override parameters: {e}")
            sys.exit(1)

    try:
        result = await execute_research_workflow(
            config_name, override_params=override_params
        )
        print("Research completed successfully!")
        print(f"Execution ID: {result.execution_id}")
        print(f"Duration: {result.duration_seconds:.2f} seconds")
        print(f"Sources analyzed: {result.sources_analyzed}")
        print(f"Insights generated: {result.insights_generated}")
        if result.notion_page_url:
            print(f"Notion page: {result.notion_page_url}")

    except Exception as e:
        print(f"Research failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
