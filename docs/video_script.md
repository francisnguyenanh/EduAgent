# Video Demo Script (≤ 4:00, unedited live execution)

> Giám khảo chỉ chấm **4 phút đầu**. Không mockup, không slideware — mọi thao tác phải chạy thật, live, không cắt ghép. Chạy thử toàn bộ kịch bản **ít nhất 2 lần** trước khi quay thật (để timing khớp và tránh lỗi bất ngờ giữa chừng).
>
> Chuẩn bị trước khi quay (làm 1 lần, không tính vào 4 phút):
> - Mở sẵn 3 tab trình duyệt: (1) terminal/VSCode, (2) Firestore Console (`student_profiles`), (3) Gmail của giáo viên (đã đăng nhập).
> - Chạy `python scripts/doctor.py` → xác nhận 6/6 PASS trước khi quay (tránh gián đoạn giữa chừng).
> - Chọn sẵn 1 ảnh viết tay thật từ `eval/test_images/` (khuyến nghị `messy_essay_videogames.jpg` — có gạch xoá, ấn tượng mạnh hơn `neat_essay_homework.jpg`).
> - `python scripts/seed_student_profiles.py` đã chạy trước đó (5 hồ sơ mẫu có sẵn trong Firestore) — KHÔNG chạy lại lúc quay (sẽ ghi đè, làm mất lịch sử "trước" để so sánh "sau").

---

## 0:00–0:30 — Vấn đề & Triết lý

**Nói (voice-over hoặc xuất hiện trên khung hình):**
> "In rural classrooms, one teacher can have 40+ students and no time to give each one real feedback on critical thinking. Existing AI tools just give students the answer — which makes them worse thinkers, not better. Our philosophy: **use AI to teach students not to depend on AI.**"

**Trên màn hình:** slide tiêu đề đơn giản (tên dự án + câu triết lý) hoặc README.md mục 1 mở sẵn. Không cần hoạt hình cầu kỳ — 30 giây, đi thẳng vào vấn đề.

---

## 0:30–1:45 — Proof of Action (Tầng 1, LIVE, không cắt ghép)

1. **(0:30–0:45)** Mở ảnh viết tay thật (`eval/test_images/messy_essay_videogames.jpg`) trên màn hình 2 giây để khán giả thấy đây là ảnh thật, xấu, có gạch xoá — không phải text gõ sẵn.
2. **(0:45–1:10)** Chạy lệnh thật:
   ```bash
   python scripts/demo_ocr_run.py
   ```
   Để terminal hiển thị live: OCR transcribe ra đúng lỗi chính tả gốc ("Impakt", "lifes"...), `confidence: high`.
3. **(1:10–1:30)** Chỉ vào output: câu hỏi Socratic của Debate Loop xuất hiện — nhấn mạnh: **không đưa ra đáp án**, chỉ hỏi ngược. Nếu có sẵn log của Validator (chạy `pytest tests/test_pure_functions.py -k answer_leak -v` chèn nhanh, hoặc chỉ show đoạn code `validator.py` 2 giây) — nói: "Every question is checked by an independent, zero-LLM validator that blocks any answer leak before the student ever sees it."
4. **(1:30–1:45)** Chuyển sang tab Firestore Console đã mở sẵn, refresh → chỉ vào document `student_profiles/{new_student_id}` vừa được tạo — **dữ liệu cập nhật live**, không phải ảnh chụp cũ.

---

## 1:45–2:45 — Memory & Tầng 2 (LIVE)

1. **(1:45–2:00)** Nói: "This isn't the student's first essay — the system remembers." Chạy hoặc chỉ vào kết quả có sẵn từ `scripts/demo_tier1_run.py` (3 essay liên tiếp, cùng 1 học sinh) — chỉ vào `persona` đổi qua từng essay và `score_trend`. Đây là bằng chứng "become more helpful over time".
2. **(2:00–2:15)** Nói: "Every graded essay fires a Pub/Sub event — a separate Cloud Run service picks it up." Chạy lệnh thật (đã verify trước đó, chạy lại live):
   ```bash
   TOKEN=$(gcloud auth print-identity-token)
   curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -d "{\"message\": {\"data\": \"$(python -c "import base64,json;print(base64.b64encode(json.dumps({'event_id':'demo-video-run','student_id':'stu_stuck','class_id':'c1','essay_id':'e1'}).encode()).decode())")\"}}" \
     https://eduagent-class-aggregator-s6pcepa2cq-as.a.run.app/
   ```
   → hiện kết quả JSON có `ranked_students` (ranking deterministic) + `digest` (Gemini synthesize).
3. **(2:15–2:35)** Chuyển sang Gmail của giáo viên → refresh Drafts → chỉ vào draft mới xuất hiện, đọc nhanh headline + priority students. Nói: **"The agent's code has no path to send() — it can only create a draft. The teacher is the one who clicks Send."**
4. **(2:35–2:45)** (Tuỳ chọn nếu kịp giờ) Thử mở code `gmail_mcp.py`, chỉ dòng comment "never sends" + chạy nhanh `pytest tests/test_gmail_mcp_never_sends.py -v` → PASS, làm bằng chứng kỹ thuật cho "least-privilege ở tầng code, không phải OAuth".

---

## 2:45–3:30 — Kiến trúc & GCP Proof

Chuyển nhanh qua các tab Console đã mở sẵn (đã chụp bằng chứng trước theo `docs/gcp_evidence_checklist.md`, nhưng ở đây show **live**, không phải ảnh tĩnh nếu có thời gian):

1. Cloud Run Console — service `eduagent-class-aggregator` đang chạy, logs có request vừa gửi ở bước trên.
2. Pub/Sub Console — topic `essay-evaluated` + DLQ `essay-evaluated-dlq` (trống — hệ thống khoẻ).
3. Cloud Trace — 1 trace đầy đủ span `intake → sanitizer → summarizer → ... → profile_mutator`.
4. Terminal: `cat eval/results/eval_report.md` hoặc mở file — chỉ vào **15/15 PASS (100%)**, nói: "Our eval suite runs before every deploy — answer-leak prevention, prompt-injection resistance, and persona fidelity all at 100%, scored deterministically, not by another LLM grading itself."

---

## 3:30–4:00 — Track Alignment (chốt, nói rõ ràng)

**Nói:**
> "We directly answer the two core judging questions for Collaborative Partner. First: does the agent synthesize and mutate data, not just read it? Yes — it builds a weakness taxonomy per student, clusters shared fallacies across a class, and computes an Intervention Priority ranking deterministically. Second: is the input genuinely messy? Yes — real handwritten photos, crossed-out words, poor lighting, real spelling mistakes, verbatim-transcribed and self-consistency-checked for OCR reliability.
>
> Built entirely during this hackathon's Submission Period on Gemini via Vertex AI, Google ADK2, Firestore, Pub/Sub, and Cloud Run."

(Kết thúc đúng 4:00 — phần sau 4 phút giám khảo có thể không xem, nên đừng để thông tin quan trọng rơi vào đây.)

---

## Sau khi quay xong

- [ ] Xem lại: đúng ≤ 4:00 cho phần nội dung chính (có thể để thêm outro/credit sau 4:00 nếu muốn, không bắt buộc).
- [ ] Upload YouTube/Vimeo **Public** (không Unlisted/Private), tiếng Anh hoặc phụ đề tiếng Anh.
- [ ] Dán link video vào Devpost submission (`docs/devpost_submission_draft.md`).
