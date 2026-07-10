import json
import uuid
import time
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select

from app.core.config import settings
from app.database.connection import get_db
from app.database.models.conversation import ChatSession, ChatMessage
from app.api.schemas.chat import (
    CreateSessionRequest,
    SendMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    ChatSessionSimpleResponse,
    ChatHealthResponse
)
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStoreService
from app.services.llm_service import LLMService, get_llm_provider
from app.services.rag_service import RAGService
from app.services.conversation_service import ConversationService

logger = logging.getLogger("adaptive-newssphere.routes.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["conversational-ai"])

# ── Router Initialization helper ─────────────────────────────────────────────

def _get_rag_service() -> RAGService:
    embedder = EmbedderService()
    vector_store = VectorStoreService()
    provider = get_llm_provider()
    llm_service = LLMService(provider)
    return RAGService(embedder, vector_store, llm_service)

# ── Route Handlers ───────────────────────────────────────────────────────────

@router.get("/health", response_model=ChatHealthResponse, summary="Get chat RAG health status")
async def get_chat_health(db: AsyncSession = Depends(get_db)) -> ChatHealthResponse:
    """Returns real-time health stats, prompt version, active sessions, and engine latencies."""
    rag_service = _get_rag_service()
    
    # 1. Check retriever (Qdrant) health
    qdrant_health = rag_service.vector_store.health()
    retriever_status = "online" if qdrant_health["status"] == "PASS" else "offline"

    # 2. Check provider details
    llm_provider = settings.LLM_PROVIDER
    configured_model = rag_service.llm_service.get_model_name()
    api_key_configured = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "mock_key_for_testing")

    # 3. Calculate database metrics (sessions and message counts)
    total_sessions_stmt = select(func.count(ChatSession.id))
    total_sessions = (await db.execute(total_sessions_stmt)).scalar() or 0

    total_messages_stmt = select(func.count(ChatMessage.id))
    total_messages = (await db.execute(total_messages_stmt)).scalar() or 0

    # 4. Calculate average response latency from assistant metadata
    metadata_stmt = select(ChatMessage.chat_metadata).where(ChatMessage.sender == "assistant")
    res = await db.execute(metadata_stmt)
    metadata_list = res.scalars().all()
    latencies = []
    for meta in metadata_list:
        if isinstance(meta, dict) and "total_latency_ms" in meta:
            latencies.append(meta["total_latency_ms"])
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    # Provider health status ping
    provider_health = "online"
    try:
        if llm_provider == "gemini" and not api_key_configured:
            provider_health = "degraded (mock key)"
    except Exception:
        provider_health = "offline"

    return ChatHealthResponse(
        llm_provider=llm_provider,
        configured_model=configured_model,
        prompt_version=settings.RAG_PROMPT_VERSION,
        conversation_engine_version=settings.CONVERSATION_ENGINE_VERSION,
        streaming_enabled=settings.ENABLE_RAG_STREAMING,
        api_key_configured=api_key_configured,
        avg_response_latency_ms=round(avg_latency, 2),
        total_sessions=total_sessions,
        total_messages=total_messages,
        retriever_status=retriever_status,
        provider_health=provider_health,
        qdrant_status=qdrant_health["status"]
    )


@router.post("/sessions", response_model=ChatSessionSimpleResponse, status_code=status.HTTP_201_CREATED, summary="Create chat session")
async def create_chat_session(
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db)
) -> ChatSession:
    """Creates a new conversational thread for a specific user and story cluster."""
    try:
        session = await ConversationService.create_session(
            db=db,
            user_id=request.user_id,
            story_id=request.story_id
        )
        return session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse, summary="Get chat session details")
async def get_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ChatSession:
    """Retrieves session details and full history of chat messages."""
    session = await ConversationService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found."
        )
    return session


