import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.responses import StreamingResponse

from sqlalchemy.future import select

from app.core.config import settings
from app.database.models.user import User
from app.database.models.story import Story
from app.database.models.article import Article
from app.database.models.publisher import Publisher
from app.database.models.conversation import ChatSession, ChatMessage
from app.services.llm_providers.base import BaseLLMProvider
from app.services.llm_providers.gemini import GeminiProvider
from app.services.llm_providers.mock import MockProvider
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.conversation_service import ConversationService
from app.services.prompt_builder import PromptBuilderService


# ── Fixtures ──

@pytest.fixture
def mock_embedder():
    embedder = MagicMock()
    embedder.generate_embedding.return_value = [0.1] * 384
    return embedder


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.collection_name = "articles"
    store.search_similar.return_value = []
    store.health.return_value = {"status": "PASS"}
    return store


@pytest.fixture
def mock_provider():
    return MockProvider(model_name="mock-model")


@pytest.fixture
def mock_llm_service(mock_provider):
    return LLMService(mock_provider)


# ── Tests ──

@pytest.mark.asyncio
async def test_provider_agnostic_abstraction(mock_provider):
    """1. BaseLLMProvider, MockProvider, and GeminiProvider implementation checks."""
    assert isinstance(mock_provider, BaseLLMProvider)
    assert mock_provider.get_model_name() == "mock-model"

    with patch("google.generativeai.GenerativeModel"):
        gemini = GeminiProvider(api_key="test-key", model_name="gemini-2.0-flash")
        assert isinstance(gemini, BaseLLMProvider)
        assert gemini.get_model_name() == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_gemini_provider_generate_called():
    """2. GeminiProvider generate delegates content call to thread pool."""
    with patch("google.generativeai.GenerativeModel") as mock_gen:
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Hello from Gemini"
        mock_model_instance.generate_content.return_value = mock_response
        mock_gen.return_value = mock_model_instance

        gemini = GeminiProvider(api_key="test-key", model_name="gemini-2.0-flash")
        resp = await gemini.generate("Context prompt")
        assert resp == "Hello from Gemini"
        mock_model_instance.generate_content.assert_called_once_with("Context prompt")


@pytest.mark.asyncio
async def test_mock_provider_returns_citations(mock_provider):
    """3. MockProvider generates answer text with correctly formatted citations based on prompt."""
    prompt = "Publisher: BBC\nContent: article body\nUSER QUERY: what happened?"
    resp = await mock_provider.generate(prompt)
    assert "[Source: BBC]" in resp
    assert "verified reports" in resp


@pytest.mark.asyncio
async def test_rag_context_retrieval_story_filtering(db_session, mock_embedder, mock_vector_store, mock_llm_service):
    """4. RAG retrieval queries the vector store with correct story filters."""
    # Seed data
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Major Story")
    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="bbc",
        title="Breaking News Article",
        body_text="This is a long article body text.",
        source_url="http://bbc.com/1",
        published_at=datetime.now(timezone.utc),
        content_hash="hash1",
        article_hash="hash2"
    )
    db_session.add_all([pub, story, art])
    await db_session.commit()

    mock_vector_store.search_similar.return_value = [
        {"id": str(art.id), "score": 0.85, "payload": {}}
    ]

    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    chunks, _ = await rag_service.retrieve_context(db_session, "what happened?", story.id)

    assert len(chunks) == 1
    assert chunks[0]["article_id"] == str(art.id)
    assert chunks[0]["publisher_name"] == "BBC News"
    mock_vector_store.search_similar.assert_called_once_with(
        collection="articles",
        vector=[0.1] * 384,
        top_k=settings.RAG_TOP_K,
        filter_dict={"story_id": str(story.id)}
    )


@pytest.mark.asyncio
async def test_rag_context_threshold_filtering(db_session, mock_embedder, mock_vector_store, mock_llm_service):
    """5. Chunks matching scores below the similarity threshold are discarded."""
    mock_vector_store.search_similar.return_value = [
        {"id": str(uuid.uuid4()), "score": 0.35, "payload": {}}  # below default 0.55 threshold
    ]
    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    chunks, _ = await rag_service.retrieve_context(db_session, "query", uuid.uuid4())
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_rag_prompt_compilation_with_history(mock_embedder, mock_vector_store, mock_llm_service):
    """6. build_prompt correctly formats the past thread conversations."""
    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    history = [
        ChatMessage(sender="user", message="hello"),
        ChatMessage(sender="assistant", message="hi there")
    ]
    prompt = rag_service.build_prompt("new query", [], history)
    assert "User: hello" in prompt
    assert "Assistant: hi there" in prompt
    assert "USER QUERY:\nnew query" in prompt


