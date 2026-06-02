import json
from typing import Dict, List

from sqlalchemy.orm import Session

from models.audit import AuditLog, ImportedDataset
from models.disease import Disease, DiseaseSymptomLink, RiskRule, Symptom, SymptomAlias


def _add_alias_if_missing(symptom_id: int, alias_name: str, alias_slug: str | None, db: Session) -> bool:
    existing = (
        db.query(SymptomAlias)
        .filter(SymptomAlias.symptom_id == symptom_id, SymptomAlias.alias_name == alias_name)
        .first()
    )
    if existing:
        return False

    db.add(
        SymptomAlias(
            symptom_id=symptom_id,
            alias_name=alias_name,
            alias_slug=alias_slug,
        )
    )
    return True


def upsert_diseases(diseases: List[Dict], db: Session) -> Dict[str, int]:
    added = updated = 0
    name_to_id = {}
    for d in diseases:
        name = d.get("name", "").strip()
        if not name:
            continue

        existing = db.query(Disease).filter(Disease.name == name).first()
        if existing:
            # Update
            existing.category = d.get("category") or existing.category
            existing.description = d.get("description") or existing.description
            existing.severity = d.get("severity") or existing.severity
            existing.advice = d.get("advice") or existing.advice
            name_to_id[name] = existing.id
            updated += 1
        else:
            # Create mới
            valid_data = {
                "name": name,
                "category": d.get("category"),
                "description": d.get("description"),
                "severity": d.get("severity"),
                "advice": d.get("advice"),
            }
            new_d = Disease(**valid_data)
            db.add(new_d)
            db.flush()
            name_to_id[name] = new_d.id
            added += 1
    return {"added": added, "updated": updated, "name_to_id": name_to_id}


def upsert_symptoms(symptoms: List[Dict], db: Session) -> Dict[str, int]:
    added = updated = 0
    aliases_added = 0
    name_to_id = {}
    for s in symptoms:
        name = s["name"]
        slug = s.get("slug")
        existing = db.query(Symptom).filter(Symptom.name == name).first()
        if not existing and slug:
            existing = db.query(Symptom).filter(Symptom.slug == slug).first()

        if existing:
            if not existing.slug:
                existing.slug = slug
            existing.category = s.get("category") or existing.category
            existing.description = s.get("description") or existing.description
            existing.is_danger_sign = s.get("is_danger_sign", existing.is_danger_sign)
            name_to_id[name] = existing.id
            if existing.name != name:
                aliases_added += int(_add_alias_if_missing(existing.id, name, slug, db))
            updated += 1
        else:
            new_s = Symptom(
                name=name,
                slug=slug,
                category=s.get("category"),
                description=s.get("description"),
                is_danger_sign=s.get("is_danger_sign", False),
            )
            db.add(new_s)
            db.flush()
            name_to_id[name] = new_s.id
            added += 1
    return {
        "added": added,
        "updated": updated,
        "aliases_added": aliases_added,
        "name_to_id": name_to_id,
    }


def upsert_aliases(aliases: List[Dict], symptom_name_to_id: Dict[str, int], db: Session) -> int:
    added = 0
    for a in aliases:
        sym_id = symptom_name_to_id.get(a["symptom_name"])
        if not sym_id:
            continue
        added += int(_add_alias_if_missing(sym_id, a["alias_name"], a.get("alias_slug"), db))
    return added


def upsert_links(
    links: List[Dict],
    disease_map: Dict[str, int],
    symptom_map: Dict[str, int],
    db: Session,
) -> int:
    added = 0
    for link in links:
        d_id = disease_map.get(link["disease_name"])
        s_id = symptom_map.get(link["symptom_name"])
        if not d_id or not s_id:
            continue
        existing = (
            db.query(DiseaseSymptomLink)
            .filter(
                DiseaseSymptomLink.disease_id == d_id,
                DiseaseSymptomLink.symptom_id == s_id,
            )
            .first()
        )
        if existing:
            existing.weight_score = link.get(
                "weight_score", existing.weight_score
            )
        else:
            db.add(
                DiseaseSymptomLink(
                    disease_id=d_id,
                    symptom_id=s_id,
                    weight_score=link.get("weight_score", 3),
                )
            )
            added += 1
    return added


def upsert_risk_rules(rules: List[Dict], db: Session) -> int:
    added = 0
    for r in rules:
        existing = db.query(RiskRule).filter(RiskRule.rule_name == r["rule_name"]).first()
        if not existing:
            db.add(RiskRule(**r))
            added += 1
    return added


def merge_parsed_data(parsed: Dict, db: Session, filename: str = "", file_format: str = "") -> Dict:
    d_result = upsert_diseases(parsed.get("diseases", []), db)
    s_result = upsert_symptoms(parsed.get("symptoms", []), db)

    disease_map = d_result["name_to_id"]
    symptom_map = s_result["name_to_id"]

    # Update map với dữ liệu hiện có
    existing_diseases = {d.name: d.id for d in db.query(Disease).all()}
    existing_symptoms = {s.name: s.id for s in db.query(Symptom).all()}
    disease_map.update(existing_diseases)
    symptom_map.update(existing_symptoms)

    aliases_added = s_result.get("aliases_added", 0)
    aliases_added += upsert_aliases(parsed.get("aliases", []), symptom_map, db)
    links_added = upsert_links(parsed.get("links", []), disease_map, symptom_map, db)
    rules_added = upsert_risk_rules(parsed.get("risk_rules", []), db)

    record = ImportedDataset(
        filename=filename,
        file_format=file_format,
        diseases_added=d_result["added"],
        diseases_updated=d_result["updated"],
        symptoms_added=s_result["added"],
        links_added=links_added,
        status="success",
    )
    db.add(record)

    audit = AuditLog(
        action="IMPORT_DATASET",
        details=json.dumps({
            "filename": filename,
            "diseases_added": d_result["added"],
            "diseases_updated": d_result["updated"],
            "symptoms_added": s_result["added"],
            "links_added": links_added,
        }),
        result="success",
    )
    db.add(audit)
    db.commit()

    return {
        "diseases_added": d_result["added"],
        "diseases_updated": d_result["updated"],
        "symptoms_added": s_result["added"],
        "links_added": links_added,
        "rules_added": rules_added,
        "aliases_added": aliases_added,
    }