import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.audit import AuditLog, ImportedDataset
from models.diagnosis import DiagnosisSession
from models.disease import Disease, DiseaseSymptomLink, RiskRule, Symptom
from models.ml_model import MLModelVersion
from models.patient import Patient
from pipeline.importer import (
    detect_kaggle_csv_format,
    detect_medai_excel_format,
    get_csv_format_hint,
    normalize_kaggle_csv,
    parse_csv,
    parse_excel,
    parse_medai_excel,
)
from pipeline.merger import merge_parsed_data
from pipeline.translations import (
    kaggle_symptom_slug,
    translate_kaggle_disease,
    translate_kaggle_symptom,
)
from schemas.disease import (
    DiseaseCreate,
    DiseaseDetailOut,
    DiseaseOut,
    LinkSymptomRequest,
    RiskRuleCreate,
    RiskRuleOut,
    SymptomCreate,
    SymptomOut,
)
from services.ml_engine import invalidate_model_cache

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Diseases ──────────────────────────────────────────────────────────────────

@router.get("/diseases", response_model=List[DiseaseOut])
def list_diseases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(Disease)
        .filter(Disease.is_active)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/diseases/{disease_id}", response_model=DiseaseDetailOut)
def get_disease(disease_id: int, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    d = (
        db.query(Disease)
        .options(joinedload(Disease.symptom_links).joinedload(DiseaseSymptomLink.symptom))
        .filter(Disease.id == disease_id)
        .first()
    )
    if not d:
        raise HTTPException(404, "Không tìm thấy bệnh")
    links = [
        {
            "symptom_id": link.symptom_id,
            "symptom_name": link.symptom.name if link.symptom else "",
            "weight_score": link.weight_score,
        }
        for link in d.symptom_links
    ]
    base_data = {c.name: getattr(d, c.name) for c in d.__table__.columns}
    return {**base_data, "symptom_links": links}


@router.post("/diseases", response_model=DiseaseOut)
def create_disease(data: DiseaseCreate, db: Session = Depends(get_db)):
    if db.query(Disease).filter(Disease.name == data.name).first():
        raise HTTPException(400, "Bệnh đã tồn tại")
    d = Disease(**data.model_dump())
    db.add(d)
    db.commit()
    db.refresh(d)
    _audit(db, "CREATE_DISEASE", {"name": data.name})
    return d


@router.put("/diseases/{disease_id}", response_model=DiseaseOut)
def update_disease(disease_id: int, data: DiseaseCreate, db: Session = Depends(get_db)):
    d = db.query(Disease).filter(Disease.id == disease_id).first()
    if not d:
        raise HTTPException(404, "Không tìm thấy bệnh")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/diseases/{disease_id}")
def delete_disease(disease_id: int, db: Session = Depends(get_db)):
    d = db.query(Disease).filter(Disease.id == disease_id).first()
    if not d:
        raise HTTPException(404, "Không tìm thấy bệnh")
    d.is_active = False
    db.commit()
    _audit(db, "DELETE_DISEASE", {"id": disease_id, "name": d.name})
    return {"message": "Đã xoá bệnh"}


@router.post("/diseases/{disease_id}/symptoms")
def link_symptom_to_disease(disease_id: int, data: LinkSymptomRequest, db: Session = Depends(get_db)):
    d = db.query(Disease).filter(Disease.id == disease_id).first()
    if not d:
        raise HTTPException(404, "Không tìm thấy bệnh")
    s = db.query(Symptom).filter(Symptom.id == data.symptom_id).first()
    if not s:
        raise HTTPException(404, "Không tìm thấy triệu chứng")
    existing = (
        db.query(DiseaseSymptomLink)
        .filter(
            DiseaseSymptomLink.disease_id == disease_id,
            DiseaseSymptomLink.symptom_id == data.symptom_id,
        )
        .first()
    )
    if existing:
        existing.weight_score = data.weight_score
    else:
        db.add(
            DiseaseSymptomLink(
                disease_id=disease_id,
                symptom_id=data.symptom_id,
                weight_score=data.weight_score,
            )
        )
    db.commit()
    return {"message": "Đã gán triệu chứng"}


# ── Symptoms ──────────────────────────────────────────────────────────────────

@router.get("/symptoms", response_model=List[SymptomOut])
def list_symptoms(skip: int = 0, limit: int = 200, db: Session = Depends(get_db)):
    return (
        db.query(Symptom)
        .filter(Symptom.is_active)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.post("/symptoms", response_model=SymptomOut)
def create_symptom(data: SymptomCreate, db: Session = Depends(get_db)):
    if db.query(Symptom).filter(Symptom.name == data.name).first():
        raise HTTPException(400, "Triệu chứng đã tồn tại")
    from services.nlp import text_to_slug
    slug = data.slug or text_to_slug(data.name)
    s = Symptom(**{**data.model_dump(), "slug": slug})
    db.add(s)
    db.commit()
    db.refresh(s)
    from services.nlp import invalidate_alias_index_cache
    invalidate_alias_index_cache()
    return s


@router.put("/symptoms/{symptom_id}", response_model=SymptomOut)
def update_symptom(symptom_id: int, data: SymptomCreate, db: Session = Depends(get_db)):
    s = db.query(Symptom).filter(Symptom.id == symptom_id).first()
    if not s:
        raise HTTPException(404, "Không tìm thấy triệu chứng")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    from services.nlp import invalidate_alias_index_cache
    invalidate_alias_index_cache()
    return s


# ── Risk Rules ─────────────────────────────────────────────────────────────────

@router.get("/risk-rules", response_model=List[RiskRuleOut])
def list_risk_rules(db: Session = Depends(get_db)):
    return db.query(RiskRule).filter(RiskRule.is_active).all()


@router.post("/risk-rules", response_model=RiskRuleOut)
def create_risk_rule(data: RiskRuleCreate, db: Session = Depends(get_db)):
    r = RiskRule(**data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# ── Import Dataset ─────────────────────────────────────────────────────────────


@router.post("/llm-ingest-file")
async def llm_ingest_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not settings.OLLAMA_ENABLED:
        raise HTTPException(400, "LLM (Ollama) is không được bật.")
    
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content = await file.read()
    
    import pandas as pd
    import io
    from services.llm_ingestion import llm_ingestion_service

    try:
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content))
        elif ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            raise HTTPException(400, "Chỉ hỗ trợ .xlsx và .csv")
            
        success_count = 0
        errors = []
        
        for index, row in df.iterrows():
            row_text = row.to_json(force_ascii=False)
            try:
                extracted = llm_ingestion_service.parse_row(row_text)
                llm_ingestion_service.save_to_db(db, extracted)
                success_count += 1
            except Exception as e:
                errors.append({"row": index, "error": str(e)})
                
    except Exception as e:
        raise HTTPException(500, f"Lỗi khi import bằng LLM: {str(e)}")
        
    return {"message": f"Import thành công {success_count} dòng.", "errors": errors}

@router.post("/import-patients-csv")
async def import_patients_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import patient data CSV/Excel directly into Vector DB for Hybrid Search."""
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    content = await file.read()
    
    import pandas as pd
    import io
    from services.vector_db import vector_db
    
    if not vector_db:
        raise HTTPException(500, "Vector DB chưa được khởi tạo")

    try:
        if ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content))
        elif ext == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            raise HTTPException(400, "Chỉ hỗ trợ .xlsx và .csv")
            
        # Validate columns
        required_cols = ["Patient_ID", "Age", "Gender", "Symptoms", "Symptom_Count", "Disease"]
        # Check if columns are present (case-insensitive approach or exact match)
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(400, f"Thiếu cột bắt buộc: {col}")
                
        success_count = 0
        errors = []
        batch_data = []
        BATCH_SIZE = 100
        
        for index, row in df.iterrows():
            try:
                patient_data = {
                    "patient_id": int(row["Patient_ID"]),
                    "age": int(row["Age"]),
                    "gender": str(row["Gender"]).strip(),
                    "symptoms": str(row["Symptoms"]).strip(),
                    "symptom_count": int(row["Symptom_Count"]),
                    "disease": str(row["Disease"]).strip()
                }
                batch_data.append(patient_data)
                
                # Khi đủ batch, tiến hành import vào VectorDB
                if len(batch_data) >= BATCH_SIZE:
                    vector_db.index_patient_cases_batch(batch_data)
                    success_count += len(batch_data)
                    batch_data = []
            except Exception as e:
                errors.append({"row": index, "error": str(e)})
                
        # Xử lý phần còn dư chưa đủ một batch
        if batch_data:
            try:
                vector_db.index_patient_cases_batch(batch_data)
                success_count += len(batch_data)
            except Exception as e:
                errors.append({"row": "remaining_batch", "error": str(e)})
                
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, f"Lỗi khi import dataset: {str(e)}")
        
    return {"message": f"Đã đẩy thành công {success_count} ca bệnh vào VectorDB.", "errors": errors}


# ── ML Model Management ────────────────────────────────────────────────────────


@router.post("/train-xgboost")
def trigger_xgboost_training(notes: str = "", db: Session = Depends(get_db)):
    """Train XGBoost model for improved accuracy."""
    from ml.train_xgboost import train_xgboost_model
    try:
        result = train_xgboost_model(db, notes=notes)
        invalidate_model_cache()
        return {
            "message": "Huấn luyện XGBoost thành công",
            "status": "success",
            **result
        }
    except ValueError as e:
        # Handle insufficient data errors
        raise HTTPException(400, f"Dữ liệu không hợp lệ: {str(e)}")
    except Exception as e:
        import traceback
        error_detail = f"Lỗi huấn luyện XGBoost: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(500, {"error": error_detail})


@router.get("/ollama/status")
def check_ollama_status():
    """Check if Ollama is available."""
    from services.ollama_client import ollama_client
    try:
        # Use synchronous list_models to check availability
        models = ollama_client.list_models()
        is_available = len(models) > 0
        
        return {
            "status": "running" if is_available else "error",
            "available": is_available,
            "base_url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL,
            "available_models": models,
            "enabled": settings.OLLAMA_ENABLED,
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "error": str(e),
            "base_url": settings.OLLAMA_BASE_URL,
            "model": settings.OLLAMA_MODEL,
            "available_models": [],
            "enabled": settings.OLLAMA_ENABLED,
        }


@router.post("/vector-db/index")
def rebuild_vector_index(db: Session = Depends(get_db)):
    """Rebuild vector DB index with current medical data."""
    from services.vector_db import vector_db
    try:
        if not vector_db:
            raise HTTPException(500, "Vector DB chưa được khởi tạo - kiểm tra chromadb có được cài đặt không")
        vector_db.build_index(db)
        return {"message": "Vector DB index rebuilt successfully", "status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Vector DB indexing error: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(500, {"error": error_detail})


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    models = (
        db.query(MLModelVersion)
        .order_by(MLModelVersion.created_at.desc())
        .all()
    )
    return [
        {
            "id": m.id, "version": m.version, "accuracy": m.accuracy,
            "f1_score": m.f1_score, "num_diseases": m.num_diseases,
            "num_symptoms": m.num_symptoms, "training_samples": m.training_samples,
            "is_active": m.is_active, "notes": m.notes,
            "created_at": m.created_at.isoformat(),
            "fairness_report": json.loads(m.fairness_report) if m.fairness_report else None,
        }
        for m in models
    ]


@router.post("/models/{model_id}/activate")
def activate_model(model_id: int, db: Session = Depends(get_db)):
    m = db.query(MLModelVersion).filter(MLModelVersion.id == model_id).first()
    if not m:
        raise HTTPException(404, "Không tìm thấy model")
    (
        db.query(MLModelVersion)
        .filter(MLModelVersion.is_active)
        .update({"is_active": False})
    )
    m.is_active = True
    db.commit()
    invalidate_model_cache()
    _audit(db, "ACTIVATE_MODEL", {"version": m.version})
    return {"message": f"Đã kích hoạt model {m.version}"}


# ── Patient History (Admin) ────────────────────────────────────────────────────

@router.get("/patients")
def list_patients(
    name: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Patient)
    if name:
        q = q.filter(Patient.name.ilike(f"%{name}%"))
    patients = (
        q.order_by(Patient.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": p.id, "patient_code": p.patient_code,
            "name": p.name, "date_of_birth": str(p.date_of_birth),
            "created_at": p.created_at.isoformat(),
            "session_count": len(p.sessions),
        }
        for p in patients
    ]


@router.get("/patients/{patient_id}/sessions")
def get_patient_sessions(patient_id: int, db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id).first()
    if not p:
        raise HTTPException(404, "Không tìm thấy bệnh nhân")
    sessions = (
        db.query(DiagnosisSession)
        .filter(DiagnosisSession.patient_id == patient_id)
        .order_by(DiagnosisSession.created_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        diag = json.loads(s.diagnosis_results) if s.diagnosis_results else []
        result.append({
            "session_id": s.id,
            "created_at": s.created_at.isoformat(),
            "age": s.age, "gender": s.gender, "province": s.province,
            "top_diagnosis": diag[0]["disease_name"] if diag else None,
            "confidence": diag[0]["confidence_score"] if diag else None,
            "model_version": s.model_version_used,
        })
    return {"patient": {"code": p.patient_code, "name": p.name}, "sessions": result}


# ── Audit Log ──────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
def get_audit_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id, "action": l.action,
            "details": json.loads(l.details) if l.details else {},
            "result": l.result, "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/imported-datasets")
def get_imported_datasets(db: Session = Depends(get_db)):
    rows = db.query(ImportedDataset).order_by(ImportedDataset.created_at.desc()).all()
    return [
        {
            "id": r.id, "filename": r.filename, "file_format": r.file_format,
            "diseases_added": r.diseases_added, "symptoms_added": r.symptoms_added,
            "links_added": r.links_added, "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]



# ── Stats Dashboard ────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    active = (
        db.query(MLModelVersion)
        .filter(MLModelVersion.is_active)
        .first()
    )
    return {
        "diseases": db.query(Disease).filter(Disease.is_active).count(),
        "symptoms": db.query(Symptom).filter(Symptom.is_active).count(),
        "patients": db.query(Patient).count(),
        "diagnosis_sessions": db.query(DiagnosisSession).count(),
        "active_model": (
            {
                "version": active.version,
                "accuracy": active.accuracy,
                "f1_score": active.f1_score,
            }
            if active
            else None
        ),
        "total_models": db.query(MLModelVersion).count(),
    }


# ── Helper ─────────────────────────────────────────────────────────────────────

def _audit(db: Session, action: str, details: dict):
    audit = AuditLog(
        action=action,
        details=json.dumps(details, ensure_ascii=False),
        result="success",
    )
    db.add(audit)
    db.commit()
