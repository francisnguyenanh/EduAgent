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
| 7 | `07_secret_manager_all_credentials.png` | **Secret Manager** | **Cả 3** secret tồn tại (`eduagent-session-secret`, `eduagent-gmail-token`, `eduagent-sheets-token`) và Cloud Run revision mount chúng dưới dạng **secret reference**, không phải plaintext (**ĐỢT 13/14 — ADR-016 + ADR-020**). Chụp cả 2: trang Secret Manager, và tab "Variables & Secrets" của revision — điểm cần thấy là **không có credential nào hiện giá trị** |
| 8 | `08_firestore_ttl_policy.png` | **Firestore** | TTL policy trên `debate_sessions.expire_at` ở trạng thái **ACTIVE** (**ĐỢT 13** — chứng minh phát biểu retention "TTL 24h rồi tự xoá" là thật, không chỉ ghi field `expire_at` rồi không ai xoá). Lệnh CLI tương đương: `gcloud firestore fields ttls list --collection-group=debate_sessions` |
| 9 | `09_rate_limit_429.png` | **Cloud Run / terminal** | HTTP **429 + header `Retry-After`** khi flood endpoint tranh biện (**ĐỢT 13 / ADR-017** — bằng chứng "Token bucket rate limiting" trong bảng STRIDE là thật; trước ĐỢT 13 claim này không tồn tại trong code) |
| 10 | `10_student_endpoint_401.png` | **Cloud Run / terminal** | `curl` POST `/api/debate/start` **không kèm token → 401**, và kèm token của học sinh khác → **403** (**ĐỢT 13 / ADR-018**). Đây là bằng chứng mạnh vì giám khảo có thể tự chạy lại đúng lệnh này trên URL live |

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

## E-bis. Lệnh verify nhanh 4 bằng chứng bảo mật ĐỢT 13/14 (chạy được, không cần Console)

