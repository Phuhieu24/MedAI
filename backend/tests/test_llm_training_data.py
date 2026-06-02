import json
from pathlib import Path


def test_export_llm_training_jsonl(tmp_path):
    from database import SessionLocal, init_db
    from models.disease import Disease, DiseaseSymptomLink, Symptom
    from services.llm_training_data import export_llm_training_jsonl

    init_db()
    db = SessionLocal()
    try:
        fever = Symptom(name="Fever", slug="fever")
        cough = Symptom(name="Cough", slug="cough")
        disease = Disease(
            name="Flu-like illness",
            category="Respiratory",
            severity="Medium",
            advice="Monitor and refer if symptoms worsen",
        )
        db.add_all([fever, cough, disease])
        db.flush()
        db.add_all(
            [
                DiseaseSymptomLink(disease_id=disease.id, symptom_id=fever.id, weight_score=3),
                DiseaseSymptomLink(disease_id=disease.id, symptom_id=cough.id, weight_score=2),
            ]
        )
        db.commit()

        result = export_llm_training_jsonl(db, output_dir=str(tmp_path), max_examples_per_disease=2)
    finally:
        db.close()

    path = Path(result["file_path"])
    assert result["examples"] >= 1
    assert path.exists()

    first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert [msg["role"] for msg in first["messages"]] == ["system", "user", "assistant"]
    assistant = json.loads(first["messages"][2]["content"])
    assert "summary" in assistant
    assert "safety_notes" in assistant
