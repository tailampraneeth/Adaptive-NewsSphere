import logging
from typing import List, Dict, Any
from datetime import datetime
from app.core.config import settings
from app.database.models.conversation import ChatMessage

logger = logging.getLogger("adaptive-newssphere.prompt_builder")


class PromptBuilderService:
    """Handles grounding, formatting, context mapping, and history truncation for RAG prompts."""

    @staticmethod
    def build_system_instructions() -> str:
        """Returns objective grounding guidelines for the assistant model."""
        return (
            "You are an objective AI assistant for Adaptive NewsSphere.\n"
            "Generate a response to the USER QUERY using only the verified facts and source texts provided in the RAG CONTEXT below.\n"
            "Strict Guidelines:\n"
            "- Do not hallucinate or use external knowledge.\n"
            "- If the sources contradict each other, clearly explain both views.\n"
            "- Cite the source articles using [Source: Publisher Name] format exactly whenever mentioning facts from them.\n"
            f"- If the answer cannot be found in the context, say: \"{settings.NO_CONTEXT_MESSAGE}\"\n"
            "- Keep answers concise and direct."
        )

    @staticmethod
    def build_context_block(context_chunks: List[Dict[str, Any]]) -> str:
        """Formats context chunks from Qdrant into a clean prompt block."""
        context_str = "RAG CONTEXT:\n"
        if not context_chunks:
            context_str += "No verified context sources available.\n"
        else:
            for idx, chunk in enumerate(context_chunks):
                published = chunk.get("published_at")
                pub_date = published.isoformat() if isinstance(published, datetime) else str(published)
                context_str += (
                    f"--- Source [{idx + 1}]: {chunk['publisher_name']} ---\n"
                    f"Title: {chunk['title']}\n"
                    f"Published Date: {pub_date}\n"
                    f"Content:\n{chunk['content']}\n\n"
                )
        return context_str

    @staticmethod
    def build_history_block(history: List[ChatMessage]) -> str:
        """Formats chat history logs for message memory context."""
        history_str = "CHAT HISTORY:\n"
        for msg in history:
            role = "User" if msg.sender == "user" else "Assistant"
            history_str += f"{role}: {msg.message}\n"
        return history_str

    @classmethod
    def build_prompt(
        cls,
        query: str,
        context_chunks: List[Dict[str, Any]],
        history: List[ChatMessage]
    ) -> str:
        """Compiles instructions, context sources, history threads, and user query into a single prompt."""
        system_instructions = cls.build_system_instructions()
        context_str = cls.build_context_block(context_chunks)
        history_str = cls.build_history_block(history)
        current_query = f"USER QUERY:\n{query}"

        return f"{system_instructions}\n\n{context_str}\n{history_str}\n{current_query}"
