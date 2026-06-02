from typing import List

from sqlalchemy.orm import Session

from models.disease import RiskRule, Symptom
from schemas.diagnosis import RiskAlert

DANGER_SIGN_COMBINATIONS = [
    {
        "slugs": ["chest_pain", "breathlessness", "sweating"],
        "min_match": 2,
        "level": "Khẩn cấp",
        "message": "Đau ngực kết hợp khó thở/vã mồ hôi — Nghi ngờ tim mạch cấp",
        "advice": "Gọi cấp cứu ngay, không tự lái xe",
    },
    {
        "slugs": ["weakness_in_limbs", "slurring_of_speech", "loss_of_balance"],
        "min_match": 1,
        "level": "Khẩn cấp",
        "message": "Yếu một bên người / nói khó — Có thể là đột quỵ",
        "advice": "Gọi cấp cứu ngay",
    },
    {
        "slugs": ["high_fever", "skin_rash", "bleeding_gums"],
        "min_match": 2,
        "level": "Cao",
        "message": "Sốt cao kèm phát ban/chảy máu — Nghi ngờ sốt xuất huyết",
        "advice": "Đi khám sớm để loại trừ sốt xuất huyết",
    },
    {
        "slugs": ["vomiting", "diarrhoea", "dehydration"],
        "min_match": 2,
        "level": "Cao",
        "message": "Nôn/tiêu chảy kèm dấu hiệu mất nước",
        "advice": "Bù nước oresol và đi khám nếu không cải thiện",
    },
]


def check_risk_rules(matched_symptom_slugs: List[str], db: Session) -> List[RiskAlert]:
    alerts: List[RiskAlert] = []
    slug_set = set(matched_symptom_slugs)

    danger_symptoms = (
        db.query(Symptom)
        .filter(Symptom.is_danger_sign, Symptom.slug.in_(matched_symptom_slugs))
        .all()
    )
    for sym in danger_symptoms:
        alerts.append(RiskAlert(
            level="Cao",
            message=f"Triệu chứng nguy hiểm: {sym.name}",
            advice="Cần được đánh giá y tế ngay",
            triggered_by=f"danger_symptom:{sym.slug}",
        ))

    for combo in DANGER_SIGN_COMBINATIONS:
        match_count = sum(1 for s in combo["slugs"] if s in slug_set)
        if match_count >= combo["min_match"]:
            alerts.append(RiskAlert(
                level=combo["level"],
                message=combo["message"],
                advice=combo["advice"],
                triggered_by="symptom_combination",
            ))

    db_rules = db.query(RiskRule).filter(RiskRule.is_active).all()

    seen_levels = {a.level for a in alerts}
    if "Khẩn cấp" not in seen_levels and len(matched_symptom_slugs) > 0:
        for rule in db_rules:
            pass

    alerts.sort(key=lambda x: (0 if x.level == "Khẩn cấp" else 1 if x.level == "Cao" else 2))

    return alerts
