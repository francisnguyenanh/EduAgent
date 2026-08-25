# eduagent — Tài liệu Toàn diện cho NotebookLM
> Tổng hợp kiến trúc, triết lý thiết kế, kết quả thực nghiệm và kỹ thuật của dự án **eduagent**
> Dùng để tạo slide trình bày trong video demo hackathon và nộp bài.

---

## PHẦN 1: BỐI CẢNH & VẤN ĐỀ CỐT LÕI

### 1.1 Vấn đề thực tế (BYOF — Bring Your Own Friction)

**Thực trạng giáo dục:**
- Lớp học quá đông (40+ học sinh / giáo viên).
- Giáo viên không có thời gian phản hồi sâu sắc, cá nhân hóa cho từng học sinh.
- Các công cụ AI hiện tại (ChatGPT, Gemini trần...) đang làm hỏng học sinh bằng cách **đưa thẳng đáp án (Answer Machine)** → học sinh copy-paste thay vì tự suy nghĩ.

**Hệ quả nguy hiểm:**
- Học sinh học cách "nhờ AI làm bài hộ" chứ không học cách "lập luận".
- Kỹ năng tư duy độc lập, phân tích logic bị thui chột.
- Giáo viên hoàn toàn mất khả năng theo dõi học sinh nào đang thực sự "kẹt" tư duy.

### 1.2 Triết lý cốt lõi của dự án

> **"Using AI to teach students how NOT to depend on AI."**

Đây là nguyên lý sư phạm Socratic kiểu mới:
- Agent **KHÔNG bao giờ** đưa đáp án, **KHÔNG bao giờ** viết lại bài giúp học sinh.
- Agent đóng vai trò đối tác tranh biện (Collaborative Partner) đưa ra câu hỏi chất vấn để buộc học sinh tự suy nghĩ và sửa lỗi.
- Mỗi câu hỏi đều nhắm vào đúng lỗ hổng lập luận hiện tại của học sinh dựa trên trí nhớ dài hạn.

### 1.3 Tên dự án & Hackathon

| Thông tin | Chi tiết |
|-----------|----------|
| **Tên dự án** | eduagent — Collaborative Partner Socratic Mentor |
| **Hackathon** | All Things Agentic Hackathon (Google Cloud) |
| **Track** | Collaborative Partner |
| **Submission Period** | 3/8/2026 – 31/8/2026 |
| **Live Demo** | https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/ |
| **Demo Passcode** | `eduagent2026` |

---

## PHẦN 2: KIẾN TRÚC HỆ THỐNG — 2 TẦNG EVENT-DRIVEN

### 2.1 Tổng quan kiến trúc

Hệ thống gồm **2 tầng hoàn toàn tách biệt**, giao tiếp phi đồng bộ qua Pub/Sub:

```
TẦNG 1: Per-Student Adaptive Socratic Pipeline
→ Xử lý cá nhân hóa từng học sinh khi nộp bài luận (Text / Ảnh chụp viết tay).
→ Triển khai dưới dạng ADK2 Graph Workflow tự động hóa.

TẦNG 2: Class Aggregator & Teacher Co-Pilot
→ Tổng hợp dữ liệu cả lớp, xếp hạng ưu tiên can thiệp của giáo viên.
→ Tự động sinh giáo án mini-lesson 15 phút, xuất log và tạo Gmail Draft.
```

**Luồng dữ liệu tóm gọn:**
> Học sinh nộp bài (Text/Ảnh chụp) $\rightarrow$ OCR trích xuất verbatim $\rightarrow$ Sanitize chống injection $\rightarrow$ Summarize lỗi $\rightarrow$ Chọn Persona thích ứng $\rightarrow$ Tranh biện Socratic 3 lượt $\rightarrow$ Chấm điểm 4 trục $\rightarrow$ Mutate lưu Firestore $\rightarrow$ Pub/Sub event $\rightarrow$ Cloud Run Aggregator $\rightarrow$ Tính Priority Index $\rightarrow$ Gmail Draft (HITL gate) & Google Sheets Audit log.

### 2.2 Tầng 1 — Chi tiết từng node

```
[Essay Input] → intake → [OCR nếu là ảnh] → sanitizer → summarizer
              → persona_selector → debate_loop ↔ challenge_validator
              → cognitive_scorer → profile_mutator → [Firestore]
                                                         ↓
                                                [Pub/Sub event]
```

