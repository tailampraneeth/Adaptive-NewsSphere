from app.services.nlp_processor import NLPProcessorService

def test_nlp_processor_initialization():
    """Verify that the NLP processor initializes spacy and keybert."""
    nlp = NLPProcessorService()
    assert nlp.nlp is not None
    assert nlp.kw_model is not None

    # Test health check interface
    health = nlp.health()
    assert health["status"] == "PASS"
    assert health["details"]["spacy_loaded"] is True
    assert health["details"]["keybert_loaded"] is True

def test_nlp_metadata_extraction():
    """Verify that named entities, keywords, and topics are correctly extracted."""
    nlp = NLPProcessorService()

    title = "Google Acquires DeepMind in London"
    body = "Google announced today that it has completed its acquisition of DeepMind, an artificial intelligence startup based in London, United Kingdom. Larry Page praised the acquisition as a major step forward for technology."

    metadata = nlp.extract_metadata(title, body)

    # Verify entity extraction
    entities = metadata["named_entities"]
    assert "Google" in entities["organizations"] or "DeepMind" in entities["organizations"]
    assert "Larry Page" in entities["persons"]
    assert "London" in entities["locations"] or "United Kingdom" in entities["locations"]

    # Verify keywords and topics
    assert len(metadata["keywords"]) > 0
    assert len(metadata["topics"]) > 0

    # Verify text metrics
    assert metadata["word_count"] > 10
    assert metadata["character_count"] > 50
    assert metadata["reading_time"] >= 1
