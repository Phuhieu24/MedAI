from datetime import date, datetime

from pydantic import BaseModel


class PatientCreate(BaseModel):
    name: str
    date_of_birth: date


class PatientOut(BaseModel):
    id: int
    patient_code: str
    name: str
    date_of_birth: date
    sequence: int
    created_at: datetime

    class Config:
        from_attributes = True


class PatientLookup(BaseModel):
    name: str
    date_of_birth: date