| Node | Loại | Chức năng |
|------|------|-----------|
| **intake** | FunctionNode (deterministic) | Nhận input, phát hiện loại (text/image/gdoc), định tuyến |
| **multimodal_ocr** | FunctionNode (Gemini Vision) | OCR bài viết tay thật, kiểm tra self-consistency 2-pass |
| **sanitizer** | FunctionNode (regex) | Chống prompt injection, áp giới hạn kích thước đầu vào |
| **summarizer** | AgentNode (Gemini Flash) | Trích xuất luận điểm chính và danh mục lỗi ngụy biện |
| **persona_selector** | FunctionNode (deterministic) | Chọn persona tranh biện dựa trên lịch sử điểm số và lỗi mới |
| **debate_loop** | AgentNode (Gemini Flash) | 3 lượt chất vấn Socratic với persona anchoring cứng |
| **challenge_validator** | FunctionNode (ZERO LLM) | Kiểm duyệt đầu ra: chặn answer leak, đa câu hỏi, quá dài |
| **cognitive_scorer** | AgentNode (Gemini Flash) | Chấm điểm 4 trục nhận thức argumentative |
| **profile_mutator** | FunctionNode (Firestore) | Ghi nhận đột biến hồ sơ tiến độ dài hạn của học sinh |

#### 4 Persona Tranh Biện (Socratic Personas)

- **The Skeptic (Nghi ngờ):** Kích hoạt khi thiếu bằng chứng thực tế. Luôn hỏi: *"Lấy số liệu từ nguồn nào?"*.
- **The Devil's Advocate (Phản biện):** Kích hoạt khi học sinh thiên kiến 1 chiều. Hỏi về góc nhìn đối lập.
- **The Nitpicker (Bắt bẻ):** Kích hoạt khi lỗi logic, nhảy vọt kết luận (non sequitur).
- **The Expander (Mở rộng):** Kích hoạt khi khái quát hóa vội vã (hasty generalization).

#### Cognitive Radar Chart — 4 trục đánh giá nhận thức

Hệ thống đánh giá sự tiến bộ của học sinh trên biểu đồ mạng nhện SVG 4 chiều:
1. **Logical Coherence (Mạch lạc logic):** Đo khả năng xây dựng các bước kết luận chặt chẽ.
2. **Evidence Quality (Dẫn chứng thực tế):** Đo mức độ sử dụng số liệu, nghiên cứu khoa học thay vì ví dụ cá nhân.
3. **Counterargument Handling (Đối phó phản biện):** Đo khả năng giải quyết các luận điểm đối lập.
4. **Scope Awareness (Nhận thức phạm vi):** Đo tính nuance, tránh overgeneralization.

---

## PHẦN 3: BẰNG CHỨNG SƯ PHẠM ĐỘT PHÁ (PEDAGOGICAL EVIDENCE)

### 3.1 Thực nghiệm Memory A/B (A/B Testing Proof)

Chứng minh bằng thực nghiệm định lượng trên chuỗi 3 bài luận liên tiếp của học sinh "Bình" mắc lỗi lập luận lặp lại:

| Chỉ số So Sánh | Nhánh A: Stateless Baseline (Không Trí Nhớ) | Nhánh B: eduagent (Trí Nhớ Dài Hạn) |
|---|---|---|
| **Chuỗi Persona Can Thiệp** | `skeptic → skeptic → nitpicker` (Lặp bế tắc) | `skeptic → expander → nitpicker` (Luân chuyển thích ứng) |
| **Can thiệp lặp bế tắc** | **1 lần** (Hỏi cùng góc nhìn gây nản lòng) | **0 lần** (Thích ứng 100%) |
| **Tiêm ngữ cảnh lỗi cũ** | **0/3 bài** (Mù lịch sử) | **2/3 bài** (Injected: *"Bài trước em đã gặp lỗi này..."*) |
| **Xếp hạng Ưu tiên Giáo viên** | **0.0** (Không tích lũy) | **1.5** (Tính toán chính xác lỗi stuck_streak) |

### 3.2 Đánh Giá Cải Thiện Đầu Ra (Learning-Outcome Delta Evaluation)

Sự chuyển biến nhận thức thông qua vòng lặp **Metacognitive Self-Correction Loop** (Turn 3 $\rightarrow$ Rewrite Thesis) được lượng hóa thực tế trên 8 kịch bản lập luận phổ biến:

