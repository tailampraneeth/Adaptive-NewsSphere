import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models.publisher import Publisher
from app.database.models.story import Story, StoryRelation
from app.database.models.article import Article
from app.services.embedder import EmbedderService
from app.services.vector_store import VectorStoreService
from app.services.story_verification import StoryVerificationService

@pytest.mark.asyncio
async def test_story_verification_agreement_flow(db_session):
    """
    Validates the story verification pipeline when publisher claims agree semantically.
    """
    # 1. Create Mock Publishers
    pub_reuters = Publisher(id="reuters", name="Reuters", base_url="https://reuters.com", credibility_score=0.95, bias_rating="center")
    pub_ap = Publisher(id="ap", name="Associated Press", base_url="https://apnews.com", credibility_score=0.93, bias_rating="center")
    db_session.add_all([pub_reuters, pub_ap])
    await db_session.commit()

    # 2. Create Story
    story = Story(
        id=uuid.uuid4(),
        title="AI Framework Released",
        summary="A new open source AI framework is launched.",
        article_count=2,
        publisher_diversity=2,
        status="ACTIVE"
    )
    db_session.add(story)
    await db_session.commit()

    # 3. Create agreeing Articles
    art_a = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="reuters",
        title="OpenAI launches new execution optimization techniques.",
        body_text="Researchers introduced new techniques to optimize execution footprints for LLMs. This decreases serving costs substantially.",
        source_url="https://reuters.com/tech-optimization",
        published_at=datetime.now(timezone.utc) - timedelta(hours=8),
        content_hash="hash_opt_a",
        article_hash="art_opt_a",
        quality_score=0.90
    )
    art_b = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="ap",
        title="New methods launched to optimize model execution footprint.",
        body_text="Researchers introduced new techniques to optimize execution footprints for LLMs. This decreases serving costs substantially.",
        source_url="https://apnews.com/tech-footprint",
        published_at=datetime.now(timezone.utc),
        content_hash="hash_opt_b",
        article_hash="art_opt_b",
        quality_score=0.92
    )
    db_session.add_all([art_a, art_b])
    await db_session.commit()

    # 4. Initialize Services & Run Verification
    from unittest.mock import MagicMock
    embedder = MagicMock(spec=EmbedderService)

    # Sentences:
    # 0: "Researchers introduced new techniques..." (reuters)
    # 1: "This decreases serving costs substantially." (reuters)
    # 2: "Researchers introduced new techniques..." (ap)
    # 3: "This decreases serving costs substantially." (ap)
    v0 = [1.0] + [0.0] * 383
    v1 = [0.0, 1.0] + [0.0] * 382
    v2 = [1.0] + [0.0] * 383
    v3 = [0.0, 1.0] + [0.0] * 382
    embedder.generate_embeddings_batch.return_value = [v0, v1, v2, v3]

    vector_store = VectorStoreService()
    verifier = StoryVerificationService(db_session, embedder, vector_store)

    await verifier.verify_story(story.id)

    # 5. Fetch verified Story and assert outputs
    stmt = select(Story).where(Story.id == story.id).options(
        selectinload(Story.articles),
        selectinload(Story.timelines)
    )
    res = await db_session.execute(stmt)
    verified_story = res.scalar_one()

    assert verified_story.verification_score >= 0.70
    assert verified_story.credibility_score >= 0.85
    assert verified_story.has_conflicts is False
    assert len(verified_story.evidence) == 2
    assert len(verified_story.timelines) == 2  # Gaps between articles is 8 hours > 6 hours milestone

    # Assert verification_metadata Explainability JSON
    meta = verified_story.verification_metadata
    assert meta is not None
    assert meta["agreement_score"] == 1.0
    assert meta["publisher_diversity"] == 2
    assert meta["trusted_publishers"] == 2
    assert meta["supporting_articles"] == 2
    assert meta["conflicting_articles"] == 0
    assert meta["semantic_confidence"] == 1.0

    # Assert timeline sorting, types, and confidence parameters
    timelines = verified_story.timelines
    timelines.sort(key=lambda t: t.event_timestamp)
    assert timelines[0].headline == art_a.title
    assert timelines[0].supporting_articles == 1
    assert timelines[0].supporting_publishers == 1
    assert timelines[0].confidence_score == 0.90  # quality score of reuters is 0.90
    assert timelines[0].event_type == "first_appearance"

    assert timelines[1].headline == art_b.title
    assert timelines[1].supporting_articles == 1
    assert timelines[1].supporting_publishers == 1
    assert timelines[1].confidence_score == 0.92  # quality score of ap is 0.92
    assert timelines[1].event_type == "update"

