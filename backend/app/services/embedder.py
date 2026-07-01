import logging
import time
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("adaptive-newssphere.embedder")

_shared_model = None

def get_shared_model() -> SentenceTransformer:
    """Singleton getter for the shared SentenceTransformer model instance."""
    global _shared_model
    if _shared_model is None:
        logger.info("Initializing SentenceTransformer: all-MiniLM-L6-v2 ...")
        t0 = time.time()
        _shared_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info(f"Loaded embedding model in {time.time() - t0:.2f}s")
    return _shared_model

class EmbedderService:
    def __init__(self):
        # Trigger lazy load
        self.model = get_shared_model()

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a 384-dimensional vector embedding for the input text."""
        if not text or not text.strip():
            # Return zero vector if empty
            return [0.0] * 384

        # Run prediction
        vector = self.model.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generates embeddings in batch for optimal GPU/CPU throughput."""
        if not texts:
            return []

        # Clean empty texts
        cleaned_texts = [t if t and t.strip() else "" for t in texts]
        vectors = self.model.encode(cleaned_texts, batch_size=32, show_progress_bar=False)
        return [v.tolist() for v in vectors]

    def health(self) -> dict:
        """AI Service health check implementation."""
        try:
            t0 = time.time()
            vector = self.generate_embedding("Health check test phrase")
            latency = (time.time() - t0) * 1000
            assert len(vector) == 384
            return {
                "status": "PASS",
                "latency_ms": round(latency, 2),
                "details": {
                    "model_name": "all-MiniLM-L6-v2",
                    "dimension": 384,
                    "device": str(self.model.device)
                }
            }
        except Exception as e:
            logger.error(f"Embedder health check failed: {e}")
            return {
                "status": "FAIL",
                "latency_ms": 0,
                "details": {"error": str(e)}
            }
