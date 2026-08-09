"""OpenAI provider adapter.

All OpenAI-specific vendor code lives here. Core and modules only ever see the
``AIProvider`` capability interface.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from careeros.exceptions import LLMConfigurationError

from .base import AIError, AIProvider, AIResponseError

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        transport: Any | None = None,
    ) -> None:
        """Create an OpenAI-backed provider.

        Args:
            api_key: OpenAI API key. Defaults to the OPENAI_API_KEY environment
                variable.
            model: Model identifier. Defaults to OPENAI_MODEL or ``gpt-4o``.
            base_url: Chat completions endpoint override (mainly for tests /
                proxies).
            transport: Optional ``httpx.BaseTransport`` for test injection.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMConfigurationError(
                "OpenAI API key is required. Set the OPENAI_API_KEY environment variable "
                "or pass api_key to OpenAIProvider."
            )
        self.model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o"
        self.base_url = base_url or "https://api.openai.com/v1/chat/completions"
        self._transport = transport

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout: float = 60.0,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        import httpx

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=timeout, transport=self._transport) as client:
                response = client.post(self.base_url, headers=headers, json=body)
                response.raise_for_status()
                result = response.json()
        except AIError:
            raise
        except Exception as exc:
            raise AIError(f"OpenAI API call failed: {exc}") from exc

        choices = result.get("choices", [])
        if not choices:
            raise AIResponseError("OpenAI returned no choices")
        content = choices[0].get("message", {}).get("content", "") or ""
        if choices[0].get("finish_reason") == "length":
            logger.warning(
                "OpenAI generation stopped at the output length limit "
                "(model=%s, max_tokens=%s); response may be truncated.",
                self.model,
                max_tokens,
            )
        return content
