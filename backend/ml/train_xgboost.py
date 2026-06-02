import json
import os
from datetime import datetime
from typing import Any, Dict

import joblib
import numpy as np
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sqlalchemy.orm import Session

from config import settings
from ml.generate_data import build_feature_matrix
from models.audit import AuditLog
from models.ml_model import MLModelVersion


def get_next_version(db: Session) -> str:
    count = db.query(MLModelVersion).count()
    return f"v{count + 1}.0"


def train_xgboost_model(db: Session, notes: str = "") -> Dict[str, Any]:
    """
    Train XGBoost model for disease classification.
    Uses SMOTE for handling imbalanced data.
    """
    os.makedirs(settings.ML_MODELS_DIR, exist_ok=True)

    X, y, symptom_ids, disease_names = build_feature_matrix(db)

    if len(np.unique(y)) < 2:
        raise ValueError("Cần ít nhất 2 bệnh để huấn luyện")

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Handle class imbalance with SMOTE
    try:
        smote = SMOTE(random_state=42, k_neighbors=min(3, min(np.bincount(y_encoded)) - 1))
        X_res, y_res = smote.fit_resample(X, y_encoded)
    except Exception:
        X_res, y_res = X, y_encoded

    # XGBoost classifier with optimized hyperparameters
    xgb_model = xgb.XGBClassifier(
        n_estimators=settings.XGBOOST_N_ESTIMATORS,
        max_depth=settings.XGBOOST_MAX_DEPTH,
        learning_rate=settings.XGBOOST_LEARNING_RATE,
        random_state=42,
        n_jobs=-1,
        scale_pos_weight=1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        eval_metric="mlogloss",
        tree_method="hist",
    )

    # Cross-validation
    cv = StratifiedKFold(n_splits=min(5, min(np.bincount(y_res))), shuffle=True, random_state=42)
    cv_scores = cross_val_score(xgb_model, X_res, y_res, cv=cv, scoring="f1_weighted")

    # Train final model
    xgb_model.fit(X_res, y_res)

    # Evaluate
    y_pred = xgb_model.predict(X_res)
    train_acc = accuracy_score(y_res, y_pred)
    train_f1 = f1_score(y_res, y_pred, average="weighted")

    # Save model
    version = get_next_version(db)
    model_path = os.path.join(settings.ML_MODELS_DIR, f"model_{version}_xgboost.pkl")

    model_artifact = {
        "model": xgb_model,
        "label_encoder": le,
        "symptom_ids": symptom_ids,
        "disease_names": disease_names,
        "version": version,
        "model_type": "xgboost",
        "trained_at": datetime.utcnow().isoformat(),
        "feature_importance": dict(zip(
            [f"symptom_{sid}" for sid in symptom_ids],
            xgb_model.feature_importances_.tolist()
        )),
    }
    joblib.dump(model_artifact, model_path)

    # Generate report
    report = classification_report(y_res, y_pred, target_names=le.classes_, output_dict=True)
    
    # FIXED: Convert numpy.float32 to Python float
    fairness_report = {
        "cv_f1_mean": float(cv_scores.mean()),
        "cv_f1_std": float(cv_scores.std()),
        "per_class_f1": {
            cls: round(float(report[cls]["f1-score"]), 3)
            for cls in le.classes_
            if cls in report
        },
        "feature_importance": {
            f"symptom_{sid}": round(float(imp), 4)
            for sid, imp in zip(symptom_ids, xgb_model.feature_importances_)
        },
    }

    # Deactivate old models
    db.query(MLModelVersion).filter(MLModelVersion.is_active == True).update(
        {"is_active": False}
    )

    # Save new model version
    model_record = MLModelVersion(
        version=version,
        model_path=model_path,
        accuracy=round(train_acc, 4),
        f1_score=round(train_f1, 4),
        num_diseases=len(disease_names),
        num_symptoms=len(symptom_ids),
        training_samples=len(X_res),
        is_active=True,
        notes=f"XGBoost model. {notes}",
        fairness_report=json.dumps(fairness_report, ensure_ascii=False),
    )
    db.add(model_record)

    # Audit log
    audit = AuditLog(
        action="ML_TRAIN_XGBOOST",
        details=json.dumps({
            "version": version,
            "diseases": len(disease_names),
            "symptoms": len(symptom_ids),
            "samples": len(X_res),
            "accuracy": round(train_acc, 4),
            "f1": round(train_f1, 4),
            "cv_f1_mean": round(float(cv_scores.mean()), 4),
        }),
        result="success",
    )
    db.add(audit)
    db.commit()

    return {
        "version": version,
        "accuracy": round(train_acc, 4),
        "f1_score": round(train_f1, 4),
        "cv_f1_mean": round(float(cv_scores.mean()), 4),
        "cv_f1_std": round(float(cv_scores.std()), 4),
        "num_diseases": len(disease_names),
        "num_symptoms": len(symptom_ids),
        "training_samples": len(X_res),
        "model_path": model_path,
        "fairness_report": fairness_report,
    }