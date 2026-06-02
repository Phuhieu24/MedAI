import networkx as nx
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models.disease import Disease, Symptom, DiseaseSymptomLink

class GraphDBManager:
    """Quản lý In-memory Medical Knowledge Graph bằng NetworkX."""
    
    def __init__(self):
        self.graph = nx.Graph()
        
    def build_medical_graph(self, db: Session):
        """Xây dựng đồ thị từ dữ liệu SQLite."""
        self.graph.clear()
        
        # 1. Thêm Node Bệnh
        diseases = db.query(Disease).filter(Disease.is_active == True).all()
        for d in diseases:
            self.graph.add_node(f"disease_{d.id}", type="disease", name=d.name, id=d.id)
            
        # 2. Thêm Node Triệu chứng
        symptoms = db.query(Symptom).filter(Symptom.is_active == True).all()
        for s in symptoms:
            self.graph.add_node(f"symptom_{s.id}", type="symptom", name=s.name, id=s.id)
            
        # 3. Thêm Edges (Đường nối)
        links = db.query(DiseaseSymptomLink).all()
        for link in links:
            d_node = f"disease_{link.disease_id}"
            s_node = f"symptom_{link.symptom_id}"
            if self.graph.has_node(d_node) and self.graph.has_node(s_node):
                self.graph.add_edge(s_node, d_node, weight=link.weight_score)
                
        print(f"[GraphDB] Medical Graph built successfully with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
        
    def get_graph_insights(self, symptom_ids: List[int]) -> str:
        """Thuật toán loang trên đồ thị (Graph Traversal) để tìm giao điểm."""
        if not self.graph.nodes:
            return ""
            
        valid_symptom_nodes = [f"symptom_{sid}" for sid in symptom_ids if self.graph.has_node(f"symptom_{sid}")]
        if not valid_symptom_nodes:
            return ""
            
        # Tìm các bệnh có liên kết tới các triệu chứng này
        disease_scores = {}
        for s_node in valid_symptom_nodes:
            s_name = self.graph.nodes[s_node]['name']
            for neighbor in self.graph.neighbors(s_node):
                if self.graph.nodes[neighbor]['type'] == 'disease':
                    weight = self.graph[s_node][neighbor].get('weight', 1)
                    if neighbor not in disease_scores:
                        disease_scores[neighbor] = {"score": 0, "matched_symptoms": [], "name": self.graph.nodes[neighbor]['name']}
                    disease_scores[neighbor]["score"] += weight
                    disease_scores[neighbor]["matched_symptoms"].append(s_name)
                    
        if not disease_scores:
            return ""
            
        # Sắp xếp các bệnh có tổng trọng số đồ thị cao nhất
        sorted_diseases = sorted(disease_scores.values(), key=lambda x: x["score"], reverse=True)[:3]
        
        insights = []
        insights.append("Phân tích từ Đồ thị Tri thức Y khoa (Medical Knowledge Graph):")
        for rank, d in enumerate(sorted_diseases, 1):
            syms_str = ", ".join(d['matched_symptoms'])
            insights.append(f"{rank}. Các Node triệu chứng [{syms_str}] tạo ra các đường nối trực tiếp và hội tụ mạnh nhất về Node bệnh [{d['name']}] với tổng trọng số liên kết mạng nơ-ron là {d['score']} điểm.")
            
        return "\n".join(insights)

# Khởi tạo instance toàn cục (Singleton)
graph_manager = GraphDBManager()
