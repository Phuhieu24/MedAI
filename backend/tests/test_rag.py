"""Test RAG pipeline and services."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from services.ollama_client import ollama_client
from services.vector_db import vector_db
from services.explanations import explanation_service


def test_ollama_client_creation():
    """Test Ollama client initializes."""
    assert ollama_client is not None
    assert ollama_client.base_url == "http://localhost:11434"
    assert ollama_client.model == "mistral"
    print("✓ Ollama client initialized")


async def test_ollama_availability():
    """Test checking Ollama availability."""
    is_available = await ollama_client.is_available()
    # Don't assert - just log (Ollama may not be running)
    print(f"  Ollama available: {is_available}")


def test_vector_db_creation():
    """Test Vector DB initializes."""
    assert vector_db is not None
    assert vector_db.collection_name == "medical_data"
    print("✓ Vector DB initialized")


def test_explanation_service_creation():
    """Test Explanation service initializes."""
    assert explanation_service is not None
    print("✓ Explanation service initialized")


def test_vector_db_operations():
    """Test Vector DB index operations."""
    if vector_db is None:
        pytest.skip("Vector DB not available")

    # Test indexing
    vector_db.index_symptom(1, "Fever", "High body temperature")
    vector_db.index_disease(1, "Flu", "Influenza virus infection")

    # Test search
    results = vector_db.search_similar("fever", n_results=2)
    assert len(results) > 0
    print(f"✓ Vector DB search works: found {len(results)} results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
