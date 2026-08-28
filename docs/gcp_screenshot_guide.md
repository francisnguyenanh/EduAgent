# 📷 GCP Screenshot Guide — Hướng Dẫn Chi Tiết Từng Bước

**Mục đích:** Hướng dẫn từng bước chụp bằng chứng GCP cho video 4 phút demo.  
**Thời gian:** ~30-40 phút để chụp tất cả 6-10 phần.  
**Tool:** Chrome/Firefox + Screenshot tool (Print Screen / Snipping Tool)  
**Output:** Lưu vào `assets/gcp_evidence/` với tên file chuẩn.

---

## 🎯 **PHẦN 1: Cloud Run Service Status (1:30-2:15 trong video)**

### URL
```
https://console.cloud.google.com/run/detail/asia-southeast1/eduagent-class-aggregator?project=project-4fc36103-f4ca-49f6-883
```

### Bước 1: Mở URL
1. Copy URL trên
2. Paste vào tab mới trong Chrome (đảm bảo đã login GCP bằng `eikitomobe@gmail.com`)
3. Chờ page load ~3-5 giây

### Bước 2: Verify Service Running
- [ ] Xem phần **"Service details"** — phải show tên service `eduagent-class-aggregator`
- [ ] Phải có **✓ Active** (dấu tick xanh)
- [ ] URL của service: `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app` phải xuất hiện

### Bước 3: Chụp ảnh #1 (Cloud Run Overview)
**File name:** `02_cloud_run_service_metrics.png`

**Cách chụp:**
- Dùng Print Screen hoặc Snipping Tool (Windows: Win+Shift+S)
- Chọn vùng chụp: từ phần "Service details" + "Metrics" tab visible
- **Không cần chụp toàn bộ page**, chỉ cần thấy rõ:
  - ✓ Service name: `eduagent-class-aggregator`
  - ✓ Status: `Active` (xanh)
  - ✓ URL: `.asia-southeast1.run.app`
  - ✓ Region: `asia-southeast1`
  - ✓ Memory/CPU allocation

### Bước 4: Scroll xuống "Metrics" tab
- [ ] Click tab **Metrics** (ngay cạnh "Revisions")
- [ ] Chờ biểu đồ load (3-5 giây)
- [ ] Phải thấy: Request count, Latency, Container Memory, Container CPU

### Bước 5: Chụp ảnh #2 (Cloud Run Metrics)
**File name:** `02_cloud_run_metrics_chart.png`

**Cách chụp:**
- Scroll để thấy toàn bộ **4 biểu đồ**
- Chụp phần biểu đồ (không cần chụp thanh điều khiển trên)
- **Điểm cần thấy rõ:**
  - ✓ Request count > 0 (chứng minh có traffic)
  - ✓ Latency (ms) — hãy ghi lại số để dùng trong video script
  - ✓ Memory/CPU không spike quá (stable)

---

## 🎯 **PHẦN 2: Cloud Run Logs (1:30-2:15 trong video)**

### URL
```
https://console.cloud.google.com/run/detail/asia-southeast1/eduagent-class-aggregator/logs?project=project-4fc36103-f4ca-49f6-883
```

### Bước 1: Mở Logs Tab
1. Quay lại trang Cloud Run Service detail
2. Click tab **"Logs"** (nằm ở hàng tab: Overview → Revisions → Metrics → **Logs**)
3. Chờ logs load

### Bước 2: Xem Structured Logs
- [ ] Phải thấy danh sách log entries (hàng dòng có timestamp)
- [ ] Mỗi entry phải là JSON (sau khi expand)
- [ ] Tìm entry gần nhất có `"POST / HTTP/1.1"` hoặc `"POST /api"` → dấu hiệu request xử lý thành công

### Bước 3: Expand 1 Log Entry
- [ ] Click vào **1 dòng log gần nhất** (hàng xanh/xám)
- [ ] Phần chi tiết mở ra → chứa JSON structure
- [ ] Phải thấy fields:
  ```json
  {
    "httpRequest": { "status": 200, ... },
    "jsonPayload": { "essay_id": "...", "student_id": "...", "class_id": "..." }
  }
  ```

### Bước 4: Chụp ảnh #3 (Logs List)
**File name:** `05_cloud_logging_structured_list.png`

