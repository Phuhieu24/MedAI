from typing import Any, Dict, List

from sqlalchemy.orm import Session

from config import settings
from models.disease import Disease, RiskRule
from schemas.diagnosis import RiskAlert
from services.vital_signs import VITAL_THRESHOLDS
from services.graph_db import graph_manager


def _clip(text: str, limit: int = 700) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _source(
    source_id: str,
    source_type: str,
    title: str,
    content: str,
    relevance_score: float,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "source_id": source_id,
        "source_type": source_type,
        "title": title,
        "content": _clip(content),
        "relevance_score": round(float(relevance_score), 4),
        "metadata": metadata or {},
    }


def retrieve_clinical_context(
    top_diseases: List[Dict[str, Any]],
    risk_alerts: List[RiskAlert],
    vital_flags: Dict[str, Any],
    db: Session,
) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []

    disease_ids = [d["disease_id"] for d in top_diseases[:5]]
    
    symptom_ids = []
    for match in top_diseases[:5]:
        for s in match.get("matched_symptoms", []):
            if "symptom_id" in s:
                symptom_ids.append(s["symptom_id"])
            elif "id" in s:
                symptom_ids.append(s["id"])
    symptom_ids = list(set(symptom_ids))
    
    if symptom_ids:
        graph_insight = graph_manager.get_graph_insights(symptom_ids)
        if graph_insight:
            sources.append(
                _source(
                    source_id="graph_insight:1",
                    source_type="graph_insight",
                    title="Phân tích Đồ thị Tri thức (GraphRAG)",
                    content=graph_insight,
                    relevance_score=0.99,
                )
            )

    diseases = (
        db.query(Disease)
        .filter(Disease.id.in_(disease_ids))
        .all()
        if disease_ids
        else []
    )
    disease_map = {d.id: d for d in diseases}

    for rank, match in enumerate(top_diseases[:5], start=1):
        disease = disease_map.get(match["disease_id"])
        matched_symptoms = [
            s.get("symptom_name") or s.get("name") or ""
            for s in match.get("matched_symptoms", [])
            if s.get("symptom_name") or s.get("name")
        ]
        content_parts = [
            f"Bệnh gợi ý hạng {rank}: {match['disease_name']}.",
            f"Nhóm bệnh: {match.get('category') or 'chưa phân loại'}.",
            f"Mức độ: {match.get('severity') or 'chưa rõ'}.",
            f"Điểm tin cậy: {match.get('confidence_score', 0):.2f}; "
            f"điểm triệu chứng: {match.get('weighted_score', 0):.2f}; "
            f"điểm ML: {match.get('ml_score', 0):.2f}.",
        ]
        if disease and disease.description:
            content_parts.append(f"Mô tả trong cơ sở tri thức: {disease.description}.")
        if matched_symptoms:
            content_parts.append(f"Triệu chứng khớp: {', '.join(matched_symptoms)}.")
        if match.get("advice"):
            content_parts.append(f"Khuyến nghị dữ liệu: {match['advice']}.")

        sources.append(
            _source(
                source_id=f"disease:{match['disease_id']}",
                source_type="disease_match",
                title=match["disease_name"],
                content=" ".join(content_parts),
                relevance_score=1.0 - (rank - 1) * 0.08,
                metadata={
                    "rank": rank,
                    "confidence_score": match.get("confidence_score"),
                    "matched_count": match.get("matched_count"),
                },
            )
        )

    for idx, alert in enumerate(risk_alerts[:4], start=1):
        sources.append(
            _source(
                source_id=f"risk_alert:{idx}:{alert.triggered_by}",
                source_type="risk_alert",
                title=f"Cảnh báo {alert.level}",
                content=f"{alert.message}. Lời khuyên: {alert.advice}. Tác nhân: {alert.triggered_by}.",
                relevance_score=0.95 if alert.level == "Khẩn cấp" else 0.82,
                metadata={"level": alert.level, "triggered_by": alert.triggered_by},
            )
        )

    if vital_flags:
        active_flags = [f"{k}={v}" for k, v in vital_flags.items() if v]
        sources.append(
            _source(
                source_id="vital_signs:thresholds",
                source_type="vital_signs",
                title="Phân tích sinh hiệu",
                content=(
                    "Các flags sinh hiệu đang bật: "
                    f"{', '.join(active_flags) if active_flags else 'không có flag nguy cơ'}. "
                    f"Ngưỡng nội bộ: SpO2 cảnh báo < {VITAL_THRESHOLDS['spo2_warning']}%, "
                    f"SpO2 khẩn cấp < {VITAL_THRESHOLDS['spo2_critical']}%, "
                    f"huyết áp khủng hoảng >= {VITAL_THRESHOLDS['bp_crisis_systolic']}/"
                    f"{VITAL_THRESHOLDS['bp_crisis_diastolic']}, "
                    f"sốt rất cao >= {VITAL_THRESHOLDS['temp_very_high']}°C."
                ),
                relevance_score=0.78,
                metadata={"flags": vital_flags},
            )
        )

    if risk_alerts:
        rules = db.query(RiskRule).filter(RiskRule.is_active).limit(3).all()
        for rule in rules:
            sources.append(
                _source(
                    source_id=f"risk_rule:{rule.id}",
                    source_type="risk_rule",
                    title=rule.rule_name,
                    content=(
                        f"Luật nguy cơ: {rule.condition_text or 'không có mô tả điều kiện'}. "
                        f"Mức nguy cơ: {rule.risk_level}. Lời khuyên: {rule.advice or 'chưa có'}."
                    ),
                    relevance_score=0.55,
                    metadata={"risk_level": rule.risk_level},
                )
            )

    unique_sources = {src["source_id"]: src for src in sources}
    ranked = sorted(
        unique_sources.values(),
        key=lambda src: src["relevance_score"],
        reverse=True,
    )
    return ranked[: settings.RAG_MAX_SOURCES]
