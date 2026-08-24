# TODO — Kế hoạch triển khai (All Things Agentic Hackathon — Track: Collaborative Partner)

> **Mục tiêu tối thượng:** Đạt điểm tối đa Stage Two (Innovation 40%, Architecture 30%, Demo 30%) + trọn +0.4 Bonus Stage Three.
> **Cam kết:** Toàn bộ code viết MỚI trong Submission Period (3–31/8/2026), chuẩn ADK2 + Gemini 3.5 + Google Cloud Native.
> **Cách dùng file này:** làm tuần tự từ Phase 0 → Phase 8. Mỗi phase có **Definition of Done (DoD)** — không sang phase sau khi DoD chưa xanh. Task gắn 🔴 = bắt buộc (thiếu là mất điểm/rớt), 🟡 = ăn điểm cao, 🟢 = nice-to-have, cắt được nếu hết thời gian.

---

## 0. Nguyên tắc bất biến khi code (đọc lại trước mỗi phase)

- [ ] **Eligibility First:** Tuyệt đối không copy-paste code từ repo cũ (`CritqAI-main`). Viết mới từ architecture, prompt, data schema đến function node. Repo cũ chỉ là case study để học pattern và học lỗi đã gặp.
- [ ] **Deterministic-First (ADK2 Standard):** Bất kỳ logic nào không cần LLM reasoning (regex validator, heuristic scoring, rule engine, sanitize, ranking) → BẮT BUỘC là Python Function Node. LLM chỉ dùng khi thực sự cần suy luận/diễn đạt.
- [ ] **Validator Độc lập:** Validator chạy logic path riêng, zero-trust với Generator — không share context, không nằm chung LLM turn.
- [ ] **HITL & Least-Privilege:** Đúng 1 điểm Human-In-The-Loop tại hành động rủi ro cao nhất (gửi Teacher Digest). OAuth scope chỉ `gmail.compose`, chặn `send` ở tầng credential chứ không phải ở tầng prompt.
- [ ] **Data Mutation & Synthesis (Track Mandate):** Agent phải biến đổi dữ liệu (tổng hợp Cognitive Profile, phát hiện cụm lỗi cả lớp, thích ứng độ khó tranh biện), không chỉ đọc/lưu.
- [ ] **Failure-tolerant by default:** Mọi call ra ngoài (Gemini, Firestore, Pub/Sub, MCP) đều phải có timeout + retry + đường thoát khi lỗi. Không có happy-path-only code.
- [ ] **Mọi quyết định kiến trúc phải giải thích được trong 1 câu** — nếu không, ghi vào ADR để suy nghĩ lại.

---

## 1. Kiến trúc mục tiêu

