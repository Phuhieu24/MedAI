"""Test XGBoost model training."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal, init_db
from ml.train_xgboost import train_xgboost_model
from models.disease import Disease, Symptom, SymptomDiseaseLink


@pytest.fixture
def db():
    """Create test database."""
    init_db()
    db = SessionLocal()
    yield db
    db.close()


def test_xgboost_model_creation(db: Session):
    """Test XGBoost model can be created."""
    # Setup: Create sample data
    disease = Disease(name="Test Disease", description="Test", is_active=True)
    db.add(disease)
    db.commit()

    symptom1 = Symptom(name="Symptom 1", slug="symptom-1", is_active=True)
    symptom2 = Symptom(name="Symptom 2", slug="symptom-2", is_active=True)
    db.add_all([symptom1, symptom2])
    db.commit()

    # Link symptoms to disease
    link1 = SymptomDiseaseLink(disease_id=disease.id, symptom_id=symptom1.id, weight_score=3)
    link2 = SymptomDiseaseLink(disease_id=disease.id, symptom_id=symptom2.id, weight_score=2)
    db.add_all([link1, link2])
    db.commit()

    # Train model
    result = train_xgboost_model(db, notes="Test run")

    # Verify results
    assert "version" in result
    assert result["accuracy"] >= 0
    assert result["f1_score"] >= 0
    assert result["num_diseases"] == 1
    assert result["num_symptoms"] == 2
    assert "model_path" in result
    print(f"✓ XGBoost model trained successfully")
    print(f"  Accuracy: {result['accuracy']:.4f}")
    print(f"  F1 Score: {result['f1_score']:.4f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
