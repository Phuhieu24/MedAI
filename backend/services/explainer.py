from typing import Any, Dict, List, Optional

from pipeline.translations import translate_kaggle_disease


def build_explanation(
    disease_name: str,
    matched_symptoms: List[Dict],
    total_symptoms: int,
    matched_count: int,
    vital_flags: Dict,
    demographic_adj: Optional[Dict] = None,
) -> str:
    parts = []

    pct = round(matched_count / total_symptoms * 100) if total_symptoms else 0
    parts.append(f"Khớp {matched_count}/{total_symptoms} triệu chứng ({pct}%)")

    if matched_symptoms:
        names = [s.get("symptom_name", "") for s in matched_symptoms[:3]]
        parts.append(f"Triệu chứng chính: {', '.join(names)}")

    vital_contributions = []
    if (
        vital_flags.get("fever")
        or vital_flags.get("high_fever")
        or vital_flags.get("very_high_fever")
    ):
        vital_contributions.append("sốt")
    if vital_flags.get("low_spo2") or vital_flags.get("low_spo2_critical"):
        vital_contributions.append("SpO2 thấp")
    if vital_flags.get("tachycardia"):
        vital_contributions.append("nhịp tim nhanh")
    if vital_contributions:
        parts.append(f"Dấu hiệu sinh tồn liên quan: {', '.join(vital_contributions)}")

    if demographic_adj and disease_name in demographic_adj:
        for adj in demographic_adj[disease_name]:
            parts.append(adj)

    return " | ".join(parts)


def format_confidence_label(score: float) -> str:
    if score >= 0.70:
        return "Cao"
    elif score >= 0.45:
        return "Trung bình"
    elif score >= 0.20:
        return "Thấp"
    else:
        return "Rất thấp"


def build_disease_match(
    disease_data: Dict,
    ml_score: float,
    ml_weight: float,
    weighted_weight: float,
    vital_flags: Dict,
    demographic_adj: Optional[Dict],
) -> Dict[str, Any]:
    w_score = disease_data["weighted_score"]
    combined = round(weighted_weight * w_score + ml_weight * ml_score, 4)

    explanation = build_explanation(
        disease_name=disease_data["disease_name"],
        matched_symptoms=disease_data["matched_symptoms"],
        total_symptoms=disease_data["total_symptoms"],
        matched_count=disease_data["matched_count"],
        vital_flags=vital_flags,
        demographic_adj=demographic_adj,
    )

    return {
        "disease_id": disease_data["disease_id"],
        "disease_name": translate_kaggle_disease(disease_data["disease_name"]),
        "category": disease_data["category"],
        "severity": disease_data["severity"],
        "confidence_score": combined,
        "confidence_label": format_confidence_label(combined),
        "weighted_score": w_score,
        "ml_score": ml_score,
        "matched_symptoms": disease_data["matched_symptoms"],
        "advice": disease_data["advice"],
        "explanation": explanation,
    }
