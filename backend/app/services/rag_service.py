import re
import time
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.database.models.article import Article
from app.database.models.publisher import Publisher
from app.database.models.conversation import ChatMessage
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService
from app.services.rag_chunker import RAGChunker

from app.services.prompt_builder import PromptBuilderService

logger = logging.getLogger("adaptive-newssphere.rag_service")

class RAGService:
    """Isolated RAG Pipeline Service orchestrating context retrieval, prompt building, and citation extraction."""

    def __init__(
        self,
        embedder: EmbedderService,
        vector_store: VectorStoreService,
        llm_service: LLMService
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm_service = llm_service

    async def retrieve_context(
        self,
        db: AsyncSession,
        query: str,
        story_id: uuid.UUID
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Retrieves and filters context chunks matching user query within specified story."""
        t0 = time.time()
        # Encode query to embedding vector
        query_vector = self.embedder.generate_embedding(query)

        matches = self.vector_store.search_similar(
            collection="articles",
            vector=query_vector,
            top_k=settings.RAG_TOP_K,
            filter_dict={"story_id": str(story_id)}
        )

        chunks: List[Dict[str, Any]] = []
        for match in matches:
            article_id = match["id"]
            score = match["score"]

            # Filter chunks below relevance threshold
            if score < settings.RAG_SIMILARITY_THRESHOLD:
                continue

            # Load article from database to verify and retrieve body text
            stmt = select(Article).where(Article.id == uuid.UUID(article_id))
            res = await db.execute(stmt)
            article = res.scalar_one_or_none()
            if not article:
                continue

            # Verify article belongs to the active conversation story filter
            if article.story_id != story_id:
                continue

            # Load publisher details
            publisher_name = "Unknown"
            if article.publisher_id:
                pub_stmt = select(Publisher).where(Publisher.id == article.publisher_id)
                pub_res = await db.execute(pub_stmt)
                pub = pub_res.scalar_one_or_none()
                if pub:
                    publisher_name = pub.name

            # Segment full article body into overlapping RAG chunks
            article_chunks = RAGChunker.chunk_text(
                article.body_text,
                chunk_size=settings.RAG_CHUNK_SIZE_CHARS,
                overlap=settings.RAG_CHUNK_OVERLAP_CHARS
            )

            for i, chunk_content in enumerate(article_chunks):
                chunks.append({
                    "article_id": article_id,
                    "title": article.title,
                    "publisher_name": publisher_name,
                    "published_at": article.published_at,
                    "content": chunk_content,
                    "similarity_score": score,
                    "chunk_index": i
                })

        # Rank all chunks by similarity score descending
        chunks.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Truncate to maximum context characters cap
        selected_chunks: List[Dict[str, Any]] = []
        current_len = 0
        for chunk in chunks:
            if current_len + len(chunk["content"]) > settings.RAG_MAX_CONTEXT_CHARS:
                break
            selected_chunks.append(chunk)
            current_len += len(chunk["content"])

        latency = (time.time() - t0) * 1000
        logger.info(f"Retrieved {len(selected_chunks)} chunks for story {story_id} in {latency:.2f}ms")

        trace = {
            "top_k": settings.RAG_TOP_K,
            "threshold": settings.RAG_SIMILARITY_THRESHOLD,
            "retrieved_before_filter": len(matches),
            "retrieved_after_filter": len(selected_chunks),
            "passed_threshold": len(selected_chunks) > 0
        }
        return selected_chunks, trace

    def calculate_confidence(
        self,
        chunks: List[Dict[str, Any]],
        citations_count: int
    ) -> float:
        """Computes a deterministic answer confidence score based on similarity and source coverage."""
        if not chunks:
            return 0.0

        avg_similarity = sum(c["similarity_score"] for c in chunks) / len(chunks)
        retrieved_count = len(set(c["article_id"] for c in chunks))
        context_chars = sum(len(c["content"]) for c in chunks)
        max_chars = settings.RAG_MAX_CONTEXT_CHARS

        # Confidence weights: similarity (0.5), article counts (0.2), context coverage (0.1), citations (0.2)
        w1, w2, w3, w4 = 0.50, 0.20, 0.10, 0.20

        score = (
            w1 * avg_similarity +
            w2 * min(1.0, retrieved_count / 3.0) +
            w3 * min(1.0, context_chars / float(max_chars)) +
            w4 * min(1.0, citations_count / 2.0)
        )
        return round(max(0.0, min(1.0, score)), 4)

    def build_prompt(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        history: List[ChatMessage]
    ) -> str:
        """Compiles grounding instructions, RAG chunks context, thread history, and active query via PromptBuilderService."""
        return PromptBuilderService.build_prompt(query, context_chunks, history)

    def extract_citations(
        self,
        response_text: str,
        context_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parses [Source: Publisher Name] markers in response and resolves them back to article records with confidence metrics."""
        if not settings.ENABLE_RAG_CITATIONS:
            return []

        # Find all occurrences of [Source: Publisher Name]
        matches = re.findall(r"\[Source:\s*([^\]]+)\]", response_text)
        citations: List[Dict[str, Any]] = []
        seen_articles = set()

        for match in matches:
            pub_name = match.strip()
            # Match publisher name to one of our retrieved chunks
            for chunk in context_chunks:
                if chunk["publisher_name"].lower() == pub_name.lower():
                    art_id = chunk["article_id"]
                    if art_id not in seen_articles:
                        seen_articles.add(art_id)
                        citations.append({
                            "article_id": art_id,
                            "publisher_name": chunk["publisher_name"],
                            "published_at": chunk["published_at"].isoformat() if isinstance(chunk["published_at"], datetime) else chunk["published_at"],
                            "title": chunk["title"],
                            "similarity": round(chunk.get("similarity_score", 1.0), 4),
                            "confidence": round(chunk.get("similarity_score", 1.0), 4)
                        })
                    break

        return citations
