import re
import datetime
from typing import Dict, Any
from app.database.models.article import Article

class DataValidator:
    @staticmethod
    def validate_article(article: Article) -> Dict[str, Any]:
        """
        Validates article record against data quality rules.
        Returns a validation dictionary showing status (PASS, WARNING, FAIL) and details.
        """
        status = "PASS"
        issues = []

        # 1. Missing Title Check
        if not article.title or not article.title.strip():
            status = "FAIL"
            issues.append("FAIL: Title is missing or empty.")

        # 2. Missing Content Check
        if not article.body_text or not article.body_text.strip():
            status = "FAIL"
            issues.append("FAIL: Body content text is missing or empty.")

        # 3. Invalid URL Check
        url = article.source_url
        if not url or not url.strip():
            status = "FAIL"
            issues.append("FAIL: Source URL is missing or empty.")
        elif not (url.startswith("http://") or url.startswith("https://")):
            status = "FAIL"
            issues.append("FAIL: Source URL is invalid (must begin with http:// or https://).")

        # 4. Missing Publisher Check
        if not article.publisher_id or not article.publisher_id.strip():
            status = "FAIL"
            issues.append("FAIL: Publisher association is missing.")

        # 5. Invalid Timestamp Check
        now = datetime.datetime.now(datetime.timezone.utc)
        if not article.published_at:
            status = "FAIL"
            issues.append("FAIL: Publication timestamp is missing.")
        else:
            pub_time = article.published_at
            # Make timezone aware if it is naive for comparison
            if pub_time.tzinfo is None:
                pub_time = pub_time.replace(tzinfo=datetime.timezone.utc)

            if pub_time > now + datetime.timedelta(hours=1):
                status = "WARNING"
                issues.append("WARNING: Publication date is in the future.")
            elif pub_time < now - datetime.timedelta(days=365):
                status = "WARNING"
                issues.append("WARNING: Article is older than 1 year (stale archive).")

        # 6. Missing Hashes Check
        h_pattern = re.compile(r"^[a-fA-F0-9]{64}$") # SHA-256 hash pattern
        if not article.content_hash or not h_pattern.match(article.content_hash):
            status = "FAIL"
            issues.append("FAIL: Content hash is missing or not a valid 64-char SHA-256 hex string.")
        if not article.article_hash or not h_pattern.match(article.article_hash):
            status = "FAIL"
            issues.append("FAIL: Article hash is missing or not a valid 64-char SHA-256 hex string.")

        # 7. Invalid Language Check
        if not article.language or not article.language.strip():
            status = "WARNING"
            issues.append("WARNING: Language code is missing.")
        elif len(article.language) > 5 or not article.language.isalpha():
            status = "WARNING"
            issues.append("WARNING: Language code looks invalid (should be en, es, etc.).")

        # 8. Missing Category Check
        if not article.category or not article.category.strip():
            # Many RSS articles lack clear categories, categorized as WARNING
            if status != "FAIL":
                status = "WARNING"
            issues.append("WARNING: Category classification is missing.")

        # Adjust overall status if a FAIL rule matched
        has_fail = any(i.startswith("FAIL") for i in issues)
        has_warning = any(i.startswith("WARNING") for i in issues)
        if has_fail:
            status = "FAIL"
        elif has_warning:
            status = "WARNING"

        return {
            "article_id": str(article.id),
            "title": article.title[:50] + "..." if article.title else "N/A",
            "status": status,
            "issues": issues
        }