**Cách chụp:**
- Chụp phần danh sách log (3-5 entries)
- Phải thấy rõ timestamp + severity level

### Bước 5: Chụp ảnh #4 (Log Detail — JSON)
**File name:** `05_cloud_logging_structured_json.png`

**Cách chụp:**
- Chụp phần đã expand của 1 log entry
- **Điểm cần thấy:**
  - ✓ `"httpRequest": { "status": 200, "requestUrl": "..." }`
  - ✓ `"jsonPayload"` chứa `essay_id`, `student_id`, `class_id`
  - ✓ `"timestamp"` hiển thị UTC

---

## 🎯 **PHẦN 3: Pub/Sub Topics & DLQ (2:45-3:15 trong video)**

### URL 1 — Topic
```
https://console.cloud.google.com/cloudpubsub/topic/detail/essay-evaluated?project=project-4fc36103-f4ca-49f6-883
```

### Bước 1: Mở Topic `essay-evaluated`
1. Copy URL trên
2. Paste vào tab mới, chờ load

### Bước 2: Verify Topic Info
- [ ] Topic name: `essay-evaluated`
- [ ] Number of subscriptions: phải ≥1
- [ ] Messages published: > 0 (chứng minh có traffic)

### Bước 3: Chụp ảnh #5 (Pub/Sub Topic)
**File name:** `04_pubsub_topic_info.png`

---

### URL 2 — Subscription + DLQ Config
```
https://console.cloud.google.com/cloudpubsub/subscription/detail/class-aggregator-sub?project=project-4fc36103-f4ca-49f6-883
```

### Bước 4: Mở Subscription
1. Copy URL trên
2. Paste vào tab mới

### Bước 5: Tìm Dead Letter Policy
- [ ] Scroll xuống tìm section **"Delivery settings"** hoặc **"Dead Letter Policy"**
- [ ] Phải thấy:
  - `Max delivery attempts: 5`
  - `Dead letter topic: essay-evaluated-dlq`

### Bước 6: Chụp ảnh #6 (Subscription + DLQ)
**File name:** `04_pubsub_dlq_config.png`

**Cách chụp:**
- Chụp phần subscription detail + dead letter policy section
- **Điểm cần thấy:**
  - ✓ Subscription name: `class-aggregator-sub`
  - ✓ Topic: `essay-evaluated`
  - ✓ **Dead Letter Topic: `essay-evaluated-dlq`**
  - ✓ **Max Delivery Attempts: 5**

---

### URL 3 — DLQ Topic
```
https://console.cloud.google.com/cloudpubsub/topic/detail/essay-evaluated-dlq?project=project-4fc36103-f4ca-49f6-883
```

### Bước 7: Mở DLQ Topic
1. Copy URL
2. Paste vào tab

### Bước 8: Chụp ảnh #7 (DLQ Topic)
**File name:** `04_pubsub_dlq_topic.png`

**Cần thấy:**
- ✓ Topic name: `essay-evaluated-dlq`
- ✓ Number of subscriptions (phải có ≥1)
- ✓ Messages: 0 (nếu không chạy chaos test) hoặc > 0 (nếu có lỗi)

---

## 🎯 **PHẦN 4: Firestore Database (2:15-2:45 trong video)**

### URL
```
https://console.cloud.google.com/firestore/databases/default/data?project=project-4fc36103-f4ca-49f6-883
```

### Bước 1: Mở Firestore
1. Copy URL
2. Paste vào tab

### Bước 2: Click Collection `student_profiles`
- [ ] Ở bên trái, click folder `student_profiles`
- [ ] Phải thấy danh sách documents: `stu_improving`, `stu_stuck`, `stu_declining`, v.v.

### Bước 3: Click 1 Document (e.g., `stu_stuck`)
- [ ] Click vào `stu_stuck`
- [ ] Panel bên phải expand để show fields

### Bước 4: Expand Fields
Scroll trong panel fields để thấy:
- [ ] `essay_history` (array) — click expand để thấy entries
- [ ] `all_time_weaknesses` (array)
- [ ] `persona_history` (array)
- [ ] `score_trend` (string)
- [ ] `total_essays_count` (number)

### Bước 5: Chụp ảnh #8 (Firestore Document)
**File name:** `03_firestore_student_profile.png`

