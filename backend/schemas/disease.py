from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class SymptomAliasOut(BaseModel):
    id: int
    alias_name: str
    alias_slug: Optional[str]

    class Config:
        from_attributes = True


class DiseaseSymptomLinkOut(BaseModel):
    symptom_id: int
    symptom_name: str
    weight_score: int

    class Config:
        from_attributes = True


class DiseaseCreate(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    advice: Optional[str] = None


class DiseaseOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    description: Optional[str]
    severity: Optional[str]
    advice: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DiseaseDetailOut(DiseaseOut):
    symptom_links: List[DiseaseSymptomLinkOut] = []


class SymptomCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    is_danger_sign: bool = False


class SymptomOut(BaseModel):
    id: int
    name: str
    slug: Optional[str]
    category: Optional[str]
    description: Optional[str]
    is_danger_sign: bool
    is_active: bool

    class Config:
        from_attributes = True


class SymptomDetailOut(SymptomOut):
    aliases: List[SymptomAliasOut] = []


class RiskRuleCreate(BaseModel):
    rule_name: str
    condition_text: Optional[str] = None
    risk_level: str
    advice: Optional[str] = None


class RiskRuleOut(BaseModel):
    id: int
    rule_name: str
    condition_text: Optional[str]
    risk_level: str
    advice: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class LinkSymptomRequest(BaseModel):
    symptom_id: int
    weight_score: int = 3
