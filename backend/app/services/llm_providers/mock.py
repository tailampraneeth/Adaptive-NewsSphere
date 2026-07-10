import asyncio
import re
from typing import AsyncIterator
from app.services.llm_providers.base import BaseLLMProvider

class MockProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for unit testing and offline development."""

    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name

    async def generate(self, prompt: str) -> str:
        """Determines and returns a mock response containing citation patterns matching the prompt context."""
        return self._generate_mock_text(prompt)

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Simulates asynchronous token streaming with deterministic delays."""
        text = self._generate_mock_text(prompt)
        # Yield mock tokens in chunks of 8 characters
        for chunk in [text[i:i+8] for i in range(0, len(text), 8)]:
            yield chunk
            await asyncio.sleep(0.001)

    def get_model_name(self) -> str:
        return self.model_name

    def _generate_mock_text(self, prompt: str) -> str:
        # Extract sources from context format: --- Source [1]: BBC News ---
        sources = re.findall(r"Source\s*\[\d+\]:\s*([^\n\-]+)", prompt)
        # Fallback to general tags
        sources += re.findall(r"Publisher:\s*([^,\n]+)", prompt)
        sources += re.findall(r"Source:\s*([^,\n]+)", prompt)

        if sources:
            unique_sources = []
            for s in sources:
                cleaned = s.strip().replace("[", "").replace("]", "")
                if "Publisher Name" in cleaned or "format" in cleaned:
                    continue
                if cleaned not in unique_sources:
                    unique_sources.append(cleaned)

            source_citations = ", ".join(f"[Source: {src}]" for src in unique_sources)
            return (
                f"According to the verified reports, the main events are confirmed by {source_citations}. "
                "The documents corroborate that this transition is proceeding successfully."
            )
        
        return "This is a default mock response for testing. No verified context sources were found in the prompt."
