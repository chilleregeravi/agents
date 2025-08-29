"""
ConfigMap-driven content analyzer that uses research instructions from ConfigMaps.

This module provides truly dynamic content analysis where prompts, analysis approaches,
and output formats are all driven by ConfigMap configuration rather than hardcoded logic.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from ..models.research_config import AnalysisInsight, ResearchRequest, SearchResult

logger = logging.getLogger(__name__)


class ContentAnalysisError(Exception):
    """Exception raised when content analysis fails."""

    pass


class ContentAnalyzer:
    """
    Content analyzer that uses ConfigMap research instructions and requirements.

    This analyzer constructs prompts dynamically based on:
    1. Research instructions from ConfigMap
    2. Research topic and context from ConfigMap
    3. Focus areas and keywords from ConfigMap
    4. No hardcoded prompts or analysis patterns
    """

    def __init__(self, llm_client):
        """
        Initialize ConfigMap-driven content analyzer.

        Args:
            llm_client: LLM client for content analysis
        """
        self.llm_client = llm_client

    async def analyze_research_results(
        self,
        search_results: List[SearchResult],
        research_request: ResearchRequest,
    ) -> List[AnalysisInsight]:
        """
        Analyze search results using ConfigMap-driven approach.

        Args:
            search_results: List of search results to analyze
            research_request: Research configuration with analysis instructions

        Returns:
            List of analysis insights
        """
        logger.info(
            f"Starting ConfigMap-driven analysis of {len(search_results)} results"
        )

        analysis_insights = []

        # Process results in batches to avoid overwhelming the system
        batch_size = 3
        for i in range(0, len(search_results), batch_size):
            batch = search_results[i : i + batch_size]

            # Process batch concurrently
            tasks = [
                self._analyze_single_result(result, research_request)
                for result in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out exceptions and add successful results
            for result in batch_results:
                if isinstance(result, AnalysisInsight):
                    analysis_insights.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Analysis failed: {result}")

            # Small delay between batches
            await asyncio.sleep(0.5)

        logger.info(
            f"Successfully analyzed {len(analysis_insights)} insights "
            f"from {len(search_results)} results"
        )
        return analysis_insights

    async def _analyze_single_result(
        self, search_result: SearchResult, research_request: ResearchRequest
    ) -> Optional[AnalysisInsight]:
        """
        Analyze a single search result using ConfigMap instructions.

        Args:
            search_result: Search result to analyze
            research_request: Research configuration with analysis instructions

        Returns:
            Analysis insight or None if analysis fails
        """
        try:
            # Fetch full content if we only have a snippet
            full_content = await self._fetch_full_content(search_result)

            # Use ConfigMap-driven LLM analysis
            insight = await self._llm_analyze_content(
                full_content, search_result, research_request
            )

            return insight

        except Exception as e:
            logger.error(f"Failed to analyze {search_result.url}: {e}")
            return None

    async def _fetch_full_content(self, search_result: SearchResult) -> str:
        """
        Fetch full content from search result URL.

        Args:
            search_result: Search result with URL to fetch

        Returns:
            Full content text
        """
        # If we already have substantial content, use it
        if len(search_result.snippet) > 500:
            return search_result.snippet

        # Otherwise, use the snippet we have
        # In a full implementation, this would fetch and parse the full page
        return search_result.snippet

    def _construct_analysis_prompt(
        self,
        content: str,
        search_result: SearchResult,
        research_request: ResearchRequest,
    ) -> str:
        """
        Construct analysis prompt dynamically from ConfigMap research instructions.

        This method builds prompts entirely from ConfigMap data without hardcoded templates.
        """
        # Base prompt using research context from ConfigMap
        prompt_parts = [
            f"You are a research analyst specializing in {research_request.topic.name}.",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {research_request.topic.name}",
            f"Description: {research_request.topic.description}",
            f"Keywords: {', '.join(research_request.topic.keywords)}",
            f"Focus Areas: {', '.join(research_request.topic.focus_areas)}",
            f"Research Depth: {research_request.topic.depth}",
            f"Time Range: {research_request.topic.time_range}",
            "",
            "ANALYSIS INSTRUCTIONS:",
            research_request.analysis_instructions,  # Direct from ConfigMap
            "",
            "SOURCE INFORMATION:",
            f"- URL: {search_result.url}",
            f"- Title: {search_result.title}",
            f"- Domain: {search_result.domain}",
            f"- Source Type: {search_result.source_type}",
            f"- Publication Date: {search_result.publication_date}",
            f"- Credibility Score: {search_result.credibility_score}",
            f"- Relevance Score: {search_result.relevance_score}",
            "",
            "CONTENT TO ANALYZE:",
            content[:6000],  # Limit content length for LLM
            "",
        ]

        # Dynamic JSON schema based on research requirements
        json_schema = self._construct_dynamic_json_schema(research_request)
        prompt_parts.extend(
            [
                "Provide your analysis in the following JSON format:",
                json_schema,
                "",
                "ANALYSIS GUIDELINES:",
                "1. Follow the research instructions exactly as specified above",
                f"2. Focus specifically on: {', '.join(research_request.topic.focus_areas)}",
                f"3. Pay attention to keywords: {', '.join(research_request.topic.keywords)}",
                "4. Assess credibility based on source authority and evidence quality",
                "5. Provide specific, actionable insights related to the research topic",
                "6. If content is not relevant to the research topic, set relevance scores to 0.0",
                "",
                f"Remember: This analysis should directly address '{research_request.topic.name}' "
                f"according to the provided research instructions.",
            ]
        )

        return "\n".join(prompt_parts)

    def _construct_dynamic_json_schema(self, research_request: ResearchRequest) -> str:
        """
        Construct JSON schema dynamically based on research requirements from ConfigMap.

        This creates output format based on ConfigMap specifications rather than hardcoded schemas.
        """
        # Base schema fields
        schema = {
            "title": "Brief descriptive title for this insight",
            "content": "Detailed analysis following the research instructions",
            "confidence_score": "Number between 0.0-1.0 indicating analysis confidence",
            "relevance_to_topic": "Number between 0.0-1.0 indicating relevance to research topic",
            "significance": "high|medium|low based on impact assessment",
        }

        # Add fields based on research focus areas from ConfigMap
        if research_request.topic.focus_areas:
            schema["focus_area_insights"] = {
                area.replace(" ", "_").lower(): f"Specific insights related to {area}"
                for area in research_request.topic.focus_areas
            }

        # Add fields based on keywords from ConfigMap
        if research_request.topic.keywords:
            schema["keyword_relevance"] = {
                keyword.replace(
                    " ", "_"
                ).lower(): f"How this content relates to {keyword} (0.0-1.0)"
                for keyword in research_request.topic.keywords[:5]  # Limit to top 5
            }

        # Add research-specific fields based on topic characteristics
        schema.update(
            {
                "key_entities": "Array of key entities, people, organizations mentioned",
                "actionable_insights": "Array of specific actionable insights",
                "supporting_evidence": "Array of specific evidence supporting the analysis",
                "implications": f"What this means for {research_request.topic.name}",
                "temporal_context": "When this information is relevant or applicable",
                "credibility_assessment": (
                    "Assessment of source credibility and information reliability"
                ),
            }
        )

        # Format as JSON schema string
        formatted_schema = "{\n"
        for key, description in schema.items():
            if isinstance(description, dict):
                formatted_schema += f'  "{key}": {json.dumps(description, indent=2)},\n'
            else:
                formatted_schema += f'  "{key}": "{description}",\n'
        formatted_schema = formatted_schema.rstrip(",\n") + "\n}"

        return formatted_schema

    async def _llm_analyze_content(
        self,
        content: str,
        search_result: SearchResult,
        research_request: ResearchRequest,
    ) -> Optional[AnalysisInsight]:
        """
        Use LLM to analyze content with ConfigMap-driven prompts.

        Args:
            content: Full content to analyze
            search_result: Original search result metadata
            research_request: Research configuration with analysis instructions

        Returns:
            Analysis insight or None if analysis fails
        """
        # Construct prompt dynamically from ConfigMap data
        analysis_prompt = self._construct_analysis_prompt(
            content, search_result, research_request
        )

        try:
            response = await self.llm_client.generate_response(
                analysis_prompt, max_tokens=2000, temperature=0.3
            )

            # Parse LLM response
            analysis_data = json.loads(response.strip())

            # Only return insights with sufficient relevance
            if analysis_data.get("relevance_to_topic", 0) < 0.3:
                logger.debug(
                    f"Filtered out low relevance content from {search_result.url}"
                )
                return None

            # Create AnalysisInsight object with dynamic data
            insight = AnalysisInsight(
                title=analysis_data.get("title", f"Analysis: {search_result.title}"),
                content=analysis_data.get("content", ""),
                confidence_score=analysis_data.get("confidence_score", 0.5),
                category=self._determine_category_from_analysis(
                    analysis_data, research_request
                ),
                supporting_sources=[search_result.url],
                impact_level=analysis_data.get("significance", "medium"),
                key_entities=analysis_data.get("key_entities", []),
            )

            return insight

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                f"Failed to parse LLM analysis response for {search_result.url}: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"LLM analysis failed for {search_result.url}: {e}")
            return None

    def _determine_category_from_analysis(
        self, analysis_data: Dict[str, Any], research_request: ResearchRequest
    ) -> str:
        """
        Determine insight category dynamically based on analysis and research context.

        Args:
            analysis_data: Parsed analysis data from LLM
            research_request: Research configuration

        Returns:
            Category string
        """
        # Use focus areas as potential categories
        if research_request.topic.focus_areas:
            # Check if analysis mentions any focus areas
            content_lower = analysis_data.get("content", "").lower()
            title_lower = analysis_data.get("title", "").lower()

            for focus_area in research_request.topic.focus_areas:
                if (
                    focus_area.lower() in content_lower
                    or focus_area.lower() in title_lower
                ):
                    return focus_area

        # Fallback to significance level or generic category
        return analysis_data.get("significance", "general")

    async def synthesize_research_findings(
        self,
        analysis_insights: List[AnalysisInsight],
        research_request: ResearchRequest,
    ) -> Dict[str, Any]:
        """
        Synthesize individual insights using ConfigMap-driven approach.

        Args:
            analysis_insights: List of analysis insights
            research_request: Research configuration with synthesis instructions

        Returns:
            Synthesized research findings
        """
        if not analysis_insights:
            return {
                "summary": f"No significant insights found for {research_request.topic.name}.",
                "findings": [],
                "key_themes": [],
                "recommendations": [],
                "confidence_assessment": "low",
            }

        # Construct synthesis prompt from ConfigMap instructions
        synthesis_prompt = self._construct_synthesis_prompt(
            analysis_insights, research_request
        )

        try:
            response = await self.llm_client.generate_response(
                synthesis_prompt, max_tokens=3000, temperature=0.2
            )

            synthesis_data = json.loads(response.strip())
            return synthesis_data

        except Exception as e:
            logger.error(f"Failed to synthesize research findings: {e}")
            # Return basic synthesis as fallback
            return self._create_basic_synthesis(analysis_insights, research_request)

    def _construct_synthesis_prompt(
        self,
        analysis_insights: List[AnalysisInsight],
        research_request: ResearchRequest,
    ) -> str:
        """
        Construct synthesis prompt from ConfigMap research instructions.
        """
        prompt_parts = [
            f"You are a senior research analyst specializing in {research_request.topic.name}.",
            "",
            "RESEARCH CONTEXT:",
            f"Topic: {research_request.topic.name}",
            f"Description: {research_request.topic.description}",
            f"Focus Areas: {', '.join(research_request.topic.focus_areas)}",
            f"Keywords: {', '.join(research_request.topic.keywords)}",
            f"Research Instructions: {research_request.analysis_instructions}",
            f"Number of Insights: {len(analysis_insights)}",
            "",
            "INDIVIDUAL INSIGHTS TO SYNTHESIZE:",
        ]

        # Add each insight
        for i, insight in enumerate(analysis_insights[:10], 1):  # Limit to top 10
            prompt_parts.extend(
                [
                    f"Insight {i}:",
                    f"Title: {insight.title}",
                    f"Content: {insight.content}",
                    f"Confidence: {insight.confidence_score}",
                    f"Category: {insight.category}",
                    f"Impact: {insight.impact_level}",
                    f"Key Entities: {', '.join(insight.key_entities)}",
                    "",
                ]
            )

        # Add synthesis instructions based on ConfigMap research requirements
        prompt_parts.extend(
            [
                "SYNTHESIS INSTRUCTIONS:",
                "Based on the research instructions and individual insights, "
                "create a comprehensive synthesis that:",
                f"1. Addresses the research topic: {research_request.topic.name}",
                f"2. Focuses on the specified areas: "
                f"{', '.join(research_request.topic.focus_areas)}",
                f"3. Incorporates the keywords: {', '.join(research_request.topic.keywords)}",
                "4. Follows the analysis instructions provided in the research configuration:",
                "",
                research_request.analysis_instructions,  # Direct from ConfigMap
                "",
                "5. Integrates findings across all insights",
                "6. Identifies patterns, trends, and key themes",
                "7. Provides actionable conclusions and recommendations",
                "",
            ]
        )

        # Add output format based on research requirements
        synthesis_schema = self._construct_synthesis_schema(research_request)
        prompt_parts.extend(
            [
                "Provide synthesis in the following JSON format:",
                synthesis_schema,
            ]
        )

        return "\n".join(prompt_parts)

    def _construct_synthesis_schema(self, research_request: ResearchRequest) -> str:
        """
        Construct synthesis JSON schema based on ConfigMap research requirements.
        """
        # Base synthesis schema
        schema = {
            "executive_summary": (
                f"High-level summary of key findings for "
                f"{research_request.topic.name}"
            ),
            "key_findings": "Array of main findings with supporting evidence and confidence scores",
        }

        # Add focus area specific sections based on ConfigMap
        for focus_area in research_request.topic.focus_areas:
            schema[
                f"{focus_area.lower().replace(' ', '_')}_analysis"
            ] = f"Specific analysis for {focus_area}"

        # Add keyword-based analysis sections
        if len(research_request.topic.keywords) <= 3:
            for keyword in research_request.topic.keywords:
                schema[
                    f"{keyword.lower().replace(' ', '_')}_insights"
                ] = f"Insights related to {keyword}"

        # Add standard synthesis fields
        schema.update(
            {
                "key_themes": "Array of main themes identified across insights",
                "trends_and_patterns": "Array of trends and patterns with supporting evidence",
                "actionable_insights": "Array of specific actionable recommendations",
                "confidence_assessment": "Overall confidence in findings (high|medium|low)",
                "research_quality": "Assessment of research quality and completeness",
                "knowledge_gaps": "Areas where more research is needed",
                "implications": f"What these findings mean for {research_request.topic.name}",
            }
        )

        # Format as JSON schema
        formatted_schema = "{\n"
        for key, description in schema.items():
            formatted_schema += f'  "{key}": "{description}",\n'
        formatted_schema = formatted_schema.rstrip(",\n") + "\n}"

        return formatted_schema

    def _create_basic_synthesis(
        self,
        analysis_insights: List[AnalysisInsight],
        research_request: ResearchRequest,
    ) -> Dict[str, Any]:
        """
        Create basic synthesis as fallback when LLM synthesis fails.
        """
        return {
            "executive_summary": (
                f"Analysis of {len(analysis_insights)} insights related to "
                f"{research_request.topic.name}"
            ),
            "key_findings": [
                {
                    "finding": insight.title,
                    "supporting_evidence": insight.supporting_sources,
                    "confidence": insight.confidence_score,
                    "significance": insight.impact_level,
                }
                for insight in analysis_insights[:5]
            ],
            "key_themes": list(
                set(
                    [
                        entity
                        for insight in analysis_insights
                        for entity in insight.key_entities
                    ]
                )
            )[:10],
            "confidence_assessment": "medium",
            "research_quality": "Automated analysis with limited synthesis",
        }
