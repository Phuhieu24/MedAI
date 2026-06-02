from typing import List, Tuple

import numpy as np
from sqlalchemy.orm import Session

from models.disease import Disease, Symptom


def get_all_symptom_ids(db: Session) -> List[int]:
    return [s.id for s in db.query(Symptom).filter(Symptom.is_active == True).order_by(Symptom.id).all()]


def get_all_disease_names(db: Session) -> List[str]:
    return [d.name for d in db.query(Disease).filter(Disease.is_active == True).order_by(Disease.id).all()]


def build_feature_matrix(db: Session) -> Tuple[np.ndarray, np.ndarray, List[int], List[str]]:
    symptom_ids = get_all_symptom_ids(db)
    disease_names = get_all_disease_names(db)
    sym_index = {sid: i for i, sid in enumerate(symptom_ids)}

    diseases = db.query(Disease).filter(Disease.is_active == True).order_by(Disease.id).all()

    X_rows = []
    y_rows = []

    np.random.seed(42)

    for d_idx, disease in enumerate(diseases):
        links = disease.symptom_links
        if not links:
            continue

        required_syms = [l for l in links if l.weight_score >= 3]
        optional_syms = [l for l in links if l.weight_score < 3]

        for _ in range(60):
            row = np.zeros(len(symptom_ids), dtype=np.float32)

            for link in required_syms:
                if link.symptom_id in sym_index:
                    row[sym_index[link.symptom_id]] = 1.0

            for link in optional_syms:
                if link.symptom_id in sym_index:
                    if np.random.random() > 0.35:
                        row[sym_index[link.symptom_id]] = 1.0

            all_sym_ids = [l.symptom_id for l in links]
            noise_candidates = [sid for sid in symptom_ids if sid not in all_sym_ids]
            if noise_candidates:
                n_noise = np.random.randint(0, min(3, len(noise_candidates)))
                noise_ids = np.random.choice(noise_candidates, size=n_noise, replace=False)
                for nid in noise_ids:
                    if nid in sym_index:
                        row[sym_index[nid]] = 1.0

            X_rows.append(row)
            y_rows.append(disease.name)

        for _ in range(15):
            row = np.zeros(len(symptom_ids), dtype=np.float32)
            n_present = max(1, len(required_syms) - np.random.randint(1, max(2, len(required_syms))))
            sampled = np.random.choice(required_syms, size=n_present, replace=False)
            for link in sampled:
                if link.symptom_id in sym_index:
                    row[sym_index[link.symptom_id]] = 1.0
            X_rows.append(row)
            y_rows.append(disease.name)

    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_rows)

    return X, y, symptom_ids, disease_names