@pytest.mark.asyncio
async def test_rag_prompt_compilation_with_context(mock_embedder, mock_vector_store, mock_llm_service):
    """7. build_prompt injects chunk titles, publishers, and body texts."""
    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    chunks = [{
        "publisher_name": "BBC News",
        "title": "Article Title",
        "published_at": "2026-07-09T00:00:00Z",
        "content": "excerpt content"
    }]
    prompt = rag_service.build_prompt("query", chunks, [])
    assert "BBC News" in prompt
    assert "Article Title" in prompt
    assert "excerpt content" in prompt


@pytest.mark.asyncio
async def test_confidence_calculation_formula(mock_embedder, mock_vector_store, mock_llm_service):
    """8. calculate_confidence computes score based on weights and counts."""
    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    chunks = [
        {"similarity_score": 0.80, "article_id": "art-1", "content": "x" * 1500},
        {"similarity_score": 0.70, "article_id": "art-2", "content": "y" * 1500}
    ]
    # avg_sim = 0.75, retrieved = 2, size = 3000, citations = 1
    # w1*0.75 (0.375) + w2*(2/3) (0.133) + w3*(3000/6000) (0.05) + w4*(1/2) (0.10) = 0.658
    score = rag_service.calculate_confidence(chunks, citations_count=1)
    assert score == 0.6583


@pytest.mark.asyncio
async def test_no_context_optimization_prevents_llm_call(db_session):
    """9. Empty contexts return default response directly without calling LLMService."""
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Major Story")
    user = User(id=uuid.uuid4(), email="user@test.com")
    db_session.add_all([pub, story, user])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)

    # Route message handler using mock context retrieve returning empty
    with patch("app.core.config.settings.ENABLE_RAG_STREAMING", False):
        with patch("app.services.rag_service.RAGService.retrieve_context", return_value=([], {})):
            with patch("app.services.llm_service.LLMService.generate") as mock_gen:
                from app.api.routes.chat import send_message
                from app.api.schemas.chat import SendMessageRequest
                
                resp = await send_message(session.id, SendMessageRequest(message="What is this?"), db_session)
                
                mock_gen.assert_not_called()
                # If streaming is off it returns message response directly
                if not isinstance(resp, StreamingResponse):
                    assert resp.message == settings.NO_CONTEXT_MESSAGE
                    assert resp.chat_metadata["unanswered"] is True


@pytest.mark.asyncio
async def test_chat_health_endpoint(db_session):
    """10. GET /api/v1/chat/health returns correct schema status and stats."""
    from app.api.routes.chat import get_chat_health
    resp = await get_chat_health(db_session)
    assert resp.llm_provider in ["gemini", "mock"]
    assert resp.prompt_version == "v1"
    assert resp.total_sessions == 0


