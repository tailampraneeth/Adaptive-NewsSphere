from typing import AsyncIterator
from app.core.config import settings
from app.services.llm_providers.base import BaseLLMProvider
from app.services.llm_providers.gemini import GeminiProvider
from app.services.llm_providers.mock import MockProvider

class LLMService:
    """System-wide LLM coordination service depending strictly on BaseLLMProvider."""

    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    async def generate(self, prompt: str) -> str:
        """Invokes active provider for standard text generation."""
        return await self.provider.generate(prompt)

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Invokes active provider to yield async token streams."""
        async for chunk in self.provider.generate_stream(prompt):
            yield chunk

    def get_model_name(self) -> str:
        """Returns name of the active model in the provider."""
        return self.provider.get_model_name()


def get_llm_provider() -> BaseLLMProvider:
    """Factory helper to resolve the active BaseLLMProvider instance from configuration."""
    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model_name=settings.GEMINI_MODEL
        )
    return MockProvider(model_name="mock-model")
