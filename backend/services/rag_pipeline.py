from typing import List, Optional

try:
    from langchain.prompts import PromptTemplate
    from langchain_community.llms import Ollama
except ImportError:
    # Fallback for older langchain versions
    from langchain.prompts import PromptTemplate
    from langchain.llms.ollama import Ollama

from config import settings
from services.vector_db import vector_db


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline for medical diagnosis."""

    def __init__(self):
        self.llm = None
        self.vector_db = vector_db
        self.prompt_template = None
        self._initialize_llm()

    def _initialize_llm(self):
        """Initialize LLM (Ollama)."""
        if not settings.OLLAMA_ENABLED:
            return

        try:
            self.llm = Ollama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0.3,
                top_p=0.9,
                top_k=40,
            )
        except Exception as e:
            print(f"Ollama LLM initialization failed: {e}")

    def _get_medical_prompt(self) -> PromptTemplate:
        """Get medical diagnosis prompt template."""
        template = """You are a medical assistant helping with primary care diagnosis suggestions.
TẤT CẢ CÂU TRẢ LỜI CỦA BẠN PHẢI ĐƯỢC VIẾT BẰNG TIẾNG VIỆT (VIETNAMESE).

Given the patient symptoms and top suspected diseases, provide:
1. Tóm tắt kết quả (Summary of findings)
2. Suy luận lâm sàng (Clinical reasoning)
3. Lưu ý an toàn (Safety notes - when to seek immediate care)
4. Lưu ý công bằng (Fairness notes - avoid bias in recommendations)
5. Giới hạn đánh giá (Limitations of the assessment)
6. Đề xuất các bước tiếp theo (Suggested next steps)

Patient Symptoms:
{symptoms}

Top Suspected Diseases (ranked by ML model):
{diseases}

Historical Similar Patient Cases (from clinic database):
{historical_cases}

Medical Context from Knowledge Base:
{context}

Please provide a structured analysis in Vietnamese (Tiếng Việt):"""

        return PromptTemplate(
            input_variables=["symptoms", "diseases", "historical_cases", "context"],
            template=template,
        )

    def retrieve_context(
        self,
        query: str,
        top_k: int = 3,
    ) -> str:
        """Retrieve relevant medical context."""
        if not self.vector_db:
            return ""

        results = self.vector_db.search_similar(query, n_results=top_k)
        context_parts = []
        for result in results:
            context_parts.append(f"- {result['name']}: {result['document']}")

        return "\n".join(context_parts) if context_parts else ""

    def retrieve_patient_cases(self, query: str, top_k: int = 3) -> str:
        """Retrieve similar historical patient cases."""
        if not hasattr(self.vector_db, 'search_similar_patients'):
            return "No historical cases capability available."
            
        results = self.vector_db.search_similar_patients(query, n_results=top_k)
        if not results:
            return "No similar historical cases found."
            
        case_parts = []
        for i, result in enumerate(results):
            case_parts.append(f"Case {i+1}: {result['document']} (Confidence: {1 - result['distance']:.2f})")
            
        return "\n".join(case_parts)

    def generate_explanation(
        self,
        symptoms: List[str],
        top_diseases: List[dict],
        additional_context: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate LLM-based explanation for diagnosis.
        
        Args:
            symptoms: List of reported symptoms
            top_diseases: List of top predicted diseases with scores
            additional_context: Additional context from vector DB
        
        Returns:
            Generated explanation or None if LLM unavailable
        """
        if not self.llm or not settings.OLLAMA_ENABLED:
            return None

        try:
            # Format symptoms
            symptoms_text = "\n".join([f"- {s}" for s in symptoms])

            # Format diseases
            diseases_text = "\n".join([
                f"- {d['name']} (confidence: {d['score']:.2%})"
                for d in top_diseases[:5]
            ])

            # Retrieve context if vector DB available
            context = self.retrieve_context(symptoms_text, top_k=3)
            if additional_context:
                context += f"\n\nAdditional Context:\n{additional_context}"

            # Retrieve historical patient cases
            historical_cases = self.retrieve_patient_cases(symptoms_text, top_k=3)

            # Get prompt
            prompt = self._get_medical_prompt()
            formatted_prompt = prompt.format(
                symptoms=symptoms_text,
                diseases=diseases_text,
                historical_cases=historical_cases,
                context=context or "No additional context available",
            )

            # Generate using LLM
            explanation = self.llm(formatted_prompt)
            return explanation

        except Exception as e:
            print(f"RAG generation error: {e}")
            return None

    def generate_summary(
        self,
        diagnosis: dict,
        max_length: int = 200,
    ) -> str:
        """Generate a concise summary for a diagnosis."""
        if not self.llm or not settings.OLLAMA_ENABLED:
            return ""

        try:
            summary_prompt = f"""Summarize this medical diagnosis in {max_length} characters or less.
Please output the summary entirely in Vietnamese (Viết bằng Tiếng Việt).
            
Disease: {diagnosis.get('disease', '')}
Score: {diagnosis.get('score', 0):.2%}
Symptoms: {', '.join(diagnosis.get('symptoms', []))}

Keep it factual and concise:"""

            summary = self.llm(summary_prompt)
            return summary[:max_length]

        except Exception as e:
            print(f"Summary generation error: {e}")
            return ""

    def check_safety_concerns(self, diagnosis: dict) -> List[str]:
        """Check for safety concerns in diagnosis."""
        safety_prompts = []

        # Check if requires emergency care
        high_risk_keywords = ["chest pain", "severe", "emergency", "critical"]
        symptoms_text = " ".join(diagnosis.get("symptoms", [])).lower()

        for keyword in high_risk_keywords:
            if keyword in symptoms_text:
                safety_prompts.append(f"⚠️ '{keyword}' detected - may require urgent care")

        return safety_prompts


# Global RAG pipeline instance
try:
    rag_pipeline = RAGPipeline()
except Exception as e:
    print(f"Warning: RAG pipeline initialization failed: {e}")
    rag_pipeline = None