@router.get("/sessions/user/{user_id}/list", response_model=List[ChatSessionSimpleResponse], summary="List user sessions")
async def list_user_sessions(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[ChatSession]:
    """Retrieves all chat sessions created by a user, ordered newest-first."""
    return await ConversationService.get_user_sessions(db, user_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK, summary="Delete chat session")
async def delete_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Deletes a chat session and cascades deletes to all message logs."""
    deleted = await ConversationService.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found."
        )
    return {"status": "success", "message": f"Chat session {session_id} deleted successfully."}


@router.post("/sessions/{session_id}/message", summary="Send message to session")
async def send_message(
    session_id: uuid.UUID,
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Sends a message to the chat assistant.

    If settings.ENABLE_RAG_STREAMING is True:
        Returns a Server-Sent Events (SSE) token stream yielding responses in real-time.
    Else:
        Executes generation synchronously and returns the complete ChatMessageResponse JSON.
    """
    t_start = time.time()
    
    # 1. Verify session exists
    session = await ConversationService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found."
        )

    # 2. Get conversational context/history (up to limit)
    history = await ConversationService.get_history(
        db=db,
        session_id=session_id,
        max_messages=settings.RAG_MAX_HISTORY_MESSAGES
    )
    history_messages_used = len(history)
    history_truncated = session.message_count > settings.RAG_MAX_HISTORY_MESSAGES

    # 3. Retrieve context chunks from Qdrant filtered by story_id
    # 3. Retrieve context chunks and retrieval trace diagnostics from Qdrant
    rag_service = _get_rag_service()
    t0_retrieval = time.time()
    context_chunks, retrieval_trace = await rag_service.retrieve_context(
        db=db,
        query=request.message,
        story_id=session.story_id
    )
    retrieval_latency = round((time.time() - t0_retrieval) * 1000, 2)
    context_size = sum(len(c["content"]) for c in context_chunks)
    retrieved_count = len(set(c["article_id"] for c in context_chunks))

    # Save user message to database
    await ConversationService.save_message(
        db=db,
        session_id=session_id,
        sender="user",
        message=request.message,
        citations=[]
    )

    # 4. Check for No-Context Optimization
    if not context_chunks:
        t_total = round((time.time() - t_start) * 1000, 2)
        meta = {
            "conversation_engine_version": settings.CONVERSATION_ENGINE_VERSION,
            "retrieval_latency_ms": retrieval_latency,
            "llm_latency_ms": 0.0,
            "total_latency_ms": t_total,
            "retrieved_article_count": 0,
            "average_similarity": 0.0,
            "highest_similarity": 0.0,
            "citations_count": 0,
            "context_size_chars": 0,
            "token_estimate": 0,
            "history_messages_used": history_messages_used,
            "history_truncated": history_truncated,
            "retrieval_count": 1,
            "confidence": 0.0,
            "unanswered": True,
            "retrieval_trace": retrieval_trace,
            "streaming_metrics": {
                "first_token_latency_ms": 0.0,
                "stream_duration_ms": 0.0,
                "estimated_output_tokens": 0
            },
            "prompt_size_chars": 0,
            "response_size_chars": len(settings.NO_CONTEXT_MESSAGE)
        }
        
        # Save assistant mock/fallback message
        assistant_msg = await ConversationService.save_message(
            db=db,
            session_id=session_id,
            sender="assistant",
            message=settings.NO_CONTEXT_MESSAGE,
            citations=[],
            prompt_version=settings.RAG_PROMPT_VERSION,
            chat_metadata=meta
        )

        if settings.ENABLE_RAG_STREAMING:
            async def no_context_generator():
                yield f"data: {json.dumps({'token': settings.NO_CONTEXT_MESSAGE})}\n\n"
                final_payload = {
                    "id": assistant_msg.id,
                    "message": settings.NO_CONTEXT_MESSAGE,
                    "citations": [],
                    "chat_metadata": meta
                }
                yield f"data: {json.dumps(final_payload)}\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(no_context_generator(), media_type="text/event-stream")
        else:
            return ChatMessageResponse.from_orm(assistant_msg)

    # 5. Compile Prompt and track size
    compiled_prompt = rag_service.build_prompt(
        query=request.message,
        context_chunks=context_chunks,
        history=history
    )
    prompt_size = len(compiled_prompt)

    # 6. Stream or Sync Generation Execution
    if settings.ENABLE_RAG_STREAMING:
        async def event_generator():
            full_response_text = []
            t0_llm = time.time()
            first_token_latency_ms = 0.0
            stream_start_time = 0.0
            tokens_count = 0
            
            try:
                async for chunk in rag_service.llm_service.generate_stream(compiled_prompt):
                    if not stream_start_time:
                        first_token_latency_ms = round((time.time() - t0_llm) * 1000, 2)
                        stream_start_time = time.time()
                    full_response_text.append(chunk)
                    tokens_count += 1
                    yield f"data: {json.dumps({'token': chunk})}\n\n"
            except Exception as stream_err:
                logger.error(f"Streaming error in chat turn: {stream_err}")
                yield f"data: {json.dumps({'error': str(stream_err)})}\n\n"
                yield "data: [DONE]\n\n"
                return

            llm_latency = round((time.time() - t0_llm) * 1000, 2)
            stream_duration_ms = round((time.time() - stream_start_time) * 1000, 2) if stream_start_time else 0.0
            response_text = "".join(full_response_text)

            # Extract citations
            citations = rag_service.extract_citations(response_text, context_chunks)
            citations_count = len(citations)

            # Similarity metrics
            similarities = [c["similarity_score"] for c in context_chunks]
            avg_similarity = round(sum(similarities) / len(similarities), 4) if similarities else 0.0
            highest_similarity = round(max(similarities), 4) if similarities else 0.0

            # Calculate confidence score
            confidence = rag_service.calculate_confidence(context_chunks, citations_count)

            # Metadata compile
            t_total = round((time.time() - t_start) * 1000, 2)
            meta = {
                "conversation_engine_version": settings.CONVERSATION_ENGINE_VERSION,
                "retrieval_latency_ms": retrieval_latency,
                "llm_latency_ms": llm_latency,
                "total_latency_ms": t_total,
                "retrieved_article_count": retrieved_count,
                "average_similarity": avg_similarity,
                "highest_similarity": highest_similarity,
                "citations_count": citations_count,
                "context_size_chars": context_size,
                "token_estimate": int(context_size / 4),
                "history_messages_used": history_messages_used,
                "history_truncated": history_truncated,
                "retrieval_count": 1,
                "confidence": confidence,
                "unanswered": False,
                "retrieval_trace": retrieval_trace,
                "streaming_metrics": {
                    "first_token_latency_ms": first_token_latency_ms,
                    "stream_duration_ms": stream_duration_ms,
                    "estimated_output_tokens": tokens_count
                },
                "prompt_size_chars": prompt_size,
                "response_size_chars": len(response_text)
            }

            # Save assistant message
            assistant_msg = await ConversationService.save_message(
                db=db,
                session_id=session_id,
                sender="assistant",
                message=response_text,
                citations=citations,
                prompt_version=settings.RAG_PROMPT_VERSION,
                chat_metadata=meta
            )

            # Yield final payload containing citations, database id, and confidence
            final_payload = {
                "id": assistant_msg.id,
                "message": response_text,
                "citations": citations,
                "chat_metadata": meta
            }
            yield f"data: {json.dumps(final_payload)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    else:
        # Non-streaming synchronous path
        t0_llm = time.time()
        response_text = await rag_service.llm_service.generate(compiled_prompt)
        llm_latency = round((time.time() - t0_llm) * 1000, 2)

        # Citations & similarity checks
        citations = rag_service.extract_citations(response_text, context_chunks)
        citations_count = len(citations)

        similarities = [c["similarity_score"] for c in context_chunks]
        avg_similarity = round(sum(similarities) / len(similarities), 4) if similarities else 0.0
        highest_similarity = round(max(similarities), 4) if similarities else 0.0

        confidence = rag_service.calculate_confidence(context_chunks, citations_count)

        # Latency aggregate
        t_total = round((time.time() - t_start) * 1000, 2)
        meta = {
            "conversation_engine_version": settings.CONVERSATION_ENGINE_VERSION,
            "retrieval_latency_ms": retrieval_latency,
            "llm_latency_ms": llm_latency,
            "total_latency_ms": t_total,
            "retrieved_article_count": retrieved_count,
            "average_similarity": avg_similarity,
            "highest_similarity": highest_similarity,
            "citations_count": citations_count,
            "context_size_chars": context_size,
            "token_estimate": int(context_size / 4),
            "history_messages_used": history_messages_used,
            "history_truncated": history_truncated,
            "retrieval_count": 1,
            "confidence": confidence,
            "unanswered": False,
            "retrieval_trace": retrieval_trace,
            "streaming_metrics": {
                "first_token_latency_ms": 0.0,
                "stream_duration_ms": 0.0,
                "estimated_output_tokens": int(len(response_text) / 4)
            },
            "prompt_size_chars": prompt_size,
            "response_size_chars": len(response_text)
        }

        # Save assistant message
        assistant_msg = await ConversationService.save_message(
            db=db,
            session_id=session_id,
            sender="assistant",
            message=response_text,
            citations=citations,
            prompt_version=settings.RAG_PROMPT_VERSION,
            chat_metadata=meta
        )

        return ChatMessageResponse.from_orm(assistant_msg)
