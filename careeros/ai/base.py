"""AI provider interface — capability-oriented and vendor-agnostic.

Core and modules depend only on this interface and on the configuration-driven
factory. They never import a vendor SDK or issue HTTP calls directly. Vendors,
SDKs, and HTTP transports live exclusively behind implementations of this
interface (``careeros/ai/*_provider.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from careeros.exceptions import CareerOSException


class AIError(CareerOSException):
    """Base error for AI provider call failures."""


class AIResponseError(AIError):
    """Raised when a provider returns an unusable response (no content, bad shape)."""


class AIProvider(ABC):
    """Capability-oriented AI service interface.

    Only the capabilities actually needed today are exposed. Today that is a
    single capability, ``generate``: complete a prompt and return the raw model
    text. Prompt construction and response parsing are business logic and live
    in Core consumers (acquisition extraction, CV generation) — never in a
    provider implementation.
    """

    name: str = "abstract"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        timeout: float = 60.0,
    ) -> str:
        """Return the model's completion for a prompt.

        Args:
            prompt: The full prompt text (built by the consumer).
            temperature: Sampling temperature.
            timeout: Request timeout in seconds.

        Returns:
            The raw model text.

        Raises:
            AIError: If the provider call fails or the response is unusable.
        """
