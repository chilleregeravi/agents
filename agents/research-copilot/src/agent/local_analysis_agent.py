"""
Local Analysis Agent for analyzing pre-collected research data.

This agent focuses on analyzing pre-collected research data using local LLM.
It does not perform internet research or data gathering.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from ..clients.llm_client import QwenLLMClient
from ..clients.local_analysis_client import LocalAnalysisClient
from ..clients.notion_client import NotionClient
from ..config.config_loader import load_research_config
from ..config.settings import get_settings
from ..models.research_config import (
    AnalysisRequest,
    PageSection,
    ResearchData,
    ResearchResult,
    SectionType,
)

logger = logging.getLogger(__name__)


class LocalAnalysisAgent:
    """
    Local Analysis Agent.

    This agent focuses on analyzing pre-collected research data using local LLM.
    It does not perform internet research or data gathering.
    """

    def __init__(self):
        """Initialize the local analysis agent."""
        self.execution_id = (
            f"local_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        self.execution_start_time: Optional[datetime] = None
        self.current_config: Optional[AnalysisRequest] = None
        self.research_result: Optional[ResearchResult] = None

        # Component clients
        self.llm_client: Optional[QwenLLMClient] = None
        self.local_analysis_client: Optional[LocalAnalysisClient] = None
        self.notion_client: Optional[NotionClient] = None

        logger.info(
            "Local Analysis Agent initialized",
            execution_id=self.execution_id,
        )

    async def execute_analysis(
        self,
        research_data: ResearchData,
        config_name: str,
        override_params: Optional[Dict[str, Any]] = None,
    ) -> ResearchResult:
        """
        Execute analysis workflow on pre-collected research data.

        Args:
            research_data: Pre-collected research data to analyze
            config_name: Name of research configuration to use
            override_params: Optional parameters to override in config

        Returns:
            Research execution result

        Raises:
            AgentExecutionError: If analysis execution fails
        """
        self.execution_start_time = datetime.utcnow()

        logger.info(
            f"Starting local analysis execution - config_name: {config_name}, execution_id: {self.execution_id}"
        )

        try:
            # Phase 1: Load and validate configuration
            await self._load_configuration(config_name, override_params)

            # Phase 2: Initialize components
            await self._initialize_components()

            # Phase 3: Create analysis request
            analysis_request = self._create_analysis_request(research_data)

            # Phase 4: Execute analysis phase
            analysis_result = await self._execute_analysis_phase(analysis_request)

            # Phase 5: Execute publishing phase
            notion_result = await self._execute_publishing_phase(analysis_result)

            # Phase 6: Create research result
            end_time = datetime.utcnow()
            duration = (end_time - self.execution_start_time).total_seconds()

            result = ResearchResult(
                configuration_name=config_name,
                execution_id=self.execution_id,
                status="completed",
                started_at=self.execution_start_time,
                completed_at=end_time,
                duration_seconds=duration,
                sources_found=len(research_data.data_sources),
                sources_analyzed=len(research_data.data_sources),
                insights_generated=len(analysis_result.key_insights),
                quality_score=analysis_result.analysis_confidence,
                notion_page_url=notion_result,
                metadata={
                    "workflow_type": "local_analysis",
                    "llm_model": "qwen-local",
                    "analysis_id": analysis_result.analysis_id,
                    "data_collection_method": research_data.collection_method,
                },
            )

            logger.info(
                f"Local analysis execution completed successfully - execution_id: {self.execution_id}, duration_seconds: {duration}, insights_generated: {len(analysis_result.key_insights)}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Local analysis execution failed - execution_id: {self.execution_id}, error: {str(e)}",
                exc_info=True,
            )

            result = self._create_execution_result("failed", error_message=str(e))
            raise AgentExecutionError(f"Analysis execution failed: {e}") from e

    async def _load_configuration(
        self, config_name: str, override_params: Optional[Dict[str, Any]]
    ) -> None:
        """Load and validate research configuration."""
        logger.info("Loading research configuration", config_name=config_name)

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

        # Initialize local analysis client
        self.local_analysis_client = LocalAnalysisClient(llm_client=self.llm_client)

        # Initialize Notion client
        notion_token = os.getenv("NOTION_TOKEN")
        notion_database_id = os.getenv("NOTION_DATABASE_ID")

        if not notion_token:
            raise AgentExecutionError("Notion token not configured")

        self.notion_client = NotionClient(
            notion_token=notion_token, database_id=notion_database_id
        )

        logger.info("All components initialized successfully")

    def _create_analysis_request(self, research_data: ResearchData) -> AnalysisRequest:
        """Create analysis request from research data and configuration."""
        from ..models.research_config import (
            OutputSchema,
            PageStructure,
            ResearchConfiguration,
        )

        analysis_config = ResearchConfiguration(
            name=f"Analysis for {research_data.topic_name}",
            description=f"Analysis configuration for {research_data.topic_name}",
            research_request=self.current_config,
            output_schema=OutputSchema(
                output_format="notion_page",
                template="research_report",
                page_structure=PageStructure(
                    title_template=f"{research_data.topic_name} - {{date}}",
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
            analysis_focus=self.current_config.topic.focus_areas,
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

    async def _execute_analysis_phase(self, analysis_request: AnalysisRequest) -> Any:
        """Execute analysis phase using local analysis client."""
        logger.info("Starting analysis phase")

        try:
            result = await self.local_analysis_client.analyze_research_data(
                analysis_request
            )

            logger.info(
                f"Analysis phase completed successfully - insights_count: {len(result.key_insights)}, confidence: {result.analysis_confidence}"
            )

            return result

        except Exception as e:
            raise AgentExecutionError(f"Analysis phase failed: {e}")

    async def _execute_publishing_phase(self, analysis_result: Any) -> Optional[str]:
        """Execute publishing phase to Notion."""
        logger.info("Starting publishing phase")

        try:
            # Create Notion page from analysis result
            page_url = await self._create_notion_page(analysis_result)

            logger.info(
                f"Publishing phase completed successfully - page_url: {page_url}"
            )
            return page_url

        except Exception as e:
            raise AgentExecutionError(f"Publishing phase failed: {e}")

    async def _create_notion_page(self, analysis_result: Any) -> str:
        """Create Notion page from analysis result."""
        if not analysis_result or not self.current_config:
            raise AgentExecutionError("Missing analysis result or configuration")

        # Create page title
        title = f"{self.current_config.topic.name} - {datetime.utcnow().strftime('%Y-%m-%d')}"

        # Create page content based on analysis result
        page_content = self._build_notion_page_content(analysis_result)

        # Create page in Notion
        page_url = await self.notion_client.create_page(
            title=title, content=page_content
        )

        return page_url

    def _build_notion_page_content(self, analysis_result: Any) -> list:
        """Build Notion page content from analysis result."""
        if not analysis_result:
            return []

        content = []

        # Add execution summary
        summary_content = [
            f"**Research Topic**: {self.current_config.topic.name}",
            f"**Execution ID**: {self.execution_id}",
            "**Status**: completed",
            f"**Duration**: {analysis_result.processing_time_seconds:.2f} seconds",
            f"**Insights Generated**: {len(analysis_result.key_insights)}",
            f"**Analysis Confidence**: {analysis_result.analysis_confidence:.2f}",
        ]

        content.append(
            {"type": "callout", "content": "\n".join(summary_content), "icon": "📊"}
        )

        # Add executive summary
        if analysis_result.executive_summary:
            content.append(
                {
                    "type": "text_block",
                    "title": "Executive Summary",
                    "content": analysis_result.executive_summary,
                }
            )

        # Add key insights
        if analysis_result.key_insights:
            insights_content = []
            for insight in analysis_result.key_insights[:10]:  # Top 10 insights
                insights_content.append(
                    f"**{insight.title}** (Confidence: {insight.confidence_score:.2f})\n"
                    f"{insight.description}"
                )

            content.append(
                {
                    "type": "text_block",
                    "title": "Key Insights",
                    "content": "\n\n".join(insights_content),
                }
            )

        # Add trend analysis
        if analysis_result.trend_analysis:
            content.append(
                {
                    "type": "text_block",
                    "title": "Trend Analysis",
                    "content": str(analysis_result.trend_analysis),
                }
            )

        # Add quantitative findings
        if analysis_result.quantitative_findings:
            quantitative_content = []
            for finding in analysis_result.quantitative_findings[:5]:  # Top 5 findings
                quantitative_content.append(
                    f"**{finding.get('metric', 'Unknown')}**: "
                    f"{finding.get('value', 'N/A')} {finding.get('unit', '')}"
                )

            content.append(
                {
                    "type": "text_block",
                    "title": "Quantitative Findings",
                    "content": "\n".join(quantitative_content),
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
                "workflow_type": "local_analysis",
                "llm_model": "qwen-local",
                "error": error_message,
            },
        )


class AgentExecutionError(Exception):
    """Exception raised when agent execution fails."""

    pass
