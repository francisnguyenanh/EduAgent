# GCP Evidence Checklist (Phase 7 — chụp thủ công, làm sau khi code/deploy đã ổn định)

> Mục đích: thu thập bằng chứng GCP Native cho README/video demo (Phase 7 DoD: "mọi bằng chứng GCP đã nằm trong thư mục assets"). Đăng nhập Console bằng `eikitomobe@gmail.com`, đảm bảo project đang chọn là `project-4fc36103-f4ca-49f6-883`.
>
> Theo quy định của BTC, chúng ta cần chứng minh ứng dụng chạy trên GCP bằng cách: chèn live `.run.app` URL hoặc thêm một đoạn quay màn hình ngắn Cloud Console (Cloud Run dashboard, Vertex AI logs, v.v.) vào video demo. 
> Lưu các ảnh chụp/video minh họa vào `assets/gcp_evidence/` (tạo mới) để dễ dùng lại khi quay video demo (Phase 8).

**URL Cloud Run service thật (đã deploy Phase 7/ĐỢT 4):** `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app`
Lưu ý: Mở URL này bằng trình duyệt sẽ vào thẳng giao diện Web Demo (Student/Teacher Portal) do chúng ta đã deploy với cờ `--allow-unauthenticated`.

---

---

## 🚀 KỊCH BẢN TEST THỰC TẾ ĐỂ SINH DỮ LIỆU & TRACE (EXECUTION PLAN)

Trước khi chụp màn hình, hãy chạy các kịch bản sau để hệ thống sinh ra traffic, log, trace, và dữ liệu Firestore thực tế:

### Kịch bản 1: Chạy Test Pipeline Tầng 1 (Sinh Trace Spans & Firestore History)
Chạy script demo để kích hoạt pipeline 9-node hoàn chỉnh với Gemini và Firestore:
```powershell
# Chạy demo Tier 1 với 3 bài luận liên tiếp để chứng minh Memory & Trace
python scripts/demo_tier1_run.py
```
*Kết quả sinh ra:* 
- Traces thật với đầy đủ các span `@traced_node` được gửi lên **Google Cloud Trace**.
- Cập nhật profile học sinh vào **Firestore** (`student_profiles`).

### Kịch bản 2: Gửi Event vào Cloud Run & Pub/Sub (Sinh Cloud Run Metrics & Logs)
Mở trình duyệt hoặc dùng script để gửi request trực tiếp tới Cloud Run live service:
```powershell
# Kiểm tra health-check của Cloud Run
curl -X GET https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/health-check

# Hoặc chạy kiểm thử subscriber/aggregator
python scripts/verify_firestore.py
```

### Kịch bản 3: Truy cập Web Portal trực tiếp trên Cloud Run
1. Mở trình duyệt truy cập: `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app`
2. Thử nghiệm giao diện Student Portal (gửi 1 phản hồi tranh biện) và xem Teacher Dashboard.

---

## 📸 DANH SÁCH MÀN HÌNH CẦN CHỤP & HƯỚNG DẪN CHI TIẾT (WHAT & HOW TO CAPTURE)

> [!TIP]
> Tất cả ảnh chụp màn hình nên được lưu vào thư mục: `assets/gcp_evidence/` với định dạng PNG rõ nét.

| STT | Tên file đề xuất | Dịch vụ GCP | Mục tiêu bằng chứng |
|:---|:---|:---|:---|
| 1 | `01_cloud_trace_e2e_spans.png` | **Cloud Trace** | Cây phân cấp Span thời gian thực, chứng minh OpenTelemetry W3C tracing |
| 2 | `02_cloud_run_service_metrics.png` | **Cloud Run** | Service live tại `asia-southeast1`, biểu đồ Request/Latency/Memory |
| 3 | `03_firestore_live_data.png` | **Firestore** | Cấu trúc dữ liệu `student_profiles` & `class_analytics` |
| 4 | `04_pubsub_topic_dlq.png` | **Pub/Sub** | Topic `essay-evaluated` + cấu hình Dead Letter Queue (DLQ) |
| 5 | `05_cloud_logging_structured.png` | **Cloud Logging** | Log JSON có trường `logging.googleapis.com/trace` |
| 6 | `06_web_portal_live.png` | **Web UI** | Giao diện chạy live trên domain `.run.app` |

---

### Chi tiết từng bước chụp màn hình:

### 1. Cloud Trace — Cây phân cấp Span End-to-End (`01_cloud_trace_e2e_spans.png`)
* **Cách vào:** GCP Console $\rightarrow$ Tìm **Trace** (hoặc Trace Explorer).
* **Thao tác:** 
  1. Chọn khoảng thời gian **"Last 1 hour"**.
  2. Bấm vào một Trace có tên bắt đầu bằng `eduagent.pipeline.essay_evaluation` hoặc `eduagent.node.class_aggregator`.
  3. Mở rộng (Expand) toàn bộ cây Waterfall Spans.
* **Điểm cần thấy rõ trong ảnh:**
  - Chuỗi Span theo đúng thứ tự: `intake` $\rightarrow$ `sanitizer` $\rightarrow$ `summarizer` $\rightarrow$ `persona_selector` $\rightarrow$ `debate_loop` $\rightarrow$ `cognitive_scorer` $\rightarrow$ `profile_mutator`.
  - Panel bên phải: Hiển thị các Span Attributes (ví dụ: `eduagent.student_id`, `eduagent.class_id`, `gemini.model`).
  - Thời gian thực tế đo được (ví dụ: 1.5s - 4.5s cho toàn bộ pipeline).