@pytest.mark.asyncio
async def test_story_verification_conflict_flow(db_session):
    """
    Validates numeric and factual conflict detection inside multi-source story streams.
    """
    # 1. Create Publishers
    pub_wsj = Publisher(id="wsj", name="Wall Street Journal", base_url="https://wsj.com", credibility_score=0.92, bias_rating="right-center")
    pub_nyt = Publisher(id="nyt", name="New York Times", base_url="https://nytimes.com", credibility_score=0.91, bias_rating="left-center")
    db_session.add_all([pub_wsj, pub_nyt])
    await db_session.commit()

    # 2. Create Story
    story = Story(
        id=uuid.uuid4(),
        title="Stock Price Valuation Shifts",
        summary="A major tech company sees massive trading moves.",
        article_count=2,
        publisher_diversity=2,
        status="ACTIVE"
    )
    db_session.add(story)
    await db_session.commit()

    # 3. Create conflicting Articles (mismatched numbers in same claim contexts)
    art_wsj = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="wsj",
        title="Company reports 20 percent revenue growth in Q2.",
        body_text="In their latest financial filing, the tech conglomerate announced they generated 20 percent growth in Q2 revenues.",
        source_url="https://wsj.com/earnings",
        published_at=datetime.now(timezone.utc) - timedelta(hours=2),
        content_hash="hash_wsj",
        article_hash="art_wsj",
        quality_score=0.94
    )
    art_nyt = Article(
        id=uuid.uuid4(),
        story_id=story.id,
        publisher_id="nyt",
        title="Company reports 80 percent revenue growth in Q2.",
        body_text="In their latest financial filing, the tech conglomerate announced they generated 80 percent growth in Q2 revenues.",
        source_url="https://nytimes.com/earnings",
        published_at=datetime.now(timezone.utc),
        content_hash="hash_nyt",
        article_hash="art_nyt",
        quality_score=0.93
    )
    db_session.add_all([art_wsj, art_nyt])
    await db_session.commit()

    # 4. Run Verification
    from unittest.mock import MagicMock
    embedder = MagicMock(spec=EmbedderService)

    # Sentences:
    # 0: "In their latest financial filing..." (wsj, 20%)
    # 1: "In their latest financial filing..." (nyt, 80%)
    v0 = [1.0] + [0.0] * 383
    v1 = [0.1, 1.0] + [0.0] * 382
    embedder.generate_embeddings_batch.return_value = [v0, v1]

    vector_store = VectorStoreService()
    verifier = StoryVerificationService(db_session, embedder, vector_store)

    await verifier.verify_story(story.id)

    # 5. Fetch results
    stmt = select(Story).where(Story.id == story.id).options(selectinload(Story.timelines))
    res = await db_session.execute(stmt)
    verified_story = res.scalar_one()

    # WSJ reports 20%, NYT reports 80% -> Jaccard keyword overlap is very high, but numbers differ!
    assert verified_story.has_conflicts is True
    assert "conflicts" in verified_story.formation_evidence
    assert len(verified_story.formation_evidence["conflicts"]) >= 1

    # Assert conflict schema
    conflict = verified_story.formation_evidence["conflicts"][0]
    assert "20" in conflict["nums_a"] or "20" in conflict["nums_b"]
    assert "80" in conflict["nums_a"] or "80" in conflict["nums_b"]