**Cách chụp:**
- Chụp phần document detail (bên phải)
- **Điểm cần thấy:**
  - ✓ Document ID: `stu_stuck`
  - ✓ Fields: `total_essays_count`, `avg_score`, `score_trend`
  - ✓ Subcollection `essay_history` (hoặc field nếu embedded)

### Bước 6: Click Collection `class_analytics`
- [ ] Click folder `class_analytics` (bên trái)
- [ ] Phải thấy document `c1`

### Bước 7: Click Document `c1`
- [ ] Click vào `c1`
- [ ] Scroll để thấy fields:
  - `digests` (subcollection hoặc field)
  - `settings`
  - `last_analyzed_at`

### Bước 8: Chụp ảnh #9 (Firestore Class Analytics)
**File name:** `03_firestore_class_analytics.png`

---

## 🎯 **PHẦN 5: Cloud Trace (3:15-3:45 trong video)**

### URL
```
https://console.cloud.google.com/traces/list?project=project-4fc36103-f4ca-49f6-883
```

### Bước 1: Mở Trace Traces List
1. Copy URL
2. Paste vào tab

### Bước 2: Xem Traces
- [ ] Phải thấy danh sách traces (5-20 rows)
- [ ] Mỗi row: Trace ID, Latency (ms), Timestamp
- [ ] Chọn trace **gần nhất** (top row, newest)

### Bước 3: Chụp ảnh #10 (Trace List)
**File name:** `01_cloud_trace_list.png`

**Cách chụp:**
- Chụp phần list
- Ghi lại **trace ID của 1 trace gần nhất**

### Bước 4: Click vào 1 Trace
- [ ] Click vào row trace gần nhất
- [ ] Chờ trace detail load (5-10 giây)

### Bước 5: Expand Span Tree
- [ ] Phải thấy "Waterfall" view của spans
- [ ] Click icon **expand** (▶) trên từng parent span để mở rộng
- [ ] Expand tất cả để thấy toàn bộ hierarchy:
  ```
  root (pipeline)
    ├── intake
    ├── sanitizer
    ├── summarizer
    ├── persona_selector
    ├── debate_loop
    ├── challenge_validator
    ├── cognitive_scorer
    └── profile_mutator
  ```

### Bước 6: Chụp ảnh #11 (Trace Span Tree)
**File name:** `01_cloud_trace_e2e_spans.png`

**Cách chụp:**
- Chụp toàn bộ span tree (có thể cần scroll ngang để thấy timeline)
- **Điểm cần thấy:**
  - ✓ Root span (tên + latency tổng, e.g., 4.5s)
  - ✓ 8+ child spans (tên + duration từng span)
  - ✓ Timeline waterfall (thể hiện sequential hoặc parallel execution)

---

## 🎯 **PHẦN 6: BẰNG CHỨNG GEMMA ĐANG CHẠY THẬT (ADR-028) — mới, Audit Wave 25**

> **Vì sao cần riêng một phần:** Gemma 4 là model phụ mang **+0.2 điểm bonus** (`rule.txt:215`).
> Nhưng **UI demo KHÔNG hiển thị nó** — giao diện chỉ cảnh báo khi `confidence` thấp, không hề nhắc
> model nào chạy lượt hai. Nếu bạn chỉ quay UI, không có một khung hình nào chứng minh Gemma tồn tại,
> và +0.2 trở thành lời khai suông.
>
> **Tin tốt:** điều lệ đòi *"Must demonstrate the backend is running on Google Cloud (ie: Google Cloud
> Console, Cloud Run dashboard, **Vertex AI logs**, URL of .run)"* — nên **một khung hình log Vertex
> phục vụ CẢ HAI**: vừa chứng minh backend chạy trên Google Cloud (bắt buộc), vừa chứng minh Gemma
> (bonus). Đây là beat hiệu quả nhất trong video.

### ⭐ Cách 1 (KHUYẾN NGHỊ) — Logs Explorer, hai họ model xen kẽ trên cùng một màn hình

**Tab cần mở — dán nguyên URL này, query đã điền sẵn:**

