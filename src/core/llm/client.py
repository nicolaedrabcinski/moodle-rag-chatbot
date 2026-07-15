"""
vLLM client for Qwen2.5:32B-Instruct with async support and streaming.
"""

import asyncio
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.config.logging import LoggerAdapter

from .exceptions import (
    LLMConnectionError,
    LLMGenerationError,
    LLMInvalidResponseError,
    LLMTimeoutError,
)

logger = LoggerAdapter(__name__)


class VLLMClient:
    """
    Async client for vLLM OpenAI-compatible API.

    Supports:
    - Async generation
    - Streaming responses
    - Retry logic
    - Error handling
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize vLLM client.

        Args:
            api_base: Base URL for vLLM API (e.g., http://localhost:8001/v1)
            model: Model name (e.g., Qwen/Qwen2.5-32B-Instruct)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.api_base = api_base or settings.llm_api_base
        self.model = model or settings.llm_model
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

        logger.info(
            "Initialized vLLM client",
            api_base=self.api_base,
            model=self.model,
            timeout=timeout,
        )

    async def __aenter__(self) -> "VLLMClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.debug("Closed vLLM client")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMConnectionError, LLMTimeoutError)),
        reraise=True,
    )
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Generate text completion.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            stop: Stop sequences
            stream: Enable streaming (not used in this method)
            **kwargs: Additional parameters

        Returns:
            str: Generated text

        Raises:
            LLMConnectionError: Connection failed
            LLMGenerationError: Generation failed
            LLMTimeoutError: Request timeout
            LLMInvalidResponseError: Invalid response format
        """
        request_data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "temperature": temperature or settings.llm_temperature,
            "top_p": top_p or settings.llm_top_p,
            "stream": False,
            **kwargs,
        }

        if stop:
            request_data["stop"] = stop

        logger.debug(
            "Sending generation request",
            prompt_length=len(prompt),
            max_tokens=request_data["max_tokens"],
            temperature=request_data["temperature"],
        )

        try:
            response = await self.client.post(
                "chat/completions",
                json=request_data,
            )
            response.raise_for_status()
        except httpx.TimeoutException as e:
            logger.error("LLM request timeout", error=str(e))
            raise LLMTimeoutError(f"Request timeout: {e}") from e
        except httpx.ConnectError as e:
            logger.error("LLM connection error", error=str(e))
            raise LLMConnectionError(f"Connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error("LLM HTTP error", status_code=e.response.status_code, error=str(e))
            raise LLMGenerationError(f"HTTP error {e.response.status_code}: {e}") from e
        except Exception as e:
            logger.exception("Unexpected LLM error", error=str(e))
            raise LLMGenerationError(f"Unexpected error: {e}") from e

        try:
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]
            logger.debug(
                "Generation successful",
                generated_length=len(generated_text),
                finish_reason=result["choices"][0].get("finish_reason"),
            )
            return generated_text
        except (KeyError, IndexError) as e:
            logger.error("Invalid LLM response format", error=str(e), response=result)
            raise LLMInvalidResponseError(f"Invalid response format: {e}") from e

    async def generate_stream(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Generate text completion with streaming.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            stop: Stop sequences
            **kwargs: Additional parameters

        Yields:
            str: Generated text chunks

        Raises:
            LLMConnectionError: Connection failed
            LLMGenerationError: Generation failed
            LLMTimeoutError: Request timeout
        """
        request_data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "temperature": temperature or settings.llm_temperature,
            "top_p": top_p or settings.llm_top_p,
            "stream": True,
            **kwargs,
        }

        if stop:
            request_data["stop"] = stop

        logger.debug(
            "Sending streaming generation request",
            prompt_length=len(prompt),
            max_tokens=request_data["max_tokens"],
        )

        try:
            async with self.client.stream("POST", "chat/completions", json=request_data) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # Parse SSE format: "data: {...}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix

                        # Check for stream end
                        if data_str.strip() == "[DONE]":
                            break

                        try:
                            import json

                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                text = delta.get("content", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse SSE data", data=data_str)
                            continue

        except httpx.TimeoutException as e:
            logger.error("LLM streaming request timeout", error=str(e))
            raise LLMTimeoutError(f"Streaming timeout: {e}") from e
        except httpx.ConnectError as e:
            logger.error("LLM streaming connection error", error=str(e))
            raise LLMConnectionError(f"Streaming connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM streaming HTTP error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise LLMGenerationError(f"Streaming HTTP error {e.response.status_code}: {e}") from e
        except Exception as e:
            logger.exception("Unexpected LLM streaming error", error=str(e))
            raise LLMGenerationError(f"Unexpected streaming error: {e}") from e

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Generate chat completion (OpenAI format).

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            stop: Stop sequences
            stream: Enable streaming (not used in this method)
            **kwargs: Additional parameters

        Returns:
            str: Generated response

        Raises:
            LLMConnectionError: Connection failed
            LLMGenerationError: Generation failed
            LLMTimeoutError: Request timeout
        """
        request_data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "temperature": temperature or settings.llm_temperature,
            "top_p": top_p or settings.llm_top_p,
            "stream": False,
            **kwargs,
        }

        if stop:
            request_data["stop"] = stop

        logger.debug(
            "Sending chat completion request",
            num_messages=len(messages),
            max_tokens=request_data["max_tokens"],
        )

        try:
            response = await self.client.post("chat/completions", json=request_data)
            response.raise_for_status()
        except httpx.TimeoutException as e:
            logger.error("Chat completion timeout", error=str(e))
            raise LLMTimeoutError(f"Chat timeout: {e}") from e
        except httpx.ConnectError as e:
            logger.error("Chat completion connection error", error=str(e))
            raise LLMConnectionError(f"Chat connection failed: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "Chat completion HTTP error",
                status_code=e.response.status_code,
                error=str(e),
            )
            raise LLMGenerationError(f"Chat HTTP error {e.response.status_code}: {e}") from e
        except Exception as e:
            logger.exception("Unexpected chat completion error", error=str(e))
            raise LLMGenerationError(f"Unexpected chat error: {e}") from e

        try:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            logger.debug(
                "Chat completion successful",
                generated_length=len(content),
                finish_reason=result["choices"][0].get("finish_reason"),
            )
            return content
        except (KeyError, IndexError) as e:
            logger.error("Invalid chat response format", error=str(e), response=result)
            raise LLMInvalidResponseError(f"Invalid chat response: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if LLM server is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            # /v1/models is a valid OpenAI-compatible endpoint on vLLM
            response = await self.client.get("models", timeout=5)
            is_healthy = response.status_code == 200
            logger.debug("LLM health check", is_healthy=is_healthy)
            return is_healthy
        except Exception as e:
            logger.warning("LLM health check failed", error=str(e))
            return False


# Global client instance (singleton)
_client: Optional[VLLMClient] = None


def get_llm_client() -> VLLMClient:
    """
    Get global LLM client instance (singleton).

    Returns:
        VLLMClient: LLM client instance
    """
    global _client
    if _client is None:
        _client = VLLMClient()
    return _client


async def close_llm_client() -> None:
    """Close global LLM client."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
