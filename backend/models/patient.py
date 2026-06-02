from datetime import datetime

from sqlalchemy import Column, Date, DateTime, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_code = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    sequence = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("DiagnosisSession", back_populates="patient")
