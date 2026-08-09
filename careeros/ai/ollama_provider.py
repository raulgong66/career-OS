"""Local LLM (Ollama) provider adapter.

All Ollama-specific vendor code lives here. Core and modules only ever see the
``AIProvider`` capability interface.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .base import AIError, AIProvider, AIResponseError

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        transport: Any | None = None,
        num_ctx: int | None = None,
        num_predict: int | None = None,
    ) -> None:
        """Create a local Ollama-backed provider.

        Args:
            host: Ollama server host. Defaults to OLLAMA_HOST or
                ``http://localhost:11434``.
            model: Model identifier. Defaults to OLLAMA_MODEL or ``qwen2.5:3b``.
            transport: Optional ``httpx.BaseTransport`` for test injection.
            num_ctx: Context window (prompt + output) in tokens. Defaults to
                OLLAMA_NUM_CTX or ``16384``. Ollama's default is only 4096,
                which truncates long CV extraction output mid-JSON.
            num_predict: Maximum output tokens. Defaults to OLLAMA_NUM_PREDICT
                or ``8192``.
        """
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
        self.num_ctx = num_ctx or int(os.environ.get("OLLAMA_NUM_CTX", "16384"))
        self.num_predict = num_predict or int(os.environ.get("OLLAMA_NUM_PREDICT", "8192"))
        self._transport = transport

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout: float = 300.0,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> str:
        import httpx

        body: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,
                "num_predict": max_tokens or self.num_predict,
            },
        }
        if json_mode:
            body["format"] = "json"
        try:
            with httpx.Client(timeout=timeout, transport=self._transport) as client:
                response = client.post(f"{self.host}/api/generate", json=body)
                response.raise_for_status()
                result = response.json()
        except AIError:
            raise
        except Exception as exc:
            raise AIError(f"Ollama API call failed: {exc}") from exc

        content = result.get("response", "")
        if not content:
            raise AIResponseError("Ollama returned empty response")
        if result.get("done_reason") == "length":
            logger.warning(
                "Ollama generation stopped at the output length limit "
                "(model=%s, num_ctx=%d, num_predict=%d); response may be truncated.",
                self.model,
                self.num_ctx,
                self.num_predict,
            )
        return content