@pytest.mark.asyncio
async def test_story_relations_flow(db_session):
    """
    Validates graph relationship classification (RELATED vs FOLLOW_UP) between stories using Qdrant.
    """
    from qdrant_client.http import models as q_models

    # 1. Create Publishers
    pub = Publisher(id="bbc", name="BBC", base_url="https://bbc.co.uk", credibility_score=0.94, bias_rating="center")
    db_session.add(pub)
    await db_session.commit()

    # 2. Create Story A (earlier)
    story_a = Story(
        id=uuid.uuid4(),
        centroid_vector_id=str(uuid.uuid4()),
        title="Breaking News from London",
        summary="Events unfolding in London.",
        article_count=1,
        publisher_diversity=1,
        status="ACTIVE",
        first_reported_at=datetime.now(timezone.utc) - timedelta(hours=30),
        created_at=datetime.now(timezone.utc) - timedelta(hours=30)
    )
    db_session.add(story_a)
    await db_session.commit()

    # Create Article for Story A
    art_a = Article(
        id=uuid.uuid4(),
        story_id=story_a.id,
        publisher_id="bbc",
        title="Breaking News from London",
        body_text="Details are arriving regarding an event in central London.",
        source_url="https://bbc.co.uk/london-news",
        published_at=datetime.now(timezone.utc) - timedelta(hours=30),
        content_hash="hash_a",
        article_hash="art_a",
        quality_score=0.90
    )
    db_session.add(art_a)
    await db_session.commit()

    # 3. Create Story B (later, 30 hours gap -> FOLLOW_UP)
    story_b = Story(
        id=uuid.uuid4(),
        centroid_vector_id=str(uuid.uuid4()),
        title="Follow up updates from London",
        summary="Further events unfolding in London.",
        article_count=1,
        publisher_diversity=1,
        status="ACTIVE",
        first_reported_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(story_b)
    await db_session.commit()

    # Create Article for Story B
    art_b = Article(
        id=uuid.uuid4(),
        story_id=story_b.id,
        publisher_id="bbc",
        title="Follow up updates from London",
        body_text="Further details are arriving regarding the London event.",
        source_url="https://bbc.co.uk/london-updates",
        published_at=datetime.now(timezone.utc),
        content_hash="hash_b",
        article_hash="art_b",
        quality_score=0.91
    )
    db_session.add(art_b)
    await db_session.commit()

    # 4. Upsert centroid vectors into Qdrant
    from unittest.mock import MagicMock
    embedder = MagicMock(spec=EmbedderService)
    vector_store = VectorStoreService()
    verifier = StoryVerificationService(db_session, embedder, vector_store)

    q_client = verifier.vector_store.client
    q_client.upsert(
        collection_name="stories",
        points=[
            q_models.PointStruct(
                id=str(story_a.id),
                vector=[0.1] * 384,
                payload={}
            ),
            q_models.PointStruct(
                id=str(story_b.id),
                vector=[0.1] * 384,
                payload={}
            )
        ]
    )

    # 5. Run Verification on Story B
    await verifier.verify_story(story_b.id)

    # 6. Fetch graph relations
    stmt_r = select(StoryRelation).where(
        StoryRelation.parent_story_id == story_a.id,
        StoryRelation.child_story_id == story_b.id
    )
    res_r = await db_session.execute(stmt_r)
    relation = res_r.scalar_one_or_none()

    assert relation is not None
    assert relation.relation_type == "FOLLOW_UP"


@pytest.mark.asyncio
async def test_story_timeline_windowing_logic(db_session):
    """
    Validates chronological window grouping and confidence score math inside story timelines.
    """
    # 1. Create Publishers
    pub_reuters = Publisher(id="reuters", name="Reuters", base_url="https://reuters.com", credibility_score=0.90, bias_rating="center")
    pub_ap = Publisher(id="ap", name="AP", base_url="https://ap.org", credibility_score=0.88, bias_rating="center")
    pub_bbc = Publisher(id="bbc", name="BBC", base_url="https://bbc.co.uk", credibility_score=0.92, bias_rating="center")
    db_session.add_all([pub_reuters, pub_ap, pub_bbc])
    await db_session.commit()

    # 2. Create Story
    story = Story(
        id=uuid.uuid4(),
        title="Multi-Publisher Dynamic Event",
        summary="A major event is developing rapidly.",
        article_count=4,
        publisher_diversity=3,
        status="ACTIVE"
    )
    db_session.add(story)
    await db_session.commit()

    # 3. Create Articles
    # Window 1: Three articles within 6 hours of each other
    t0 = datetime.now(timezone.utc) - timedelta(hours=10)
    art_reuters = Article(
        id=uuid.uuid4(), story_id=story.id, publisher_id="reuters",
        title="Breaking reuters event report", body_text="reuters content",
        source_url="https://reuters.com/t0", published_at=t0,
        content_hash="h1", article_hash="a1", quality_score=0.80
    )
    art_ap = Article(
        id=uuid.uuid4(), story_id=story.id, publisher_id="ap",
        title="AP updates the breaking event", body_text="ap content",
        source_url="https://ap.org/t1", published_at=t0 + timedelta(hours=2),
        content_hash="h2", article_hash="a2", quality_score=0.84
    )
    art_bbc = Article(
        id=uuid.uuid4(), story_id=story.id, publisher_id="bbc",
        title="BBC corroborates breaking event", body_text="bbc content",
        source_url="https://bbc.co.uk/t2", published_at=t0 + timedelta(hours=4),
        content_hash="h3", article_hash="a3", quality_score=0.88
    )

    # Window 2: One article published 8 hours after the start of window 1
    art_reuters_2 = Article(
        id=uuid.uuid4(), story_id=story.id, publisher_id="reuters",
        title="Reuters correction on final figures", body_text="A correction on previous estimates was issued.",
        source_url="https://reuters.com/t3", published_at=t0 + timedelta(hours=8),
        content_hash="h4", article_hash="a4", quality_score=0.90
    )

    db_session.add_all([art_reuters, art_ap, art_bbc, art_reuters_2])
    await db_session.commit()

    # 4. Run Verification
    from unittest.mock import MagicMock
    embedder = MagicMock(spec=EmbedderService)
    # 4 sentences to return (1 per article)
    embedder.generate_embeddings_batch.return_value = [[1.0] + [0.0]*383] * 4

    vector_store = VectorStoreService()
    verifier = StoryVerificationService(db_session, embedder, vector_store)

    await verifier.verify_story(story.id)

    # 5. Fetch timelines and assert groupings
    stmt = select(Story).where(Story.id == story.id).options(selectinload(Story.timelines))
    res = await db_session.execute(stmt)
    verified_story = res.scalar_one()

    timelines = verified_story.timelines
    timelines.sort(key=lambda t: t.event_timestamp)

    # We expect 2 milestones: Window 1 (first 3 articles) and Window 2 (the 4th article)
    assert len(timelines) == 2

    # Milestone 0 (Window 1): first_appearance, supporting_articles=3, supporting_publishers=3
    # avg_quality = (0.80 + 0.84 + 0.88) / 3 = 0.84
    # confidence = min(1.0, 0.84 + 0.05 * (3 - 1)) = 0.94
    assert timelines[0].event_type == "first_appearance"
    assert timelines[0].supporting_articles == 3
    assert timelines[0].supporting_publishers == 3
    assert timelines[0].confidence_score == 0.94

    # Milestone 1 (Window 2): correction, supporting_articles=1, supporting_publishers=1
    # confidence = min(1.0, 0.90 + 0.05 * 0) = 0.90
    assert timelines[1].event_type == "correction"
    assert timelines[1].supporting_articles == 1
    assert timelines[1].supporting_publishers == 1
    assert timelines[1].confidence_score == 0.90


