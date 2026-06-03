from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class VitalSigns(BaseModel):
    temperature: Optional[float] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None


class MedicalHistory(BaseModel):
    allergies: Optional[List[str]] = []
    chronic_conditions: Optional[List[str]] = []
    current_medications: Optional[List[str]] = []
    family_history: Optional[List[str]] = []


class RiskFactors(BaseModel):
    smoking: Optional[str] = None
    alcohol: Optional[str] = None
    recent_contact_sick: Optional[bool] = None
    recent_travel: Optional[bool] = None


class DiagnosisRequest(BaseModel):
    patient_name: str
    date_of_birth: date

    age: int
    gender: str
    province: str

    vital_signs: Optional[VitalSigns] = None

    symptoms: List[str]
    symptom_duration_days: Optional[int] = None
    symptom_onset: Optional[str] = None
    symptom_severity: Optional[str] = None

    medical_history: Optional[MedicalHistory] = None
    risk_factors: Optional[RiskFactors] = None

    use_demographic_adjustment: bool = True
    engine: Optional[str] = "xgboost"


class RiskAlert(BaseModel):
    level: str
    message: str
    advice: str
    triggered_by: str


class DiseaseMatch(BaseModel):
    disease_id: int
    disease_name: str
    category: Optional[str] = None
    severity: Optional[str] = None
    confidence_score: float
    weighted_score: float
    ml_score: float
    matched_symptoms: List[Dict[str, Any]]
    advice: Optional[str] = None
    explanation: Optional[str] = None
    lime_explanation: Optional[Dict[str, Any]] = None
    shap_explanation: Optional[Dict[str, Any]] = None


class RagSource(BaseModel):
    source_id: str
    source_type: str
    title: str
    content: str
    relevance_score: float
    metadata: Dict[str, Any] = {}


class LLMExplanation(BaseModel):
    enabled: bool
    provider: str
    model: Optional[str] = None
    status: str
    summary: str
    reasoning: List[str] = []
    safety_notes: List[str] = []
    fairness_notes: List[str] = []
    limitations: List[str] = []
    suggested_next_steps: List[str] = []
    first_aid_and_symptom_analysis: Optional[str] = None
    sources: List[RagSource] = []


class DiagnosisResponse(BaseModel):
    session_id: int
    patient_code: str
    patient_name: str

    risk_alerts: List[RiskAlert]
    bmi: Optional[float] = None
    vital_flags: Dict[str, Any] = {}

    top_diseases: List[DiseaseMatch]

    demographic_adjustment_applied: bool
    demographic_adjustment_details: Optional[Dict] = None
    llm_explanation: Optional[LLMExplanation] = None

    disclaimer: str = (
        "Đây là hệ thống hỗ trợ chẩn đoán sơ bộ, không thay thế tư vấn của bác sĩ. "
        "Vui lòng đến cơ sở y tế để được khám và điều trị chính xác."
    )
