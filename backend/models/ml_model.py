from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from database import Base


class MLModelVersion(Base):
    __tablename__ = "ml_model_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False)
    model_path = Column(String(500))
    accuracy = Column(Float)
    f1_score = Column(Float)
    num_diseases = Column(Integer)
    num_symptoms = Column(Integer)
    training_samples = Column(Integer)
    is_active = Column(Boolean, default=False)
    notes = Column(Text)
    fairness_report = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
