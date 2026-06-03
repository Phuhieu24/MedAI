import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from config import settings
from schemas.diagnosis import DiagnosisRequest, RiskAlert


def _as_text_list(value: Any, fallback: List[str]) -> List[str]:
    if not isinstance(value, list):
        return fallback
    cleaned = [str(item).strip() for item in value if str(item).strip()]
    return cleaned or fallback


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _fallback_explanation(
    top_diseases: List[Dict[str, Any]],
    risk_alerts: List[RiskAlert],
    rag_sources: List[Dict[str, Any]],
    status: str,
    error: str | None = None,
) -> Dict[str, Any]:
    if top_diseases:
        top = top_diseases[0]
        summary = (
            f"Hệ thống ưu tiên {top['disease_name']} vì có điểm tin cậy "
            f"{top.get('confidence_score', 0) * 100:.0f}% dựa trên triệu chứng khớp, "
            "điểm ML và các cảnh báo nguy cơ hiện có."
        )
    else:
        summary = (
            "Chưa có bệnh gợi ý đủ mạnh từ dữ liệu hiện tại. Cần bổ sung triệu chứng "
            "hoặc kiểm tra lại cơ sở tri thức."
        )

    emergency_count = sum(1 for alert in risk_alerts if alert.level == "Khẩn cấp")
    reasoning = [
        "RAG đã truy xuất các nguồn liên quan từ bảng bệnh, triệu chứng, sinh hiệu và luật nguy cơ trong SQLite.",
        "Kết quả cuối vẫn dựa trên bộ chấm điểm có kiểm soát; LLM không được tự thêm bệnh ngoài danh sách top gợi ý.",
    ]
    if emergency_count:
        reasoning.append(f"Có {emergency_count} cảnh báo khẩn cấp nên cần ưu tiên xử trí an toàn trước.")

    limitations = [
        "Đây là hỗ trợ sàng lọc ban đầu, không phải kết luận chẩn đoán.",
        "Độ tin cậy phụ thuộc vào chất lượng dữ liệu bệnh-triệu chứng và thông tin người dùng nhập.",
    ]
    if error:
        limitations.append(f"LLM chưa tạo được phản hồi do lỗi cấu hình hoặc kết nối: {error}.")

    return {
        "enabled": settings.LLM_ENABLED and bool(settings.LLM_API_KEY and settings.LLM_MODEL),
        "provider": settings.LLM_PROVIDER if settings.LLM_ENABLED else "structured_rag",
        "model": settings.LLM_MODEL or None,
        "status": status,
        "summary": summary,
        "reasoning": reasoning,
        "safety_notes": [
            "Nếu có dấu hiệu nguy hiểm hoặc triệu chứng nặng lên, cần chuyển tuyến hoặc gọi cấp cứu.",
            "Không tự dùng thuốc kê đơn chỉ dựa trên kết quả hệ thống.",
        ],
        "fairness_notes": [
            "Nhân khẩu học chỉ được dùng như tín hiệu hiệu chỉnh có giới hạn, không dùng để loại trừ khả năng bệnh.",
            "Nhóm yếu thế cần được ưu tiên tiếp cận khám trực tiếp khi dữ liệu đầu vào thiếu hoặc không chắc chắn.",
        ],
        "limitations": limitations,
        "suggested_next_steps": [
            "Đối chiếu kết quả với khám lâm sàng, sinh hiệu và tiền sử bệnh.",
            "Thu thập thêm triệu chứng còn thiếu trước khi ra quyết định điều trị.",
        ],
        "first_aid_and_symptom_analysis": "Chưa có phân tích sơ cứu và triệu chứng chi tiết do hệ thống đang chạy ở chế độ dự phòng.",
        "sources": rag_sources,
    }