### 2. Cloud Run — Dashboard & Metrics (`02_cloud_run_service_metrics.png`)
* **Cách vào:** GCP Console $\rightarrow$ **Cloud Run** $\rightarrow$ chọn service `eduagent-class-aggregator`.
* **Thao tác:**
  1. Ở trang tổng quan (Service details), hiển thị rõ URL: `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app` và trạng thái tích xanh (Active).
  2. Chọn tab **Metrics** $\rightarrow$ Chụp đồ thị **Request count**, **Request latency**, và **Container CPU/Memory allocation**.
* **Điểm cần thấy rõ trong ảnh:** Service đang chạy tại region `asia-southeast1`, có traffic gửi đến và xử lý thành công (2xx).

### 3. Firestore Database — Dữ liệu học sinh & Lớp học (`03_firestore_live_data.png`)
* **Cách vào:** GCP Console $\rightarrow$ **Firestore** $\rightarrow$ **Data**.
* **Thao tác:**
  1. Cột Collection: Chọn `student_profiles`.
  2. Cột Document: Chọn một học sinh (ví dụ `stu_stuck` hoặc học sinh vừa chạy test).
  3. Cột Fields: Mở rộng các trường `essay_history`, `weakness_tags`, `flags`, `persona_streak`.
* **Điểm cần thấy rõ trong ảnh:** Cấu trúc tài liệu NoSQL lưu trữ lịch sử học tập dài hạn (Long-term Memory), phục vụ cho khả năng cá nhân hóa của Agent.

### 4. Pub/Sub & Dead Letter Queue (`04_pubsub_topic_dlq.png`)
* **Cách vào:** GCP Console $\rightarrow$ **Pub/Sub**.
* **Thao tác:**
  1. Vào **Subscriptions** $\rightarrow$ Chọn `class-aggregator-sub`.
  2. Kéo xuống phần **Dead lettering** (thấy rõ Topic chuyển tiếp khi lỗi: `essay-evaluated-dlq`, Maximum delivery attempts = 5).
* **Điểm cần thấy rõ trong ảnh:** Thiết kế kiến trúc Event-Driven chịu lỗi cao (Fault-tolerant & Resilient).

### 5. Cloud Logging — Structured Logs (`05_cloud_logging_structured.png`)
* **Cách vào:** GCP Console $\rightarrow$ **Logging** $\rightarrow$ **Logs Explorer**.
* **Thao tác:**
  1. Lọc: `resource.type="cloud_run_revision" AND resource.labels.service_name="eduagent-class-aggregator"`
  2. Mở rộng 1 dòng log JSON thành công.
* **Điểm cần thấy rõ trong ảnh:** Trường `logging.googleapis.com/trace` liên kết chặt chẽ với Cloud Trace, cùng message xử lý bài chấm.

### 6. Live Web Portal trên Cloud Run (`06_web_portal_live.png`)
* **Cách vào:** Mở tab ẩn danh trình duyệt $\rightarrow$ gõ URL `.run.app`.
* **Thao tác:** Chụp toàn màn hình bao gồm thanh địa chỉ trình duyệt hiển thị rõ domain `.asia-southeast1.run.app` và giao diện Student / Teacher Portal.

---

## F. Giữ Live Demo & Tối ưu chi phí (Cập nhật theo chỉ dẫn của BTC)

> [!IMPORTANT]
> BTC cho phép tắt các dịch vụ sau khi đã có bằng chứng để tiết kiệm credit. Tuy nhiên, nếu muốn giữ live demo để giám khảo tự trải nghiệm (khuyên dùng để tăng điểm trải nghiệm thực tế), ta phải chú ý tối ưu chi phí và thiết lập tài khoản thanh toán chuẩn xác.

1. **Quay màn hình / Chụp bằng chứng (Evidence Collection):**
   - Quay một đoạn clip ngắn (5-10 giây) hoặc chụp màn hình lúc truy cập vào live `.run.app` URL hoặc Cloud Run dashboard / Vertex AI dashboard.
   - Đưa URL live `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app` vào phần text mô tả và chèn text overlay hoặc cảnh quay URL này vào video demo.
2. **Cấu hình Scale-to-Zero cho Cloud Run (Tối ưu hóa chi phí):**
   - Đảm bảo service `eduagent-class-aggregator` được cấu hình để scale về 0 instance khi rảnh rỗi (idle) để không bị tính tiền vô ích.
   - Kiểm tra cấu hình Auto-scaling: Target instance tối thiểu (`min-instances`) phải là `0`. Lệnh deploy nên có: `--min-instances 0`.
3. **Quản lý Billing Account:**
   - Đảm bảo GCP Project được liên kết đúng Billing Account đã nhận credit $150 (chuyển đổi từ "Trial Billing Account" sang account chính nếu cần để áp dụng mã code khuyến mãi).
   - Tuyệt đối không để khoảng trống (no spaces) khi dán code khuyến mãi và thiết lập cảnh báo ngân sách (Budget Alerts) ở mức $120-$130 để nhận email cảnh báo sớm.

---

## Sau khi chụp xong

1. Lưu toàn bộ ảnh vào `assets/gcp_evidence/`.
2. Đánh dấu mục *"Thu thập bằng chứng GCP Native"* trong `TODO.md`.
3. Tích hợp ảnh và clip vào Video Demo (Phase 8) & README bài nộp.