```
[MESSY INPUT] (Ảnh chụp bài viết tay / Bản nháp lỗi chính tả / Text thô)
      │
      ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: PER-STUDENT ADAPTIVE SOCRATIC PIPELINE (ADK2 Graph Workflow)   │
│                                                                        │
│  [Intake]  (Function Node: nhận text; nếu là ảnh → nhánh OCR)          │
│      ├──► [Multimodal OCR] (Gemini 3.5 Flash Vision) ─┐ 🟡             │
│      └───────────── text thô ─────────────────────────┤                │
│                                                       ▼                │
│  [Sanitizer] (Function Node: chống Prompt Injection, strip delimiters) │
│             │                                                          │
│             ▼                                                          │
│  [Summarizer] (Agent Node, Flash: Claim / Premise / Fallacy / Evidence)│
│             │                                                          │
│             ▼                                                          │
│  [Memory-Informed Persona Selector] ◄─── ADK Memory Service (Firestore)│
│  (Đọc Cognitive Profile: điểm yếu dai dẳng, persona streak, lịch sử)   │
│             │                                                          │
│             ▼                                                          │
│  [Debate Loop (3 turns)] ◄───► [Challenge Validator (FUNCTION NODE)]   │
│  - Persona Anchoring mỗi turn    - Regex: chống Answer-Leak            │
│  - Escalation skill module       - Single-Question & Length guardrail  │
│  - Trích dẫn lỗi bài trước       - Interceptor chặn persona drift      │
│             │                                                          │
│             ▼                                                          │
│  [Cognitive Scorer & Profile Mutator] (Agent + Function Node)          │
│  (Chấm 4 trục rubric + tái cấu trúc weakness_taxonomy)                 │
│             │                                                          │
│             ▼                                                          │
│  [Ghi Firestore student_profiles]  ──►  [Publish `essay.evaluated`]    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Pub/Sub (at-least-once → cần idempotency)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 2: CLASS AGGREGATOR & TEACHER CO-PILOT (Collaborative Pattern)    │
│                                                                        │
│  [Cloud Run Subscriber]  ──(lỗi 3 lần)──►  [Dead Letter Topic]         │
│             │                                                          │
│             ▼                                                          │
│  [Class Cluster & Pattern Engine] (Deterministic Function Node)        │
│  - Quét student_profiles theo class_id                                 │
│  - Systemic Fallacy Clustering (cụm lỗi chung cả lớp)                  │
│  - Intervention Priority Index (thuật toán xếp hạng, KHÔNG dùng LLM)   │
│             │                                                          │
│             ▼                                                          │
│  [Teacher Digest Synthesizer] (Agent Node, Gemini 3.5 Pro)             │
│  (Chỉ diễn đạt kết quả đã tính sẵn thành báo cáo hành động + mini-lesson)│
│             │                                                          │
│             ├──────────────────┬──────────────────┬───────────────────┐│
│             ▼                  ▼                  ▼                   ▼│
│      [Gmail MCP]         [Sheets MCP]       [Web UI]         [Cloud   ]│
│    Compose Draft        Audit Append       Live Feed          Trace    │
│    🔴 GATE HITL         Log minh bạch      Realtime        Observability│
│    Giáo viên bấm Gửi                                                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 0 — Nền móng & khoá rủi ro sớm 🔴

> Mục tiêu: dựng hạ tầng và **xử lý trước 2 rủi ro có thể giết demo vào phút chót** (Gmail OAuth, code cũ lọt repo).

- [ ] **Cô lập repo mới khỏi code cũ (rủi ro eligibility):**
  - `git init` tại `CritiqAI_ver2`; thêm `CritqAI-main/` vào `.gitignore` NGAY dòng đầu tiên.
  - Sau commit đầu, chạy `git ls-files | grep -i critqai` để xác nhận **zero** file cũ lọt vào history.
- [ ] `.gitignore` chuẩn production: `.env`, `*service-account*.json`, `*credentials*`, `__pycache__/`, `.venv/`.
- [ ] Môi trường: Python 3.11+, ADK2, `google-genai`, `google-cloud-firestore`, `google-cloud-pubsub`, `google-cloud-trace`.
- [ ] GCP Project: bật Vertex AI/Gemini API, Firestore Native, Cloud Run API, Pub/Sub, Cloud Trace/Logging.
- [ ] Service Account + phân quyền least-privilege (chỉ role cần thiết, không dùng Owner).
- [ ] Firestore collections: `student_profiles`, `class_analytics`, `system_audit_logs`, `processed_events` (dùng cho idempotency).
- [ ] 🔴 **Verify Gmail MCP OAuth NGAY BÂY GIỜ, không để đến cuối:**
  - Tạo OAuth client, cấp đúng scope `gmail.compose`.
  - Test tạo được 1 draft thật trong hòm thư.
  - Test gọi `send` → xác nhận **bị từ chối ở tầng credential** (đây chính là bằng chứng least-privilege để quay video).
  - Nếu vướng OAuth verification cho app chưa verified → xử lý bằng test user, hoặc chốt phương án dự phòng (Sheets + Web UI làm kênh digest chính) ngay từ giờ.
- [ ] Skeleton graph ADK2 chạy end-to-end với mock data (mọi node là stub) → commit.

**DoD:** `git ls-files` sạch • Gmail draft tạo được thật, `send` bị chặn • skeleton graph chạy hết luồng không lỗi.

---

## PHASE 1 — Tầng 1 lõi (text-only, chạy được end-to-end) 🔴

> Nguyên tắc: **làm pipeline text chạy thông trước**, multimodal để phase sau. Đây là xương sống, không được trượt.

- [ ] **Intake + Sanitizer (Function Node):** validate input, strip delimiter nguy hiểm, chặn pattern prompt injection cơ bản (`ignore previous instructions`, system prompt override, delimiter injection). Ghi lại input gốc trước khi sanitize để audit.
- [ ] **Summarizer Agent (Gemini 3.5 Flash):** trích Claim chính, Premise, Fallacy nháp, Evidence Type → structured output (JSON schema, không free text).
- [ ] **Persona library (4 persona, prompt viết mới hoàn toàn):**
  - *Skeptic* — nghi ngờ bằng chứng, đòi nguồn.
  - *Devil's Advocate* — phản biện ngược chiều luận điểm.
  - *Nitpicker* — bắt bẻ lỗ hổng logic, bước nhảy suy luận.
  - *Expander* — kéo rộng phạm vi, buộc xét trường hợp biên.
- [ ] **Debate Loop (Agent Node, 3 turn leo thang):**
  - **Persona Anchoring:** tái khẳng định persona instruction ở **mỗi turn**, không chỉ system prompt đầu — triệt tiêu hiện tượng "tuột persona" thành trợ lý dễ dãi.
  - Escalation logic tách thành **skill module riêng**, không nhét chung 1 prompt khổng lồ.
- [ ] 🔴 **Challenge Validator (Function Node, ZERO LLM, độc lập 100%):**
  - Chống answer-leak (không được đưa đáp án/viết hộ).
  - Single Socratic question rule (đúng 1 câu hỏi gợi mở).
  - Length & reading-level guardrail phù hợp học sinh.
  - Khi fail → trả về lý do cụ thể, buộc Debate Agent regenerate (tối đa N lần rồi fallback an toàn).
- [ ] **Cognitive Scorer (Agent Node):** chấm 4 trục `logical_coherence`, `evidence_quality`, `counterargument_handling`, `scope_awareness`.
- [ ] **Profile Mutator (Function Node — Data Mutation):** cập nhật `weakness_taxonomy` (VD: *Hasty Generalization*, *Ad Hominem*, *Unsourced Claim*), `persona_streak`, `score_trend` — đây là phần "mutate data" mà track yêu cầu.
- [ ] Ghi Firestore `student_profiles/{id}` đúng schema.

**DoD:** submit 1 essay text → chạy hết 3 turn → Validator có ít nhất 1 lần chặn thật → Firestore ghi đúng document → đọc lại profile thấy weakness_taxonomy đã mutate.

---

## PHASE 2 — Long-Term Memory (điểm ăn của Track Collaborative Partner) 🔴

> Đây là câu trả lời trực tiếp cho *"remember context, become more helpful over time"*.

- [ ] Cấu hình **Firestore làm ADK Memory Service backend** (prefix `student:` cho memory xuyên session). Không dùng in-memory/SQLite cho bản demo.
- [ ] Phân định rõ **Session state** (trong 1 phiên tranh biện) vs **Memory** (xuyên nhiều bài luận/nhiều tuần) — viết vào ADR, đây là thứ giám khảo Architecture sẽ soi.
- [ ] **Memory-Informed Persona Selector:**
  - Đọc `essay_history` + `weakness_taxonomy` + `persona_streak` TRƯỚC khi chọn persona.
  - Không lặp persona đã dùng liên tiếp mà học sinh chưa tiến bộ.
  - Tiêm ngữ cảnh cụ thể vào debate: *"Bài luận tuần trước em thiếu nguồn dẫn — lần này hãy xem em bảo vệ luận điểm ra sao."*
- [ ] **Test tiến hoá (quan trọng cho video):** chạy 3 essay liên tiếp cùng `student_id`, chứng minh persona/độ khó/nội dung chất vấn **thay đổi theo lịch sử**, không lặp lại.
- [ ] **Seed script — 5 hồ sơ mẫu** phục vụ demo Tầng 2:
  - 1 em tiến bộ đều • 1 em kẹt streak 3 lần • 1 em điểm giảm dần • 1 em lâu chưa nộp • 2 em chung 1 lỗi ngụy biện (tạo cụm lỗi lớp).

**DoD:** chạy 3 lần cùng 1 học sinh cho ra 3 persona/góc chất vấn khác nhau có lý do truy vết được • seed data nằm trong Firestore thật.

---

## PHASE 3 — Tầng 2: Event-driven Class Aggregator & Teacher Co-Pilot 🔴

> Phần khác biệt lớn nhất so với dự án cũ. **Không được để phase này bị bóp thời gian.**

- [ ] **Pub/Sub event-driven:** Tầng 1 xong → publish `essay.evaluated` → Cloud Run subscriber trigger Class Aggregator.
- [ ] 🔴 **Idempotency:** Pub/Sub là at-least-once — cùng 1 event CHẮC CHẮN sẽ đến 2 lần. Dùng `event_id` ghi vào collection `processed_events`, gặp lại thì skip. Không có cái này, demo có thể gửi digest trùng ngay trên sóng.
- [ ] 🔴 **Dead Letter Topic:** subscriber fail 3 lần → đẩy sang DLQ thay vì retry vô hạn. Show DLQ trống trong video = bằng chứng hệ thống chạy sạch.
- [ ] **Class Cluster & Pattern Engine (Function Node, deterministic):**
  - Quét `student_profiles` theo `class_id`.
  - **Systemic Fallacy Clustering:** gom cụm lỗi chung cả lớp.
  - **Intervention Priority Index** — công thức có trọng số **hằng số ghi rõ trong code**, audit được:
    `Priority = w1·stuck_streak + w2·score_decline + w3·inactivity_days + w4·shared_fallacy_weight`
    (w1..w4 khai báo trong `config.py`, có comment giải thích vì sao chọn giá trị đó)
  - **LLM tuyệt đối không tham gia xếp hạng** — chỉ function node. Giáo viên phải hiểu được TẠI SAO em A xếp trên em B.
- [ ] **Teacher Digest Synthesizer (Gemini 3.5 Pro):** chỉ **diễn đạt** kết quả đã tính sẵn thành: danh sách cần kèm cặp, phân tích nguyên nhân gốc, gợi ý 1 mini-lesson 15 phút cho tiết tới.
- [ ] **Gmail MCP (compose-only):** tạo email draft trong hòm thư giáo viên. 🔴 **GATE HITL DUY NHẤT** — giáo viên bấm Gửi.
- [ ] **Sheets MCP (append-only):** audit log mỗi lần digest được tạo/gửi.
- [ ] **Web UI tối giản:** hiển thị live feed pipeline + digest chờ duyệt + nút Send. Không cần đẹp, cần chạy thật và quay được.

**DoD:** submit essay mới → Pub/Sub trigger tự động → digest sinh ra với ranking giải thích được → draft xuất hiện trong Gmail → bấm Send gửi thật → Sheets có dòng log • gửi lặp event không tạo digest trùng.

---

## PHASE 4 — Resilience & Observability (chốt 30% Architecture) 🔴

> Rules ghi rõ: *"design robust, failure-tolerant agentic systems"*. Đây là ranh giới giữa "script mong manh" và "production-minded".

- [ ] **Retry + exponential backoff** cho mọi call Gemini / Firestore / MCP; timeout rõ ràng, không để treo vô hạn.
- [ ] **Graceful degradation theo từng điểm gãy:**
  - Gemini timeout → retry, quá N lần thì lưu essay ở trạng thái `pending_retry`, không mất bài của học sinh.
  - OCR không đọc được ảnh → trả lỗi thân thiện, yêu cầu nhập text, KHÔNG đẩy rác vào pipeline.
  - Validator fail liên tục → fallback về câu hỏi Socratic an toàn có sẵn, không bao giờ trả answer-leak ra cho học sinh.
  - Gmail MCP lỗi → digest vẫn được lưu Firestore + hiện trên Web UI, không mất dữ liệu.
- [ ] **Structured logging (JSON)** với `trace_id` xuyên suốt 1 essay từ Intake → Digest.
- [ ] 🟡 **Cloud Trace:** instrument span cho từng node (Intake → Sanitizer → Summarizer → Persona → Debate ↔ Validator → Scorer → Pub/Sub → Aggregator). **Một trace span hoàn chỉnh là "proof of action" mạnh nhất trong cả video** — chi phí implement thấp, điểm thu về cao.
- [ ] Chaos test nhanh: cắt mạng giữa chừng / bơm event lỗi vào Pub/Sub → xác nhận hệ thống không chết, DLQ nhận đúng.

**DoD:** kill 1 dependency bất kỳ → hệ thống degrade có kiểm soát, không crash, không mất dữ liệu học sinh • Cloud Trace hiển thị 1 trace đầy đủ end-to-end.

---

## PHASE 5 — ADK Eval Suite (điểm cộng lớn cho Architectural Discipline) 🟡

- [ ] Viết `evalset` ~10 test case, ưu tiên 3 nhóm:
  - **Answer-Leak Prevention** — Validator phải chặn 100%, đây là chỉ số cốt lõi của triết lý *"dạy học sinh không phụ thuộc AI"*.
  - **Persona Fidelity** — agent giữ đúng persona qua cả 3 turn.
  - **Prompt Injection Resistance** — Sanitizer chặn được các mẫu tấn công.
- [ ] **Cảnh giác reward hacking:** viết custom metric deterministic, đừng chỉ dựa vào built-in metric chung chung (bài học từ workshop Self-Evolving Agent).
- [ ] Chạy eval tự động, xuất báo cáo JSON/Markdown, **commit kết quả vào repo** làm bằng chứng.
- [ ] Câu chốt để nói trong video: *"Chúng tôi có eval pipeline chạy trước mỗi lần deploy — answer-leak prevention đạt 100%."*

**DoD:** có file report thật trong repo với số liệu, không phải claim suông.

---

## PHASE 6 — Multimodal Ingestion (ăn điểm "messy data") 🟡

> Trả lời trực tiếp câu chấm điểm: *"Did the team ingest unusual, messy, or highly complex unstructured data streams?"*
> **Đây là task có deadline cứng — nếu Phase 0–5 trượt tiến độ, CẮT phase này không thương tiếc.** Pipeline text-only vẫn nộp được, Tầng 2 hỏng thì không.

- [ ] Nhánh OCR bằng **Gemini 3.5 Flash Vision**: ảnh chụp bài viết tay → text có cấu trúc.
- [ ] Xử lý dữ liệu lộn xộn: lỗi chính tả, gạch xoá, chữ xấu, bố cục không đều, ảnh nghiêng/thiếu sáng.
- [ ] Confidence check: OCR mờ/không chắc → đánh dấu đoạn nghi ngờ thay vì bịa nội dung.
- [ ] Chuẩn bị sẵn 2 ảnh mẫu cho video: 1 ảnh "đẹp vừa phải" (chắc chắn chạy được) + 1 ảnh thật sự lộn xộn (gây ấn tượng mạnh).

**DoD:** upload ảnh viết tay thật → ra text → chạy tiếp toàn bộ pipeline không cần can thiệp tay.

---

## PHASE 7 — Deploy, Bằng chứng GCP & Tài liệu 🔴

- [ ] Dockerfile multi-stage (tối ưu dung lượng + bảo mật, non-root user).
- [ ] Deploy lên **Cloud Run** (HTTPS endpoint thật, `.run.app` URL).
- [ ] Thu thập **bằng chứng GCP Native** (chụp + quay màn hình):
  - Cloud Run service status & metrics • Firestore live collections/documents
  - Pub/Sub topic + subscription metrics + DLQ • Vertex AI / Gemini API logs • Cloud Trace span
- [ ] **README.md chuẩn quốc tế:**
  - Spin-up instructions từng bước — viết như thể người lạ hoàn toàn phải tự chạy được từ đầu.
  - **Architecture Decision Records (ADR)** — bảng ma trận: quyết định / lý do / phương án đã loại. Đây là thứ trực tiếp ăn điểm *"We are evaluating your engineering decisions"*.
  - Kết quả ADK Eval Suite.
  - Sơ đồ luồng dữ liệu + mô hình bảo mật (OAuth scope, least-privilege SA).
- [ ] **Architecture Diagram** (Mermaid + export PNG/SVG) — không cần đẹp, cần RÕ.
- [ ] 🔴 Test spin-up lại từ máy sạch/incognito. Nếu repo private → share `testing@devpost.com` và `cloudhackathons@google.com`.
- [ ] 🔴 Quét lại toàn bộ git history: không có API key, không có service account json, không có file từ repo cũ.

**DoD:** người lạ đọc README tự deploy được • mọi bằng chứng GCP đã nằm trong thư mục assets.

---

## PHASE 8 — Video Demo, Submission & Bonus 🔴

> Video là thứ giám khảo xem nhiều nhất và chiếm phần lớn 30% Demo. Chỉ 4 phút đầu được chấm.

- [ ] **Kịch bản video ≤ 4:00:**
  - **0:00–0:30 — Vấn đề & Triết lý:** lớp học nông thôn quá tải, giáo viên không kèm nổi từng em. Triết lý: *"Using AI to teach students not to depend on AI."*
  - **0:30–1:45 — Proof of Action (Tầng 1):** live upload bài viết tay lộn xộn → Vision OCR → Socratic debate thật → **Validator chặn answer-leak hiện ngay trên log** → Firestore cập nhật live. Không cắt ghép đoạn này.
  - **1:45–2:45 — Memory & Tầng 2:** agent nhắc lại lỗi bài trước (bằng chứng "become more helpful over time") → Pub/Sub trigger chạy ngầm → Class Aggregator phát hiện cụm lỗi → Teacher Digest → email draft xuất hiện trong Gmail → **thử gửi bằng quyền của agent bị từ chối** (proof least-privilege) → giáo viên bấm Send.
  - **2:45–3:30 — Kiến trúc & GCP Proof:** Cloud Run, Firestore Console, Pub/Sub metrics + DLQ trống, **Cloud Trace span end-to-end**, kết quả ADK Eval.
  - **3:30–4:00 — Track Alignment:** nói thẳng đã trả lời trọn 2 câu hỏi cốt lõi: (a) agent **synthesize & mutate** data (weakness taxonomy, fallacy clustering, priority ranking) chứ không chỉ đọc; (b) input thật sự **messy** (ảnh viết tay, chữ xấu, lỗi chính tả). Nêu rõ: Gemini 3.5 Flash/Pro + Google ADK2 + Firestore + Cloud Run + Pub/Sub.
- [ ] Quay **unedited live execution** — tuyệt đối không mockup, không slideware. Chạy thử toàn bộ kịch bản ít nhất 2 lần trước khi quay thật.
- [ ] Upload YouTube/Vimeo **public**, tiếng Anh hoặc có phụ đề tiếng Anh.
- [ ] **Devpost submission:**
  - Mô tả: features/functionality, technologies used, other data sources, findings & learnings.
  - 🔴 **Mandatory Disclosure:** *"Kiến trúc lấy cảm hứng từ kinh nghiệm cá nhân của tác giả ở dự án CritiqAI (dự thi tại cuộc thi khác trước đây). Toàn bộ code trong submission này được viết mới hoàn toàn trong Submission Period của All Things Agentic Hackathon."*
  - 🔴 Track ghi đúng: **Collaborative Partner** (không dùng tên "Evolving Knowledge Engine").
  - Đính kèm: repo, video, hosted URL, architecture diagram.
- [ ] **Bonus Stage Three (+0.4đ):**
  - Technical blog (Medium/Dev.to) về kiến trúc ADK2 + Socratic Agent, ghi rõ làm cho hackathon này, public (+0.2đ).
  - Post X/LinkedIn kèm `#AllThingsAgenticHackathon` + link demo (+0.2đ).