@pytest.mark.asyncio
async def test_create_session_route_creates_db_record(db_session):
    """11. ConversationService.create_session inserts a session into the database."""
    user = User(id=uuid.uuid4(), email="user@test.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    db_session.add_all([user, story])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)
    assert session.title == "New Conversation"
    assert session.message_count == 0

    # Verify db record
    stmt = select(ChatSession).where(ChatSession.id == session.id)
    res = await db_session.execute(stmt)
    db_record = res.scalar_one_or_none()
    assert db_record is not None
    assert db_record.user_id == user.id


@pytest.mark.asyncio
async def test_create_session_with_invalid_story_returns_404(db_session):
    """12. ConversationService throws ValueError on invalid story, returning 404."""
    with pytest.raises(ValueError):
        await ConversationService.create_session(db_session, uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_get_session_details_with_history(db_session):
    """13. ConversationService.get_session eager loads all message list elements."""
    user = User(id=uuid.uuid4(), email="user@test.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    db_session.add_all([user, story])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)
    await ConversationService.save_message(db_session, session.id, "user", "hi", [])
    
    loaded = await ConversationService.get_session(db_session, session.id)
    assert len(loaded.messages) == 1
    assert loaded.messages[0].message == "hi"


@pytest.mark.asyncio
async def test_delete_session_removes_messages(db_session):
    """14. Deleting session cascades deletes to all message logs."""
    user = User(id=uuid.uuid4(), email="user@test.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    db_session.add_all([user, story])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)
    await ConversationService.save_message(db_session, session.id, "user", "hi", [])
    
    deleted = await ConversationService.delete_session(db_session, session.id)
    assert deleted is True

    # Verify message is gone
    msg_stmt = select(ChatMessage).where(ChatMessage.session_id == session.id)
    res = await db_session.execute(msg_stmt)
    assert len(res.scalars().all()) == 0


@pytest.mark.asyncio
async def test_list_user_sessions_route(db_session):
    """15. ConversationService lists all user active sessions newest-first."""
    user = User(id=uuid.uuid4(), email="user@test.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    db_session.add_all([user, story])
    await db_session.commit()

    session1 = await ConversationService.create_session(db_session, user.id, story.id)
    session2 = await ConversationService.create_session(db_session, user.id, story.id)

    sessions = await ConversationService.get_user_sessions(db_session, user.id)
    assert len(sessions) == 2
    assert {s.id for s in sessions} == {session1.id, session2.id}


@pytest.mark.asyncio
async def test_send_message_sync_saves_metadata(db_session, mock_embedder, mock_vector_store):
    """16. send_message non-streaming saves user and assistant messages, updating titles and metadata."""
    # Seed data
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Breaking news")
    user = User(id=uuid.uuid4(), email="user@test.com")
    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="bbc",
        title="Article Title",
        body_text="Verified facts content.",
        source_url="http://bbc.com/1",
        published_at=datetime.now(timezone.utc),
        content_hash="hash1",
        article_hash="hash2"
    )
    db_session.add_all([pub, story, user, art])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)

    mock_vector_store.search_similar.return_value = [
        {"id": str(art.id), "score": 0.85, "payload": {}}
    ]

    # Temporarily disable streaming for synchronous test
    with patch("app.core.config.settings.ENABLE_RAG_STREAMING", False):
        with patch("app.api.routes.chat._get_rag_service") as mock_rag_get:
            provider = MockProvider(model_name="mock-model")
            llm_service = LLMService(provider)
            rag_service = RAGService(mock_embedder, mock_vector_store, llm_service)
            mock_rag_get.return_value = rag_service

            from app.api.routes.chat import send_message
            from app.api.schemas.chat import SendMessageRequest
            
            resp = await send_message(session.id, SendMessageRequest(message="What is this details?"), db_session)
            
            assert resp.sender == "assistant"
            assert "[Source: BBC News]" in resp.message
            assert resp.chat_metadata["retrieved_article_count"] == 1
            assert resp.chat_metadata["confidence"] > 0.0

            # Reload session to verify title auto-generation from first user message
            session_db = (await db_session.execute(select(ChatSession).where(ChatSession.id == session.id))).scalar()
            assert session_db.title == "What is this details?"
            assert session_db.message_count == 2


@pytest.mark.asyncio
async def test_send_message_streaming_sse_yield_loop(db_session, mock_embedder, mock_vector_store):
    """17. send_message streaming SSE format returns StreamingResponse and yields chunk data."""
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Breaking news")
    user = User(id=uuid.uuid4(), email="user@test.com")
    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="bbc",
        title="Article Title",
        body_text="Verified facts content.",
        source_url="http://bbc.com/1",
        published_at=datetime.now(timezone.utc),
        content_hash="hash1",
        article_hash="hash2"
    )
    db_session.add_all([pub, story, user, art])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)

    mock_vector_store.search_similar.return_value = [
        {"id": str(art.id), "score": 0.85, "payload": {}}
    ]

    with patch("app.core.config.settings.ENABLE_RAG_STREAMING", True):
        with patch("app.api.routes.chat._get_rag_service") as mock_rag_get:
            provider = MockProvider(model_name="mock-model")
            llm_service = LLMService(provider)
            rag_service = RAGService(mock_embedder, mock_vector_store, llm_service)
            mock_rag_get.return_value = rag_service

            from app.api.routes.chat import send_message
            from app.api.schemas.chat import SendMessageRequest

            resp = await send_message(session.id, SendMessageRequest(message="What is this?"), db_session)
            assert isinstance(resp, StreamingResponse)

            chunks = []
            async for chunk in resp.body_iterator:
                chunks.append(chunk)

            assert len(chunks) > 0
            # Last block should be [DONE]
            assert "data: [DONE]" in chunks[-1]


@pytest.mark.asyncio
async def test_prompt_version_saved_in_message(db_session, mock_embedder, mock_vector_store):
    user = User(id=uuid.uuid4(), email="user@test.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    db_session.add_all([user, story])
    await db_session.commit()
    session = await ConversationService.create_session(db_session, user.id, story.id)

    # Create assistant message directly
    msg = await ConversationService.save_message(
        db=db_session,
        session_id=session.id,
        sender="assistant",
        message="response",
        citations=[],
        prompt_version="v2",
        chat_metadata={}
    )
    assert msg.prompt_version == "v2"


@pytest.mark.asyncio
async def test_citation_extraction_from_mock_response(mock_embedder, mock_vector_store, mock_llm_service):
    """19. extract_citations maps publisher names in strings to context article structures."""
    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    chunks = [
        {"article_id": "art-1", "publisher_name": "BBC News", "title": "T1", "published_at": datetime.now(timezone.utc), "similarity_score": 0.85}
    ]
    citations = rag_service.extract_citations("Based on [Source: BBC News] we confirm details.", chunks)
    assert len(citations) == 1
    assert citations[0]["article_id"] == "art-1"
    assert citations[0]["publisher_name"] == "BBC News"


@pytest.mark.asyncio
async def test_history_truncation_limit_respected(db_session):
    """20. get_history slices logs to only fetch up to max_messages counts."""
    user = User(id=uuid.uuid4(), email="user@test.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    db_session.add_all([user, story])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)
    for i in range(12):
        await ConversationService.save_message(db_session, session.id, "user", f"msg {i}", [])

    history = await ConversationService.get_history(db_session, session.id, max_messages=5)
    assert len(history) == 5
    assert history[0].message == "msg 7"
    assert history[-1].message == "msg 11"


def test_prompt_builder_service_compiles_prompt():
    """21. PromptBuilderService compiles system instructions, context chunks, history, and query."""
    chunks = [
        {"publisher_name": "BBC News", "title": "Headline", "published_at": "2026-07-09T00:00:00Z", "content": "RAG facts."}
    ]
    history = [
        ChatMessage(sender="user", message="Hi"),
        ChatMessage(sender="assistant", message="Hello")
    ]
    prompt = PromptBuilderService.build_prompt("User query text", chunks, history)
    
    assert "You are an objective AI assistant" in prompt
    assert "BBC News" in prompt
    assert "RAG facts." in prompt
    assert "User: Hi" in prompt
    assert "Assistant: Hello" in prompt
    assert "USER QUERY:\nUser query text" in prompt


@pytest.mark.asyncio
async def test_citation_confidence_math(mock_embedder, mock_vector_store, mock_llm_service):
    """22. extract_citations computes confidence and similarity from context chunks."""
    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    chunks = [
        {
            "article_id": "art-1",
            "publisher_name": "Tech Crunch",
            "title": "Title TC",
            "published_at": "2026-07-10",
            "similarity_score": 0.8754
        }
    ]
    citations = rag_service.extract_citations("According to [Source: Tech Crunch], CPU models are good.", chunks)
    assert len(citations) == 1
    assert citations[0]["similarity"] == 0.8754
    assert citations[0]["confidence"] == 0.8754


@pytest.mark.asyncio
async def test_retrieval_trace_diagnostics(db_session, mock_embedder, mock_vector_store, mock_llm_service):
    """23. RAGService retrieve_context returns both matching chunks and a detailed retrieval trace."""
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Story Title")
    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="bbc",
        title="Article Title",
        body_text="Verified facts content.",
        source_url="http://bbc.com/1",
        published_at=datetime.now(timezone.utc),
        content_hash="hash1",
        article_hash="hash2"
    )
    db_session.add_all([pub, story, art])
    await db_session.commit()

    rag_service = RAGService(mock_embedder, mock_vector_store, mock_llm_service)
    mock_vector_store.search_similar.return_value = [
        {"id": str(art.id), "score": 0.85, "payload": {}}
    ]
    
    chunks, trace = await rag_service.retrieve_context(db_session, "facts query", story.id)
    assert len(chunks) == 1
    assert trace["top_k"] == settings.RAG_TOP_K
    assert trace["threshold"] == settings.RAG_SIMILARITY_THRESHOLD
    assert trace["retrieved_before_filter"] == 1
    assert trace["retrieved_after_filter"] == 1
    assert trace["passed_threshold"] is True


@pytest.mark.asyncio
async def test_conversation_version_persistence(db_session, mock_embedder, mock_vector_store):
    """24. send_message route persists engine version in chat metadata."""
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Breaking news")
    user = User(id=uuid.uuid4(), email="user@test.com")
    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="bbc",
        title="Article Title",
        body_text="Verified facts content.",
        source_url="http://bbc.com/1",
        published_at=datetime.now(timezone.utc),
        content_hash="hash1",
        article_hash="hash2"
    )
    db_session.add_all([pub, story, user, art])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)
    mock_vector_store.search_similar.return_value = [
        {"id": str(art.id), "score": 0.85, "payload": {}}
    ]

    with patch("app.core.config.settings.ENABLE_RAG_STREAMING", False):
        with patch("app.api.routes.chat._get_rag_service") as mock_rag_get:
            provider = MockProvider(model_name="mock-model")
            llm_service = LLMService(provider)
            rag_service = RAGService(mock_embedder, mock_vector_store, llm_service)
            mock_rag_get.return_value = rag_service

            from app.api.routes.chat import send_message
            from app.api.schemas.chat import SendMessageRequest

            resp = await send_message(session.id, SendMessageRequest(message="What is this?"), db_session)
            assert resp.chat_metadata["conversation_engine_version"] == "v1"
            assert "retrieval_trace" in resp.chat_metadata
            assert "streaming_metrics" in resp.chat_metadata
            assert resp.chat_metadata["prompt_size_chars"] > 0
            assert resp.chat_metadata["response_size_chars"] > 0