* **Tỷ lệ cải thiện mục tiêu (Target Pass Rate):** **100% (8/8 kịch bản đánh giá)** cho thấy điểm cải thiện trên trục nhận thức bị chẩn đoán (không phải 8 học sinh thật riêng biệt — xem `docs/learning_outcome_eval.md` mục Methodology).
* **Mức tăng điểm trung bình trên trục bị lỗi ($\Delta_{\text{targeted}}$):** **+5.62 / 10 điểm** (Ngưỡng kỳ vọng $> +3.0$).
* **Mức tăng điểm trung bình toàn diện ($\Delta_{\text{overall}}$):** **+3.38 / 10 điểm** (Ngưỡng kỳ vọng $> +2.0$).
* **Ví dụ chuyển biến (Evidence Quality):**
  - *Trước:* *"Xe điện hoàn toàn sạch và không gây chút ô nhiễm nào."* (2/10 điểm - Lập luận cảm tính).
  - *Sau:* *"Mặc dù xe điện không phát thải trực tiếp, nghiên cứu cho thấy lượng giảm carbon ròng đạt 40-60% tùy thuộc vào nguồn điện lưới là tái tạo hay hóa thạch."* (8/10 điểm - Đã qualified và có số liệu).

---

## PHẦN 4: AN NINH & BẢO MẬT DỮ LIỆU (PRIVACY BY DESIGN)

### 4.1 Vòng Đời Dữ Liệu Học Sinh (Student Data Lifecycle)

1. **Ingestion (Thu nhận):** Văn bản / ảnh chụp viết tay tạm thời xử lý trong bộ nhớ RAM Cloud Run.
2. **In-Transit Processing:** Truyền tải mã hóa qua hạ tầng TLS quản lý bởi Google Cloud, không lưu trữ ảnh gốc trên đĩa.
3. **Session State (Tạm thời):** Tranh biện 1-3 lượt lưu tại Firestore với TTL 24h rồi tự động xóa vĩnh viễn.
4. **Persistent Memory Profile:** Ghi nhận lỗi ngụy biện lũy kế và điểm số (Capped tối đa 50 bài luận gần nhất).
5. **Class Analytics:** Báo cáo Digest lớp học lưu giữ 90 ngày (1 học kỳ) rồi lưu trữ/xóa bỏ.

### 4.2 STRIDE Threat Modeling

- **Spoofing (Giả mạo):** Định danh bằng HMAC-signed Scoped Access Token mang `class_id` và `role`.
- **Tampering (Sửa đổi):** Logic chấm điểm và priority hoàn toàn chạy phía Server, không tin cậy client.
- **Repudiation (Chối bỏ):** Ghi nhật ký event Pub/Sub với ID và Timestamp ISO UTC không thể thay đổi.
- **Information Disclosure (Rò rỉ):** Cấm truy cập chéo (IDOR Prevention): App layer từ chối nếu `token.class_id != target.class_id`.
- **Denial of Service (DoS):** Giới hạn cứng 3 lượt tranh luận (Hard Cap) và rate limiting input size.
- **Elevation of Privilege (Leo thang):** Role-based access control (RBAC) nghiêm ngặt (`role == "teacher"` để vào dashboard).

### 4.3 Privacy & Regulatory Considerations (Cân nhắc Bảo mật & Pháp lý)

- **Không chia sẻ dữ liệu huấn luyện:** Sử dụng Google Vertex AI Enterprise API với cấu hình **Zero Data Retention** cho mục đích train model nền tảng.
- **Không quảng cáo:** Không thu thập dữ liệu hành vi, 100% dữ liệu dùng cho mục đích giáo dục.
- **Lưu ý minh bạch:** Đây là các cân nhắc thiết kế theo hướng privacy-by-design, không phải chứng nhận pháp lý tuân thủ FERPA/COPPA — dự án prototype này chưa qua rà soát pháp lý/compliance chính thức.

---

## PHẦN 5: TÍNH NĂNG VẬN HÀNH ĐẶC SẮC (PRODUCTION FEATURES)

### 5.1 OCR Self-Consistency Cross-Check (Phát Hiện Hallucination)
- **Vấn đề:** Gemini Vision đôi khi bịa ra văn bản từ ảnh mờ/tối nhưng vẫn tự tin báo `confidence: "high"`.
- **Giải pháp:** Chạy OCR 2 lần độc lập. So sánh khoảng cách văn bản (difflib ratio $< 0.75$). Nếu bất nhất, hạ confidence xuống `low`, chuyển bài luận vào hàng đợi giáo viên phê duyệt (`pending_essays`), không ghi điểm sai vào profile.

