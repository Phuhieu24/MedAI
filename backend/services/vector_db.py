import os
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from config import settings
from models.disease import Disease, Symptom, DiseaseSymptomLink

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class VectorDB:
    """Vector database manager using Chroma for semantic search."""

    def __init__(self):
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb not installed. pip install chromadb")
        
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        
        # Initialize Chroma persistent client (updated API for chromadb 0.4.24+)
        try:
            self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        except TypeError:
            # Fallback for older chromadb versions
            self.client = chromadb.Client()
        
        # Cấu hình mô hình Đa ngôn ngữ (Hỗ trợ tốt Tiếng Việt)
        try:
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )
        except Exception as e:
            print(f"Lỗi tải mô hình đa ngôn ngữ: {e}. Sẽ dùng mặc định.")
            self.embedding_fn = None
            
        self.collection_name = settings.CHROMA_COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure collection exists."""
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=self.embedding_fn
            )

    def index_disease(self, disease_id: int, disease_name: str, description: str = ""):
        """Index a disease in vector DB."""
        doc_id = f"disease_{disease_id}"
        metadata = {
            "type": "disease",
            "disease_id": str(disease_id),
            "disease_name": disease_name,
        }
        
        text = f"{disease_name}. {description}"
        self.collection.add(
            ids=[doc_id],
            metadatas=[metadata],
            documents=[text],
        )

    def index_symptom(self, symptom_id: int, symptom_name: str, description: str = ""):
        """Index a symptom in vector DB."""
        doc_id = f"symptom_{symptom_id}"
        metadata = {
            "type": "symptom",
            "symptom_id": str(symptom_id),
            "symptom_name": symptom_name,
        }
        
        text = f"{symptom_name}. {description}"
        self.collection.add(
            ids=[doc_id],
            metadatas=[metadata],
            documents=[text],
        )

    def build_index(self, db: Session):
        """Build full index from database using batch processing."""
        # Clear existing collection
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        
        self._ensure_collection()
        
        # 1. Batch Index Diseases
        diseases = db.query(Disease).filter(Disease.is_active == True).all()
        d_ids, d_metadatas, d_documents = [], [], []
        
        for disease in diseases:
            description = disease.description or ""
            # Nối các triệu chứng liên quan
            symptoms_list = [link.symptom.name for link in disease.symptom_links if link.symptom]
            symptoms_text = ", ".join(symptoms_list) if symptoms_list else "Chưa rõ triệu chứng"
            
            d_ids.append(f"disease_{disease.id}")
            d_metadatas.append({
                "type": "disease",
                "disease_id": str(disease.id),
                "disease_name": disease.name,
            })
            d_documents.append(f"Bệnh: {disease.name}. Mô tả: {description}. Triệu chứng thường gặp: {symptoms_text}")
            
        if d_ids:
            self.collection.add(ids=d_ids, metadatas=d_metadatas, documents=d_documents)
        
        # 2. Batch Index Symptoms
        symptoms = db.query(Symptom).filter(Symptom.is_active == True).all()
        s_ids, s_metadatas, s_documents = [], [], []
        
        for symptom in symptoms:
            description = symptom.description or ""
            s_ids.append(f"symptom_{symptom.id}")
            s_metadatas.append({
                "type": "symptom",
                "symptom_id": str(symptom.id),
                "symptom_name": symptom.name,
            })
            s_documents.append(f"Triệu chứng: {symptom.name}. Mô tả: {description}")
            
        if s_ids:
            self.collection.add(ids=s_ids, metadatas=s_metadatas, documents=s_documents)

    def search_similar(
        self,
        query: str,
        n_results: int = 5,
        query_type: Optional[str] = None,
    ) -> List[Dict]:
        """
        Search for similar documents.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            query_type: Filter by 'disease' or 'symptom' (None for both)
        
        Returns:
            List of search results with metadata
        """
        try:
            where_filter = None
            if query_type:
                where_filter = {"type": query_type}
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
            )
            
            output = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0
                    document = results["documents"][0][i] if results["documents"] else ""
                    
                    output.append({
                        "id": doc_id,
                        "type": metadata.get("type"),
                        "name": metadata.get("disease_name") or metadata.get("symptom_name"),
                        "distance": float(distance),
                        "document": document,
                    })
            
            return output
        except Exception as e:
            print(f"Vector search error: {e}")
            return []

    def index_patient_case(self, patient_id: int, age: int, gender: str, symptoms: str, symptom_count: int, disease: str):
        """Index a patient case in vector DB for hybrid search."""
        doc_id = f"patient_case_{patient_id}"
        metadata = {
            "type": "patient_case",
            "patient_id": patient_id,
            "age": age,
            "gender": gender,
            "disease": disease,
            "symptom_count": symptom_count
        }
        
        # Text document for semantic search
        text = f"Bệnh nhân {gender.lower()}, {age} tuổi. Có {symptom_count} triệu chứng: {symptoms}. Được chẩn đoán: {disease}."
        
        try:
            self.collection.add(
                ids=[doc_id],
                metadatas=[metadata],
                documents=[text],
            )
        except Exception as e:
            # If exists, we update
            self.collection.update(
                ids=[doc_id],
                metadatas=[metadata],
                documents=[text],
            )

    def index_patient_cases_batch(self, patients_data: List[Dict]):
        """Index multiple patient cases in vector DB efficiently in batches."""
        if not patients_data:
            return
            
        ids = []
        metadatas = []
        documents = []
        
        for p in patients_data:
            doc_id = f"patient_case_{p['patient_id']}"
            metadata = {
                "type": "patient_case",
                "patient_id": p['patient_id'],
                "age": p['age'],
                "gender": p['gender'],
                "disease": p['disease'],
                "symptom_count": p['symptom_count']
            }
            text = f"Bệnh nhân {p['gender'].lower()}, {p['age']} tuổi. Có {p['symptom_count']} triệu chứng: {p['symptoms']}. Được chẩn đoán: {p['disease']}."
            
            ids.append(doc_id)
            metadatas.append(metadata)
            documents.append(text)
            
        try:
            # Use upsert to handle both insert and update gracefully
            self.collection.upsert(
                ids=ids,
                metadatas=metadatas,
                documents=documents,
            )
        except AttributeError:
            # Fallback if upsert is not supported in the chromadb version
            try:
                self.collection.add(ids=ids, metadatas=metadatas, documents=documents)
            except Exception:
                self.collection.update(ids=ids, metadatas=metadatas, documents=documents)

    def search_similar_patients(
        self,
        query_symptoms: str,
        patient_age: Optional[int] = None,
        patient_gender: Optional[str] = None,
        n_results: int = 3
    ) -> List[Dict]:
        """Search for similar patient cases based on symptoms, age, and gender."""
        try:
            where_conditions = [{"type": "patient_case"}]
            
            if patient_gender:
                where_conditions.append({"gender": patient_gender})
                
            if patient_age is not None:
                # Age within +/- 5 years
                where_conditions.append({"age": {"$gte": max(0, patient_age - 5)}})
                where_conditions.append({"age": {"$lte": patient_age + 5}})
                
            # If multiple conditions, we must wrap them in $and
            where_filter = None
            if len(where_conditions) > 1:
                where_filter = {"$and": where_conditions}
            else:
                where_filter = where_conditions[0]

            results = self.collection.query(
                query_texts=[query_symptoms],
                n_results=n_results,
                where=where_filter,
            )
            
            output = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0
                    document = results["documents"][0][i] if results["documents"] else ""
                    
                    output.append({
                        "id": doc_id,
                        "type": metadata.get("type"),
                        "disease": metadata.get("disease"),
                        "age": metadata.get("age"),
                        "gender": metadata.get("gender"),
                        "distance": float(distance),
                        "document": document,
                    })
            
            return output
        except Exception as e:
            print(f"Patient case search error: {e}")
            return []

    def search_symptoms(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for symptoms similar to query."""
        return self.search_similar(query, n_results, query_type="symptom")

    def search_diseases(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for diseases similar to query."""
        return self.search_similar(query, n_results, query_type="disease")

    def get_disease_context(self, disease_id: int, symptom_ids: List[int]) -> str:
        """Get context about a disease and its symptoms for LLM."""
        try:
            disease_doc = self.collection.get(ids=[f"disease_{disease_id}"])
            disease_text = disease_doc["documents"][0] if disease_doc["documents"] else ""
            
            symptom_texts = []
            for sid in symptom_ids:
                symptom_doc = self.collection.get(ids=[f"symptom_{sid}"])
                if symptom_doc["documents"]:
                    symptom_texts.append(symptom_doc["documents"][0])
            
            context = f"Disease: {disease_text}\n\nSymptoms:\n"
            context += "\n".join(symptom_texts)
            return context
        except Exception:
            return ""


# Global vector DB instance
try:
    vector_db = VectorDB()
except Exception as e:
    print(f"Warning: Vector DB initialization failed: {e}")
    vector_db = None