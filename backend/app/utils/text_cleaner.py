import hashlib
import re
from bs4 import BeautifulSoup

def clean_html(raw_html: str) -> str:
    """Removes HTML tags, scripts, styles, and normalizes whitespaces."""
    if not raw_html:
        return ""
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(raw_html, "lxml")
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style"]):
        script_or_style.decompose()
        
    # Get plain text
    text = soup.get_text()
    
    # Normalize whitespaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_hash(text: str) -> str:
    """Generates a SHA-256 hash for a given text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def generate_article_hashes(title: str, body_text: str) -> tuple[str, str]:
    """
    Computes both content_hash and article_hash.
    - content_hash: SHA-256 of the cleaned body text (for duplicate coverage detection).
    - article_hash: SHA-256 of the title + body text (for exact article version tracking).
    """
    cleaned_body = clean_html(body_text)
    cleaned_title = clean_html(title)
    
    content_hash = generate_hash(cleaned_body)
    article_hash = generate_hash(cleaned_title + "||" + cleaned_body)
    
    return content_hash, article_hash