- [ ] 🔴 **Nộp sớm ít nhất 1 ngày** trước 31/8 17:00 PT. Sau deadline: TUYỆT ĐỐI không sửa repo/video/link.

---

## 2. Ma trận tự kiểm tra điểm tối đa

| Tiêu chí | Trọng số | Bằng chứng cụ thể trong dự án | Phase | Đạt? |
|---|---|---|---|---|
| **Eligibility Stage One** | Pass/Fail | Gemini 3.5+, ADK2, Firestore+Cloud Run+Pub/Sub, 100% code mới, có disclosure | 0, 8 | [ ] |
| **Innovation & Utility** | **40%** | Giảm tải thật cho giáo viên (auto-triage cả lớp), học sinh rèn tư duy không chép văn mẫu, ingest ảnh viết tay lộn xộn, data mutation (weakness taxonomy + fallacy clustering) | 1,2,3,6 | [ ] |
| **Architectural Discipline** | **30%** | Deterministic-first, Session vs Memory tách bạch, Validator độc lập zero-trust, idempotency + DLQ + retry, least-privilege OAuth, ADK Eval suite, ADR trong README | 1,2,3,4,5,7 | [ ] |
| **Demo & Readiness** | **30%** | Video ≤4' unedited live, GCP console proof + Cloud Trace, README spin-up test từ máy sạch, architecture diagram | 4,7,8 | [ ] |
| **Stage Three Bonus** | **+0.4đ** | 1 technical blog (+0.2) + 1 social post có hashtag (+0.2) | 8 | [ ] |

