"""
Local Analysis Client for analyzing pre-collected research data.

This module implements the "Analysis & Synthesis Phase" of the research workflow.
It takes pre-collected ResearchData and uses the local LLM to generate insights,
trends, quantitative findings, and an executive summary.
"""


import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.research_config import (
    AnalysisInsight,
    AnalysisRequest,
    AnalysisResult,
    ResearchData,
)

logger = logging.getLogger(__name__)


class LocalAnalysisError(Exception):
    """Exception raised when local analysis fails."""

    pass


class LocalAnalysisClient:
    """
    Client for local analysis of pre-collected research data.

    This client handles:
    1. Analysis of pre-collected research data
    2. Generation of insights and summaries
    3. Synthesis of findings
    4. Output generation in various formats

    It does NOT handle:
    - Web scraping or data collection
    - External API calls for research
    - Real-time information gathering
    """

    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.analysis_id_counter = 0

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    async def analyze_research_data(
        self, analysis_request: AnalysisRequest
    ) -> AnalysisResult:
        """
        Analyze pre-collected research data using local LLM.

        Args:
            analysis_request: Request containing research data and analysis config

        Returns:
            Analysis result with insights, trends, and summary

        Raises:
            LocalAnalysisError: If analysis fails
        """
        start_time = datetime.utcnow()
        analysis_id = f"local_analysis_{self.analysis_id_counter:06d}"
        self.analysis_id_counter += 1

        logger.info(f"Starting local analysis: {analysis_id}")

        try:
            # Phase 1: Preprocess research data
            processed_data = await self._preprocess_research_data(
                analysis_request.research_data
            )

            # Phase 2: Generate insights from content
            insights = await self._generate_insights(processed_data, analysis_request)

            # Phase 3: Analyze trends across content
            trend_analysis = None
            if analysis_request.trend_analysis:
                trend_analysis = await self._analyze_trends(
                    processed_data, analysis_request
                )

            # Phase 4: Extract quantitative data
            quantitative_findings = []
            if analysis_request.include_quantitative_data:
                quantitative_findings = await self._extract_quantitative_data(
                    processed_data, analysis_request
                )

            # Phase 5: Generate executive summary
            executive_summary = await self._generate_executive_summary(
                insights, trend_analysis, quantitative_findings, analysis_request
            )

            # Phase 6: Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                insights, processed_data, analysis_request
            )

            # Phase 7: Create analysis result
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            result = AnalysisResult(
                analysis_id=analysis_id,
                analysis_request=analysis_request,
                completed_at=end_time,
                executive_summary=executive_summary,
                key_insights=insights,
                trend_analysis=trend_analysis,
                quantitative_findings=quantitative_findings,
                analysis_confidence=quality_metrics["confidence"],
                coverage_score=quality_metrics["coverage"],
                insight_quality=quality_metrics["quality"],
                processing_time_seconds=duration,
                llm_model_used="qwen-local",
                analysis_notes=f"Local analysis completed in {duration:.2f}s",
            )

            logger.info(
                f"Local analysis completed: {analysis_id} - insights_count: {len(insights)}, duration: {duration}, confidence: {quality_metrics['confidence']}"
            )

            return result

        except Exception as e:
            logger.error(f"Local analysis failed: {e}", exc_info=True)
            raise LocalAnalysisError(f"Analysis failed: {e}") from e

    async def _preprocess_research_data(
        self, research_data: ResearchData
    ) -> Dict[str, Any]:
        """
        Preprocess research data for analysis.

        Args:
            research_data: Raw research data

        Returns:
            Processed data ready for analysis
        """
        processed = {
            "topic_name": research_data.topic_name,
            "total_content_length": research_data.total_content_length,
            "source_diversity": research_data.source_diversity,
            "content_freshness": research_data.content_freshness,
            "relevance_score": research_data.relevance_score,
            "content_by_type": {
                "web_pages": research_data.web_pages,
                "documents": research_data.documents,
                "news_articles": research_data.news_articles,
                "social_media": research_data.social_media,
            },
            "metadata": {
                "collection_method": research_data.collection_method,
                "collection_notes": research_data.collection_notes,
                "collected_at": research_data.collected_at.isoformat(),
            },
        }

        return processed

    async def _generate_insights(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> List[AnalysisInsight]:
        """
        Generate insights from processed research data.

        Args:
            processed_data: Preprocessed research data
            analysis_request: Analysis configuration

        Returns:
            List of generated insights
        """
        insights = []

        # Analyze each content type
        for content_type, content_items in processed_data["content_by_type"].items():
            if content_items:
                content_insights = await self._analyze_content_type(
                    content_type, content_items, analysis_request
                )
                insights.extend(content_insights)

        # Generate cross-content insights
        cross_content_insights = await self._generate_cross_content_insights(
            processed_data, analysis_request
        )
        insights.extend(cross_content_insights)

        # Filter and rank insights
        filtered_insights = self._filter_and_rank_insights(insights, analysis_request)

        return filtered_insights

    async def _analyze_content_type(
        self,
        content_type: str,
        content_items: List[Dict[str, Any]],
        analysis_request: AnalysisRequest,
    ) -> List[AnalysisInsight]:
        """
        Analyze a specific content type.

        Args:
            content_type: Type of content (web_pages, documents, etc.)
            content_items: List of content items
            analysis_request: Analysis configuration

        Returns:
            List of insights from this content type
        """
        insights = []

        # Process content in batches
        batch_size = 5
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i : i + batch_size]

            batch_insights = await self._analyze_content_batch(
                content_type, batch, analysis_request
            )
            insights.extend(batch_insights)

        return insights

    async def _analyze_content_batch(
        self,
        content_type: str,
        content_batch: List[Dict[str, Any]],
        analysis_request: AnalysisRequest,
    ) -> List[AnalysisInsight]:
        """
        Analyze a batch of content items.

        Args:
            content_type: Type of content
            content_batch: Batch of content items
            analysis_request: Analysis configuration

        Returns:
            List of insights from this batch
        """
        prompt = self._construct_content_analysis_prompt(
            content_type, content_batch, analysis_request
        )

        try:
            response = await self.llm_client.generate_response(
                prompt, max_tokens=2000, temperature=0.3
            )

            # Parse insights from response
            insights_data = json.loads(response.strip())
            insights = []

            for insight_data in insights_data.get("insights", []):
                insight = AnalysisInsight(
                    insight_id=f"insight_{len(insights):03d}",
                    title=insight_data.get("title", ""),
                    description=insight_data.get("description", ""),
                    category=insight_data.get("category", "general"),
                    confidence_score=insight_data.get("confidence", 0.7),
                    source_references=insight_data.get("sources", []),
                    impact_level=insight_data.get("impact", "medium"),
                    supporting_evidence=insight_data.get("evidence", ""),
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.warning(f"Failed to analyze content batch: {e}")
            return []

    def _construct_content_analysis_prompt(
        self,
        content_type: str,
        content_batch: List[Dict[str, Any]],
        analysis_request: AnalysisRequest,
    ) -> str:
        """Construct prompt for content analysis."""
        prompt_parts = [
            f"Analyze the following {content_type} content and extract key insights.",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {analysis_request.research_data.topic_name}",
            f"Focus Areas: {', '.join(analysis_request.analysis_focus)}",
            f"Analysis Instructions: {analysis_request.analysis_config.research_request.analysis_instructions}",
            "",
            "CONTENT TO ANALYZE:",
        ]

        for i, item in enumerate(content_batch):
            prompt_parts.extend(
                [
                    f"Item {i+1}:",
                    f"Title: {item.get('title', 'N/A')}",
                    f"Source: {item.get('url', 'N/A')}",
                    f"Content: {item.get('content', '')[:1000]}...",
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "Generate insights in JSON format:",
                "{",
                '  "insights": [',
                "    {",
                '      "title": "Insight title",',
                '      "description": "Detailed description",',
                '      "category": "trend|finding|recommendation|observation",',
                '      "confidence": 0.8,',
                '      "sources": ["source1", "source2"],',
                '      "impact": "high|medium|low",',
                '      "evidence": "Supporting evidence from content"',
                "    }",
                "  ]",
                "}",
                "",
                "Focus on insights that are relevant to the research topic and analysis focus.",
            ]
        )

        return "\n".join(prompt_parts)

    async def _generate_cross_content_insights(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> List[AnalysisInsight]:
        """
        Generate insights that span across different content types.

        Args:
            processed_data: Processed research data
            analysis_request: Analysis configuration

        Returns:
            List of cross-content insights
        """
        prompt = self._construct_cross_content_prompt(processed_data, analysis_request)

        try:
            response = await self.llm_client.generate_response(
                prompt, max_tokens=1500, temperature=0.4
            )

            insights_data = json.loads(response.strip())
            insights = []

            for insight_data in insights_data.get("cross_content_insights", []):
                insight = AnalysisInsight(
                    insight_id=f"cross_insight_{len(insights):03d}",
                    title=insight_data.get("title", ""),
                    description=insight_data.get("description", ""),
                    category="cross_content",
                    confidence_score=insight_data.get("confidence", 0.7),
                    source_references=insight_data.get("sources", []),
                    impact_level=insight_data.get("impact", "medium"),
                    supporting_evidence=insight_data.get("evidence", ""),
                )
                insights.append(insight)

            return insights

        except Exception as e:
            logger.warning(f"Failed to generate cross-content insights: {e}")
            return []

    def _construct_cross_content_prompt(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> str:
        """Construct prompt for cross-content analysis."""
        content_summary = []
        for content_type, items in processed_data["content_by_type"].items():
            if items:
                content_summary.append(f"- {content_type}: {len(items)} items")

        prompt_parts = [
            "Analyze patterns and insights that span across different content types.",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {analysis_request.research_data.topic_name}",
            f"Focus Areas: {', '.join(analysis_request.analysis_focus)}",
            "",
            "CONTENT SUMMARY:",
            "\n".join(content_summary),
            "",
            "Generate cross-content insights in JSON format:",
            "{",
            '  "cross_content_insights": [',
            "    {",
            '      "title": "Cross-content insight title",',
            '      "description": "Description spanning multiple content types",',
            '      "confidence": 0.8,',
            '      "sources": ["source1", "source2"],',
            '      "impact": "high|medium|low",',
            '      "evidence": "Evidence from multiple content types"',
            "    }",
            "  ]",
            "}",
            "",
            "Focus on patterns, trends, and insights that emerge when considering all content types together.",
        ]

        return "\n".join(prompt_parts)

    def _filter_and_rank_insights(
        self, insights: List[AnalysisInsight], analysis_request: AnalysisRequest
    ) -> List[AnalysisInsight]:
        """
        Filter and rank insights based on quality and relevance.

        Args:
            insights: List of all generated insights
            analysis_request: Analysis configuration

        Returns:
            Filtered and ranked insights
        """
        # Filter by confidence threshold
        min_confidence = 0.5
        filtered_insights = [
            insight
            for insight in insights
            if insight.confidence_score >= min_confidence
        ]

        # Sort by confidence and impact
        filtered_insights.sort(
            key=lambda x: (x.confidence_score, self._impact_score(x.impact_level)),
            reverse=True,
        )

        # Limit number of insights
        max_insights = 20
        return filtered_insights[:max_insights]

    def _impact_score(self, impact_level: str) -> float:
        """Convert impact level to numeric score."""
        impact_scores = {"high": 3.0, "medium": 2.0, "low": 1.0}
        return impact_scores.get(impact_level.lower(), 1.0)

    async def _analyze_trends(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze trends in the research data.

        Args:
            processed_data: Processed research data
            analysis_request: Analysis configuration

        Returns:
            Trend analysis results or None
        """
        prompt = self._construct_trend_analysis_prompt(processed_data, analysis_request)

        try:
            response = await self.llm_client.generate_response(
                prompt, max_tokens=1000, temperature=0.3
            )

            trend_data = json.loads(response.strip())
            return trend_data

        except Exception as e:
            logger.warning(f"Failed to analyze trends: {e}")
            return None

    def _construct_trend_analysis_prompt(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> str:
        """Construct prompt for trend analysis."""
        prompt_parts = [
            "Analyze trends in the research data.",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {analysis_request.research_data.topic_name}",
            f"Focus Areas: {', '.join(analysis_request.analysis_focus)}",
            "",
            "DATA METRICS:",
            f"Total Content Length: {processed_data['total_content_length']}",
            f"Source Diversity: {processed_data['source_diversity']:.2f}",
            f"Content Freshness: {processed_data['content_freshness']:.2f}",
            f"Relevance Score: {processed_data['relevance_score']:.2f}",
            "",
            "Generate trend analysis in JSON format:",
            "{",
            '  "trends": [',
            "    {",
            '      "trend_name": "Trend description",',
            '      "direction": "increasing|decreasing|stable",',
            '      "confidence": 0.8,',
            '      "evidence": "Supporting evidence"',
            "    }",
            "  ],",
            '  "summary": "Overall trend summary"',
            "}",
        ]

        return "\n".join(prompt_parts)

    async def _extract_quantitative_data(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> List[Dict[str, Any]]:
        """
        Extract quantitative data from research content.

        Args:
            processed_data: Processed research data
            analysis_request: Analysis configuration

        Returns:
            List of quantitative findings
        """
        prompt = self._construct_quantitative_analysis_prompt(
            processed_data, analysis_request
        )

        try:
            response = await self.llm_client.generate_response(
                prompt, max_tokens=1000, temperature=0.2
            )

            quantitative_data = json.loads(response.strip())
            return quantitative_data.get("quantitative_findings", [])

        except Exception as e:
            logger.warning(f"Failed to extract quantitative data: {e}")
            return []

    def _construct_quantitative_analysis_prompt(
        self, processed_data: Dict[str, Any], analysis_request: AnalysisRequest
    ) -> str:
        """Construct prompt for quantitative analysis."""
        prompt_parts = [
            "Extract quantitative data and statistics from the research content.",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {analysis_request.research_data.topic_name}",
            f"Focus Areas: {', '.join(analysis_request.analysis_focus)}",
            "",
            "Generate quantitative findings in JSON format:",
            "{",
            '  "quantitative_findings": [',
            "    {",
            '      "metric": "Metric name",',
            '      "value": "Numeric value or range",',
            '      "unit": "Unit of measurement",',
            '      "source": "Source of the data",',
            '      "confidence": 0.8',
            "    }",
            "  ]",
            "}",
            "",
            "Focus on numbers, percentages, statistics, and measurable data points.",
        ]

        return "\n".join(prompt_parts)

    async def _generate_executive_summary(
        self,
        insights: List[AnalysisInsight],
        trend_analysis: Optional[Dict[str, Any]],
        quantitative_findings: List[Dict[str, Any]],
        analysis_request: AnalysisRequest,
    ) -> str:
        """
        Generate executive summary from analysis results.

        Args:
            insights: Generated insights
            trend_analysis: Trend analysis results
            quantitative_findings: Quantitative data
            analysis_request: Analysis configuration

        Returns:
            Executive summary text
        """
        prompt = self._construct_executive_summary_prompt(
            insights, trend_analysis, quantitative_findings, analysis_request
        )

        try:
            response = await self.llm_client.generate_response(
                prompt, max_tokens=1500, temperature=0.3
            )

            return response.strip()

        except Exception as e:
            logger.warning(f"Failed to generate executive summary: {e}")
            return "Executive summary generation failed."

    def _construct_executive_summary_prompt(
        self,
        insights: List[AnalysisInsight],
        trend_analysis: Optional[Dict[str, Any]],
        quantitative_findings: List[Dict[str, Any]],
        analysis_request: AnalysisRequest,
    ) -> str:
        """Construct prompt for executive summary generation."""
        # Prepare insights summary
        insights_summary = []
        for insight in insights[:5]:  # Top 5 insights
            insights_summary.append(f"- {insight.title}: {insight.description}")

        # Prepare quantitative summary
        quantitative_summary = []
        for finding in quantitative_findings[:3]:  # Top 3 findings
            quantitative_summary.append(
                f"- {finding.get('metric', 'Unknown')}: {finding.get('value', 'N/A')} "
                f"{finding.get('unit', '')}"
            )

        prompt_parts = [
            f"Generate an executive summary for research on: {analysis_request.research_data.topic_name}",
            "",
            "ANALYSIS CONTEXT:",
            f"Focus Areas: {', '.join(analysis_request.analysis_focus)}",
            f"Summary Length: {analysis_request.summary_length}",
            "",
            "KEY INSIGHTS:",
            "\n".join(insights_summary),
            "",
            "QUANTITATIVE FINDINGS:",
            "\n".join(quantitative_summary),
            "",
            "TREND ANALYSIS:",
            trend_analysis.get("summary", "No trend analysis available")
            if trend_analysis
            else "No trend analysis available",
            "",
            "Generate a comprehensive executive summary that synthesizes the key findings, "
            "trends, and quantitative data into actionable insights for decision-makers.",
        ]

        return "\n".join(prompt_parts)

    def _calculate_quality_metrics(
        self,
        insights: List[AnalysisInsight],
        processed_data: Dict[str, Any],
        analysis_request: AnalysisRequest,
    ) -> Dict[str, float]:
        """
        Calculate quality metrics for the analysis.

        Args:
            insights: Generated insights
            processed_data: Processed research data
            analysis_request: Analysis configuration

        Returns:
            Dictionary of quality metrics
        """
        # Calculate confidence (average of insight confidences)
        if insights:
            confidence = sum(insight.confidence_score for insight in insights) / len(
                insights
            )
        else:
            confidence = 0.0

        # Calculate coverage (based on content diversity and amount)
        coverage = min(
            1.0,
            processed_data["source_diversity"] * 0.7
            + min(processed_data["total_content_length"] / 10000, 0.3),
        )

        # Calculate quality (based on insight count and relevance)
        quality = min(
            1.0, len(insights) / 10.0 * 0.6 + processed_data["relevance_score"] * 0.4
        )

        return {"confidence": confidence, "coverage": coverage, "quality": quality}
