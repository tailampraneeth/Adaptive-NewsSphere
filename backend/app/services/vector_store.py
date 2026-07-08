import logging
import time
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings

logger = logging.getLogger("adaptive-newssphere.vector_store")

class VectorStoreService:
    def __init__(self):
        # Configure client connection
        self.qdrant_url = settings.QDRANT_URL
        logger.info(f"Connecting to Qdrant Vector DB: {self.qdrant_url} ...")
        self.client = QdrantClient(url=self.qdrant_url)

        self.collection_name = "articles"
        self.story_collection_name = "stories"
        self.user_preferences_collection_name = "user_preferences"  # Milestone 4

        # Ensure target collections are initialized
        self._ensure_collections_exist()

    def _ensure_collections_exist(self):
        """Initializes the articles and stories collections if not already defined."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]

            created_any = False
            # 1. Create articles collection
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: '{self.collection_name}' (dim=384, dist=COSINE)...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384,
                        distance=models.Distance.COSINE
                    )
                )
                created_any = True

            # 2. Create stories collection
            if self.story_collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection: '{self.story_collection_name}' (dim=384, dist=COSINE)...")
                self.client.create_collection(
                    collection_name=self.story_collection_name,
                    vectors_config=models.VectorParams(
                        size=384,
                        distance=models.Distance.COSINE
                    )
                )
                created_any = True

            # 3. Create user_preferences collection (Milestone 4)
            if self.user_preferences_collection_name not in collection_names:
                logger.info(
                    f"Creating Qdrant collection: '{self.user_preferences_collection_name}' "
                    "(dim=384, dist=COSINE)..."
                )
                self.client.create_collection(
                    collection_name=self.user_preferences_collection_name,
                    vectors_config=models.VectorParams(
                        size=384,
                        distance=models.Distance.COSINE
                    )
                )
                created_any = True

            if created_any:
                logger.info("Waiting 0.5s for collection synchronization...")
                time.sleep(0.5)
                logger.info("Successfully initialized all vector collections.")
        except Exception as e:
            logger.error(f"Failed to verify/initialize Qdrant collections: {e}")

    def upsert_vector(self, collection: str, point_id: str, vector: List[float], payload: Dict[str, Any]) -> bool:
        """Indexes an embedding vector and payload into the target Qdrant collection."""
        try:
            self.client.upsert(
                collection_name=collection,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ],
                wait=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert vector {point_id} to collection '{collection}': {e}")
            return False

    def search_similar(
        self,
        collection: str,
        vector: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Queries the target collection for top-K nearest neighbors using Cosine similarity."""
        try:
            query_filter = None
            if filter_dict:
                conditions: List[models.Condition] = []
                for key, val in filter_dict.items():
                    if val is not None:
                        conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=val)
                            )
                        )
                if conditions:
                    query_filter = models.Filter(must=conditions)

            results = self.client.search(
                collection_name=collection,
                query_vector=vector,
                limit=top_k,
                query_filter=query_filter
            )

            matches = []
            for hit in results:
                matches.append({
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                })
            return matches
        except Exception as e:
            logger.error(f"Similarity search query failed on collection '{collection}': {e}")
            return []

    def health(self) -> dict:
        """Checks Qdrant connection and HTTP endpoint readiness."""
        try:
            t0 = time.time()
            self.client.get_collections()
            latency = (time.time() - t0) * 1000

            return {
                "status": "PASS",
                "latency_ms": round(latency, 2),
                "details": {
                    "connected": True,
                    "url": self.qdrant_url,
                    "collections": [self.collection_name, self.story_collection_name]
                }
            }
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {
                "status": "FAIL",
                "latency_ms": 0,
                "details": {"error": str(e)}
            }
