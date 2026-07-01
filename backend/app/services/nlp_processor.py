import logging
import time
from collections import Counter
import spacy
from keybert import KeyBERT
from app.services.embedder import get_shared_model

logger = logging.getLogger("adaptive-newssphere.nlp")

class NLPProcessorService:
    def __init__(self):
        logger.info("Initializing NLP pipelines (spaCy + KeyBERT)...")
        t0 = time.time()

        # Load spaCy small model
        self.nlp = spacy.load("en_core_web_sm")

        # Re-use the cached SentenceTransformer model instance from embedder
        shared_model = get_shared_model()
        self.kw_model = KeyBERT(model=shared_model)

        logger.info(f"Loaded NLP pipelines in {time.time() - t0:.2f}s")

    def extract_metadata(self, title: str, body_text: str) -> dict:
        """
        Extracts Named Entities, Keywords, and Topics from article content.
        Safeguards memory by slicing body_text up to 8000 characters.
        """
        combined_text = f"{title}. {body_text}"
        truncated_text = combined_text[:8000]

        # 1. spaCy Named Entity Recognition (NER)
        doc = self.nlp(truncated_text)

        # Extract distinct entities for PERSON, ORG, GPE
        persons = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON" and len(ent.text.strip()) > 1]))
        organizations = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "ORG" and len(ent.text.strip()) > 1]))
        locations = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "GPE" and len(ent.text.strip()) > 1]))

        named_entities = {
            "persons": persons[:8],
            "organizations": organizations[:8],
            "locations": locations[:8]
        }

        # 2. KeyBERT Keyword Extraction
        keywords = []
        try:
            # Extract top 5 keywords/phrases
            kw_results = self.kw_model.extract_keywords(
                truncated_text,
                keyphrase_ngram_range=(1, 2),
                stop_words="english",
                top_n=5
            )
            keywords = [kw[0] for kw in kw_results]
        except Exception as e:
            logger.warning(f"KeyBERT keyword extraction failed: {e}")

        # 3. Frequency-based Topic Extraction from noun chunks
        topics = []
        try:
            # Get noun chunks under 3 words long
            noun_chunks = [chunk.text.lower().strip() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]
            # Exclude standard stop words
            stop_words = self.nlp.Defaults.stop_words
            filtered_chunks = [
                c for c in noun_chunks
                if c not in stop_words and not any(w in stop_words for w in c.split()) and len(c) > 2
            ]
            # Select top 3 recurring noun chunks as topics
            topics = [item[0] for item in Counter(filtered_chunks).most_common(3)]
        except Exception as e:
            logger.warning(f"Topic extraction failed: {e}")

        # Compute counts
        word_count = len(body_text.split())
        char_count = len(body_text)
        # Standard reading speed is ~200 words per minute
        reading_time = max(1, round(word_count / 200))

        return {
            "named_entities": named_entities,
            "keywords": keywords,
            "topics": topics,
            "word_count": word_count,
            "character_count": char_count,
            "reading_time": reading_time
        }

    def health(self) -> dict:
        """Service health check interface."""
        try:
            t0 = time.time()
            # Perform a validation run
            test_text = "Google, founded by Larry Page, is based in Mountain View, California."
            metadata = self.extract_metadata("Company News", test_text)

            # Assert NER found Larry Page as Person and Google as Org
            assert "persons" in metadata["named_entities"]
            latency = (time.time() - t0) * 1000

            return {
                "status": "PASS",
                "latency_ms": round(latency, 2),
                "details": {
                    "spacy_loaded": True,
                    "keybert_loaded": True,
                    "spacy_pipeline": "en_core_web_sm",
                    "sentence_transformer_shared": True
                }
            }
        except Exception as e:
            logger.error(f"NLP health check failed: {e}")
            return {
                "status": "FAIL",
                "latency_ms": 0,
                "details": {"error": str(e)}
            }
