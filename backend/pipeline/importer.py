import json
from io import BytesIO
from typing import Any, Dict, List

import pandas as pd


def parse_excel(file_bytes: bytes) -> Dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(BytesIO(file_bytes))
    sheets = {}
    for sheet in xl.sheet_names:
        sheets[sheet] = xl.parse(sheet)
    return sheets


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    import io

    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(file_bytes))


def parse_json(file_bytes: bytes) -> Any:
    return json.loads(file_bytes.decode("utf-8"))


def detect_kaggle_csv_format(df: pd.DataFrame) -> bool:
    cols = [_normalize_col(c) for c in df.columns]
    disease_col = _find_disease_col(cols)
    if disease_col is None:
        return False

    symptom_cols = [c for c in cols if c.startswith("symptom")]
    if symptom_cols:
        return True

    if any(c in cols for c in ("symptoms", "symptom", "all_symptoms")):
        return True

    return _looks_like_one_hot_symptom_csv(df, disease_col)


def normalize_kaggle_csv(df: pd.DataFrame) -> List[Dict]:
    col_map = {_normalize_col(c): c for c in df.columns}
    normalized_cols = list(col_map.keys())
    disease_key = _find_disease_col(normalized_cols)
    if disease_key is None:
        return []

    disease_col = col_map[disease_key]
    symptom_cols = [
        original
        for key, original in col_map.items()
        if key.startswith("symptom") and key not in {"symptoms", "symptom"}
    ]
    combined_symptom_cols = [
        col_map[key]
        for key in ("symptoms", "symptom", "all_symptoms")
        if key in col_map
    ]
    records = []
    for _, row in df.iterrows():
        disease = str(row.get(disease_col, "")).strip()
        if not disease:
            continue
        syms = []
        for sc in symptom_cols:
            val = str(row.get(sc, "")).strip()
            if val and val.lower() not in ("nan", "none", ""):
                syms.append(val)
        for sc in combined_symptom_cols:
            val = str(row.get(sc, "")).strip()
            if val and val.lower() not in ("nan", "none", ""):
                syms.extend(_split_symptom_cell(val))
        if not syms and _looks_like_one_hot_symptom_csv(df, disease_key):
            for key, original in col_map.items():
                if key == disease_key:
                    continue
                value = row.get(original, 0)
                if _is_positive_flag(value):
                    syms.append(str(original).strip())
        if syms:
            records.append({"disease": disease, "symptoms": syms})
    return records


def get_csv_format_hint(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "columns": [str(c) for c in df.columns[:30]],
        "accepted_formats": [
            "Disease, Symptom_1, Symptom_2, ...",
            "disease, symptoms",
            "prognosis, itching, skin_rash, ... với giá trị 0/1",
        ],
    }


def _normalize_col(col: Any) -> str:
    text = str(col).strip().lower().replace("\ufeff", "")
    text = text.replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _find_disease_col(cols: List[str]) -> str | None:
    for candidate in ("disease", "prognosis", "diagnosis", "condition", "label", "target"):
        if candidate in cols:
            return candidate
    return None


def _split_symptom_cell(value: str) -> List[str]:
    import re

    return [
        item.strip()
        for item in re.split(r"[,;|/]+", value)
        if item.strip()
    ]


def _is_positive_flag(value: Any) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "có", "co"}
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _looks_like_one_hot_symptom_csv(df: pd.DataFrame, disease_col: str) -> bool:
    cols = [_normalize_col(c) for c in df.columns]
    feature_cols = [c for c in cols if c != disease_col]
    if len(feature_cols) < 3:
        return False

    sample = df.head(20)
    positive_like = 0
    checked = 0
    for original_col, normalized in zip(df.columns, cols):
        if normalized == disease_col:
            continue
        checked += 1
        values = set(str(v).strip().lower() for v in sample[original_col].dropna().unique())
        if values and values.issubset({"0", "1", "0.0", "1.0", "true", "false", "yes", "no"}):
            positive_like += 1
    return checked > 0 and positive_like / checked >= 0.6


def detect_medai_excel_format(sheets: Dict[str, pd.DataFrame]) -> bool:
    required = {"Diseases", "Symptoms", "Disease_Symptoms_Link"}
    return required.issubset(set(sheets.keys()))


def parse_medai_excel(sheets: Dict[str, pd.DataFrame]) -> Dict[str, List[Dict]]:
    result = {"diseases": [], "symptoms": [], "links": [], "aliases": [], "risk_rules": []}

    diseases_df = sheets.get("Diseases", pd.DataFrame())
    for _, row in diseases_df.iterrows():
        if pd.isna(row.get("name")) or not str(row.get("name", "")).strip():
            continue
        result["diseases"].append({
            "name": str(row.get("name", "")).strip(),
            "category": str(row.get("category", "")).strip() if not pd.isna(row.get("category", "")) else None,
            "description": str(row.get("description", "")).strip() if not pd.isna(row.get("description", "")) else None,
            "severity": str(row.get("severity", "")).strip() if not pd.isna(row.get("severity", "")) else None,
            "advice": str(row.get("advice", "")).strip() if not pd.isna(row.get("advice", "")) else None,
        })

    symptoms_df = sheets.get("Symptoms", pd.DataFrame())
    for _, row in symptoms_df.iterrows():
        if pd.isna(row.get("name")) or not str(row.get("name", "")).strip():
            continue
        danger = str(row.get("is_danger_sign", "Không")).strip().lower()
        result["symptoms"].append({
            "name": str(row.get("name", "")).strip(),
            "slug": str(row.get("slug", "")).strip() if not pd.isna(row.get("slug", "")) else None,
            "category": str(row.get("category", "")).strip() if not pd.isna(row.get("category", "")) else None,
            "description": str(row.get("description", "")).strip() if not pd.isna(row.get("description", "")) else None,
            "is_danger_sign": danger in ("có", "yes", "true", "1"),
        })

    aliases_df = sheets.get("Symptom_Aliases", pd.DataFrame())
    for _, row in aliases_df.iterrows():
        if pd.isna(row.get("symptom_name")) or pd.isna(row.get("alias_name")):
            continue
        result["aliases"].append({
            "symptom_name": str(row.get("symptom_name", "")).strip(),
            "alias_name": str(row.get("alias_name", "")).strip(),
            "alias_slug": str(row.get("alias_slug", "")).strip() if not pd.isna(row.get("alias_slug", "")) else None,
        })

    links_df = sheets.get("Disease_Symptoms_Link", pd.DataFrame())
    for _, row in links_df.iterrows():
        if pd.isna(row.get("disease_name")) or pd.isna(row.get("symptom_name")):
            continue
        weight = int(row.get("weight_score", 3)) if not pd.isna(row.get("weight_score", 3)) else 3
        result["links"].append({
            "disease_name": str(row.get("disease_name", "")).strip(),
            "symptom_name": str(row.get("symptom_name", "")).strip(),
            "weight_score": weight,
        })

    risk_df = sheets.get("Risk_Rules", pd.DataFrame())
    for _, row in risk_df.iterrows():
        if pd.isna(row.get("rule_name")):
            continue
        result["risk_rules"].append({
            "rule_name": str(row.get("rule_name", "")).strip(),
            "condition_text": str(row.get("condition_text", "")).strip() if not pd.isna(row.get("condition_text", "")) else None,
            "risk_level": str(row.get("risk_level", "Trung bình")).strip(),
            "advice": str(row.get("advice", "")).strip() if not pd.isna(row.get("advice", "")) else None,
        })

    return result
