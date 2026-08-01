"""Deterministic mock AI provider for unit testing.

Never performs network access. Completions are selected from a mapping of
prompt-substring keys to canned responses, falling back to a fixed default.
Every call is recorded so tests can assert on prompts and call counts.
"""

from __future__ import annotations

from typing import Callable, Mapping

from .base import AIError, AIProvider


class MockAIProvider(AIProvider):
    name = "mock"

    def __init__(
        self,
        responses: Mapping[str, str] | None = None,
        default_response: str = "{}",
        *,
        fail: bool = False,
        error_message: str = "mock provider failure",
        generator: Callable[[str, float, float], str] | None = None,
    ) -> None:
        """Create a deterministic, offline provider.

        Args:
            responses: Mapping of prompt substrings to canned completions. The
                first key contained in the prompt wins.
            default_response: Completion returned when no key matches.
            fail: When True, every ``generate`` raises ``AIError``.
            error_message: Message used when ``fail`` is True.
            generator: Optional callable ``(prompt, temperature, timeout) ->
                str`` overriding canned responses entirely.
        """
        self.responses = dict(responses or {})
        self.default_response = default_response
        self.fail = fail
        self.error_message = error_message
        self._generator = generator
        self.calls: list[str] = []

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout: float = 60.0,
    ) -> str:
        self.calls.append(prompt)
        if self.fail:
            raise AIError(self.error_message)
        if self._generator is not None:
            return self._generator(prompt, temperature, timeout)
        for key, response in self.responses.items():
            if key in prompt:
                return response
        return self.default_response
