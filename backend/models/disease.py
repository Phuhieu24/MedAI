from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class Disease(Base):
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    category = Column(String(100))
    description = Column(Text)
    severity = Column(String(50))
    advice = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    symptom_links = relationship("DiseaseSymptomLink", back_populates="disease", cascade="all, delete-orphan")


class Symptom(Base):
    __tablename__ = "symptoms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), unique=True, index=True)
    category = Column(String(100))
    description = Column(Text)
    is_danger_sign = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    aliases = relationship("SymptomAlias", back_populates="symptom", cascade="all, delete-orphan")
    disease_links = relationship("DiseaseSymptomLink", back_populates="symptom")


class SymptomAlias(Base):
    __tablename__ = "symptom_aliases"

    id = Column(Integer, primary_key=True, index=True)
    symptom_id = Column(Integer, ForeignKey("symptoms.id"), nullable=False, index=True)
    alias_name = Column(String(255), nullable=False)
    alias_slug = Column(String(255), index=True)

    symptom = relationship("Symptom", back_populates="aliases")


class DiseaseSymptomLink(Base):
    __tablename__ = "disease_symptoms_link"

    id = Column(Integer, primary_key=True, index=True)
    disease_id = Column(Integer, ForeignKey("diseases.id"), nullable=False, index=True)
    symptom_id = Column(Integer, ForeignKey("symptoms.id"), nullable=False, index=True)
    weight_score = Column(Integer, default=1)

    disease = relationship("Disease", back_populates="symptom_links")
    symptom = relationship("Symptom", back_populates="disease_links")


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(255), nullable=False)
    condition_text = Column(Text)
    risk_level = Column(String(50))
    advice = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
