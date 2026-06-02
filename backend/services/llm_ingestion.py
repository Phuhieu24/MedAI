import json
from typing import List

from fastapi import UploadFile
import pandas as pd
from sqlalchemy.orm import Session

try:
    from langchain.prompts import PromptTemplate
    from langchain.output_parsers import PydanticOutputParser
    from langchain_community.llms import Ollama
    from pydantic import BaseModel, Field
except ImportError:
    pass

from config import settings
from models.disease import Disease, Symptom, DiseaseSymptomLink
from services.vector_db import vector_db


class ExtractedSymptom(BaseModel):
    name: str = Field(description="Tên triệu chứng bằng Tiếng Việt (ví dụ: Sốt cao, Ho có đờm)")
    weight: int = Field(description="Trọng số của triệu chứng đối với bệnh này (1-10)", default=5)
    is_danger: bool = Field(description="Triệu chứng này có nguy hiểm không?", default=False)


class ExtractedDisease(BaseModel):
    disease_name: str = Field(description="Tên bệnh bằng Tiếng Việt")
    category: str = Field(description="Phân loại bệnh (ví dụ: Hô hấp, Tiêu hóa)", default="Chung")
    description: str = Field(description="Mô tả bệnh bằng Tiếng Việt")
    severity: str = Field(description="Mức độ nghiêm trọng (Nhẹ, Vừa, Nặng)", default="Vừa")
    advice: str = Field(description="Lời khuyên sơ cứu an toàn, rẻ tiền bằng Tiếng Việt dễ hiểu cho người nghèo")
    symptoms: List[ExtractedSymptom] = Field(description="Danh sách các triệu chứng của bệnh này")


class LLMIngestionService:
    def __init__(self):
        self.llm = None
        if settings.OLLAMA_ENABLED:
            try:
                self.llm = Ollama(
                    model=settings.OLLAMA_MODEL,
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=0.1,
                    timeout=settings.OLLAMA_TIMEOUT_SECONDS * 2  # Longer timeout for parsing
                )
            except Exception as e:
                print(f"Ollama initialization failed for ingestion: {e}")
        
        self.parser = PydanticOutputParser(pydantic_object=ExtractedDisease)
        
        template = """Bạn là một chuyên gia y tế và dịch giả. 
Nhiệm vụ của bạn là nhận một dòng dữ liệu thô (thường bằng tiếng Anh từ các file y khoa) và trích xuất cấu trúc bệnh lý.
BẤT KỂ NGÔN NGỮ ĐẦU VÀO LÀ GÌ, BẠN PHẢI DỊCH VÀ TRẢ VỀ KẾT QUẢ HOÀN TOÀN BẰNG TIẾNG VIỆT.
Trong phần lời khuyên, hãy đưa ra các cách sơ cứu rẻ tiền, an toàn, dùng từ ngữ dân dã cho người nghèo.
TUYỆT ĐỐI không thiên vị theo giới tính hoặc chủng tộc.

Dữ liệu đầu vào thô:
{raw_data}

{format_instructions}
"""
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["raw_data"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

    def parse_row(self, row_text: str) -> ExtractedDisease:
        if not self.llm:
            raise ValueError("Ollama LLM is not configured or enabled.")
        
        _input = self.prompt.format_prompt(raw_data=row_text)
        output = self.llm.invoke(_input.to_string())
        
        try:
            # Try parsing directly
            return self.parser.parse(output)
        except Exception as e:
            # Sometimes LLM wraps output in markdown or adds text, try to extract JSON
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', output, re.DOTALL)
            if json_match:
                try:
                    return self.parser.parse(json_match.group(1))
                except Exception:
                    pass
            
            # If still fails, try to find any { ... } block
            json_match = re.search(r'(\{.*\})', output, re.DOTALL)
            if json_match:
                try:
                    return self.parser.parse(json_match.group(1))
                except Exception:
                    pass
                    
            safe_output = output.encode('ascii', 'ignore').decode('ascii')
            print(f"Error parsing LLM output: {e}\nOutput was: {safe_output}")
            raise

    def save_to_db(self, db: Session, data: ExtractedDisease):
        # 1. Save or get Disease
        disease = db.query(Disease).filter(Disease.name.ilike(data.disease_name)).first()
        if not disease:
            disease = Disease(
                name=data.disease_name,
                category=data.category,
                description=data.description,
                severity=data.severity,
                advice=data.advice
            )
            db.add(disease)
            db.commit()
            db.refresh(disease)

        # 2. Save Symptoms and Links
        for sym in data.symptoms:
            import re
            from unidecode import unidecode
            slug = re.sub(r'[^a-z0-9]+', '-', unidecode(sym.name).lower()).strip('-')
            
            symptom = db.query(Symptom).filter(Symptom.slug == slug).first()
            if not symptom:
                symptom = Symptom(
                    name=sym.name,
                    slug=slug,
                    is_danger_sign=sym.is_danger,
                    category=disease.category
                )
                db.add(symptom)
                db.commit()
                db.refresh(symptom)

            link = db.query(DiseaseSymptomLink).filter(
                DiseaseSymptomLink.disease_id == disease.id,
                DiseaseSymptomLink.symptom_id == symptom.id
            ).first()
            
            if not link:
                link = DiseaseSymptomLink(
                    disease_id=disease.id,
                    symptom_id=symptom.id,
                    weight_score=sym.weight
                )
                db.add(link)
        
        db.commit()

        # Update Vector DB
        if vector_db:
            doc_text = f"Bệnh: {disease.name}. Triệu chứng: {', '.join([s.name for s in data.symptoms])}. Hướng dẫn: {disease.advice}"
            vector_db.add_document(
                document_id=f"disease_{disease.id}",
                text=doc_text,
                metadata={"type": "disease", "disease_id": disease.id, "name": disease.name}
            )


llm_ingestion_service = LLMIngestionService()
