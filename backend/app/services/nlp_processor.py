import logging
import time
from collections import Counter
import spacy

logger = logging.getLogger("heimdall.nlp")


class NLPProcessorService:
    def __init__(self):
        logger.info("Initializing NLP pipeline (spaCy en_core_web_sm)...")
        t0 = time.time()
        # Load spaCy small model
        self.nlp = spacy.load("en_core_web_sm")
        logger.info(f"Loaded spaCy in {time.time() - t0:.2f}s")

    def extract_metadata(self, title: str, body_text: str) -> dict:
        """
        Extracts Named Entities, Keywords, and Topics from article content using spaCy.
        Safeguards memory by slicing body_text up to 8000 characters.
        """
        combined_text = f"{title}. {body_text}"
        truncated_text = combined_text[:8000]

        # 1. spaCy Named Entity Recognition (NER)
        doc = self.nlp(truncated_text)

        persons = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON" and len(ent.text.strip()) > 1]))
        organizations = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "ORG" and len(ent.text.strip()) > 1]))
        locations = list(set([ent.text.strip() for ent in doc.ents if ent.label_ == "GPE" and len(ent.text.strip()) > 1]))

        named_entities = {
            "persons": persons[:8],
            "organizations": organizations[:8],
            "locations": locations[:8]
        }

        # 2. Extract keywords using spaCy (nouns and proper nouns, sorted by frequency)
        stop_words = self.nlp.Defaults.stop_words
        words = [
            token.text.lower().strip()
            for token in doc
            if token.pos_ in {"NOUN", "PROPN"}
            and token.text.lower().strip() not in stop_words
            and len(token.text.strip()) > 2
        ]
        keyword_counts = Counter(words)
        keywords = [item[0] for item in keyword_counts.most_common(5)]

        # 3. Frequency-based Topic Extraction from noun chunks
        topics = []
        try:
            noun_chunks = [chunk.text.lower().strip() for chunk in doc.noun_chunks if len(chunk.text.split()) <= 3]
            filtered_chunks = [
                c for c in noun_chunks
                if c not in stop_words and not any(w in stop_words for w in c.split()) and len(c) > 2
            ]
            topics = [item[0] for item in Counter(filtered_chunks).most_common(3)]
        except Exception as e:
            logger.warning(f"Topic extraction failed: {e}")

        # Compute counts
        word_count = len(body_text.split())
        reading_time = max(1, round(word_count / 200))

        return {
            "named_entities": named_entities,
            "keywords": keywords,
            "topics": topics,
            "reading_time": reading_time
        }

    def health(self) -> dict:
        """Service health check interface."""
        try:
            t0 = time.time()
            test_text = "Google, founded by Larry Page, is based in Mountain View, California."
            metadata = self.extract_metadata("Company News", test_text)

            assert "persons" in metadata["named_entities"]
            latency = (time.time() - t0) * 1000

            return {
                "status": "PASS",
                "latency_ms": round(latency, 2),
                "details": {
                    "spacy_loaded": True,
                    "spacy_pipeline": "en_core_web_sm",
                }
            }
        except Exception as e:
            logger.error(f"NLP health check failed: {e}")
            return {
                "status": "FAIL",
                "latency_ms": 0,
                "details": {"error": str(e)}
            }