### 5.2 Giáo Án 15 Phút Tự Động (Actionable Mini-Lesson Plan)
- Khi phát hiện lỗi lập luận hệ thống chung của cả lớp ($\ge 3$ học sinh cùng mắc), Class Aggregator tự động tạo cấu trúc:
  - Tên chủ đề dạy lại.
  - Mục tiêu sư phạm rõ ràng.
  - Hoạt động 3 bước chi tiết trên lớp.
  - 1 Ví dụ ngụy biện + 1 Phản ví dụ mẫu mực để giáo viên dissect trực tiếp trên bảng.

### 5.3 Gmail Human-In-The-Loop (HITL) Gate
- Bản thảo email báo cáo gửi phụ huynh được soạn tự động và đẩy vào thư mục **Drafts** của Gmail. 
- Giáo viên là người trực tiếp bấm nút "Gửi" cuối cùng. Bảo vệ bằng kiểm thử AST (`test_gmail_mcp_never_sends.py`) chặn mọi lời gọi `.send()` trong module tích hợp Gmail (`gmail_mcp.py`).

---

## PHẦN 6: 4-LAYER DETERMINISTIC ADK EVAL SUITE (50/50 PASS)

Không dùng mô hình LLM-as-judge (tránh rủi ro Reward Hacking). Kiểm thử bằng các hàm logic tất định và string signature đối chiếu với code sản xuất.

**Kết quả chạy tự động trước deploy (`scripts/run_eval_suite.py --strict`):**

| Tầng Kiểm Thử (Evaluation Layer) | Số Test Case Đạt | Tổng Số Ca | Tỷ Lệ Đạt (Pass Rate) |
|---|:---:|:---:|:---:|
| **Layer 1: Safety & Security** (Answer leak, Prompt injection, IDOR Isolation) | 15 | 15 | **100%** |
| **Layer 2: Behavioral Discipline** (Persona fidelity, Single-Q constraint, Length limits, Escalation) | 15 | 15 | **100%** |
| **Layer 3: Long-Term Memory** (Streak breaking, Trend slope, Context injection) | 10 | 10 | **100%** |
| **Layer 4: Learning Outcomes** (Metacognitive Delta $\ge 4.0$, Breakthrough accumulation) | 10 | 10 | **100%** |
| **TỔNG CỘNG** | **50** | **50** | **100% PASS** |

---

## PHẦN 7: ARCHITECTURE DECISION RECORDS (ADRs)

Hệ thống tuân thủ 16 Quyết định Kiến trúc ghi nhận trực tiếp tại codebase:

* **ADR-001 — Gmail HITL Gate:** Chặn cứng `.send()` bằng kiểm thử cấu trúc AST.
* **ADR-004 — Bilingual Expression Layer:** Lưu danh mục ngụy biện ở dạng tiếng Anh để persona selection không bị lỗi khớp chuỗi.
* **ADR-006 — Eval không dùng LLM-as-judge:** Triệt tiêu rủi ro reward-hacking.
* **ADR-007 — OCR Self-Consistency Cross-Check:** Transcribe 2 lần, so sánh bằng difflib để phát hiện ảnh mờ.
* **ADR-011 — Endpoint /health-check:** Thay thế `/healthz` tránh Knative intercept.
* **ADR-013 — HMAC-signed Scoped Token:** Giảm thiểu lỗ hổng IDOR xuyên lớp qua kiểm tra phân quyền phía server.
* **ADR-014 — Pub/Sub OIDC Verification:** Xác thực token OIDC tại App Layer của Cloud Run.
* **ADR-015 — Distributed Session via Firestore TTL:** Khắc phục container restart, lưu session tranh biện tập trung với TTL 24h.
* **ADR-016 — 4-Layer Deterministic ADK Eval Suite:** Chuẩn hóa 50 test case đo lường mọi khía cạnh an toàn và hành vi của agent.

---

## PHẦN 8: GCP PRODUCTION EVIDENCE & OBSERVABILITY

- **Cloud Run Deployment:** Healthy live service chạy tại region `asia-southeast1`.
- **W3C Trace Context Propagation:** Gắn Trace ID OpenTelemetry xuyên suốt từ intake đến class aggregator.
- **Span Tree Structure (illustrative hierarchy — see `docs/trace_evidence.md` for the real captured trace with actual measured durations, not the numbers below):**
  - `eduagent.node.intake`
  - `eduagent.node.sanitizer`
  - `eduagent.node.summarizer`
  - `eduagent.node.persona_selector`
  - `eduagent.node.debate_loop (3 turns)`
  - `eduagent.node.scorer`
  - `eduagent.node.class_aggregator`
