import re
from typing import List, Tuple, Optional, Set
from datetime import datetime
from app.database.models.article import Article
from app.database.models.story import Story


def normalize_text(text: str) -> str:
    """Lowercase and remove non-alphanumeric characters."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text


class StoryGrouperService:
    """Deterministic article-to-story clustering service using Jaccard headline similarity and keyword overlap."""

    def __init__(self) -> None:
        pass

    def cluster_article(self, new_article: Article, recent_stories: List[Story]) -> Tuple[Optional[Story], bool]:
        """
        Groups a new article into an existing story cluster or returns None if it forms a new story.

        Returns:
            Tuple[Optional[Story], is_same_publisher_update]
        """
        # Get new article tokens
        title_norm = normalize_text(new_article.title)
        tokens_new = set(title_norm.split())
        keywords_new = set(new_article.keywords or [])

        for story in recent_stories:
            # Gate 1: Must be same category
            if new_article.predicted_category != story.predicted_category:
                continue

            # Gate 2: Must be within 12-hour clustering window
            # Check difference between article publish time and story's last updated time
            time_diff = abs((new_article.published_at - story.last_updated_at).total_seconds())
            if time_diff > 43200:  # 12 hours
                continue

            # Gate 3: Headline Jaccard similarity (token overlap)
            story_title_norm = normalize_text(story.title or "")
            tokens_story = set(story_title_norm.split())

            jaccard = 0.0
            if tokens_new or tokens_story:
                jaccard = len(tokens_new & tokens_story) / len(tokens_new | tokens_story)

            # Gate 4: Keyword overlap
            story_keywords = set()
            for art in story.articles:
                if art.keywords:
                    story_keywords.update(art.keywords)

            keyword_overlap = len(keywords_new & story_keywords)

            # Match threshold: Jaccard >= 0.40 OR at least 2 overlapping keywords
            if jaccard >= 0.40 or keyword_overlap >= 2:
                # ── Publisher-Update Rule ────────────────────────────────────
                # If this article is from a publisher that already contributed
                # to this story, it's treated as a same-publisher update.
                existing_publisher_ids = {art.publisher_id for art in story.articles}
                is_same_publisher_update = new_article.publisher_id in existing_publisher_ids

                return story, is_same_publisher_update

        # No match found
        return None, False
