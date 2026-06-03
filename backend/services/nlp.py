import re
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from thefuzz import fuzz, process
from unidecode import unidecode

from config import settings
from models.disease import Symptom, SymptomAlias
from services.vector_db import vector_db


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def text_to_slug(text: str) -> str:
    text = normalize_text(text)
    text = unidecode(text)
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text


def sanitize_symptoms_input(symptoms: List[str]) -> List[str]:
    clean_symptoms = []
    
    # Danh sách các từ khóa thường dùng để hack LLM
    forbidden_words = r"(bỏ qua|ignore|forget|system prompt|prompt|lệnh|hướng dẫn|instruction)"
    
    for s in symptoms:
        # 1. Loại bỏ các thẻ đặc biệt của LLM (ví dụ: <|im_start|>, [INST])
        s_clean = re.sub(r"[<\[].*?[>\]]", "", s)
        
        # 2. Xóa các ký tự đặc biệt không thuộc về y tế (chỉ giữ chữ cái, số, dấu phẩy, khoảng trắng, gạch ngang)
        s_clean = re.sub(r"[^\w\s,.-]", "", s_clean, flags=re.UNICODE)
        
        # 3. Kiểm tra nếu chứa từ khóa độc hại thì bỏ qua triệu chứng đó
        if not re.search(forbidden_words, s_clean, re.IGNORECASE):
            if s_clean.strip():
                clean_symptoms.append(s_clean.strip())
                
    return clean_symptoms


_alias_index_cache = None


def invalidate_alias_index_cache():
    global _alias_index_cache
    _alias_index_cache = None


def build_alias_index(db: Session, force_rebuild: bool = False) -> Dict[str, Dict]:
    global _alias_index_cache
    if _alias_index_cache is not None and not force_rebuild:
        return _alias_index_cache

    index = {}
    aliases = db.query(SymptomAlias).all()
    for alias in aliases:
        key = normalize_text(alias.alias_name)
        index[key] = {
            "symptom_id": alias.symptom_id,
            "symptom_name": alias.symptom_name if hasattr(alias, 'symptom_name') else "",
            "alias_slug": alias.alias_slug,
        }
    symptoms = db.query(Symptom).filter(Symptom.is_active).all()
    for sym in symptoms:
        key = normalize_text(sym.name)
        index[key] = {
            "symptom_id": sym.id,
            "symptom_name": sym.name,
            "alias_slug": sym.slug,
        }
        if sym.slug:
            slug_key = normalize_text(sym.slug.replace("_", " "))
            index[slug_key] = {
                "symptom_id": sym.id,
                "symptom_name": sym.name,
                "alias_slug": sym.slug,
            }
            
    _alias_index_cache = index
    return index


def match_symptom(
    input_text: str,
    alias_index: Dict[str, Dict],
    threshold: int = None,
) -> Optional[Dict]:
    if threshold is None:
        threshold = settings.FUZZY_MATCH_THRESHOLD

    normalized = normalize_text(input_text)

    if normalized in alias_index:
        return {**alias_index[normalized], "match_score": 100, "matched_text": normalized}

    slug_input = text_to_slug(input_text)
    for key, val in alias_index.items():
        if text_to_slug(key) == slug_input:
            return {**val, "match_score": 100, "matched_text": key}

    candidates = list(alias_index.keys())
    result = process.extractOne(normalized, candidates, scorer=fuzz.token_sort_ratio)

    if result and result[1] >= threshold:
        matched_key = result[0]
        return {
            **alias_index[matched_key],
            "match_score": result[1],
            "matched_text": matched_key,
        }

    if vector_db:
        semantic_results = vector_db.search_symptoms(normalized, n_results=1)
        if semantic_results and semantic_results[0]['distance'] < 0.3:
            best_match = semantic_results[0]
            try:
                symptom_id = int(best_match['id'].split('_')[1])
                return {
                    "symptom_id": symptom_id,
                    "symptom_name": best_match['name'],
                    "alias_slug": text_to_slug(best_match['name']),
                    "match_score": int((1.0 - best_match['distance']) * 100),
                    "matched_text": input_text
                }
            except (ValueError, IndexError):
                pass

    return None


def extract_symptoms(
    raw_symptoms: List[str],
    db: Session,
) -> Tuple[List[Dict], List[str]]:
    alias_index = build_alias_index(db)
    matched = []
    unmatched = []
    seen_ids = set()

    for raw in raw_symptoms:
        if not raw or not raw.strip():
            continue
        result = match_symptom(raw.strip(), alias_index)
        if result and result["symptom_id"] not in seen_ids:
            matched.append({
                "original_input": raw,
                "symptom_id": result["symptom_id"],
                "symptom_name": result.get("symptom_name", ""),
                "slug": result.get("alias_slug", ""),
                "match_score": result["match_score"],
            })
            seen_ids.add(result["symptom_id"])
        else:
            unmatched.append(raw)

    return matched, unmatched
