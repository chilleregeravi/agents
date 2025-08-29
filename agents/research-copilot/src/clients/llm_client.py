"""LLM client for Qwen model integration via Ollama."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import Settings

logger = logging.getLogger(__name__)


class LLMConnectionError(Exception):
    """Exception raised when LLM server connection fails."""

    pass


class LLMGenerationError(Exception):
    """Exception raised when LLM content generation fails."""

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
                if response.status != 200:
                    error_text = await response.text()
                    raise LLMConnectionError(
                        f"LLM server returned status {response.status}: {error_text}"
                    )

                return await response.json()

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {e}")
            raise LLMConnectionError(f"Failed to connect to LLM server: {e}")

        except asyncio.TimeoutError as e:
            logger.error(f"Request timeout: {e}")
            raise LLMConnectionError(f"Request to LLM server timed out: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate text using the LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature

        Returns:
            Generated text

        Raises:
            LLMGenerationError: If generation fails
        """
        try:
            # Prepare messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens,
                },
            }

            response = await self._make_request("api/generate", payload)

            if "response" not in response:
                raise LLMGenerationError("Invalid response format from LLM server")

            return response["response"]

        except LLMConnectionError:
            raise
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            raise LLMGenerationError(f"Failed to generate text: {e}")

    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Generate response using the LLM (alias for generate method).

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature

        Returns:
            Generated response
        """
        return await self.generate(prompt, system_prompt, max_tokens, temperature)

    async def health_check(self) -> Dict[str, Any]:
        """Check LLM server health.

        Returns:
            Health status information
        """
        try:
            # Simple test generation
            test_response = await self.generate("Test connection", max_tokens=10)

            return {
                "status": "healthy",
                "model": self.model,
                "response": test_response,
                "timestamp": asyncio.get_event_loop().time(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time(),
            }


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
