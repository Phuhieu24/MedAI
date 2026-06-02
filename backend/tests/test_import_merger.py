def test_merge_symptom_by_existing_slug_adds_alias():
    from database import SessionLocal, init_db
    from models.disease import Disease, DiseaseSymptomLink, Symptom, SymptomAlias
    from pipeline.merger import merge_parsed_data

    init_db()
    db = SessionLocal()
    try:
        existing = Symptom(name="Ngứa test", slug="itching_test")
        disease = Disease(name="Dị ứng test", category="Test")
        db.add_all([existing, disease])
        db.commit()

        result = merge_parsed_data(
            {
                "diseases": [{"name": "Dị ứng test"}],
                "symptoms": [{"name": "itching test", "slug": "itching_test"}],
                "links": [
                    {
                        "disease_name": "Dị ứng test",
                        "symptom_name": "itching test",
                        "weight_score": 3,
                    }
                ],
                "aliases": [],
                "risk_rules": [],
            },
            db,
            filename="kaggle.csv",
            file_format="csv",
        )

        symptoms = db.query(Symptom).filter(Symptom.slug == "itching_test").all()
        alias = (
            db.query(SymptomAlias)
            .filter(SymptomAlias.symptom_id == existing.id, SymptomAlias.alias_name == "itching test")
            .first()
        )
        link = (
            db.query(DiseaseSymptomLink)
            .filter(
                DiseaseSymptomLink.disease_id == disease.id,
                DiseaseSymptomLink.symptom_id == existing.id,
            )
            .first()
        )
    finally:
        db.close()

    assert result["symptoms_added"] == 0
    assert result["aliases_added"] == 1
    assert len(symptoms) == 1
    assert alias is not None
    assert link is not None


def test_kaggle_translation_maps_to_vietnamese_labels():
    from pipeline.translations import (
        kaggle_symptom_slug,
        translate_kaggle_disease,
        translate_kaggle_symptom,
    )

    assert translate_kaggle_disease("Fungal infection") == "Nhiễm nấm da"
    assert translate_kaggle_disease("Peptic ulcer diseae") == "Loét dạ dày tá tràng"
    assert kaggle_symptom_slug("_skin_rash") == "skin_rash"
    assert translate_kaggle_symptom("_skin_rash") == "Phát ban da"


def test_kaggle_csv_variants_are_detected_and_normalized():
    import pandas as pd

    from pipeline.importer import detect_kaggle_csv_format, normalize_kaggle_csv

    symptom_columns = pd.DataFrame(
        [{"Disease": "Dengue", "Symptom_1": "high_fever", "Symptom_2": "skin_rash"}]
    )
    assert detect_kaggle_csv_format(symptom_columns)
    assert normalize_kaggle_csv(symptom_columns) == [
        {"disease": "Dengue", "symptoms": ["high_fever", "skin_rash"]}
    ]

    combined = pd.DataFrame([{"disease": "Dengue", "symptoms": "high_fever, skin_rash"}])
    assert detect_kaggle_csv_format(combined)
    assert normalize_kaggle_csv(combined) == [
        {"disease": "Dengue", "symptoms": ["high_fever", "skin_rash"]}
    ]

    one_hot = pd.DataFrame(
        [
            {
                "itching": 0,
                "skin_rash": 1,
                "high_fever": 1,
                "vomiting": 0,
                "prognosis": "Dengue",
            }
        ]
    )
    assert detect_kaggle_csv_format(one_hot)
    assert normalize_kaggle_csv(one_hot) == [
        {"disease": "Dengue", "symptoms": ["skin_rash", "high_fever"]}
    ]
