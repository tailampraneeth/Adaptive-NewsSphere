import uuid
from app.services.vector_store import VectorStoreService

def test_vector_store_health_and_setup():
    """Verify that vector store service connects to Qdrant container and collections exist."""
    vs = VectorStoreService()

    # Test health check interface
    health = vs.health()
    assert health["status"] == "PASS"
    assert vs.collection_name in health["details"]["collections"]
    assert vs.story_collection_name in health["details"]["collections"]

def test_vector_upsert_and_similarity():
    """Verify that vectors are successfully uploaded and retrieved using Cosine similarity."""
    vs = VectorStoreService()

    point_id_1 = str(uuid.uuid4())
    point_id_2 = str(uuid.uuid4())

    # Create simple 384-dimension mock vectors
    vec_1 = [0.1] * 384
    vec_2 = [0.9] * 384 # Highly similar to itself and vec_1 under cosine similarity

    unique_cat = f"test-{uuid.uuid4()}"

    # 1. Upsert vectors
    res_1 = vs.upsert_vector("articles", point_id_1, vec_1, {"category": unique_cat})
    res_2 = vs.upsert_vector("articles", point_id_2, vec_2, {"category": unique_cat})

    assert res_1 is True
    assert res_2 is True

    # 2. Similarity Search Query
    matches = vs.search_similar("articles", vec_1, top_k=2, filter_dict={"category": unique_cat})
    assert len(matches) > 0
    assert matches[0]["id"] in [point_id_1, point_id_2]
