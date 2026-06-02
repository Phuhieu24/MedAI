from typing import Any, Dict, List, Optional


def check_equalized_odds(
    adjusted_scores: List[Dict],
    baseline_scores: List[Dict],
    threshold: float = 0.15,
) -> bool:
    if not adjusted_scores or not baseline_scores:
        return True

    baseline_map = {d["disease_name"]: d["weighted_score"] for d in baseline_scores}
    adjusted_map = {d["disease_name"]: d["weighted_score"] for d in adjusted_scores}

    for name, adj_score in adjusted_map.items():
        base_score = baseline_map.get(name, 0)
        if base_score > 0:
            relative_change = abs(adj_score - base_score) / base_score
            if relative_change > threshold:
                return False
    return True


def apply_fairness_constraint(
    adjusted_scores: List[Dict],
    baseline_scores: List[Dict],
) -> tuple[List[Dict], bool, str]:
    passes = check_equalized_odds(adjusted_scores, baseline_scores)

    if passes:
        return adjusted_scores, True, "Điều chỉnh nhân khẩu học hợp lệ"
    else:
        return baseline_scores, False, (
            "Điều chỉnh nhân khẩu học bị hủy do vi phạm ràng buộc công bằng "
            "(thay đổi > 15% so với baseline). Sử dụng kết quả không điều chỉnh."
        )


def generate_fairness_summary(
    adjustment_applied: bool,
    adjustment_details: Optional[Dict],
    reason: str,
) -> Dict[str, Any]:
    return {
        "adjustment_applied": adjustment_applied,
        "reason": reason,
        "details": adjustment_details or {},
        "note": (
            "Dữ liệu nhân khẩu học chỉ được dùng để điều chỉnh xác suất tiền nghiệm "
            "và không làm giảm chất lượng kết quả cho bất kỳ nhóm nào."
        ),
    }
