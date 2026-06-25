import os
import json
import asyncio
import logging
from typing import Any, Optional, AsyncGenerator
from google import genai
from google.genai import types
from google.api_core import retry
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError
from pydantic import BaseModel
import time

logger = logging.getLogger(__name__)


class GeminiResponse(BaseModel):
    content: str
    structured_data: Optional[dict] = None
    tokens_used: int = 0
    model: str


class GeminiClient:
    """Async Gemini client with retry and rate limit handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        self.model_name = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.client = genai.Client(api_key=self.api_key)

        self._rate_limit_semaphore = asyncio.Semaphore(10)
        self._last_request_time = 0
        self._min_request_interval = 0.1

    async def _wait_for_rate_limit(self):
        async with self._rate_limit_semaphore:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                await asyncio.sleep(self._min_request_interval - elapsed)
            self._last_request_time = time.time()

    def _get_retry_policy(self) -> retry.Retry:
        return retry.Retry(
            predicate=lambda exc: isinstance(exc, (ResourceExhausted, GoogleAPIError)),
            initial=self.retry_delay,
            maximum=60.0,
            multiplier=2.0,
        )

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        response_schema: Optional[dict] = None,
    ) -> GeminiResponse:
        """Generate a response from Gemini."""
        await self._wait_for_rate_limit()

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

        if system_instruction:
            config.system_instruction = system_instruction

        if response_schema:
            config.response_schema = response_schema
            config.response_mime_type = "application/json"

        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                response = await asyncio.to_thread(
                    lambda: self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=config,
                    )
                )

                content = response.text

                structured_data = None
                if response_schema:
                    try:
                        structured_data = json.loads(content)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse JSON response")

                usage = response.usage_metadata or {}
                tokens_used = getattr(usage, "total_token_count", 0)

                return GeminiResponse(
                    content=content,
                    structured_data=structured_data,
                    tokens_used=tokens_used,
                    model=self.model_name,
                )

            except ResourceExhausted as e:
                last_error = e
                retries += 1
                wait_time = self.retry_delay * (2**retries)
                logger.warning(f"Rate limited, waiting {wait_time}s before retry {retries}")
                await asyncio.sleep(wait_time)

            except GoogleAPIError as e:
                last_error = e
                retries += 1
                wait_time = self.retry_delay * (2**retries)
                logger.error(f"API error: {e}, retrying {retries}/{self.max_retries}")
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

        raise Exception(f"Failed after {self.max_retries} retries: {last_error}")

    async def generate_structured(
        self,
        prompt: str,
        schema: dict,
        system_instruction: Optional[str] = None,
        temperature: float = 0.3,
    ) -> dict:
        """Generate a structured JSON response."""
        response = await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            response_schema=schema,
        )
        return response.structured_data or {}

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        await self._wait_for_rate_limit()

        config = types.GenerateContentConfig(
            temperature=temperature,
        )

        if system_instruction:
            config.system_instruction = system_instruction

        try:
            stream = await asyncio.to_thread(
                lambda: self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
            )

            for chunk in stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise


gemini_client = GeminiClient()
