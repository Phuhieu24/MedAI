from typing import Any, Dict, List

from sqlalchemy.orm import Session, joinedload

from models.disease import Disease, DiseaseSymptomLink


def compute_weighted_scores(
    matched_symptom_ids: List[int],
    db: Session,
) -> List[Dict[str, Any]]:
    if not matched_symptom_ids:
        return []

    symptom_id_set = set(matched_symptom_ids)

    diseases = (
        db.query(Disease)
        .options(joinedload(Disease.symptom_links).joinedload(DiseaseSymptomLink.symptom))
        .filter(Disease.is_active)
        .all()
    )
    results = []

    for disease in diseases:
        raw_links = disease.symptom_links
        if not raw_links:
            continue
            
        # Deduplicate links by symptom_id, keeping the max weight score
        unique_links_map = {}
        for link in raw_links:
            if link.symptom_id not in unique_links_map or link.weight_score > unique_links_map[link.symptom_id].weight_score:
                unique_links_map[link.symptom_id] = link
        
        links = list(unique_links_map.values())

        total_possible = sum(link.weight_score for link in links)
        if total_possible == 0:
            continue

        matched_links = [
            link for link in links if link.symptom_id in symptom_id_set
        ]
        if not matched_links:
            continue

        matched_score = sum(link.weight_score for link in matched_links)
        coverage = len(matched_links) / len(links)
        raw_score = matched_score / total_possible
        final_score = raw_score * (0.7 + 0.3 * coverage)

        results.append({
            "disease_id": disease.id,
            "disease_name": disease.name,
            "category": disease.category or "",
            "severity": disease.severity or "",
            "advice": disease.advice or "",
            "weighted_score": round(final_score, 4),
            "matched_symptoms": [
                {
                    "symptom_id": link.symptom_id,
                    "symptom_name": link.symptom.name if link.symptom else "",
                    "weight": link.weight_score,
                }
                for link in matched_links
            ],
            "total_symptoms": len(links),
            "matched_count": len(matched_links),
        })

    results.sort(key=lambda x: x["weighted_score"], reverse=True)
    return results


def apply_demographic_prior(
    scored_diseases: List[Dict],
    age: int,
    gender: str,
    province: str,
) -> tuple[List[Dict], Dict]:
    adjustments = {}

    REGIONAL_PRIORS = {
        "malaria_regions": [
            "Gia Lai", "Đắk Lắk", "Đắk Nông", "Kon Tum",
            "Bình Phước", "Quảng Nam",
        ],
        "malaria_diseases": ["Sốt rét"],
    }

    GENDER_PRIORS = {
        "male_boost": {
            "genders": ["nam", "male"],
            "diseases": ["Gút (Gout)", "Nhồi máu cơ tim", "Heart Disease", "Ung thư gan", "Sỏi thận", "Tiểu đường type 2", "Gout"],
            "factor": 1.10,
        },
        "female_boost": {
            "genders": ["nữ", "female"],
            "diseases": ["Suy giáp", "Cường giáp", "Thyroid Disorder", "Lupus ban đỏ", "Loãng xương", "Viêm khớp dạng thấp", "Nhiễm trùng đường tiết niệu", "Urinary tract infection"],
            "factor": 1.10,
        }
    }

    AGE_PRIORS = {
        "pediatric_boost": {
            "min_age": 0, "max_age": 12,
            "diseases": ["Thủy đậu", "Sởi", "Tay chân miệng"],
            "factor": 1.15,
        },
        "geriatric_boost": {
            "min_age": 60, "max_age": 150,
            "diseases": ["Tăng huyết áp", "Đái tháo đường type 2", "Viêm khớp"],
            "factor": 1.12,
        },
    }

    adjusted = []
    for d in scored_diseases:
        score = d["weighted_score"]
        adj_details = []

        for prior_name, prior in AGE_PRIORS.items():
            if prior["min_age"] <= age <= prior["max_age"]:
                if d["disease_name"] in prior["diseases"]:
                    score = min(score * prior["factor"], 1.0)
                    adj_details.append(f"Tuổi {age} → +{int((prior['factor']-1)*100)}% cho {d['disease_name']}")

        if province in REGIONAL_PRIORS["malaria_regions"]:
            if d["disease_name"] in REGIONAL_PRIORS["malaria_diseases"]:
                score = min(score * 1.10, 1.0)
                adj_details.append(f"Vùng {province} → +10% cho {d['disease_name']}")
                
        for prior_name, prior in GENDER_PRIORS.items():
            if gender.strip().lower() in prior["genders"]:
                if d["disease_name"] in prior["diseases"]:
                    score = min(score * prior["factor"], 1.0)
                    gender_str = "Nam" if "male" in prior["genders"] else "Nữ"
                    adj_details.append(f"Giới tính {gender_str} → +{int((prior['factor']-1)*100)}% cho {d['disease_name']}")

        if adj_details:
            adjustments[d["disease_name"]] = adj_details

        adjusted.append({**d, "weighted_score": round(score, 4)})

    adjusted.sort(key=lambda x: x["weighted_score"], reverse=True)
    return adjusted, adjustments
