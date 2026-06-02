# 🩺 MedAI - Hệ Thống Hỗ Trợ Chẩn Đoán Y Khoa Thông Minh

Dự án MedAI cung cấp một nền tảng khám chữa bệnh tích hợp **AI Động Cơ Kép** (Dual Engine AI) mạnh mẽ, kết hợp giữa mô hình phân tích ngôn ngữ tự nhiên **LLM (Llama 3)** và mô hình học máy vững chắc **XGBoost**.

Dưới đây là hướng dẫn chi tiết từng bước để chạy dự án trên máy tính của bạn.

---

## 🛠️ Cài đặt yêu cầu hệ thống

Trước khi bắt đầu, hãy đảm bảo máy tính bạn đã cài đặt các phần mềm sau:

1. **Python 3.9+**: Dùng để chạy Backend.
2. **Node.js (v16+)**: Dùng để chạy giao diện Frontend.
3. **Ollama**: Động cơ để chạy mô hình AI nội bộ cục bộ (rất quan trọng cho tính năng phân tích LLM).

---

## 🚀 Bước 1: Cài đặt và Bật Ollama (Rất quan trọng)

Gần đây hệ thống báo lỗi `The term 'ollama' is not recognized`. Điều này có nghĩa là máy bạn chưa cài đặt Ollama. Hãy làm theo hướng dẫn sau:

1. Vào trang chủ Ollama: [https://ollama.com/download/windows](https://ollama.com/download/windows)
2. Tải file cài đặt `.exe` và click đúp để cài đặt.
3. Sau khi cài đặt xong, hãy mở lại một cửa sổ dòng lệnh (Terminal/PowerShell) **mới hoàn toàn** để hệ thống nhận diện lệnh `ollama`.
4. Tải mô hình AI (Llama 3) về máy (Máy bạn dùng RTX 3060Ti 8GB rất dư sức chạy mô hình này):
   ```bash
   ollama pull llama3
   ```
   *(Quá trình tải có thể mất vài phút tùy tốc độ mạng, dung lượng khoảng 4.7GB)*
5. Đảm bảo Ollama luôn chạy ngầm ở dưới thanh Taskbar, hoặc chạy lệnh sau để bật server:
   ```bash
   ollama serve
   ```

---

## ⚙️ Bước 2: Khởi động Backend (Máy chủ)

Mở một cửa sổ Terminal/PowerShell mới và điều hướng vào thư mục gốc của dự án, sau đó làm theo các bước:

1. Di chuyển vào thư mục `backend`:
   ```bash
   cd backend
   ```
2. Cài đặt các thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. Chạy server Backend (FastAPI):
   ```bash
   python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```
   *Thành công khi bạn thấy dòng chữ `Application startup complete`.*

---

## 🖥️ Bước 3: Khởi động Frontend (Giao diện)

Mở thêm **một cửa sổ Terminal/PowerShell thứ hai**, giữ nguyên cửa sổ Backend đang chạy, và thực hiện:

1. Di chuyển vào thư mục `frontend`:
   ```bash
   cd frontend
   ```
2. Cài đặt thư viện Node.js:
   ```bash
   npm install
   ```
3. Khởi chạy giao diện website:
   ```bash
   npm run dev -- --host 127.0.0.1 --port 5173
   ```
   *Thành công khi Terminal hiện đường link truy cập, ví dụ `http://127.0.0.1:5173`.*

---

## 🎯 Trải nghiệm tính năng

Bây giờ bạn có thể mở trình duyệt (Chrome, Edge...) và truy cập:

- **Giao diện Chẩn Đoán (Cho bệnh nhân/bác sĩ):** [http://127.0.0.1:5173/](http://127.0.0.1:5173/)
- **Giao diện Quản Trị (Nhập liệu & Huấn luyện AI):** [http://127.0.0.1:5173/admin](http://127.0.0.1:5173/admin)

### ✨ Mẹo dùng:
1. Vào tab **Admin > Dữ liệu** để dùng tính năng **Import qua LLM** để nạp file CSV Kaggle tiếng Anh, AI sẽ tự dịch sang tiếng Việt.
2. Tại trang **Chẩn Đoán**, chọn động cơ **"LLM (Phân tích sâu bằng ngôn ngữ tự nhiên)"** để thấy sự khác biệt về sự chi tiết và lập luận y khoa!
