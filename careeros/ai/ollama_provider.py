"""Local LLM (Ollama) provider adapter.

All Ollama-specific vendor code lives here. Core and modules only ever see the
``AIProvider`` capability interface.
"""

from __future__ import annotations

import os
from typing import Any

from .base import AIError, AIProvider, AIResponseError


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        transport: Any | None = None,
    ) -> None:
        """Create a local Ollama-backed provider.

        Args:
            host: Ollama server host. Defaults to OLLAMA_HOST or
                ``http://localhost:11434``.
            model: Model identifier. Defaults to OLLAMA_MODEL or ``qwen2.5:3b``.
            transport: Optional ``httpx.BaseTransport`` for test injection.
        """
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
        self._transport = transport

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout: float = 300.0,
    ) -> str:
        import httpx

        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
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
        return content
