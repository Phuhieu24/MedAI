import os
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from sqlalchemy.orm import Session

from models.ml_model import MLModelVersion


_model_cache: Optional[Dict] = None
_active_version: Optional[str] = None


def load_active_model(db: Session) -> Optional[Dict]:
    global _model_cache, _active_version

    active = (
        db.query(MLModelVersion)
        .filter(MLModelVersion.is_active)
        .first()
    )
    if not active:
        return None

    if _model_cache and _active_version == active.version:
        return _model_cache

    if not os.path.exists(active.model_path):
        return None

    _model_cache = joblib.load(active.model_path)
    _active_version = active.version
    return _model_cache


def invalidate_model_cache():
    global _model_cache, _active_version
    _model_cache = None
    _active_version = None


def predict_diseases(
    matched_symptom_ids: List[int],
    db: Session,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    model_artifact = load_active_model(db)
    if model_artifact is None:
        return []

    # Hỗ trợ cả 2 loại model: cũ (ensemble) và mới (xgboost)
    if "ensemble" in model_artifact:
        # Model cũ (ensemble)
        model = model_artifact["ensemble"]
        le = model_artifact["label_encoder"]
        symptom_ids = model_artifact["symptom_ids"]
    else:
        # Model mới (XGBoost)
        model = model_artifact["model"]
        le = model_artifact["label_encoder"]
        symptom_ids = model_artifact["symptom_ids"]

    # Tạo feature vector
    sym_index = {sid: i for i, sid in enumerate(symptom_ids)}
    feature_vector = np.zeros(len(symptom_ids), dtype=np.float32)

    for sid in matched_symptom_ids:
        if sid in sym_index:
            feature_vector[sym_index[sid]] = 1.0

    try:
        # Dự đoán
        if "ensemble" in model_artifact:
            probas = model.predict_proba([feature_vector])[0]
        else:
            # XGBoost
            probas = model.predict_proba([feature_vector])[0]
    except Exception:
        return []

    # Lấy top kết quả
    top_indices = np.argsort(probas)[::-1][:top_n]

    results = []
    for idx in top_indices:
        if probas[idx] > 0.01:   # Ngưỡng tối thiểu
            results.append({
                "disease_name": le.classes_[idx],
                "ml_score": round(float(probas[idx]), 4),
            })

    return results