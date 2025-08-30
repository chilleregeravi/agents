"""
Web Scraping Agent - Complete workflow orchestrator.

This agent implements the complete research flow:
1. Research Request → Scrape internet by agent based on what sites should be scraped
2. Collect data by agent and provide to LLM with context of research request
3. LLM generates output based on the data
4. Send data to Notion
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from ..clients.llm_client import QwenLLMClient
from ..clients.notion_client import NotionClient
from ..clients.web_scraping_research_client import WebScrapingResearchClient
from ..config.config_loader import load_research_config
from ..config.settings import get_settings
from ..models.research_config import ResearchRequest, ResearchResult

logger = logging.getLogger(__name__)


class WebScrapingAgent:
    """
    Web Scraping Agent.

    This agent orchestrates the complete research workflow:
    - Generates scraping strategies based on research requests
    - Scrapes internet data from identified sources
    - Collects and organizes the data
    - Provides data to local LLM with research context
    - Generates analysis and insights
    - Publishes results to Notion
    """

    def __init__(self):
        """Initialize the web scraping agent."""
        self.execution_id = (
            f"web_scraping_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        self.execution_start_time: Optional[datetime] = None
        self.current_config: Optional[ResearchRequest] = None
        self.research_result: Optional[ResearchResult] = None

        # Component clients
        self.llm_client: Optional[QwenLLMClient] = None
        self.web_scraping_research_client: Optional[WebScrapingResearchClient] = None
        self.notion_client: Optional[NotionClient] = None

        logger.info(
            "Web Scraping Agent initialized",
            execution_id=self.execution_id,
        )

    async def execute_web_scraping_research(
        self, config_name: str, override_params: Optional[Dict[str, Any]] = None
    ) -> ResearchResult:
        """
        Execute complete web scraping research workflow.

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
            f"Starting web scraping research execution - config_name: {config_name}, execution_id: {self.execution_id}"
        )

        try:
            # Phase 1: Load and validate configuration
            await self._load_configuration(config_name, override_params)

            # Phase 2: Initialize components
            await self._initialize_components()

            # Phase 3: Execute web scraping research (scraping + analysis)
            self.research_result = await self._execute_web_scraping_research_phase()

            # Phase 4: Generate and publish report to Notion
            notion_result = await self._execute_publishing_phase()

            # Phase 5: Update result with Notion URL
            if notion_result:
                self.research_result.notion_page_url = notion_result

            logger.info(
                f"Web scraping research execution completed successfully - execution_id: {self.execution_id}, duration_seconds: {self.research_result.duration_seconds}, sources_analyzed: {self.research_result.sources_analyzed}, insights_generated: {self.research_result.insights_generated}"
            )

            return self.research_result

        except Exception as e:
            logger.error(
                f"Web scraping research execution failed - execution_id: {self.execution_id}, error: {str(e)}",
                exc_info=True,
            )

            raise AgentExecutionError(f"Research execution failed: {e}") from e

    async def _load_configuration(
        self, config_name: str, override_params: Optional[Dict[str, Any]]
    ) -> None:
        """Load and validate research configuration."""
        logger.info(f"Loading research configuration - config_name: {config_name}")

        try:
            # Load configuration from mounted files or environment
            config = load_research_config(config_name)
            self.current_config = config.research_request

            # Apply overrides if provided
            if override_params:
                self._apply_configuration_overrides(override_params)

            logger.info(
                f"Configuration loaded successfully - config_name: {config_name}, topic_name: {self.current_config.topic.name}"
            )

        except Exception as e:
            logger.error(f"Failed to load configuration: {str(e)}")
            raise AgentExecutionError(f"Configuration error: {e}")

    def _apply_configuration_overrides(self, override_params: Dict[str, Any]) -> None:
        """Apply parameter overrides to configuration."""
        if "max_sources" in override_params:
            self.current_config.search_strategy.max_sources = override_params[
                "max_sources"
            ]

        if "credibility_threshold" in override_params:
            threshold = override_params["credibility_threshold"]
            self.current_config.search_strategy.credibility_threshold = threshold

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
                    f"LLM client health check failed: "
                    f"{health_status.get('error', 'Unknown error')}"
                )
            logger.info("LLM client initialized successfully")
        except Exception as e:
            raise AgentExecutionError(f"Failed to initialize LLM client: {e}")

        # Initialize web scraping research client
        self.web_scraping_research_client = WebScrapingResearchClient(
            llm_client=self.llm_client
        )

        # Initialize Notion client
        notion_token = os.getenv("NOTION_TOKEN")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        if not notion_token:
            raise AgentExecutionError("Notion token not configured")

        self.notion_client = NotionClient(
            notion_token=notion_token, database_id=notion_database_id
        )

        logger.info("All components initialized successfully")

    async def _execute_web_scraping_research_phase(self) -> ResearchResult:
        """Execute web scraping research phase (scraping + analysis)."""
        logger.info("Starting web scraping research phase")

        try:
            async with self.web_scraping_research_client:
                result = await self.web_scraping_research_client.execute_web_scraping_research(
                    self.current_config
                )

            logger.info(
                f"Web scraping research phase completed successfully - sources_found: {result.sources_found}, sources_analyzed: {result.sources_analyzed}, insights_generated: {result.insights_generated}, quality_score: {result.quality_score}"
            )

            return result

        except Exception as e:
            raise AgentExecutionError(f"Web scraping research phase failed: {e}")

    async def _execute_publishing_phase(self) -> Optional[str]:
        """Execute publishing phase to Notion."""
        logger.info("Starting publishing phase")

        try:
            if not self.research_result:
                raise AgentExecutionError("No research result to publish")

            # Create Notion page from research result
            page_url = await self._create_notion_page()

            logger.info(
                f"Publishing phase completed successfully - page_url: {page_url}"
            )
            return page_url

        except Exception as e:
            raise AgentExecutionError(f"Publishing phase failed: {e}")

    async def _create_notion_page(self) -> str:
        """Create Notion page from research result."""
        if not self.research_result or not self.current_config:
            raise AgentExecutionError("Missing research result or configuration")

        # Create page title
        title = f"{self.current_config.topic.name} - {datetime.utcnow().strftime('%Y-%m-%d')}"

        # Create page content based on research result
        page_content = self._build_notion_page_content()

        # Create page in Notion
        page_url = await self.notion_client.create_page(
            title=title, content=page_content
        )

        return page_url

    def _build_notion_page_content(self) -> list:
        """Build Notion page content from research result."""
        if not self.research_result:
            return []

        content = []

        # Add execution summary
        summary_content = [
            f"**Research Topic**: {self.current_config.topic.name}",
            f"**Execution ID**: {self.research_result.execution_id}",
            f"**Status**: {self.research_result.status}",
            f"**Duration**: {self.research_result.duration_seconds:.2f} seconds",
            f"**Sources Found**: {self.research_result.sources_found}",
            f"**Sources Analyzed**: {self.research_result.sources_analyzed}",
            f"**Insights Generated**: {self.research_result.insights_generated}",
            f"**Quality Score**: {self.research_result.quality_score:.2f}",
        ]

        content.append(
            {"type": "callout", "content": "\n".join(summary_content), "icon": "📊"}
        )

        # Add research metadata
        if self.research_result.metadata:
            metadata_content = []
            for key, value in self.research_result.metadata.items():
                if isinstance(value, dict):
                    metadata_content.append(f"**{key}**: {len(value)} items")
                else:
                    metadata_content.append(f"**{key}**: {value}")

            content.append(
                {
                    "type": "text_block",
                    "title": "Research Metadata",
                    "content": "\n".join(metadata_content),
                }
            )

        # Add research topic details
        topic_content = [
            f"**Description**: {self.current_config.topic.description}",
            f"**Keywords**: {', '.join(self.current_config.topic.keywords)}",
            f"**Focus Areas**: {', '.join(self.current_config.topic.focus_areas)}",
            f"**Time Range**: {self.current_config.topic.time_range}",
            f"**Research Depth**: {self.current_config.topic.depth}",
        ]

        content.append(
            {
                "type": "text_block",
                "title": "Research Topic Details",
                "content": "\n".join(topic_content),
            }
        )

        # Add analysis instructions
        if self.current_config.analysis_instructions:
            content.append(
                {
                    "type": "text_block",
                    "title": "Analysis Instructions",
                    "content": self.current_config.analysis_instructions,
                }
            )

        return content

    def _create_execution_result(
        self, status: str, error_message: Optional[str] = None
    ) -> ResearchResult:
        """Create execution result for failed execution."""
        end_time = datetime.utcnow()
        duration = (
            (end_time - self.execution_start_time).total_seconds()
            if self.execution_start_time
            else 0.0
        )

        return ResearchResult(
            configuration_name=(
                self.current_config.topic.name if self.current_config else "unknown"
            ),
            execution_id=self.execution_id,
            status=status,
            started_at=self.execution_start_time or datetime.utcnow(),
            completed_at=end_time,
            duration_seconds=duration,
            sources_found=0,
            sources_analyzed=0,
            insights_generated=0,
            error_message=error_message,
            quality_score=0.0,
            metadata={
                "workflow_type": "web_scraping_research",
                "llm_model": "qwen-local",
                "error": error_message,
            },
        )


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails."""

    pass
