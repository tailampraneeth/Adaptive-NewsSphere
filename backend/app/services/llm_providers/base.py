from abc import ABC, abstractmethod
from typing import AsyncIterator

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers supporting both sync and async stream responses."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """
        Generates a complete response for a given prompt.

        Args:
            prompt: Compiled text prompt.

        Returns:
            The generated response string.
        """
        pass

    @abstractmethod
    def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """
        Streams response tokens asynchronously.

        Args:
            prompt: Compiled text prompt.

        Returns:
            An async iterator yielding chunks of the generated response.
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Returns the configured model name string."""
        pass
