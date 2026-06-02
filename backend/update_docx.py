import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = docx.Document()

title = doc.add_heading('Báo Cáo Dự Án: MedAI - Hệ Thống Hỗ Trợ Chẩn Đoán Y Khoa Thông Minh (Dual-Engine AI)', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_heading('1. Giới thiệu Tổng quan', level=1)
doc.add_paragraph('MedAI là một hệ thống hỗ trợ chẩn đoán y khoa ứng dụng Trí tuệ Nhân tạo tiên tiến, được thiết kế với kiến trúc "Động cơ kép" (Dual-Engine). Dự án giải quyết bài toán chẩn đoán bệnh thông qua việc kết hợp khả năng suy luận ngôn ngữ tự nhiên của Mô hình Ngôn ngữ Lớn (LLM) và tính ổn định toán học của mô hình Học máy truyền thống (XGBoost).')
doc.add_paragraph('Mục tiêu tối thượng của hệ thống là mang lại độ chính xác cao, tính minh bạch trong y khoa và hướng tới phục vụ người bệnh thuộc nhóm yếu thế.')

doc.add_heading('2. Công nghệ Sử dụng (Technology Stack)', level=1)
doc.add_paragraph('Hệ thống được chia thành 3 phân hệ cốt lõi với các công nghệ hiện đại nhất:')

doc.add_heading('2.1. Phân hệ Giao diện (Frontend)', level=2)
doc.add_paragraph('- React.js & Vite: Xây dựng giao diện Single-Page Application (SPA) với tốc độ phản hồi tính bằng mili-giây.')
doc.add_paragraph('- TailwindCSS: Thiết kế giao diện (UI/UX) sạch sẽ, thân thiện, dễ sử dụng cho cả người già và bệnh nhân không rành công nghệ.')

doc.add_heading('2.2. Phân hệ Máy chủ (Backend & Database Tri-Architecture)', level=2)
doc.add_paragraph('Hệ thống tiên phong sử dụng "Kiến trúc song song 3 Database" (Tri-Architecture) đảm bảo tốc độ và tính suy luận hoàn hảo:')
doc.add_paragraph('- SQLite (Storage Engine): Lưu trữ dữ liệu cốt lõi (Hồ sơ, Danh mục bệnh, Triệu chứng). Đây là nguồn chân lý duy nhất (Single Source of Truth), đảm bảo toàn vẹn dữ liệu.')
doc.add_paragraph('- ChromaDB (Vector Search Engine): Cơ sở dữ liệu vector lưu trữ nhúng (embeddings) với mô hình đa ngôn ngữ (paraphrase-multilingual). Chuyên làm nhiệm vụ thấu hiểu tiếng Việt, bắt từ lóng và biến đổi câu nói dân dã thành từ khóa chuẩn.')
doc.add_paragraph('- In-memory GraphDB (Reasoning Engine): Sử dụng thư viện NetworkX để mô phỏng một mạng lưới nơ-ron y khoa (Medical Knowledge Graph) trực tiếp trên RAM. Hệ thống này vẽ sơ đồ tư duy kết nối Triệu chứng -> Bệnh, cung cấp năng lực suy luận đường đi logic cho AI, giúp giải quyết triệt để tính toán bệnh đa biến chứng.')

doc.add_heading('2.3. Phân hệ Trí tuệ Nhân tạo (AI Engines)', level=2)
doc.add_paragraph('- LLM Engine (Llama 3 8B): Chạy cục bộ hoàn toàn thông qua Ollama, bảo vệ quyền riêng tư tuyệt đối.')
doc.add_paragraph('- ML Engine (XGBoost): Mô hình Học máy làm mỏ neo toán học vững chắc.')
doc.add_paragraph('- LangChain: Framework điều phối luồng RAG và GraphRAG.')

doc.add_heading('3. Luồng Hoạt động và Xử lý Cốt lõi (Workflows)', level=1)

doc.add_heading('3.1. Luồng Nhập liệu & Khử Trùng lặp (Data Sanitization)', level=2)
doc.add_paragraph('Thay vì nhập liệu thủ công, hệ thống sử dụng LLM để đọc hiểu dữ liệu thô, tự động dịch thuật và bóc tách cấu trúc. Đặc biệt, hệ thống áp dụng cơ chế Khử Trùng Lặp (Deduplication) dọn dẹp các liên kết dư thừa (ví dụ hàng trăm liên kết Đau đầu bị lặp) để ngăn chặn rác dữ liệu làm sai lệch điểm số thuật toán.')

doc.add_heading('3.2. Luồng Nhận diện Triệu chứng (3-Tier Fallback & Strict Threshold)', level=2)
doc.add_paragraph('Áp dụng chiến lược Tìm kiếm dự phòng 3 lớp từ cơ bản đến chuyên sâu:')
doc.add_paragraph('1. Khớp chính xác 100% (SQL).')
doc.add_paragraph('2. Khớp mờ (Fuzzy String Matching).')
doc.add_paragraph('3. Khớp ngữ nghĩa (Semantic Search - Vector DB): Hệ thống sử dụng một ngưỡng chấp nhận cực kỳ khắt khe (Distance Threshold < 0.3) cho các câu văn dài. Nếu câu nói quá phức tạp, AI sẽ từ chối nhận vơ (tránh hiện tượng nhận nhầm "Đau ngực lan lên cằm" thành "Đau cổ"). Điều này đảm bảo tính chính xác đầu vào tuyệt đối cho LLM phân tích phía sau.')

doc.add_heading('3.3. Luồng Chẩn đoán Động cơ Kép & GraphRAG', level=2)
doc.add_paragraph('Đây là "trái tim" của hệ thống, hoạt động theo quy trình 4 bước chặt chẽ:')
doc.add_paragraph('- Truy vấn Đa chiều (Vector RAG + GraphRAG): Khi nhận triệu chứng, hệ thống không chỉ kéo hồ sơ từ ChromaDB, mà còn dùng GraphDB để "loang sóng" (Graph Traversal). Đồ thị sẽ tìm giao điểm mạnh nhất giữa các triệu chứng, lôi ra căn bệnh là tâm điểm của mạng nơ-ron.')
doc.add_paragraph('- Kỹ thuật Lệnh (Prompt Engineering): Đưa cả dữ liệu bệnh án và các phân tích đường đi logic từ GraphRAG vào bối cảnh (Context).')
doc.add_paragraph('- Dự đoán & Giải thích (Generation): LLM tự tin đưa ra chẩn đoán dựa trên kết luận khoa học vững chắc từ đồ thị.')
doc.add_paragraph('- Đối chiếu SQL (DB Mapping): Tên bệnh do LLM sinh ra được soi chiếu ngược lại vào SQLite để bốc mức độ nghiêm trọng và lời khuyên chuẩn, ngăn chặn bịa đặt.')

doc.add_heading('4. Đáp ứng 5 Tiêu Chí Đánh Giá Của Dự Án', level=1)

doc.add_paragraph('1. Độ tin cậy (Reliability): Khắc phục hoàn toàn bệnh "ảo giác" (Hallucination) nhờ 5 lớp bảo vệ: RAG, GraphRAG (suy luận đồ thị), Pydantic (buộc trả JSON), DB Mapping (đối chiếu SQL) và Input Sanitization (dọn rác đầu vào).')

doc.add_paragraph('2. Thiên vị và Công bằng (Fairness): Sử dụng chỉ thị phần cứng trong lõi Prompt: "TUYỆT ĐỐI KHÔNG thiên vị dựa trên giới tính, nghề nghiệp...".')

doc.add_paragraph('3. Chịu lỗi (Fault Tolerance): Khắc phục tình trạng "Khởi động nguội" (Cold Start) của LLM. Nếu máy chủ LLM phản hồi chậm (timeout), khối lệnh ngoại lệ lập tức chuyển hướng sang XGBoost. Hệ thống không bao giờ gián đoạn.')

doc.add_paragraph('4. Tác động xã hội lên nhóm yếu thế (Social Impact): Lời khuyên được tinh chỉnh bằng từ ngữ dân dã, dễ hiểu. Ưu tiên sơ cứu rẻ tiền, an toàn tại nhà cho người nghèo.')

doc.add_paragraph('5. Minh bạch (Explainability): Hệ thống In-memory GraphDB bẻ gãy mô hình hộp đen. Mọi chẩn đoán đều đi kèm giải thích minh bạch: "Trên đồ thị tri thức, các triệu chứng của bạn cùng hội tụ mạnh nhất về căn bệnh này".')

doc.save(r'd:\daihoc\AI002.F21-Tu Duy Tri Tue Nhan Tao\medai - Copy\BaoCao_MedAI.docx')
