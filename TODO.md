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

## PHASE 0 — Nền móng & khoá rủi ro sớm 🔴 (ĐANG LÀM — code xong, chờ thao tác GCP/Gmail thật của bạn)

> Mục tiêu: dựng hạ tầng và **xử lý trước 2 rủi ro có thể giết demo vào phút chót** (Gmail OAuth, code cũ lọt repo).

- [x] **Cô lập repo mới khỏi code cũ (rủi ro eligibility):** ✅ ĐÃ LÀM + ĐÃ REVIEW
  - `git init` tại `CritiqAI_ver2`; `CritqAI-main/` nằm dòng đầu `.gitignore`.
  - Verify: `git diff --cached --name-only | grep -i critqai` → **0 kết quả** trước commit đầu tiên. PASS.
- [x] `.gitignore` chuẩn production: `.env`, `*service-account*.json`, `*credentials*`, `__pycache__/`, `.venv/`. ✅ ĐÃ LÀM
- [x] Môi trường: Python 3.14 sẵn có, đã verify cài đặt `google-adk==2.3.0`, `google-genai==2.9.0`, `google-cloud-firestore==2.28.0`, `pytest==8.3.3`. `requirements.txt` đã khai đủ (kèm `google-cloud-pubsub`, `google-cloud-trace` cho Phase 3–4, chưa cài — cài khi tới phase đó). ✅ ĐÃ LÀM
- [x] **GCP Project: bật Vertex AI/Gemini API, Firestore Native, Cloud Run API, Pub/Sub, Cloud Trace/Logging, Gmail API.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS
  - Project thật: `project-4fc36103-f4ca-49f6-883` (đã verify quyền truy cập qua `gcloud projects describe`).
  - Verify: `gcloud services list --enabled` → cả 6 API (`aiplatform`, `firestore`, `run`, `pubsub`, `cloudtrace`, `logging`) hiện đủ, + `gmail.googleapis.com` bật riêng cho MCP sau này.
- [x] **Service Account + phân quyền least-privilege.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS
  - Tạo SA riêng `eduagent-sa@project-4fc36103-f4ca-49f6-883.iam.gserviceaccount.com` — KHÔNG tái dùng SA có sẵn của project (project này đang có SA của các dự án khác: `docutranslate-vertex-sa`, `vti-nagoya-sa`...).
  - Gán đúng 5 role, không Owner/Editor: `datastore.user`, `pubsub.editor`, `aiplatform.user`, `cloudtrace.agent`, `logging.logWriter`. Verify bằng `gcloud projects get-iam-policy --filter=...` → khớp chính xác 5 role.
  - Key JSON tại `secrets/eduagent-sa-key.json` — **phát hiện và vá lỗ hổng**: tên file không khớp pattern cũ `*service-account*.json` trong `.gitignore`. Đã thêm `*-key.json` + `secrets/` vào `.gitignore`, verify bằng `git check-ignore -v` → bị ignore đúng, không lọt vào `git status`.
- [x] Firestore Native database thật đã tạo tại `asia-southeast1` (Singapore, theo lựa chọn của bạn). ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS
  - Verify bằng `scripts/verify_firestore.py`: ghi + đọc + xoá document thật trong cả 4 collection (`student_profiles`, `class_analytics`, `system_audit_logs`, `processed_events`) dùng chính SA least-privilege vừa tạo → **PASSED**.
- [x] Skeleton graph ADK2 chạy end-to-end với mock data (mọi node là stub) → commit. ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS
  - Xây bằng API thật `google.adk.workflow.{Workflow, FunctionNode, START}` (không phải mock tự chế) — khớp đúng ADK2 Graph Workflow trong wiki 7.5.3.
  - 8 stub node nối tuyến tính: `intake → sanitizer → summarizer → persona_selector → debate_loop → challenge_validator → cognitive_scorer → profile_mutator`, state thread qua `Context.state` (khớp wiki 7.5.6 — Context tách biệt `state` và `session`).
  - Chạy qua `InMemoryRunner(node=workflow).run_debug(...)` — verify bằng `python -m pytest tests/ -q` → **1 passed**, không cần `GOOGLE_API_KEY` (chưa gọi LLM ở giai đoạn stub, đúng deterministic-first).
  - Commit `69b49d3` — 14 file, không có file nào từ `CritqAI-main`.
