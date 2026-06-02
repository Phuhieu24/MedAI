import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.diagnosis import DiagnosisSession
from models.ml_model import MLModelVersion
from schemas.diagnosis import DiagnosisRequest, DiagnosisResponse, DiseaseMatch, RiskAlert
from services.explainer import build_disease_match
from services.fairness import apply_fairness_constraint, generate_fairness_summary
from services.llm_assistant import generate_llm_explanation
from services.ml_engine import predict_diseases
from services.nlp import extract_symptoms
from services.patient_service import get_or_create_patient
from services.rag import retrieve_clinical_context
from services.risk_engine import check_risk_rules
from services.scorer import apply_demographic_prior, compute_weighted_scores
from services.vital_signs import analyze_vital_signs

router = APIRouter(prefix="/api/diagnosis", tags=["Diagnosis"])


@router.post("", response_model=DiagnosisResponse)
def run_diagnosis(req: DiagnosisRequest, db: Session = Depends(get_db)):
    patient, _ = get_or_create_patient(req.patient_name, req.date_of_birth, db)

    vital_analysis = analyze_vital_signs(req.vital_signs)
    vital_alerts: list[RiskAlert] = vital_analysis["alerts"]
    vital_flags: dict = vital_analysis["flags"]
    bmi = vital_analysis["bmi"]

    matched_symptoms, unmatched = extract_symptoms(req.symptoms, db)
    matched_ids = [m["symptom_id"] for m in matched_symptoms]
    matched_slugs = [m["slug"] for m in matched_symptoms if m.get("slug")]

    symptom_alerts = check_risk_rules(matched_slugs, db)

    all_alerts = vital_alerts + symptom_alerts
    all_alerts.sort(key=lambda x: (0 if x.level == "Khẩn cấp" else 1 if x.level == "Cao" else 2))

    adj_applied = False
    adj_details = {}
    fairness_reason = "Không áp dụng điều chỉnh nhân khẩu học"

    combined = []
    
    if req.engine == "llm" or getattr(settings, "DIAGNOSIS_ENGINE", "xgboost") == "llm":
        try:
            from services.llm_diagnostician import llm_diagnostician_service
            llm_results = llm_diagnostician_service.diagnose(req.symptoms, db, patient_info=f"Giới tính: {req.gender}, Tuổi: {req.age}")
            if llm_results:
                combined = llm_results
        except Exception as e:
            print(f"LLM diagnosis failed, falling back to XGBoost: {e}")
            # Fallback happens below if combined is empty
            
    if not combined:
        baseline_scores = compute_weighted_scores(matched_ids, db)
        ml_predictions = predict_diseases(matched_ids, db)
        ml_map = {p["disease_name"]: p["ml_score"] for p in ml_predictions}

        if req.use_demographic_adjustment and baseline_scores:
            adjusted_scores, adj_details = apply_demographic_prior(
                baseline_scores, req.age, req.gender, req.province
            )
            final_scores, adj_applied, fairness_reason = apply_fairness_constraint(
                adjusted_scores, baseline_scores
            )
        else:
            final_scores = baseline_scores

        for d in final_scores[:15]:
            ml_score = ml_map.get(d["disease_name"], 0.0)
            match = build_disease_match(
                disease_data=d,
                ml_score=ml_score,
                ml_weight=settings.ML_SCORE_WEIGHT if ml_map else 0.0,
                weighted_weight=settings.WEIGHTED_SCORE_WEIGHT if ml_map else 1.0,
                vital_flags=vital_flags,
                demographic_adj=adj_details if adj_applied else None,
            )
            combined.append(match)

        combined.sort(key=lambda x: x["confidence_score"], reverse=True)
    top_diseases = combined[:5]
    top_diseases = combined[:5]
    demographic_summary = generate_fairness_summary(adj_applied, adj_details, fairness_reason)
    rag_sources = retrieve_clinical_context(top_diseases, all_alerts, vital_flags, db)
    llm_explanation = generate_llm_explanation(
        request=req,
        top_diseases=top_diseases,
        risk_alerts=all_alerts,
        vital_flags=vital_flags,
        rag_sources=rag_sources,
        demographic_adjustment_applied=adj_applied,
        demographic_adjustment_details=demographic_summary,
    )

    active_model = (
        db.query(MLModelVersion)
        .filter(MLModelVersion.is_active)
        .first()
    )
    model_version = active_model.version if active_model else "weighted_only"

    session = DiagnosisSession(
        patient_id=patient.id,
        age=req.age,
        gender=req.gender,
        province=req.province,
        temperature=req.vital_signs.temperature if req.vital_signs else None,
        systolic_bp=req.vital_signs.systolic_bp if req.vital_signs else None,
        diastolic_bp=req.vital_signs.diastolic_bp if req.vital_signs else None,
        heart_rate=req.vital_signs.heart_rate if req.vital_signs else None,
        spo2=req.vital_signs.spo2 if req.vital_signs else None,
        respiratory_rate=req.vital_signs.respiratory_rate if req.vital_signs else None,
        weight=req.vital_signs.weight if req.vital_signs else None,
        height=req.vital_signs.height if req.vital_signs else None,
        bmi=bmi,
        symptoms_input=json.dumps([s for s in req.symptoms], ensure_ascii=False),
        symptoms_normalized=json.dumps([m["slug"] for m in matched_symptoms], ensure_ascii=False),
        symptom_duration_days=req.symptom_duration_days,
        symptom_onset=req.symptom_onset,
        symptom_severity=req.symptom_severity,
        allergies=json.dumps(req.medical_history.allergies if req.medical_history else [], ensure_ascii=False),
        chronic_conditions=json.dumps(req.medical_history.chronic_conditions if req.medical_history else [], ensure_ascii=False),
        current_medications=json.dumps(req.medical_history.current_medications if req.medical_history else [], ensure_ascii=False),
        family_history=json.dumps(req.medical_history.family_history if req.medical_history else [], ensure_ascii=False),
        smoking=req.risk_factors.smoking if req.risk_factors else None,
        alcohol=req.risk_factors.alcohol if req.risk_factors else None,
        recent_contact_sick=req.risk_factors.recent_contact_sick if req.risk_factors else None,
        recent_travel=req.risk_factors.recent_travel if req.risk_factors else None,
        risk_alerts=json.dumps([a.model_dump() for a in all_alerts], ensure_ascii=False),
        diagnosis_results=json.dumps(top_diseases, ensure_ascii=False),
        model_version_used=model_version,
        demographic_adjustment_applied=adj_applied,
        demographic_adjustment_details=json.dumps(adj_details, ensure_ascii=False) if adj_details else None,
        llm_explanation=json.dumps(llm_explanation, ensure_ascii=False),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return DiagnosisResponse(
        session_id=session.id,
        patient_code=patient.patient_code,
        patient_name=patient.name,
        risk_alerts=all_alerts,
        bmi=bmi,
        vital_flags=vital_flags,
        top_diseases=[DiseaseMatch(**d) for d in top_diseases],
        demographic_adjustment_applied=adj_applied,
        demographic_adjustment_details=demographic_summary,
        llm_explanation=llm_explanation,
    )


@router.get("/history/{patient_code}")
def get_patient_history(patient_code: str, db: Session = Depends(get_db)):
    from models.patient import Patient
    patient = db.query(Patient).filter(Patient.patient_code == patient_code).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")

    sessions = (
        db.query(DiagnosisSession)
        .filter(DiagnosisSession.patient_id == patient.id)
        .order_by(DiagnosisSession.created_at.desc())
        .all()
    )

    history = []
    for s in sessions:
        results = json.loads(s.diagnosis_results) if s.diagnosis_results else []
        alerts = json.loads(s.risk_alerts) if s.risk_alerts else []
        history.append({
            "session_id": s.id,
            "created_at": s.created_at.isoformat(),
            "age": s.age,
            "symptoms_input": json.loads(s.symptoms_input) if s.symptoms_input else [],
            "top_diagnosis": results[0]["disease_name"] if results else None,
            "risk_alert_count": len(alerts),
            "model_version": s.model_version_used,
        })

    return {"patient": {"code": patient.patient_code, "name": patient.name, "dob": str(patient.date_of_birth)}, "sessions": history}


@router.get("/history/{patient_code}/session/{session_id}")
def get_session_detail(patient_code: str, session_id: int, db: Session = Depends(get_db)):
    from models.patient import Patient
    patient = db.query(Patient).filter(Patient.patient_code == patient_code).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Không tìm thấy bệnh nhân")

    session = db.query(DiagnosisSession).filter(
        DiagnosisSession.id == session_id,
        DiagnosisSession.patient_id == patient.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chẩn đoán")

    return {
        "session_id": session.id,
        "created_at": session.created_at.isoformat(),
        "patient": {"code": patient.patient_code, "name": patient.name},
        "demographics": {"age": session.age, "gender": session.gender, "province": session.province},
        "vital_signs": {
            "temperature": session.temperature, "systolic_bp": session.systolic_bp,
            "diastolic_bp": session.diastolic_bp, "heart_rate": session.heart_rate,
            "spo2": session.spo2, "bmi": session.bmi,
        },
        "symptoms": json.loads(session.symptoms_input) if session.symptoms_input else [],
        "risk_alerts": json.loads(session.risk_alerts) if session.risk_alerts else [],
        "diagnosis_results": json.loads(session.diagnosis_results) if session.diagnosis_results else [],
        "model_version": session.model_version_used,
        "llm_explanation": json.loads(session.llm_explanation) if session.llm_explanation else None,
    }
