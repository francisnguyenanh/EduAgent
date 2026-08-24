# GCP Evidence Checklist (Phase 7 — chụp thủ công, làm sau khi code/deploy đã ổn định)

> Mục đích: thu thập bằng chứng GCP Native cho README/video demo (Phase 7 DoD: "mọi bằng chứng GCP đã nằm trong thư mục assets"). Đăng nhập Console bằng `eikitomobe@gmail.com`, đảm bảo project đang chọn là `project-4fc36103-f4ca-49f6-883`.
>
> Lưu ảnh chụp vào `assets/gcp_evidence/` (tạo mới), đặt tên theo từng mục bên dưới để dễ dùng lại khi quay video demo (Phase 8) — không cần quay live lại Console lúc đó.

**URL Cloud Run service thật (đã deploy Phase 7):** `https://eduagent-class-aggregator-s6pcepa2cq-as.a.run.app`
Lưu ý: mở URL này bằng trình duyệt sẽ báo `403 Forbidden` — đây là **hành vi đúng thiết kế** (service deploy `--no-allow-unauthenticated`, route `/` chỉ nhận `POST` từ Pub/Sub push, không có trang web để xem). Không cần sửa gì, chỉ cần chụp bằng chứng qua Console theo hướng dẫn dưới.

---

## A. Cloud Run service status & metrics

1. Console → **Cloud Run** → chọn service `eduagent-class-aggregator` (region `asia-southeast1`).
2. Tab **"Metrics"** — chụp biểu đồ Request count / Request latency / Container CPU-Memory (sẽ thấy các request thật đã gửi: 2 lần `POST /`, vài lần `GET /health-check`).
3. Tab **"Logs"** — chụp log có dòng `POST / HTTP/1.1 200 OK` và `Uvicorn running on http://0.0.0.0:8080` (bằng chứng container chạy thật + xử lý request thật).
4. Tab **"Revisions"** — chụp thấy revision mới nhất (`eduagent-class-aggregator-00003-qkr` hoặc mới hơn) đang serving 100% traffic.

## B. Firestore live collections/documents

1. Console → **Firestore** → **Data**.
2. Chụp danh sách collections: `student_profiles` (5 doc từ seed Phase 2: `stu_improving`, `stu_stuck`, `stu_declining`, `stu_inactive`, `stu_common_fallacy`), `processed_events`, `class_analytics` (có `c1/digests/...` sau khi test event thật).
3. Mở document `student_profiles/stu_stuck` — chụp thấy `persona_streak`, `flags.needs_attention: true`, `essay_history` có field `student_feedback`.

## C. Pub/Sub topic + subscription metrics + DLQ

1. Console → **Pub/Sub** → **Topics** → `essay-evaluated`.
2. Chụp tab Metrics (publish message count).
3. Vào **Subscriptions** → `class-aggregator-sub` → chụp cấu hình Dead Letter (trỏ đúng `essay-evaluated-dlq`, max delivery attempts = 5).
4. Vào topic `essay-evaluated-dlq` → chụp Metrics — bình thường nên trống/0 message (chứng minh hệ thống không bị lỗi dồn vào DLQ trong vận hành thật). Nếu muốn thêm bằng chứng "DLQ hoạt động được khi cần", dùng lại ảnh chụp từ `scripts/chaos_test_pubsub.py` ở Phase 4 (đã từng đẩy 1 message thật vào DLQ để verify).

## D. Vertex AI / Gemini API logs

1. Console → **Logging** → **Logs Explorer**.
2. Filter: `resource.type="aiplatform.googleapis.com"` hoặc search từ khoá `generateContent` — sẽ thấy các request Gemini thật (từ digest synthesis lúc verify deploy, và từ các lần chạy demo script trước đó).
3. Cách khác đơn giản hơn: Console → **Vertex AI** → **Dashboard** — chụp biểu đồ request/quota có traffic thật.

## E. Cloud Trace span end-to-end

1. Console → **Trace** → **Trace list**.
2. Lọc theo thời gian gần nhất, tìm trace có tên `eduagent.node.class_aggregator` hoặc trace chứa chuỗi span `intake → sanitizer → summarizer → persona_selector → debate_loop → challenge_validator → cognitive_scorer → profile_mutator` (từ lần chạy `scripts/demo_tier1_run.py` / `scripts/demo_ocr_run.py`).
3. Chụp cây span đầy đủ — đây là bằng chứng "Cloud Trace hiển thị 1 trace đầy đủ end-to-end" (Phase 4 DoD).

---

## Sau khi xong

Báo lại để cập nhật TODO.md Phase 7 (đánh dấu mục "Thu thập bằng chứng GCP Native" hoàn thành) và chuyển sang Phase 7's mục còn lại (test spin-up từ máy sạch) hoặc Phase 8 (video demo/submission).