- [x] **OAuth Consent Screen + Client ID tạo xong** (External, test user `eikitomobe@gmail.com`, Desktop app client `eduagent-gmail-mcp`). ✅ ĐÃ LÀM (bạn thao tác Console UI).
- [x] **Verify Gmail OAuth thật + PHÁT HIỆN & SỬA sai lầm kiến trúc quan trọng.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS (nhưng kết luận khác giả định ban đầu)
  - ⚠️ **ADR-001 — `gmail.compose` KHÔNG chặn `send()` ở tầng OAuth.** Test thật ngày 2026-08-24 với token chỉ xin scope `gmail.compose`: `drafts.create()` OK, và `messages.send()` **cũng thành công** (không bị 403). Đây là hành vi CHÍNH THỨC của Gmail API — scope `gmail.compose` theo tài liệu Google là *"create, read, update, delete drafts; send messages and drafts"*, tức nó VỐN có quyền gửi. Không tồn tại scope Gmail nào chỉ tạo draft mà chặn cứng send.
  - **Sự cố phát sinh khi test:** 2 email thật đã được gửi vào hòm thư của chính bạn (`eikitomobe@gmail.com`), nội dung vô hại ("Phase 0 verification draft... safe to delete"). Đã dọn dẹp draft rác bằng `scripts/cleanup_gmail_test_artifacts.py`; 2 email đã gửi thì không thu hồi được (harmless, tự gửi cho mình).
  - **Sửa lại thiết kế HITL gate (khác với PROJECT_WIKI.md mục 9.1 nguyên bản):** least-privilege của Teacher Digest Mailer phải enforce ở **tầng code**, không phải tầng OAuth:
    - Codebase KHÔNG BAO GIỜ được gọi `messages.send`/`drafts.send` trong luồng digest — đây là kỷ luật code + code review, viết 1 test/lint rule chặn việc này ở Phase 3.
    - "Gate" thật sự là: giáo viên tự mở Gmail của họ và bấm Send trên draft — hành động người thật ngoài mọi code path của hệ thống — không phải "về mặt kỹ thuật AI không gửi được".
    - Trong video/README: nói đúng sự thật này (agent's code path has no send call, not "OAuth technically blocks it") — nói sai sẽ bị soi ở Architectural Discipline nếu giám khảo test thử.
  - Script cuối cùng (`scripts/verify_gmail_compose_only.py`) đã sửa để chỉ test draft create/delete, không test send() thật nữa (tránh lặp lại side-effect gửi mail).

**DoD:** `git ls-files` sạch [PASS] • skeleton graph chạy hết luồng không lỗi [PASS] • GCP project/service account/Firestore thật tồn tại và verify được [PASS] • Gmail OAuth thật hoạt động, draft tạo/xoá được [PASS] • hiểu đúng giới hạn thật của scope và đã sửa thiết kế HITL tương ứng [PASS].

**→ Phase 0 HOÀN THÀNH 100%.** Bao gồm 1 phát hiện kiến trúc quan trọng (ADR-001) đã sửa trước khi nó lộ ra trong video demo hoặc bị giám khảo chất vấn. Chuyển sang **Phase 1**.

---

## PHASE 1 — Tầng 1 lõi (text-only, chạy được end-to-end) 🔴 (ĐANG LÀM — batch mode xong, cần thêm interactive multi-turn)

> ADR-002 (xem `src/eduagent/config.py`): `gemini-3.5-pro` không tồn tại trong project/region này (verify bằng `client.models.list()`). Dùng `gemini-3.5-flash` mặc định + `gemini-3.7-flash` (`heavy_model`) cho tác vụ cần reasoning sâu hơn — vẫn thoả yêu cầu "Gemini 3.5 trở lên". Toàn bộ LLM call đi qua Vertex AI bằng chính `eduagent-sa` đã tạo ở Phase 0 (không xin thêm API key riêng).

> Nguyên tắc: **làm pipeline text chạy thông trước**, multimodal để phase sau. Đây là xương sống, không được trượt.

- [x] **Intake + Sanitizer (Function Node).** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/nodes/intake.py`. Regex chặn injection (`ignore previous instructions`, override system prompt, thẻ `<system>`), giữ nguyên `raw_input` trước khi sanitize để audit. Bug thật tìm thấy qua unit test: pattern gốc chỉ khớp 1 tính từ trước "instructions" nên bỏ lọt `"ignore all previous instructions"` (2 tính từ) — đã sửa quantifier `{1,3}`.
- [x] **Summarizer Agent (Gemini 3.5 Flash).** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/nodes/summarizer.py`, structured JSON output thật qua Vertex AI (không free text). Verify bằng `scripts/demo_tier1_run.py`: với essay nguỵ biện thật, model trích đúng `hasty generalization`, `anecdotal evidence`, `appeal to popularity`.
- [x] **Persona library (4 persona, viết mới hoàn toàn).** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/skills/personas.py`. Mỗi persona có `anchor` text riêng để tái khẳng định mỗi turn (Skeptic/Devil's Advocate/Nitpicker/Expander), map với 1 trục rubric tương ứng.
- [x] **Debate Loop (Agent Node, leo thang, persona anchoring mỗi turn).** ✅ ĐÃ LÀM MỘT PHẦN — `src/eduagent/nodes/debate.py` + `src/eduagent/skills/debate_escalation.py` (escalation tách riêng module, đúng yêu cầu). Verify: Turn 1 sinh câu hỏi Socratic đúng persona, đúng 1 câu hỏi, không leak đáp án.
  - ⚠️ **Giới hạn đã phát hiện, cần làm tiếp:** graph hiện chạy 1 lượt (batch) — `node_input` của Workflow chỉ nhận essay ban đầu, chưa có đường dẫn để bơm câu trả lời thật của học sinh giữa các turn. Muốn tranh biện 3-turn tương tác thật (học sinh trả lời → agent leo thang dựa trên câu trả lời đó) cần dùng cơ chế **interrupt/resume** của ADK2 Workflow (`RequestInput`, đã thấy trong `google.adk.workflow`) để graph dừng chờ input thật sau mỗi turn — việc này cần làm cùng lúc với Web UI (Phase 3), ghi vào việc còn lại của Phase 1 thay vì giả lập vội.
- [x] 🔴 **Challenge Validator (Function Node, ZERO LLM, độc lập 100%).** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/nodes/validator.py`, không import `eduagent.llm` (verify bằng đọc code, không có LLM call nào). Test thật: chặn đúng answer-leak, chặn câu hỏi kép, chặn quá ngắn/quá dài. Dùng lại (không gọi chồng LLM) cả trong vòng regenerate của Debate Loop lẫn làm node cuối kiểm tra toàn bộ transcript.
- [x] **Cognitive Scorer (Agent Node).** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/nodes/scorer.py`. Verify: essay nguỵ biện thật bị chấm điểm thấp hợp lý (2/1/0/2 trên thang 10) ở cả 4 trục.
- [x] **Profile Mutator (Function Node — Data Mutation).** ✅ ĐÃ LÀM MỘT PHẦN — `src/eduagent/nodes/mutator.py` tính đúng delta (`persona_used`, `new_weaknesses`, `scores`, `validator_passed`) từ 1 essay. Đây mới là delta cho MỘT bài; hợp nhất `persona_streak`/`score_trend` xuyên nhiều bài (cần đọc lịch sử cũ trước khi mutate) dời sang **Phase 2** cùng với ghi Firestore thật — làm ở đây sẽ phải giả lập lịch sử giả, không có giá trị.
- [ ] ⏸️ Ghi Firestore `student_profiles/{id}` đúng schema thật (hiện `profile_delta` mới nằm trong `ctx.state`, chưa persist). — Dời sang Phase 2 vì cần thiết kế cùng lúc với read-modify-write hợp nhất lịch sử, tách làm 2 lần sẽ phải viết lại.

**Kiểm chứng thật đã chạy** (`scripts/demo_tier1_run.py`, essay ngụy biện mẫu qua Vertex AI thật): Summarizer → Persona Selector (chọn đúng Skeptic) → Debate Turn 1 (câu hỏi đúng persona, qua Validator) → Scorer (điểm thấp hợp lý) → Mutator (delta đúng cấu trúc). `pytest tests/ -q` → **10/10 pass** (1 test end-to-end thật qua LLM + 9 unit test thuần cho Sanitizer/Validator/PersonaSelector/Mutator).

**DoD:** submit 1 essay text → chạy hết pipeline không lỗi [PASS, nhưng mới 1 turn do giới hạn interrupt/resume nêu trên] • Validator có test case chặn thật [PASS] • Firestore ghi đúng document [CHƯA — dời Phase 2 có chủ đích].

**→ Phase 1 hoàn thành ~85%.** Lõi pipeline text-only chạy thật qua Gemini/Vertex AI, có unit test khoá hành vi deterministic. 2 việc còn lại (interactive multi-turn qua interrupt/resume, ghi Firestore thật) dời sang đúng chỗ (Phase 2/3) để không phải làm lại.

---

## PHASE 2 — Long-Term Memory (điểm ăn của Track Collaborative Partner) 🔴 HOÀN THÀNH

> Đây là câu trả lời trực tiếp cho *"remember context, become more helpful over time"*.

- [x] **Firestore làm ADK Memory Service backend.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/memory/firestore_memory.py`. Không dùng in-memory/SQLite. Read-modify-write qua **Firestore transaction** (`@firestore.transactional`), không phải get-rồi-set rời rạc — tránh 2 bài luận cùng học sinh ghi đè nhau khi Tầng 2 chạy đồng thời (Phase 3).
- [x] **Phân định Session state vs Memory — verify bằng test thật, không chỉ lý thuyết.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS
  - Xác nhận bằng thực nghiệm: `ctx.state` (ADK Session) reset mỗi `session_id` mới, nhưng document Firestore `student_profiles/{student_id}` sống xuyên qua 3 session riêng biệt trong `scripts/demo_tier1_run.py` — đúng khớp phân biệt Session/Memory ở wiki 7.5.6.
  - Cách truyền `student_id`/`name`/`class_id` vào graph: `session_service.create_session(state={...})` rồi `runner.run_async(new_message=...)` — ADK tự coerce `Content` essay text thành tham số `node_input: str` của node `intake`. Đây là cách dùng đúng API thật (khác `run_debug` chỉ hợp cho chat đơn giản, không hỗ trợ seed state).
- [x] **Memory-Informed Persona Selector.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `src/eduagent/nodes/persona_selector.py` gọi `firestore_memory.get_profile(student_id)` TRƯỚC khi chọn persona, lấy `persona_history` thật từ Firestore (không phải state giả). Verify: chạy 3 essay liên tiếp cùng 1 học sinh mới → persona đổi `skeptic → nitpicker → skeptic` (không lặp liên tiếp), đúng logic `choose_persona`.
  - ⚠️ Chưa làm: tiêm câu ngữ cảnh cụ thể kiểu *"bài luận tuần trước em thiếu nguồn dẫn..."* vào prompt Debate Loop — hiện Debate Loop chỉ nhận `persona_id`, chưa nhận `weakness_taxonomy` lịch sử. Ghi nợ, làm ở Phase 3 khi build Web UI/interactive vì lúc đó mới thật sự cần nói với học sinh giữa các turn.
- [x] **Test tiến hoá thật (không phải mock).** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `scripts/demo_tier1_run.py`: 3 essay khác nhau, cùng 1 `student_id` mới tạo, qua Vertex AI + Firestore thật. Kết quả quan sát được: persona đổi đúng logic, `avg_score` tính đúng (1.0 → 1.0 → 1.25), `persona_streak` reset đúng khi đổi persona.
- [x] **Seed script — 5 hồ sơ mẫu.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `scripts/seed_student_profiles.py`, ghi thật vào Firestore, idempotent (chạy lại ghi đè sạch, không nhân đôi):
  - `stu_improving` (Mai) — 3 essay, điểm tăng dần đều, persona đổi bình thường.
  - `stu_stuck` (Binh) — 4 essay, kẹt `skeptic` liên tiếp không cải thiện → `needs_attention=True` verify đúng khi chạy script.
  - `stu_declining` (Chi) — 3 essay, điểm giảm dần (8→6→3).
  - `stu_inactive` (Duc) — chỉ 1 essay cách đây 45 ngày.
  - `stu_common_fallacy` (Em) — 2 essay, cùng lỗi "hasty generalization" với `stu_stuck` — dữ liệu cho Systemic Fallacy Clustering ở Phase 3.
- [x] Unit test logic merge thuần (`tests/test_student_profile_memory.py`, 7 test, không cần Firestore thật) — khoá đúng luật `persona_streak`/`needs_attention`/dedupe `weakness_taxonomy`. ✅ PASS ngay lần đầu.

**DoD:** chạy 3 lần cùng 1 học sinh cho ra 3 persona/góc chất vấn khác nhau có lý do truy vết được [PASS] • seed data nằm trong Firestore thật [PASS, 5/5 profile, `stu_stuck` verify đúng flag] • Session state tách biệt Memory được chứng minh bằng thực nghiệm chứ không chỉ khai báo [PASS].

**→ Phase 2 hoàn thành 100%** (trừ 1 việc nợ nhỏ — tiêm ngữ cảnh lịch sử vào câu hỏi debate — dời đúng chỗ sang Phase 3 vì cần Web UI/interactive để có giá trị thật). `pytest tests/ -q` → **17/17 pass**.

---

## 💡 ĐỀ XUẤT CẢI TIẾN CÁC PHẦN ĐÃ LÀM XONG (Phase 0 – Phase 2) — ĐÃ THỰC HIỆN 100%

> **Mục đích:** Tối ưu hóa các module đã hoàn thành để tăng độ chịu lỗi (resilience), chống false-positive khi demo/chấm thi và chuẩn bị đầu vào tốt nhất cho Tầng 2 (Phase 3).

### 1. Challenge Validator & Intake (Tăng độ chịu lỗi & Đa ngôn ngữ) 🟡
- [x] **Bilingual Answer-Leak Regex (EN + VI).** ✅ ĐÃ LÀM + PASS — thêm 4 pattern tiếng Việt vào `_ANSWER_LEAK_PATTERNS` (`validator.py`). Test mới `test_validator_rejects_answer_leak_vietnamese` pass.
- [x] **Smart Question Count (tránh False-Positive khi quote).** ✅ ĐÃ LÀM + PASS — `_count_questions_outside_quotes()` bỏ qua `?` trong `"..."`/`'...'`. Test `test_validator_ignores_question_marks_inside_quotes` pass.
- [x] **Prompt Injection Pattern Expansion.** ✅ ĐÃ LÀM + PASS — thêm `</user>`, `</assistant>`, `what is your original/system prompt`, `print your system prompt` vào `intake.py`. **Bug thật tìm thấy khi viết test:** pattern "what is your ... prompt" ban đầu chỉ cho 1 tính từ ("original" HOẶC "system"), bỏ lọt "what is your **original system** prompt" (2 tính từ) — cùng loại lỗi quantifier như Phase 1, đã sửa `{0,2}`.

### 2. Debate Loop & Memory Integration (Gia tăng điểm Innovation/Demo) 🔴
- [x] **Inject Long-term Memory vào Debate Prompt.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `persona_selector.py` giờ lấy thêm `weakness_taxonomy_from_profile(profile)` và lưu vào `ctx.state["prior_weakness_taxonomy"]`; `debate_loop.py` tiêm câu ngữ cảnh cụ thể vào turn 1 (*"This student has previously struggled with: ..."*) — chỉ ở turn mở màn vì lặp lại mỗi turn sẽ thành nhiễu. Đây chính là bằng chứng "become more helpful over time" xuất hiện ngay trong prompt, không chỉ trong dữ liệu Firestore ẩn.
- [x] **Persona-Specific Fallback Questions.** ✅ ĐÃ LÀM + PASS — `_PERSONA_FALLBACK_QUESTIONS` (4 câu, 1 mỗi persona) thay `_SAFE_FALLBACK_QUESTION` tĩnh — giữ đúng chất persona ngay cả khi validator reject hết số lần retry.

### 3. Cognitive Scorer & Data Mutation (Tối ưu dữ liệu cho Phase 3) 🟡
- [x] **Scorer Rubric Rationale.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — schema `scorer.py` tách thành 2 object riêng `scores` (numeric, giữ nguyên contract cũ cho `_avg()`/Firestore/test) + `rationale` (string mỗi trục) — không phá hợp đồng dữ liệu hiện có. Verify qua Vertex AI thật, không lỗi parse.
- [x] **Deterministic `essay_id` từ Intake.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `intake.py` mint `essay_id` 1 lần bằng `ctx.state.setdefault`, `mutator.py` dùng lại thay vì tự sinh `uuid4()` mới (chỉ fallback sinh mới nếu node bị gọi trực tiếp không qua intake — trường hợp unit test).
- [x] **Score Trend Metric trong Profile.** ✅ ĐÃ LÀM + ĐÃ REVIEW + PASS — `_score_trend()` trong `student_profile.py`, tính slope trung bình 3 bài gần nhất, ngưỡng "phẳng" `TREND_FLAT_BAND=0.3` tránh nhiễu số lẻ. 4 unit test mới (`improving`/`declining`/`stagnant`/`insufficient_data`) pass, verify thêm bằng chạy thật (`scripts/demo_tier1_run.py` → `score_trend: "improving"` đúng với slope (0+0.75)/2=0.375 > 0.3).

### 4. LLM JSON Parsing Resilience (Tầng Foundation) 🟢
- [x] **Defensive Markdown Stripping.** ✅ ĐÃ LÀM + PASS — `_strip_markdown_fence()` trong `llm.py`, bóc \`\`\`json và \`\`\` trước `json.loads()`. 3 unit test mới pass.

**Kiểm chứng tổng:** `pytest tests/ -q` → **27/27 pass** (tăng từ 17, thêm 10 test mới cho các cải tiến). Bug thật thứ 3 (sau 2 bug quantifier ở Phase 1) tìm thấy và sửa ngay khi viết test cho pattern injection mới. `scripts/demo_tier1_run.py` chạy lại full 3-essay qua Vertex AI + Firestore thật, xác nhận `score_trend`, `essay_id` ổn định, và câu hỏi turn 1 giờ có ngữ cảnh lịch sử — không phá vỡ hành vi Phase 0-2 đã verify trước đó.

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
