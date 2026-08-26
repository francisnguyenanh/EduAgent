# Hackathon Eligibility & Originality Boundary Statement

> **Submission Certification:** Dự án **EduAgent** được phát triển hoàn chỉnh cho cuộc thi Hackathon, tuân thủ 100% quy định về tính nguyên bản (Originality), minh bạch kiến trúc và bản quyền mã nguồn mở.

---

## 1. Tuyên Bố Ranh Giới Đóng Góp Mới (Original Contribution Boundary)

Nhằm đảm bảo tính minh bạch tuyệt đối đối với ban giám khảo, chúng tôi làm rõ ranh giới kiến trúc và các đóng góp hoàn toàn mới trong đợt phát triển này:

| Hạng Mục (Area) | Kiến Trúc Đã Có Trước Đây (Prior Art / Baseline) | Đóng Góp Hoàn Toàn Mới Của EduAgent (New Contribution) |
|---|---|---|
| **Mô Hình Tương Tác** | Chatbot một lượt (Single-turn QA / Answer Generator) | **Autonomous Socratic Debate Loop (3 turns)** với 4 Persona sư phạm chuyên sâu và quy tắc không tiết lộ đáp án (Zero-Answer-Leak). |
| **Trí Nhớ Tác Nhân** | Stateless (Mỗi phiên là một khởi tạo trống) | **Persistent Long-Term Memory (Firestore)**: Đột biến hồ sơ học sinh qua nhiều tuần, theo dõi chuỗi kẹt persona, tính toán độ dốc điểm số. |
| **Tổng Hợp Cấp Lớp** | Không có (Mỗi học sinh là một ốc đảo cô lập) | **Class-Wide Systemic Fallacy Clustering & Intervention Priority Index**: Thuật toán phân cụm và xếp hạng 100% tất định (ZERO LLM-as-judge). |
| **Công Cụ Giáo Viên** | Không có | **Autonomous Teacher Action Loop**: Tự động sinh giáo án bài giảng 15 phút, xuất bảng Google Sheets, gửi Gmail Digest và tạo Thư gửi phụ huynh 1-click. |
| **Độ Tin Cậy & Eval** | Đánh giá chủ quan qua LLM-as-judge | **4-Layer Deterministic ADK Eval Suite (50/50 deterministic test cases passed)**: Kiểm thử tất định đa tầng (An ninh, Hành vi, Trí nhớ, Bước nhảy nhận thức). |
| **Khả Năng Vận Hành** | Chạy thử nghiệm Localhost | **Google Cloud Native Microservices**: Cloud Run (`asia-southeast1`), Cloud Trace, Event-driven Pub/Sub, Firestore Session TTL. |

---

## 2. Thống Kê Mã Nguồn & Bản Quyền (Codebase & Licensing)

* **Giấy phép mã nguồn (License):** MIT License / Open Source.
* **Quy chuẩn mã nguồn:** 100% type-annotated Python (FastAPI, Google GenAI SDK, Pydantic, OpenTelemetry), chuẩn linting nghiêm ngặt, bao phủ kiểm thử tự động với hơn 35 unit test và 50 eval test case.
* **Cam kết:** Không sử dụng bất kỳ thư viện đóng độc quyền (proprietary closed-source) nào ngoài các dịch vụ công khai tiêu chuẩn của Google Cloud Platform.
