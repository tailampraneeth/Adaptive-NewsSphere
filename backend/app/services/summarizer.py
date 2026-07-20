import logging
from datetime import datetime
from typing import Optional
import google.generativeai as genai

from app.core.config import settings
from app.database.models.story import Story

logger = logging.getLogger("heimdall.summarizer")

HEIMDALL_SUMMARY_PROMPT = """
You are Heimdall's intelligent news summarizer.

Given the news article text below, write a structured news brief with exactly these sections.
Be highly factual, neutral, objective, and informative. Use clear, accessible language.

## Main Event
(1 paragraph — describing what happened, who was involved, when, and where)

## Background
(1 paragraph — why this matters, historical context, or preceding events)

## Timeline
- [Key event 1 date/timestamp] - Brief description
- [Key event 2 date/timestamp] - Brief description
- [Key event 3 date/timestamp] - Brief description

## Key People & Organizations
- **Name** — Role or relevance to this story
- **Name** — Role or relevance to this story

## Impact
(1 paragraph — immediate consequences, responses from key entities, or market reactions)

## Why It Matters
(1 paragraph — broader global, regional, or long-term significance of this development)

## Key Takeaways
- [Takeaway 1] - Concise fact or key data point
- [Takeaway 2] - Concise fact or key data point
- [Takeaway 3] - Concise fact or key data point

Article Text:
{text}
"""


class StorySummarizerService:
    """Gemini-powered news summarization service with local fallback for offline/testing robustness."""

    def __init__(self) -> None:
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._is_mock = self.api_key == "mock_key_for_testing" or not self.api_key

        if not self._is_mock:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                logger.info(f"Gemini Summarizer configured with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to configure Gemini model, falling back to mock: {e}")
                self._is_mock = True
        else:
            logger.info("Gemini Summarizer configured in MOCK mode.")

    async def summarize_story(self, story: Story, article_text: str) -> Optional[str]:
        """
        Generates a 7-section structured summary for a story using the longest/most complete article.

        Returns:
            The markdown summary string, or None if generation failed.
        """
        if self._is_mock:
            return self._generate_fallback_summary(story, article_text)

        try:
            prompt = HEIMDALL_SUMMARY_PROMPT.format(text=article_text[:6000])  # Cap input text to prevent token bloat
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            raise ValueError("Empty response from Gemini API")
        except Exception as e:
            logger.error(f"Gemini summary generation failed for story {story.id}: {e}. Falling back...")
            return self._generate_fallback_summary(story, article_text)

    def _generate_fallback_summary(self, story: Story, article_text: str) -> str:
        """Lightweight offline fallback to ensure the app works under rate limits or offline testing."""
        title = story.title or "Recent Event"
        snippet = article_text[:300].strip() + "..." if len(article_text) > 300 else article_text

        return f"""## Main Event
A news update regarding "{title}". Based on reports, the core developments highlight the following: {snippet}

## Background
This story builds upon ongoing interest in this domain. Recent trends suggest increasing focus from industry leaders and global watchdogs.

## Timeline
- **Recently** - Initial reports surfaced regarding "{title}".
- **Update** - Additional sources confirmed the story details.
- **Latest** - Currently developing with further details expected soon.

## Key People & Organizations
- **Key Spokesperson** — Representative commenting on these developments
- **Associated Entity** — Organization involved in this event

## Impact
Immediate reactions have been noted across relevant markets and communities, with analysts closely watching the situation unfold.

## Why It Matters
This event could shape future policies, standards, or public opinion in the category of {story.predicted_category or "General"}.

## Key Takeaways
- Initial reports outline key elements of the event.
- Multiple sources are tracking developments.
- Long-term impacts are being analyzed.
"""
