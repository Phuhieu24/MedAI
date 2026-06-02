from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class DiagnosisSession(Base):
    __tablename__ = "diagnosis_sessions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    age = Column(Integer)
    gender = Column(String(20))
    province = Column(String(100))

    temperature = Column(Float)
    systolic_bp = Column(Integer)
    diastolic_bp = Column(Integer)
    heart_rate = Column(Integer)
    spo2 = Column(Float)
    respiratory_rate = Column(Integer)
    weight = Column(Float)
    height = Column(Float)
    bmi = Column(Float)

    symptoms_input = Column(Text)
    symptoms_normalized = Column(Text)
    symptom_duration_days = Column(Integer)
    symptom_onset = Column(String(50))
    symptom_severity = Column(String(50))

    allergies = Column(Text)
    chronic_conditions = Column(Text)
    current_medications = Column(Text)
    family_history = Column(Text)

    smoking = Column(String(50))
    alcohol = Column(String(50))
    recent_contact_sick = Column(Boolean)
    recent_travel = Column(Boolean)

    risk_alerts = Column(Text)
    diagnosis_results = Column(Text)
    model_version_used = Column(String(50))

    demographic_adjustment_applied = Column(Boolean, default=False)
    demographic_adjustment_details = Column(Text)
    llm_explanation = Column(Text)

    patient = relationship("Patient", back_populates="sessions")