Bốn hạng mục mới (#7–#10) verify bằng CLI/curl nhanh hơn là chụp Console, và **giám khảo có thể tự chạy lại** — điều đó thuyết phục hơn ảnh chụp. ✅ **Đã redeploy và verify thật trong phiên làm việc ĐỢT 16** (revision `eduagent-class-aggregator-00030-jkn`) — output mẫu dưới đây là output THẬT đo được, không phải kỳ vọng lý thuyết.

```bash
URL=https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app

# (7) Cả 3 secret tồn tại, và KHÔNG credential nào còn ở dạng plaintext
gcloud secrets list --format='table(name.basename())' | grep eduagent
.venv/bin/python scripts/doctor.py   # check "No plaintext credentials on Cloud Run" phải PASS

# ...hoặc xem thẳng: mỗi credential phải in ra "secretRef", không phải "PLAINTEXT"
gcloud run services describe eduagent-class-aggregator --region asia-southeast1 --format=json \
  | .venv/bin/python -c 'import json,sys; [print(("PLAINTEXT " if "value" in e else "secretRef  ")+e["name"]) for e in json.load(sys.stdin)["spec"]["template"]["spec"]["containers"][0].get("env",[])]'

# (8) TTL policy ACTIVE (không chỉ có field expire_at)
gcloud firestore fields ttls list --collection-group=debate_sessions

# (9) Rate limit thật: flood 15 request, phải thấy 429 xen giữa các 200
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST $URL/api/debate/start \
    -H 'Content-Type: application/json' -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'
done; echo

# (10a) Endpoint học sinh có xác thực: không token -> 401
curl -s -o /dev/null -w "no-token: %{http_code}\n" -X POST $URL/api/debate/start \
  -H 'Content-Type: application/json' -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'

# (10b) Học sinh KHÁC nộp thay -> 403 (login lấy token THẬT từ chính service live)
TOK=$(curl -s -X POST $URL/api/auth/login -H 'Content-Type: application/json' \
  -d '{"role":"student","user_id":"c1_stu99","password":"eduagent2026"}' \
  | .venv/bin/python -c "import json,sys; print(json.load(sys.stdin).get('token',''))")
curl -s -o /dev/null -w "student nop thay hoc sinh khac: %{http_code}\n" -X POST $URL/api/debate/start \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'

# (10c) Học sinh đọc dashboard giáo viên -> 403
curl -s -o /dev/null -w "student doc route giao vien: %{http_code}\n" \
  -X GET "$URL/api/classes/c1/priority" -H "Authorization: Bearer $TOK"
```

**Output thật đo được (ĐỢT 16, sau redeploy):**

```
(7) doctor.py -> [PASS] No plaintext credentials on Cloud Run
    All credentials mounted as Secret Manager references (secretKeyRef):
    ['EDUAGENT_SESSION_SECRET', 'GMAIL_COMPOSE_TOKEN_JSON', 'SHEETS_TOKEN_JSON']

(10a) no-token: 401
(10b) student nop thay hoc sinh khac: 403
(10c) student doc route giao vien: 403
```

⚠️ **Nếu bạn thấy `200` ở (10a):** revision đang chạy là bản CHƯA redeploy — chạy `.venv/bin/python scripts/deploy_to_cloud_run.py` trước, sau đó chạy lại các lệnh trên. Nếu chụp bằng chứng trước khi redeploy, bạn đang chụp bằng chứng ngược lại điều mình muốn chứng minh.

---

## E-ter. Hướng dẫn chụp evidence chi tiết cho mục #9 và #10 (từng bước, có ảnh nào chụp ảnh nào)

Đây là 2 mục **mạnh nhất về mặt thuyết phục** trong toàn bộ checklist, vì chúng không phải ảnh chụp Console tĩnh mà là **terminal + lệnh giám khảo tự gõ lại được**. Làm đúng cách chụp dưới đây biến nó thành 1 đoạn video ngắn dùng được trực tiếp trong demo (Scene 4, xem `video_script.md`), không chỉ là file PNG nằm trong assets.

### Chuẩn bị (làm 1 lần)

1. Mở Terminal, `cd` vào đúng thư mục project:
   ```bash
   cd "/Users/eikitomobe/Documents/3. Học tập/Lập trình/VS code/EduAgent"
   ```
2. **Tăng font size terminal lên to** (⌘+ nhiều lần, hoặc Terminal → Settings → Profiles → Text → cỡ chữ ≥ 18pt) — ảnh chụp/video terminal chữ nhỏ là lỗi hay gặp nhất khiến giám khảo phải zoom, đừng để họ phải làm vậy.
3. Nếu dùng terminal có theme nền đen chữ trắng, giữ nguyên — nó thường rõ hơn nền sáng khi quay màn hình.
4. Chạy thử 1 lần lệnh `curl` bất kỳ để chắc chắn có mạng và service đang lên (`GET $URL/health-check` → phải ra `{"status": "ok"}`).

### Cách #1 — chụp ảnh tĩnh (nhanh, dùng cho mục #9/#10 trong bảng ở phần trên)

1. Dán **toàn bộ khối lệnh (9)** ở mục E-bis vào terminal, Enter, đợi in hết dãy mã HTTP.
2. Chụp màn hình **cả lệnh đã gõ VÀ output** trong cùng 1 khung (macOS: `⌘+Shift+4` rồi kéo chọn vùng, hoặc `⌘+Shift+5` → "Capture Selected Portion").
3. Lưu file tên `09_rate_limit_429.png` vào `assets/gcp_evidence/`.
4. Làm tương tự với khối lệnh (10a) + (10b) + (10c) — có thể chụp chung 1 ảnh nếu cả 3 lệnh còn hiện trên màn hình, lưu tên `10_student_endpoint_401.png`.
5. **Điểm cần thấy rõ trong ảnh:** dãy số ở (9) phải có ít nhất một `429` xen giữa các `200`; ở (10) phải thấy đúng `401` rồi `403` rồi `403` — không phải toàn `200`.

### Cách #2 — quay lại thành GIF/video ngắn (khuyến khích hơn, dùng trực tiếp trong Scene 4 của video demo)

Terminal chạy `curl` xong gần như ngay lập tức nên một đoạn ghi 15-20 giây là đủ, không cần dựng cảnh gì thêm:

1. Mở QuickTime Player → File → **New Screen Recording** (hoặc `⌘+Shift+5` → "Record Selected Portion").
2. Chọn vùng quay là đúng khung cửa sổ Terminal.
3. Bấm Record, rồi lần lượt: dán và chạy khối lệnh (9) → đợi in hết → dán và chạy khối (10a), (10b), (10c) → dừng quay.
4. Lưu file `.mov`, đặt tên `09_10_rate_limit_and_auth_live.mov` trong `assets/gcp_evidence/`.
5. **Dùng trực tiếp đoạn này trong video demo** ở beat bảo mật (`video_script.md` Scene 4, đoạn "Optional 5-second security beat") — cắt lấy đúng đoạn thấy rõ mã `401`/`403`/`429` là đủ, không cần chiếu hết 20 giây.

### Cách #3 — nếu muốn có prompt hiện trong ảnh cho đẹp (không bắt buộc)

Nếu terminal của bạn không hiện rõ lệnh đã gõ (một số theme ẩn prompt khi output dài), thêm `echo` trước mỗi lệnh để chính output ghi lại luôn câu lệnh đang test — hữu ích khi ảnh chỉ chụp phần cuối màn hình:

```bash
echo "--- (10a) khong token ---"; curl -s -o /dev/null -w "%{http_code}\n" -X POST $URL/api/debate/start -H 'Content-Type: application/json' -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'
echo "--- (10b) hoc sinh khac nop thay ---"; curl -s -o /dev/null -w "%{http_code}\n" -X POST $URL/api/debate/start -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'
```

### Việc dễ quên nhất khi chụp bằng chứng này

- **Che passcode demo?** Không cần — `eduagent2026` là passcode demo công khai, đã ghi thẳng trong README, không phải secret thật. Không cần blur nó trong ảnh/video.
- **Che project ID / service account email?** Cũng không cần — cả hai đã public trong README/PROJECT_WIKI, không phải bí mật.
- **Cái DUY NHẤT cần đảm bảo KHÔNG lọt vào ảnh/video:** nội dung thật của `$TOK` (token JWT) nếu bạn dùng `echo $TOK` để debug — token đó tuy hết hạn sau 24h nhưng vẫn không nên phơi ra không cần thiết. Các lệnh mẫu ở trên không in `$TOK` ra màn hình, chỉ dùng nó trong header — an toàn để chụp nguyên văn.
- **Thứ tự chụp:** làm mục #7/#8 (Secret Manager, TTL) TRƯỚC khi làm #9/#10 (auth/rate-limit) — nếu #7 chưa PASS thì #10 gần như chắc sẽ vẫn là bản cũ, chụp trước sẽ tiết kiệm 1 lần chụp lại.

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

