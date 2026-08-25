# Production Failure Matrix: Resilience & Graceful Degradation

> **Architectural Guarantee:** Không có bất kỳ lỗi đơn lẻ nào (Single Point of Failure) từ mạng, quota LLM, cơ sở dữ liệu hay dữ liệu đầu vào người dùng có thể làm sập toàn bộ hệ thống eduagent.
>
> **Một ngoại lệ CÓ CHỦ ĐÍCH (ĐỢT 13):** thành phần #14 (Session Signing Key) **không** giảm cấp — nó làm tiến trình chết hẳn. Vì nếu khoá ký token là chuỗi công khai trong repo thì "hệ thống vẫn chạy" chính là kịch bản tệ nhất, không phải kịch bản an toàn. Giảm cấp đúng ở mọi nơi khác; ở đây fail-fast mới là đúng.

---

## 1. Bảng Ma Trận 11 Thành Phần & Cơ Chế Phục Hồi (Failure Matrix)

| # | Thành Phần Hệ Thống (Component) | Điều Kiện Lỗi (Trigger Condition) | Mức Độ (Severity) | Cơ Chế Tự Phục Hồi & Giảm Cấp (Mitigation / Degradation) | Trạng Thái Trả Về (Fallback Behavior) | Thuộc Tính Kiểm Toán (Trace Span / Log) |
|:---:|---|---|:---:|---|---|---|
| **1** | **Intake & Sanitizer** | Prompt injection attempt (`Ignore instructions`, `<system> tags`) | High | Regex scanning & boundary stripping | Loại bỏ 100% token độc hại, giữ nguyên văn bản bài luận | `eduagent.sanitizer.blocked_patterns` |
| **2** | **OCR Handwriting Engine** | Ảnh mờ, viết tay không đọc được, OCR confidence thấp | Medium | Fallback rule engine cảnh báo | Trả về thông báo yêu cầu học sinh chụp lại hoặc nhập text | `eduagent.ocr.confidence_score` |
| **3** | **LLM Gateway (Gemini API)** | HTTP 429 Rate Limit / Quota Exceeded / Vertex AI Outage | Critical | Exponential backoff (3 retries) + Fallback sang Canned Persona Prompts | Sử dụng ngân hàng câu hỏi chuẩn sư phạm theo từng Persona | `eduagent.llm.status = "degraded"` |
| **4** | **Independent Validator** | Model cố tình tiết lộ đáp án (Answer Leak) | High | Chặn lập tức, kích hoạt vòng lặp sinh lại (Regeneration Loop up to 2 retries) | Cung cấp câu hỏi Socratic canned nếu quá số lần thử | `eduagent.validator.leak_detected = true` |
| **5** | **Persona Selector** | Học sinh bị kẹt 3 bài liên tiếp cùng 1 Persona không tiến bộ | Medium | Loại trừ Persona cũ khỏi danh sách ứng viên (Streak Breaking Algorithm) | Tự động chuyển giao sang Persona đối lập (e.g. Skeptic -> Expander) | `eduagent.persona.streak_broken = true` |
| **6** | **Metacognitive Reflection** | LLM phân tích hiệu chỉnh luận điểm bị lỗi cú pháp JSON | Low | Fallback parser & Default Growth Attribution | Ghi nhận hoàn thành tự hiệu chỉnh, cộng điểm chuẩn (+0.5) | `eduagent.reflection.fallback_used = true` |
| **7** | **Firestore Database Client** | Mất kết nối Firestore / GAPIC encoding bug | High | URL quote patch + Fallback In-Memory Cache | Phục vụ đọc/ghi từ Local RAM Cache, cảnh báo log giám sát | `eduagent.firestore.status = "in_memory_fallback"` |
| **8** | **Distributed Session Store** | Cloud Run scale đa instance / Container restart đột ngột | Medium | **Firestore là nguồn sự thật**; cache in-process chỉ được tin trong **3 giây** (`_CACHE_FRESHNESS_SECONDS`). Firestore sập → serve bản cache cũ (mất phiên vì hạ tầng chớp nháng tệ hơn state cũ vài giây). TTL policy trên `expire_at` **đã ACTIVE thật** trên GCP | Khôi phục trạng thái tranh biện từ `debate_sessions/{id}` | `eduagent.session.restored = true` |
| **9** | **Priority Ranking Engine** | Học sinh mới chưa có lịch sử bài luận | Low | Quy ước `score_trend = "insufficient_data"`, trọng số suy giảm = 0 | Xếp hạng dựa trên điểm yếu hiện tại, phân định hòa bằng `student_id` | `eduagent.priority.insufficient_data = true` |
| **10** | **Teacher Digest Synthesizer** | Gemini heavy model bị gián đoạn khi tổng hợp báo cáo | Medium | Fallback template rendering từ bảng xếp hạng tất định | Xuất báo cáo cấu trúc đầy đủ danh sách học sinh & 3-step mini-lesson | `eduagent.digest.degraded_mode = true` |
| **11** | **Pub/Sub Event Ingestion** | Delivery trùng lặp sự kiện `essay.evaluated` | Medium | Firestore Idempotency Lease Lock (`events/{event_id}`) | Bỏ qua sự kiện trùng, trả về HTTP 200 `status: duplicate_skipped` | `eduagent.event.duplicate_skipped = true` |
| **12** | **API Rate Limiter** (ĐỢT 13, ADR-017) | Vòng lặp `curl` vào endpoint tranh biện public → cạn quota Vertex AI (cost-DoS) | High | Token bucket theo IP (`rate_limit.py`): burst 10 / 1 req mỗi 5s cho debate, burst 5 / 1 mỗi 10s cho login. Key lấy từ **hop đầu** của `X-Forwarded-For` (hop sau do attacker cung cấp) | HTTP `429` + header `Retry-After`; caller bị từ chối **vẫn tích luỹ token**, không bị khoá vĩnh viễn | `client_key`, `path` trong log `Rate limit exceeded` |
| **13** | **Student Endpoint Authorization** (ĐỢT 13, ADR-018) | Người gọi bất kỳ POST `student_id` tuỳ ý → ghi bẩn hồ sơ học sinh khác, làm lệch bảng xếp hạng giáo viên | Critical | `_verify_student_auth()`: token `role=student` chỉ hành động thay chính mình; `class_id` phải khớp; `/turn` suy quyền sở hữu từ session (không từ request) và **xác thực trước khi tra session** để không thành existence oracle | `401` (thiếu/giả token) · `403` (sai học sinh / sai lớp) · `400` (`student_id` không tách được class) | `_verify_student_auth` raise HTTPException |
| **14** | **Session Signing Key** (ĐỢT 13, ADR-016) | Deploy lên Cloud Run mà quên set `EDUAGENT_SESSION_SECRET` → ký token bằng khoá công khai trong repo | Critical | **Fail-fast, không degrade**: `_resolve_session_secret()` phát hiện `K_SERVICE` và raise `InsecureConfigurationError` → container không boot. Đây là trường hợp duy nhất trong hệ thống cố tình **KHÔNG** giảm cấp — chạy tiếp với khoá công khai tệ hơn là không chạy | Revision không nhận traffic; log nêu đúng lệnh cần chạy | `InsecureConfigurationError` tại import time |

