from typing import List, Dict, Any
from sqlalchemy.orm import Session

try:
    from langchain.prompts import PromptTemplate
    from langchain.output_parsers import PydanticOutputParser
    from langchain_community.llms import Ollama
    from pydantic import BaseModel, Field
except ImportError:
    pass

from config import settings
from services.vector_db import vector_db
from models.disease import Disease
from pipeline.translations import translate_kaggle_disease


class LLMDiseasePrediction(BaseModel):
    disease_name: str = Field(description="Tên bệnh dự đoán (có thể giữ nguyên tên tiếng Anh hoặc dịch sang tiếng Việt)")
    confidence_score: float = Field(description="Độ tin cậy của chẩn đoán (từ 0.0 đến 1.0)")
    reasoning: str = Field(description="Lập luận chi tiết giải thích tại sao chọn bệnh này. BẮT BUỘC PHẢI VIẾT BẰNG TIẾNG VIỆT.")


class LLMDiagnosisOutput(BaseModel):
    predictions: List[LLMDiseasePrediction] = Field(
        description="Top 3 đến 5 bệnh có khả năng mắc phải nhất dựa trên triệu chứng"
    )


class LLMDiagnosticianService:
    def __init__(self):
        self.llm = None
        if settings.OLLAMA_ENABLED:
            try:
                self.llm = Ollama(
                    model=settings.OLLAMA_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.2,
                    timeout=settings.OLLAMA_TIMEOUT_SECONDS * 2
                )
            except Exception as e:
                print(f"Ollama initialization failed for diagnostician: {e}")
        
        self.parser = PydanticOutputParser(pydantic_object=LLMDiagnosisOutput)
        
        template = """Bạn là một bác sĩ chẩn đoán y khoa thông minh. 
BẮT BUỘC: Toàn bộ nội dung giải thích và lập luận của bạn PHẢI được viết hoàn toàn bằng TIẾNG VIỆT.

Dựa vào danh sách triệu chứng của bệnh nhân, hãy dự đoán các căn bệnh có thể mắc phải.
Tiêu chí chẩn đoán (BẮT BUỘC):
1. TUYỆT ĐỐI KHÔNG thiên vị hoặc thay đổi tỷ lệ bệnh dựa trên giới tính, nghề nghiệp, khu vực sống trừ khi đó là đặc thù sinh học khách quan.
2. Bạn phải xem xét các thông tin y khoa từ cơ sở dữ liệu (nếu có).

Triệu chứng của bệnh nhân:
{symptoms}

Thông tin y khoa tham khảo (RAG Context):
{context}

{format_instructions}

LƯU Ý CỰC KỲ QUAN TRỌNG: Toàn bộ nội dung chữ (string) bạn điền vào bên trong JSON (như reasoning) BẮT BUỘC PHẢI ĐƯỢC DỊCH SANG TIẾNG VIỆT 100%. Tuyệt đối không trả lời bằng tiếng Anh.
"""
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["symptoms", "context"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

    def diagnose(self, symptoms: List[str], db: Session) -> List[Dict[str, Any]]:
        if not self.llm:
            raise ValueError("Ollama LLM is not enabled.")
            
        unique_symptoms = list(dict.fromkeys(symptoms))
        symptoms_str = ", ".join(unique_symptoms)
        
        # Retrieve context from RAG
        context = ""
        if vector_db:
            results = vector_db.search_similar(symptoms_str, n_results=3)
            context_parts = []
            for r in results:
                context_parts.append(f"- {r['name']}: {r['document']}")
            context = "\n".join(context_parts)
            
        _input = self.prompt.format_prompt(symptoms=symptoms_str, context=context)
        output = self.llm.invoke(_input.to_string())
        
        try:
            parsed: LLMDiagnosisOutput = self.parser.parse(output)
            
            # Map predictions to database records
            results = []
            for pred in parsed.predictions:
                # Fuzzy or exact match to DB disease
                disease = db.query(Disease).filter(Disease.name.ilike(f"%{pred.disease_name}%")).first()
                if disease:
                    results.append({
                        "disease_name": translate_kaggle_disease(disease.name),
                        "disease_id": disease.id,
                        "category": disease.category,
                        "severity": disease.severity,
                        "confidence_score": pred.confidence_score,
                        "ml_score": pred.confidence_score,
                        "weighted_score": pred.confidence_score,
                        "matched_symptoms": [{"name": s} for s in unique_symptoms],
                        "advice": disease.advice,
                        "explanation": pred.reasoning,
                        "lime_explanation": None,
                        "shap_explanation": None,
                    })
            return results
        except Exception as e:
            print(f"Error in LLM diagnosis parsing: {e}\nOutput was: {output}")
            raise


llm_diagnostician = LLMDiseasePrediction
llm_diagnostician_service = LLMDiagnosticianService()