def _build_prompt(
    request: DiagnosisRequest,
    top_diseases: List[Dict[str, Any]],
    risk_alerts: List[RiskAlert],
    vital_flags: Dict[str, Any],
    rag_sources: List[Dict[str, Any]],
    demographic_adjustment_applied: bool,
    demographic_adjustment_details: Optional[Dict[str, Any]],
) -> List[Dict[str, str]]:
    payload = {
        "patient_context": {
            "age": request.age,
            "gender": request.gender,
            "province": request.province,
            "symptom_duration_days": request.symptom_duration_days,
            "symptom_onset": request.symptom_onset,
            "symptom_severity": request.symptom_severity,
        },
        "top_diseases": top_diseases,
        "risk_alerts": [alert.model_dump() for alert in risk_alerts],
        "vital_flags": vital_flags,
        "demographic_adjustment": {
            "applied": demographic_adjustment_applied,
            "details": demographic_adjustment_details,
        },
        "rag_sources": rag_sources,
    }

    system = (
        "Bạn là trợ lý y tế. Bạn BẮT BUỘC phải trả lời 100% bằng TIẾNG VIỆT (Vietnamese) cho toàn bộ nội dung. "
        "Chỉ dùng dữ liệu được cung cấp trong RAG sources và top_diseases. "
        "Không tự tạo chẩn đoán mới, không kê đơn thuốc. Luôn ưu tiên an toàn và minh bạch."
    )
    user = (
        "TẠO GIẢI THÍCH BẰNG TIẾNG VIỆT (VIETNAMESE) ở dạng JSON hợp lệ với đúng các khóa: "
        "summary, reasoning, safety_notes, fairness_notes, limitations, suggested_next_steps, first_aid_and_symptom_analysis. "
        "LƯU Ý QUAN TRỌNG: Dù dữ liệu đầu vào là tiếng Anh, bạn phải dịch và tự viết lại toàn bộ giá trị (value) trong JSON bằng TIẾNG VIỆT.\n"
        "Với khóa first_aid_and_symptom_analysis (kiểu chuỗi/string): Dưới dạng một đoạn văn ngắn gọn (BẰNG TIẾNG VIỆT), hãy giải thích trực tiếp tại sao các triệu chứng của bệnh nhân lại dẫn đến bệnh này, và đưa ra ngay các bước sơ cứu tại nhà thiết thực, an toàn.\n"
        "Mỗi khóa khác trừ summary là mảng chuỗi ngắn. Nội dung phải dễ hiểu cho nhân viên y tế tuyến cơ sở. "
        "Dữ liệu:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _call_openai_compatible(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    base_url = settings.LLM_BASE_URL.rstrip("/")
    url = f"{base_url}/chat/completions"
    data = json.dumps(
        {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 900,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=settings.LLM_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    content = parsed["choices"][0]["message"]["content"]
    llm_json = _extract_json_object(content)
    if llm_json is None:
        raise ValueError("LLM không trả về JSON hợp lệ")
    return llm_json


def generate_llm_explanation(
    request: DiagnosisRequest,
    top_diseases: List[Dict[str, Any]],
    risk_alerts: List[RiskAlert],
    vital_flags: Dict[str, Any],
    rag_sources: List[Dict[str, Any]],
    demographic_adjustment_applied: bool,
    demographic_adjustment_details: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not settings.LLM_ENABLED:
        return _fallback_explanation(top_diseases, risk_alerts, rag_sources, "rag_fallback")

    if not settings.LLM_API_KEY or not settings.LLM_MODEL:
        return _fallback_explanation(
            top_diseases,
            risk_alerts,
            rag_sources,
            "rag_fallback_missing_llm_config",
        )

    try:
        messages = _build_prompt(
            request,
            top_diseases,
            risk_alerts,
            vital_flags,
            rag_sources,
            demographic_adjustment_applied,
            demographic_adjustment_details,
        )
        llm_json = _call_openai_compatible(messages)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return _fallback_explanation(
            top_diseases,
            risk_alerts,
            rag_sources,
            "rag_fallback_llm_error",
            error=str(exc),
        )

    fallback = _fallback_explanation(top_diseases, risk_alerts, rag_sources, "llm_generated")
    return {
        "enabled": True,
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "status": "llm_generated",
        "summary": str(llm_json.get("summary") or fallback["summary"]).strip(),
        "reasoning": _as_text_list(llm_json.get("reasoning"), fallback["reasoning"]),
        "safety_notes": _as_text_list(llm_json.get("safety_notes"), fallback["safety_notes"]),
        "fairness_notes": _as_text_list(llm_json.get("fairness_notes"), fallback["fairness_notes"]),
        "limitations": _as_text_list(llm_json.get("limitations"), fallback["limitations"]),
        "suggested_next_steps": _as_text_list(
            llm_json.get("suggested_next_steps"),
            fallback["suggested_next_steps"],
        ),
        "first_aid_and_symptom_analysis": str(llm_json.get("first_aid_and_symptom_analysis") or fallback["first_aid_and_symptom_analysis"]).strip(),
        "sources": rag_sources,
    }