@pytest.mark.asyncio
async def test_streaming_telemetry_metrics(db_session, mock_embedder, mock_vector_store):
    """25. send_message streaming path records first_token_latency, stream_duration, and output token counts."""
    pub = Publisher(id="bbc", name="BBC News", base_url="http://bbc.com")
    story = Story(id=uuid.uuid4(), title="Breaking news")
    user = User(id=uuid.uuid4(), email="user@test.com")
    art = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="bbc",
        title="Article Title",
        body_text="Verified facts content.",
        source_url="http://bbc.com/1",
        published_at=datetime.now(timezone.utc),
        content_hash="hash1",
        article_hash="hash2"
    )
    db_session.add_all([pub, story, user, art])
    await db_session.commit()

    session = await ConversationService.create_session(db_session, user.id, story.id)
    mock_vector_store.search_similar.return_value = [
        {"id": str(art.id), "score": 0.85, "payload": {}}
    ]

    with patch("app.core.config.settings.ENABLE_RAG_STREAMING", True):
        with patch("app.api.routes.chat._get_rag_service") as mock_rag_get:
            provider = MockProvider(model_name="mock-model")
            llm_service = LLMService(provider)
            rag_service = RAGService(mock_embedder, mock_vector_store, llm_service)
            mock_rag_get.return_value = rag_service

            from app.api.routes.chat import send_message
            from app.api.schemas.chat import SendMessageRequest

            resp = await send_message(session.id, SendMessageRequest(message="What is this?"), db_session)
            
            # Consume SSE stream output to trigger generator metrics
            body_list = []
            async for line in resp.body_iterator:
                body_list.append(line)

            # Retrieve final message to inspect persisted metadata
            history = await ConversationService.get_history(db_session, session.id, max_messages=5)
            assistant_msg = history[-1]
            
            meta = assistant_msg.chat_metadata
            assert meta["conversation_engine_version"] == "v1"
            assert "streaming_metrics" in meta
            assert meta["streaming_metrics"]["first_token_latency_ms"] >= 0.0
            assert meta["streaming_metrics"]["stream_duration_ms"] >= 0.0
            assert meta["streaming_metrics"]["estimated_output_tokens"] > 0