```
https://console.cloud.google.com/logs/query;query=resource.labels.service_name%3D%22eduagent-class-aggregator%22%0A%28jsonPayload.message%3A%22gemma-4-26b-a4b-it-maas%22%20OR%20jsonPayload.message%3A%22gemini-3.5-flash%3AgenerateContent%22%29;duration=PT1H?project=project-4fc36103-f4ca-49f6-883
```

Nếu URL không load, dán thủ công vào ô query của Logs Explorer:

```
resource.labels.service_name="eduagent-class-aggregator"
(jsonPayload.message:"gemma-4-26b-a4b-it-maas" OR jsonPayload.message:"gemini-3.5-flash:generateContent")
```

**Nội dung sẽ hiện ra (đã kiểm chứng thật ngày 2026-08-28):**

```
POST .../publishers/google/models/gemini-3.5-flash:generateContent      "HTTP/1.1 200 OK"
POST .../publishers/google/models/gemini-3.5-flash:generateContent      "HTTP/1.1 200 OK"
POST .../publishers/google/models/gemma-4-26b-a4b-it-maas:generateContent  "HTTP/1.1 200 OK"   <-- Gemma
POST .../publishers/google/models/gemini-3.5-flash:generateContent      "HTTP/1.1 200 OK"
```

**Vì sao khung hình này mạnh:** hai họ model **xen kẽ nhau trong cùng một luồng request** — chính là
hình ảnh trực quan của luận điểm ADR-028 (*"chúng tôi không so một model với chính nó"*). Không cần
giải thích thêm, người xem tự thấy.

**Câu nói khi quay (≈8 giây):**
> *"This is the live Vertex AI log from the deployed service. Notice two different model families
> interleaved on the same request: Gemini Vision transcribes the photo, then Gemma — a different
> family — transcribes it again. We compare the two, because a model agreeing with itself proves
> nothing."*

**Bước làm:**
1. **Chạy một request TRƯỚC** để có log tươi: mở Student Portal → preset *📷 2. Handwritten Essay (OCR)* → submit.
2. Mở URL trên (hoặc dán query).
3. Đặt **Time range = Last 1 hour**.
4. Chờ ~15–30 giây rồi bấm **Refresh** — log Cloud Run có độ trễ ingest.
5. Zoom Chrome **125%** để dòng `gemma-4-26b-a4b-it-maas` đọc được trên video.
6. Chụp `06_vertex_gemma_crossmodel_logs.png`.

⚠️ **Bẫy đã gặp thật:** log của service nằm ở trường **`jsonPayload.message`**, KHÔNG phải
`textPayload`. Query bằng `textPayload:"gemma"` trả về **0 kết quả** và làm tưởng nhầm là Gemma không
chạy. Dùng đúng query ở trên.

### Cách 2 (dự phòng, nhanh hơn) — DevTools Network tab

Nếu Logs Explorer chậm hoặc log chưa kịp ingest:

1. Mở Student Portal, bấm **F12** → tab **Network**.
2. Bấm nút **Extract OCR** (luồng hai bước: trích text → xem lại → rồi mới Start).
3. Click request **`extract-image`** → tab **Response** (hoặc **Preview**) → mở khối `ocr`:

```json
"ocr": {
  "confidence": "high",
  "uncertain_segments": [],
  "degraded": false,
  "cross_check_model": "gemma-4-26b-a4b-it-maas"
}
```

⚠️ **Quan trọng — soi đúng request.** Từ Audit Wave 25 giao diện dùng **luồng hai bước**: `extract-image`
trả text ra ô soạn thảo để học sinh sửa, rồi `start` mới bắt đầu tranh biện. Khối `ocr` (và
`cross_check_model`) **chỉ nằm trong response của `extract-image`** — response của `start` là đường
văn bản gõ tay nên **không có** khối `ocr` nào cả. Soi nhầm `start` sẽ tưởng tín hiệu biến mất.
*(Luồng cũ `start-with-image` một bước vẫn còn và vẫn trả `cross_check_model`, nhưng UI không dùng nó nữa.)*

Trường `cross_check_model` được thêm ở Audit Wave 25 đúng để quay được cảnh này. **Ưu điểm:** đây là
response trực tiếp từ Cloud Run, không phải log — tức thì, không delay. **Nhược điểm:** DevTools trông
rối hơn trên video; nhớ đóng bớt panel thừa.

### Cách 3 (chỉ khi cần, cho terminal beat)

