from typing import Dict, List, Optional

from schemas.diagnosis import RiskAlert, VitalSigns

VITAL_THRESHOLDS = {
    "spo2_critical": 90.0,
    "spo2_warning": 95.0,
    "bp_crisis_systolic": 180,
    "bp_crisis_diastolic": 120,
    "bp_high_systolic": 140,
    "bp_high_diastolic": 90,
    "heart_rate_high": 120,
    "heart_rate_low": 50,
    "heart_rate_tachycardia": 100,
    "temp_very_high": 40.0,
    "temp_high": 38.5,
    "temp_fever": 38.0,
    "respiratory_high": 25,
    "respiratory_critical": 30,
}


def calculate_bmi(weight: Optional[float], height: Optional[float]) -> Optional[float]:
    if weight and height and height > 0:
        h_m = height / 100
        return round(weight / (h_m ** 2), 1)
    return None


def get_bmi_category(bmi: Optional[float]) -> Optional[str]:
    if bmi is None:
        return None
    if bmi < 18.5:
        return "Thiếu cân"
    elif bmi < 25.0:
        return "Bình thường"
    elif bmi < 30.0:
        return "Thừa cân"
    else:
        return "Béo phì"


def analyze_vital_signs(vital: Optional[VitalSigns]) -> Dict:
    if vital is None:
        return {"alerts": [], "flags": {}, "bmi": None, "bmi_category": None}

    alerts: List[RiskAlert] = []
    flags: Dict[str, bool] = {}

    bmi = calculate_bmi(vital.weight, vital.height)
    bmi_category = get_bmi_category(bmi)

    if vital.spo2 is not None:
        if vital.spo2 < VITAL_THRESHOLDS["spo2_critical"]:
            alerts.append(
                RiskAlert(
                    level="Khẩn cấp",
                    message=(
                        f"SpO2 = {vital.spo2}% — "
                        "Nồng độ oxy máu nguy hiểm thấp"
                    ),
                    advice="Đưa đi cấp cứu ngay lập tức",
                    triggered_by="spo2",
                )
            )
            flags["low_spo2_critical"] = True
        elif vital.spo2 < VITAL_THRESHOLDS["spo2_warning"]:
            alerts.append(
                RiskAlert(
                    level="Cao",
                    message=(
                        f"SpO2 = {vital.spo2}% — "
                        "Nồng độ oxy máu thấp"
                    ),
                    advice="Cần khám ngay, theo dõi sát SpO2",
                    triggered_by="spo2",
                )
            )
            flags["low_spo2"] = True

    if vital.systolic_bp is not None and vital.diastolic_bp is not None:
        if (
            vital.systolic_bp >= VITAL_THRESHOLDS["bp_crisis_systolic"]
            or vital.diastolic_bp >= VITAL_THRESHOLDS["bp_crisis_diastolic"]
        ):
            alerts.append(
                RiskAlert(
                    level="Khẩn cấp",
                    message=(
                        f"Huyết áp {vital.systolic_bp}/{vital.diastolic_bp} "
                        "mmHg — Khủng hoảng huyết áp"
                    ),
                    advice="Đến cơ sở y tế ngay, không tự lái xe",
                    triggered_by="blood_pressure",
                )
            )
            flags["bp_crisis"] = True
        elif (
            vital.systolic_bp >= VITAL_THRESHOLDS["bp_high_systolic"]
            or vital.diastolic_bp >= VITAL_THRESHOLDS["bp_high_diastolic"]
        ):
            flags["high_bp"] = True

    if vital.heart_rate is not None:
        if vital.heart_rate > VITAL_THRESHOLDS["heart_rate_high"]:
            alerts.append(RiskAlert(
                level="Cao",
                message=f"Nhịp tim {vital.heart_rate} bpm — Nhịp nhanh đáng lo ngại",
                advice="Cần đánh giá tim mạch, tránh gắng sức",
                triggered_by="heart_rate"
            ))
            flags["tachycardia"] = True
        elif vital.heart_rate < VITAL_THRESHOLDS["heart_rate_low"]:
            alerts.append(RiskAlert(
                level="Cao",
                message=f"Nhịp tim {vital.heart_rate} bpm — Nhịp chậm",
                advice="Cần theo dõi và tư vấn y tế",
                triggered_by="heart_rate"
            ))
            flags["bradycardia"] = True
        elif vital.heart_rate > VITAL_THRESHOLDS["heart_rate_tachycardia"]:
            flags["mild_tachycardia"] = True

    if vital.temperature is not None:
        if vital.temperature >= VITAL_THRESHOLDS["temp_very_high"]:
            alerts.append(RiskAlert(
                level="Khẩn cấp",
                message=f"Nhiệt độ {vital.temperature}°C — Sốt rất cao",
                advice="Đến cơ sở y tế ngay, hạ sốt khẩn cấp",
                triggered_by="temperature"
            ))
            flags["very_high_fever"] = True
        elif vital.temperature >= VITAL_THRESHOLDS["temp_high"]:
            flags["high_fever"] = True
        elif vital.temperature >= VITAL_THRESHOLDS["temp_fever"]:
            flags["fever"] = True

    if vital.respiratory_rate is not None:
        if vital.respiratory_rate >= VITAL_THRESHOLDS["respiratory_critical"]:
            alerts.append(RiskAlert(
                level="Khẩn cấp",
                message=f"Nhịp thở {vital.respiratory_rate} lần/phút — Suy hô hấp nghiêm trọng",
                advice="Đưa đi cấp cứu ngay",
                triggered_by="respiratory_rate"
            ))
            flags["respiratory_failure"] = True
        elif vital.respiratory_rate >= VITAL_THRESHOLDS["respiratory_high"]:
            flags["high_respiratory"] = True

    flags["bmi_category"] = bmi_category

    return {
        "alerts": alerts,
        "flags": flags,
        "bmi": bmi,
        "bmi_category": bmi_category,
    }
