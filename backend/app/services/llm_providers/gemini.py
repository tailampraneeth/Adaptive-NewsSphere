import asyncio
import logging
from typing import AsyncIterator
import google.generativeai as genai
from app.services.llm_providers.base import BaseLLMProvider

logger = logging.getLogger("adaptive-newssphere.llm_providers.gemini")

class GeminiProvider(BaseLLMProvider):
    """Google Gemini Free Tier LLM Provider implementation."""

    def __init__(self, api_key: str, model_name: str):
        self.model_name = model_name
        if not api_key or api_key == "mock_key_for_testing":
            logger.warning("Gemini API key is not configured or using default mock value.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_ONLY_HIGH",
                },
            ]
        )

    async def generate(self, prompt: str) -> str:
        """Runs generation in an executor thread to keep FastAPI event loop unblocked."""
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt)
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"Gemini API generate_content call failed: {e}")
            raise

    async def generate_stream(self, prompt: str) -> AsyncIterator[str]:
        """Streams response tokens by running blocking generator in an executor."""
        try:
            loop = asyncio.get_running_loop()
            # Fetch full generator object synchronously in a worker thread first
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(prompt, stream=True)
            )
            
            # Helper to run next(iterator) safely in thread
            iterator = iter(response)
            while True:
                try:
                    chunk = await loop.run_in_executor(None, lambda: next(iterator, None))
                    if chunk is None:
                        break
                    if chunk.text:
                        yield chunk.text
                except StopIteration:
                    break
                except Exception as chunk_err:
                    logger.warning(f"Error extracting text chunk from Gemini stream: {chunk_err}")
                    continue
        except Exception as e:
            logger.error(f"Gemini API generate_content stream initialization failed: {e}")
            raise

    def get_model_name(self) -> str:
        return self.model_name
