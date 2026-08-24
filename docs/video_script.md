# Video Demo Script (≤ 4:00, unedited live execution)

> Giám khảo chỉ chấm **4 phút đầu**. Không mockup, không slideware — mọi thao tác phải chạy thật, live, không cắt ghép.
>
> **Chuẩn bị trước khi quay:**
> - Mở sẵn 4 tab trình duyệt:
>   1. Web UI Live (`https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/`)
>   2. Firestore Console (`student_profiles`, `class_analytics`)
>   3. Gmail của giáo viên (đã đăng nhập, mở hòm thư Drafts)
>   4. Google Cloud Console (Cloud Run, Pub/Sub, Cloud Trace)
> - Chọn sẵn 1 ảnh viết tay thật từ `eval/test_images/` (`messy_essay_videogames.jpg` — có gạch xoá thực tế).

---

## 0:00–0:30 — Problem & Socratic Philosophy (English Voice-Over)

**Nói:**
> "In overcrowded classrooms, one teacher often manages 40+ students with zero time to provide individualized critical thinking coaching. Generic AI tools take the lazy shortcut — they just give students the answer, creating dependency. Our core philosophy: **we use AI to teach students how NOT to depend on AI.**"

**Trên màn hình:** Trang chủ Web UI `eduagent` hoặc slide tiêu đề tinh gọn với triết lý Socratic.

---

## 0:30–1:45 — Tier 1: Multimodal Ingestion & Autonomous Socratic Pipeline (LIVE)

1. **(0:30–0:50) Multimodal Ingestion:**
   - Học sinh đăng nhập (`c1_stu01`).
   - Tải lên ảnh bài luận viết tay thật (`messy_essay_videogames.jpg`) hoặc bấm nút nạp mẫu bài luận.
   - Để nguyên Persona ở chế độ **`🎯 Auto-Detect Weakness`** và bấm **Start Debate**.
2. **(0:50–1:15) Autonomous Routing & Persona Anchoring:**
   - Chỉ vào **Huy hiệu Định tuyến Tự hành (Autonomous Agent Routing)**:
     *"The agent autonomously diagnoses the student's reasoning flaw and routes to the matching Socratic Persona — here, The Devil's Advocate for one-sided argumentation."*
   - Tranh biện 3 lượt Socratic: Nhấn mạnh AI **không bao giờ mớm câu trả lời**, chỉ đặt câu hỏi đào sâu. Mọi câu hỏi đều được kiểm duyệt bởi Zero-LLM Challenge Validator độc lập.
3. **(1:15–1:45) Cognitive Radar Chart & Metacognitive Loop:**
   - Phiên kết thúc $\rightarrow$ Chỉ vào **Biểu đồ Radar Điểm Nhận Thức (2D SVG Spider Chart)** đánh giá 4 trục: *Logical Coherence, Evidence Quality, Scope Awareness, Counterargument Handling*.
   - Nhập 1 câu luận điểm đã sửa đổi vào phần **Metacognitive Self-Correction** và bấm Submit để nhận phản hồi nhận thức tức thì.

---

## 1:45–2:45 — Tier 2: Class Aggregator & Teacher Co-Pilot (LIVE)

1. **(1:45–2:10) Deterministic Priority Index & Fallacy Clusters:**
   - Chuyển sang tài khoản Giáo viên (`c1_teacher`).
   - Mở tab **Priority**: Chỉ vào bảng xếp hạng ưu tiên can thiệp (tính toán bằng công thức toán học xác định, không dùng LLM cảm tính) và biểu đồ phân cụm lỗi tư duy chung của cả lớp.
   - Mở tab **Roster**: Xem biểu đồ Sparkline xu hướng tiến bộ qua từng bài luận của từng học sinh.
2. **(2:10–2:35) Dynamic Settings & Human-In-The-Loop:**
   - Mở tab **Settings**: Chỉ vào ô cấu hình Google Sheet $\rightarrow$ Bấm **`🧪 Test Sheet Connection`** $\rightarrow$ Dòng trạng thái báo xanh thành công ngay lập tức!
   - Chuyển sang Gmail của giáo viên $\rightarrow$ Refresh Drafts $\rightarrow$ Chỉ vào bản thảo email tổng hợp lớp vừa được tự động soạn sẵn:
     *"The agent has zero permission to send emails on its own. The teacher retains the final human-in-the-loop decision to review and click Send."*

---

## 2:45–3:30 — Architecture, GCP Proof & Zero-Trust Eval

Chuyển nhanh qua các tab Cloud Console và Terminal làm bằng chứng kỹ thuật:
1. **Cloud Run Console:** Service `eduagent-class-aggregator` đang chạy live, xử lý các request vừa gửi.
2. **Pub/Sub Console:** Topic `essay-evaluated` + Dead Letter Queue (`essay-evaluated-dlq`).
3. **Cloud Trace:** Cây span phân tán hoàn chỉnh từ `intake → OCR → summarizer → debate → profile_mutator`.
4. **Terminal / Eval Report:** Mở `eval/results/eval_report.md` — chỉ vào **15/15 PASS (100%)** cho Answer-Leak Prevention, Prompt-Injection Resistance, và Persona Fidelity (chấm bằng code xác định, loại bỏ hoàn toàn nguy cơ reward-hacking của LLM-as-judge).

---

## 3:30–4:00 — Track Alignment & Closing

**Nói:**
> "eduagent directly answers the core criteria for Collaborative Partner:
> 1. Does the agent synthesize and mutate data? Yes — it maintains longitudinal student profiles, clusters systemic class weaknesses, and computes an Intervention Priority Index.
> 2. Is the input genuinely messy? Yes — real handwritten photos, cross-outs, low light, transcribed with self-consistency OCR validation.
>
> Built from scratch for this hackathon using Gemini on Vertex AI, Google ADK2, Firestore, Pub/Sub, and Cloud Run."

*(Kết thúc đúng 4:00).*

