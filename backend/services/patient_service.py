import re
from datetime import date
from typing import Optional, Tuple

from sqlalchemy.orm import Session
from unidecode import unidecode

from models.patient import Patient


def name_to_slug(name: str) -> str:
    name = name.lower().strip()
    name = unidecode(name)
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', '-', name)
    return name


def generate_patient_code(name: str, dob: date, sequence: int) -> str:
    slug = name_to_slug(name)
    dob_str = dob.strftime("%Y%m%d")
    base = f"{slug}_{dob_str}"
    if sequence == 1:
        return base
    return f"{base}_{sequence}"


def get_or_create_patient(name: str, dob: date, db: Session) -> Tuple[Patient, bool]:
    existing = (
        db.query(Patient)
        .filter(Patient.name == name, Patient.date_of_birth == dob)
        .order_by(Patient.sequence)
        .all()
    )

    if existing:
        return existing[0], False

    slug = name_to_slug(name)
    dob_str = dob.strftime("%Y%m%d")
    base_code = f"{slug}_{dob_str}"

    count_same_code = (
        db.query(Patient)
        .filter(Patient.patient_code.like(f"{base_code}%"))
        .count()
    )
    sequence = count_same_code + 1
    code = generate_patient_code(name, dob, sequence)

    patient = Patient(
        patient_code=code,
        name=name,
        date_of_birth=dob,
        sequence=sequence,
    )
    db.add(patient)
    db.flush()
    return patient, True


def lookup_patient_by_code(patient_code: str, db: Session) -> Optional[Patient]:
    return db.query(Patient).filter(Patient.patient_code == patient_code).first()


def lookup_patients_by_name_dob(name: str, dob: date, db: Session):
    return (
        db.query(Patient)
        .filter(Patient.name == name, Patient.date_of_birth == dob)
        .order_by(Patient.sequence)
        .all()
    )