- **Structured Cloud Logging:** Logs Cloud Run tự động mang trường `logging.googleapis.com/trace` giúp truy vết tức thời.

---

## PHẦN 9: RANH GIỚI NGUYÊN BẢN CỦA DỰ ÁN (ORIGINALITY BOUNDARY)

Để đảm bảo tính trung thực đối với ban giám khảo hackathon:
- **Nguyên văn đóng góp mới:**
  > *"Sự đóng góp mới của eduagent KHÔNG chỉ là một chatbot tranh luận Socratic. Điểm đột phá nằm ở **Kiến trúc Tác nhân 2 tầng Event-Driven** kết hợp Trí nhớ thích ứng dài hạn của Học sinh và Bảng điều khiển Sư phạm tất định của Giáo viên, cùng Vòng lặp tự hiệu chỉnh Metacognitive giúp đo lường bước nhảy nhận thức."*
- **Sẵn sàng mã nguồn:** 100% mã nguồn mở bản quyền MIT/Apache, không phụ thuộc thư viện đóng độc quyền.

---

## PHẦN 10: TÓM TẮT CHO 10 SLIDES TRÌNH BÀY (PRESENTATION DECK SUMMARY)

### Slide 1: The Problem — Trợ lý AI đang làm hại tư duy
- Gemini trần hoạt động như một "máy đưa đáp án" (Answer Machine).
- Học sinh copy-paste thay vì học lập luận; giáo viên không có thời gian theo dõi sâu.

### Slide 2: The Vision — eduagent: Collaborative Thinking Partner
- *"Using AI to teach students how NOT to depend on AI."*
- Agent không làm hộ bài, chỉ chất vấn Socratic theo các persona chuyên môn sâu.

### Slide 3: 2-Tier Event-Driven Architecture
- Tầng 1: Per-Student Adaptive Pipeline (ADK2 Workflow).
- Tầng 2: Class Aggregator & Teacher Co-Pilot (Cloud Run + Pub/Sub).

### Slide 4: Adaptive Socratic Pipeline (Tier 1)
- 9-node workflow: Ingest (Text/Ảnh chụp/GDoc) $\rightarrow$ OCR 2-pass $\rightarrow$ Sanitize $\rightarrow$ Summarize $\rightarrow$ Debate / Validate $\rightarrow$ Score $\rightarrow$ Mutate.

### Slide 5: Long-Term Memory & Adaptation Proof
- Thực nghiệm Memory A/B: Tự động xoay chuyển persona để tránh kẹt, tiêm ngữ cảnh lỗi cũ của học sinh, không lặp câu hỏi vô ích.

### Slide 6: Metacognitive Self-Correction Loop & Delta Scoring
- Đo lường thực chất bước nhảy nhận thức: $\Delta = \text{Score}_{\text{after}} - \text{Score}_{\text{before}}$.
- Kết quả thực nghiệm: Mức tăng điểm trung bình đạt $+5.62/10$ trên trục bị lỗi.

### Slide 7: Tier 2: Teacher Co-Pilot Dashboard
- Bảng ưu tiên can thiệp Intervention Priority Index bằng thuật toán tất định.
- Tự động sinh kế hoạch bài giảng mini-lesson 15 phút cho cả lớp.

### Slide 8: Human-in-the-Loop & Security Guards
- Gmail Draft Creator (HITL Gate): Giáo viên kiểm duyệt thủ công trước khi gửi.
- HMAC-signed scoped tokens (IDOR Prevention) và AST-based code guard.

### Slide 9: 4-Layer Deterministic Eval Suite (50/50 PASS)
- 50 test case bao phủ toàn diện: An ninh, Hành vi Persona, Trí nhớ dài hạn, và Đầu ra học tập. 100% tất định, loại bỏ rủi ro LLM-as-judge.

### Slide 10: GCP Evidence & Live Demo
- Cloud Run live tại `asia-southeast1` $\rightarrow$ Concurrency 80, event-driven design cho phép Tầng 1 và Tầng 2 scale độc lập dưới tải submit đồng thời.
- Google Sheets audit log tự động ghi nhận khi học sinh hoàn thành.

---
*Tài liệu được cập nhật đồng bộ với mã nguồn và kết quả thực nghiệm mới nhất của dự án eduagent — All Things Agentic Hackathon 2026.*