```bash
URL=https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app
T=$(curl -s -X POST $URL/api/auth/login -H 'Content-Type: application/json' \
  -d '{"role":"student","user_id":"zz9_ocrtest","password":"eduagent2026"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
# ... POST /api/debate/start-with-image với image_base64 ...
# -> khối .ocr trả về "cross_check_model": "gemma-4-26b-a4b-it-maas"
```

### ⚠️ Nếu trên camera nó hiện `"gemini-fallback"` thì sao?

**Đừng hoảng, và ĐỪNG quay lại giả vờ không thấy.** Nghĩa là hàng đợi MaaS dùng chung của Gemma đang
đầy (`429 RESOURCE_EXHAUSTED`) và hệ thống đã tự lùi về lượt hai cùng-model đúng thiết kế. Đo được
**0/16 lần fallback** trên live ngày 2026-08-28, nên xác suất thấp — nhưng nếu gặp, đó lại là **câu
chuyện tốt hơn**, hãy nói thẳng:

> *"That says gemini-fallback — Gemma runs on shared capacity, so it can be busy. When it is, the
> system falls back to the original same-model check instead of failing the student's submission.
> A busy queue never blocks a kid's homework."*

Một hệ thống thừa nhận degrade trên camera đáng tin hơn một hệ thống chỉ chạy đúng lúc thuận lợi.

---

## 📁 **Lưu File Chụp**

Sau khi chụp xong tất cả, lưu vào thư mục:
```
assets/gcp_evidence/
├── 01_cloud_trace_list.png
├── 01_cloud_trace_e2e_spans.png
├── 02_cloud_run_service_metrics.png
├── 02_cloud_run_metrics_chart.png
├── 03_firestore_student_profile.png
├── 03_firestore_class_analytics.png
├── 04_pubsub_topic_info.png
├── 04_pubsub_dlq_config.png
├── 04_pubsub_dlq_topic.png
├── 05_cloud_logging_structured_list.png
├── 05_cloud_logging_structured_json.png
└── 06_vertex_gemma_crossmodel_logs.png      <-- Audit Wave 25 (bằng chứng Gemma + backend on GCP)
```

---

## ✅ **Checklist Trước Quay Video**

- [ ] Tất cả 12 ảnh chụp đã lưu vào `assets/gcp_evidence/` (11 cũ + `06_vertex_gemma_crossmodel_logs.png`)
- [ ] 🔴 **Đã chạy thử PHẦN 6 ít nhất một lần trước khi quay** — xác nhận log hiện `gemma-4-26b-a4b-it-maas` chứ không phải `gemini-fallback`
- [ ] Mỗi ảnh có tên file theo chuẩn
- [ ] Tất cả ảnh resize sao cho chữ rõ ràng (không quá to/nhỏ)
- [ ] Đọc qua từng ảnh 1 lần để chắc nó match ý muốn show trong video

---

## 💡 **Mẹo Chụp**

1. **Brightness/Contrast:** Nếu màn hình quá tối, tăng brightness trước khi chụp
2. **Zoom:** Để dễ nhìn trên video, có thể zoom Chrome lên 110-125% (Ctrl+Plus)
3. **Crop sau:** Dùng tool edit ảnh (Paint, Online tool) để crop chi tiết nếu cần
4. **Không cần HD:** 1920x1080 hoặc 1280x720 đã đủ; không cần chụp 4K

---

## 📞 **Nếu gặp vấn đề**

| Vấn đề | Giải pháp |
|---|---|
| Cloud Run service "Creating" | Chờ 2-3 phút, refresh page |
| Logs trống | Chạy `python scripts/demo_ocr_run.py` để trigger request |
| Firestore trống | Chạy seed script trước: `python scripts/seed_student_profiles.py` |
| Traces không có | Traces delay ~30s từ lúc request; chờ rồi refresh |
| **Query Gemma trả về 0 dòng** | Đang dùng `textPayload:` — sai trường. Log service nằm ở **`jsonPayload.message`**. Dùng query ở PHẦN 6 |
| **Log Gemma chưa xuất hiện** | Ingest delay 15–30s. Chạy 1 request rồi chờ, bấm Refresh |
| DLQ có messages | Bình thường nếu chạy chaos test trước |

