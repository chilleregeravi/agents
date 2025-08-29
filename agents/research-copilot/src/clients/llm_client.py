"""LLM client for Qwen model integration via Ollama."""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import Settings
from ..models import AnalysisRequest, AnalysisResult, Company, ContentType, ImpactLevel

logger = logging.getLogger(__name__)


class LLMConnectionError(Exception):
    """Exception raised when LLM server connection fails."""

    pass


class LLMAnalysisError(Exception):
    """Exception raised when LLM analysis fails."""

    pass


class QwenLLMClient:
    """Client for interacting with Qwen LLM via Ollama."""

    def __init__(self, settings: Settings):
        """Initialize LLM client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.base_url = f"http://{settings.llm.host}"
        self.model = settings.llm.model
        self.timeout = settings.llm.timeout
        self.max_retries = settings.llm.max_retries
        self.temperature = settings.llm.temperature
        self.max_tokens = settings.llm.max_tokens
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def _make_request(
        self, endpoint: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make HTTP request to Ollama server.

        Args:
            endpoint: API endpoint
            payload: Request payload

        Returns:
            Response data

        Raises:
            LLMConnectionError: If connection fails
        """
        await self._ensure_session()

        try:
            url = f"{self.base_url}/{endpoint}"
            logger.debug(f"Making request to {url} with payload: {payload}")

            async with self._session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Received response: {data}")
                    return data
                else:
                    error_text = await response.text()
                    raise LLMConnectionError(f"HTTP {response.status}: {error_text}")

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Request failed: {e}")
            raise LLMConnectionError(f"Failed to connect to LLM server: {e}")

    async def health_check(self) -> bool:
        """Check if LLM server is healthy.

        Returns:
            True if server is healthy
        """
        try:
            response = await self._make_request("api/tags", {})
            return "models" in response
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using the LLM.

        Args:
            prompt: Input prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text

        Raises:
            LLMAnalysisError: If generation fails
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature or self.temperature,
                "num_predict": max_tokens or self.max_tokens,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = await self._make_request("api/generate", payload)

            if "response" not in response:
                raise LLMAnalysisError("Invalid response format from LLM")

            return response["response"].strip()

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise LLMAnalysisError(f"Failed to generate text: {e}")

    async def analyze_content(self, request: AnalysisRequest) -> AnalysisResult:
        """Analyze content for LLM news extraction.

        Args:
            request: Analysis request

        Returns:
            Analysis result

        Raises:
            LLMAnalysisError: If analysis fails
        """
        system_prompt = self._build_analysis_system_prompt(request.content_type)
        user_prompt = self._build_analysis_user_prompt(request)

        try:
            response_text = await self.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Low temperature for consistent analysis
            )

            # Parse structured response
            analysis_result = self._parse_analysis_response(response_text, request)

            logger.info(
                f"Analyzed {request.content_type} content, "
                f"confidence: {analysis_result.confidence_score:.2f}"
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            raise LLMAnalysisError(f"Failed to analyze content: {e}")

    def _build_analysis_system_prompt(self, content_type: ContentType) -> str:
        """Build system prompt for content analysis.

        Args:
            content_type: Type of content being analyzed

        Returns:
            System prompt
        """
        base_prompt = """You are an AI assistant specialized in analyzing AI/ML and LLM-related content. Your task is to extract structured information from various types of content including blog posts, research papers, announcements, and news articles.

Focus on:
- Identifying the company/organization
- Extracting product names and versions
- Identifying key features, capabilities, or findings
- Assessing the impact level (low, medium, high, critical)
- Determining sentiment and confidence

Always respond with a valid JSON object following the specified schema."""

        content_specific = {
            ContentType.RELEASE: "Pay special attention to version numbers, release dates, new features, and performance improvements.",
            ContentType.ANNOUNCEMENT: "Focus on upcoming features, partnerships, strategic announcements, and timeline information.",
            ContentType.RESEARCH_PAPER: "Extract key findings, methodologies, performance metrics, and implications for the field.",
            ContentType.BLOG_POST: "Identify the main topics, key insights, and practical implications discussed.",
            ContentType.NEWS_ARTICLE: "Focus on factual information, quotes, and the significance of reported events.",
            ContentType.DOCUMENTATION: "Extract feature descriptions, API changes, and usage guidelines.",
        }

        return f"{base_prompt}\n\n{content_specific.get(content_type, '')}"

    def _build_analysis_user_prompt(self, request: AnalysisRequest) -> str:
        """Build user prompt for content analysis.

        Args:
            request: Analysis request

        Returns:
            User prompt
        """
        focus_text = ""
        if request.analysis_focus:
            focus_text = (
                f"Pay special attention to: {', '.join(request.analysis_focus)}\n\n"
            )

        company_hint = ""
        if request.company_hint:
            company_hint = (
                f"This content likely relates to {request.company_hint.value}.\n\n"
            )

        prompt = f"""Analyze the following {request.content_type.value} content and extract structured information:

{company_hint}{focus_text}Content to analyze:
---
{request.content}
---

Respond with a JSON object containing:
{{
    "company": "identified company name or null",
    "product": "identified product/service name or null",
    "key_points": ["list", "of", "key", "points"],
    "sentiment": "positive/negative/neutral",
    "impact_assessment": "low/medium/high/critical",
    "structured_data": {{"any": "additional structured data"}},
    "confidence_score": 0.0-1.0
}}

Ensure the JSON is valid and complete."""

        return prompt

    def _parse_analysis_response(
        self, response_text: str, request: AnalysisRequest
    ) -> AnalysisResult:
        """Parse LLM analysis response into structured result.

        Args:
            response_text: Raw LLM response
            request: Original analysis request

        Returns:
            Structured analysis result

        Raises:
            LLMAnalysisError: If parsing fails
        """
        try:
            # Extract JSON from response (handle cases where LLM adds extra text)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)

            # Map company string to enum
            company = None
            if data.get("company"):
                company_name = data["company"].lower()
                for comp in Company:
                    if (
                        comp.value.lower() in company_name
                        or company_name in comp.value.lower()
                    ):
                        company = comp
                        break
                if not company:
                    company = Company.OTHER

            # Map impact assessment to enum
            impact_map = {
                "low": ImpactLevel.LOW,
                "medium": ImpactLevel.MEDIUM,
                "high": ImpactLevel.HIGH,
                "critical": ImpactLevel.CRITICAL,
            }
            impact = impact_map.get(
                data.get("impact_assessment", "low").lower(), ImpactLevel.LOW
            )

            return AnalysisResult(
                content_type=request.content_type,
                company=company,
                product=data.get("product"),
                key_points=data.get("key_points", []),
                sentiment=data.get("sentiment", "neutral"),
                impact_assessment=impact,
                structured_data=data.get("structured_data"),
                confidence_score=float(data.get("confidence_score", 0.0)),
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            logger.debug(f"Raw response: {response_text}")

            # Return fallback result
            return AnalysisResult(
                content_type=request.content_type,
                company=None,
                product=None,
                key_points=["Failed to parse analysis"],
                sentiment="neutral",
                impact_assessment=ImpactLevel.LOW,
                structured_data=None,
                confidence_score=0.0,
            )

    async def summarize_weekly_content(
        self, content_items: List[Dict[str, Any]]
    ) -> str:
        """Generate weekly summary from analyzed content.

        Args:
            content_items: List of analyzed content items

        Returns:
            Weekly summary text
        """
        if not content_items:
            return "No significant LLM developments this week."

        system_prompt = """You are an AI assistant that creates executive summaries of weekly LLM and AI developments. Create a concise, informative summary that highlights the most important developments, trends, and their implications."""

        # Prepare content summary for the prompt
        content_summary = []
        for item in content_items[:20]:  # Limit to avoid token limits
            summary = (
                f"- {item.get('title', 'Unknown')}: {item.get('summary', 'No summary')}"
            )
            content_summary.append(summary)

        user_prompt = f"""Create a weekly summary of LLM developments based on these items:

{chr(10).join(content_summary)}

Provide a 2-3 paragraph executive summary that:
1. Highlights the most significant releases or announcements
2. Identifies key trends or patterns
3. Discusses potential implications for the AI field

Keep it concise but informative."""

        try:
            summary = await self.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,  # Slightly higher for more creative summary
            )
            return summary

        except Exception as e:
            logger.error(f"Weekly summary generation failed: {e}")
            return "Unable to generate weekly summary due to processing error."


@asynccontextmanager
async def get_llm_client(settings: Settings):
    """Get LLM client as async context manager.

    Args:
        settings: Application settings

    Yields:
        LLM client instance
    """
    client = QwenLLMClient(settings)
    try:
        yield client
    finally:
        await client.close()