---

## 3. Rủi ro & phương án dự phòng

| Rủi ro | Xác suất | Phương án |
|---|---|---|
| Gmail OAuth verification chặn app chưa verified | Trung bình | Đã test ở **Phase 0**. Fallback: Web UI + Sheets làm kênh digest chính, Gmail thành nice-to-have |
| Multimodal OCR ngốn thời gian, đe doạ Tầng 2 | Cao | Phase 6 đặt SAU Tầng 2 — cắt được mà không ảnh hưởng xương sống |
| Pub/Sub gửi event trùng ngay trong lúc quay demo | **Cao** (at-least-once) | Idempotency qua `processed_events` — Phase 3 |
| Debate Agent tuột persona giữa chừng (lỗi đã gặp ở bản cũ) | Trung bình | Persona anchoring mỗi turn + eval Persona Fidelity |
| Gemini quota/rate limit khi quay demo | Trung bình | Kiểm tra quota trước, chuẩn bị sẵn 1 lần chạy dự phòng, dùng Flash làm mặc định |
| Code cũ lọt vào git history → vi phạm eligibility | Thấp nhưng **chí mạng** | `.gitignore` + kiểm tra `git ls-files` ở Phase 0 và Phase 7 |

---

## 4. Việc đang theo dõi song song (không block tiến độ)

- [ ] Chờ phản hồi `cloudhackathons@google.com` về eligibility tái sử dụng ý tưởng CritiqAI → cập nhật `PROJECT_WIKI.md` mục 6 và điều chỉnh file này nếu cần.
- [ ] Cập nhật `PROJECT_WIKI.md` mục 12 mỗi khi có quyết định kiến trúc mới.