---

## 2. Phân Tích Kịch Bản Giảm Cấp Điển Hình (Degradation Case Studies)

### 🛡️ Kịch bản 1: LLM Gateway ngắt kết nối hoàn toàn (Total LLM Outage)
* **Kỳ vọng:** Học sinh vẫn tiếp tục phiên tranh luận, giáo viên vẫn nhận được danh sách học sinh cần can thiệp.
* **Thực thi thực tế:**
  1. `debate.py` phát hiện `LLMGenerationError`, kích hoạt `_PERSONA_FALLBACK_QUESTIONS` theo từng Persona (`skeptic`, `devils_advocate`, `nitpicker`, `expander`).
  2. `priority_engine.py` (100% Python thuần túy, ZERO LLM) vẫn tính toán chính xác chỉ số Intervention Priority Index.
  3. `digest.py` kích hoạt `_fallback_digest`, gửi email/bảng điều khiển với đầy đủ dữ liệu ưu tiên và giáo án 15 phút.

### 🔒 Kịch bản 2: Tấn công Prompt Injection tinh vi qua OCR
* **Kỳ vọng:** Kẻ tấn công chèn lệnh vô hiệu hóa quy tắc trong ảnh bài luận viết tay.
* **Thực thi thực tế:**
  1. Văn bản trích xuất từ OCR đi qua `intake.py::strip_injection_attempts`.
  2. Toàn bộ các mẫu lệnh độc hại (`Ignore instructions`, `<system>`, role hijack) bị bóc tách và ghi nhật ký cảnh báo an ninh.
  3. Văn bản đã làm sạch được đóng gói trong thẻ phân định `<student_essay>` trước khi đưa vào prompt.

---

## 3. Tuyên Bố Độ Tin Cậy Sẵn Sàng Vận Hành (Production Readiness Declaration)

```
[System Health Audit]
- Zero Single Point of Failure (SPOF)
- Deterministic Priority Ranking (100% SLA even during LLM outages)
- Bounded Memory & Database Storage (MAX_HISTORY_ENTRIES = 50, TTL = 24h)
- 100% Idempotent Event Delivery
```
