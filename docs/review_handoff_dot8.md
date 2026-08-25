# Review Handoff — EduAgent (All Things Agentic Hackathon, Track: Collaborative Partner)

> Mục đích tài liệu này: tổng hợp lại các vấn đề đã tìm thấy và đã sửa trong phiên review vừa qua (ĐỢT 6→8), để một AI/reviewer khác đọc và **tự kiểm chứng độc lập**, không chỉ tin lời tài liệu này. Mọi khẳng định "đã sửa" bên dưới đều có lệnh cụ thể để tái kiểm tra — hãy chạy lại trước khi kết luận.

> ⚠️ **ĐÂY LÀ ẢNH CHỤP LỊCH SỬ (ĐỢT 6→8), KHÔNG PHẢI TRẠNG THÁI HIỆN TẠI.** Giữ nguyên có chủ đích để tra cứu quá trình, nên **đừng dùng các con số trong file này làm hiện trạng**. Đã lạc hậu ít nhất: `doctor.py` giờ có **10 check** (không phải 6), test suite **245** (không phải 190), và **20 ADR** (không phải 14). Quan trọng hơn: sau file này còn 4 đợt nữa (ĐỢT 11→14) tìm ra những vấn đề mà chính phiên review này **không** phát hiện — bằng chứng bịa (`+5.62` là hằng số gõ tay), 12/50 eval case không thể FAIL, khoá ký token công khai trong repo, 5 endpoint học sinh không xác thực, và refresh token OAuth để cleartext trên service live. Trạng thái hiện tại: xem `TODO.md` (ĐỢT 12→14) và `README.md` mục 4.

## 1. Bối cảnh & tiêu chí chấm điểm

- Repo: `eduagent` — hệ thống 2 tầng (ADK2 + Gemini/Vertex AI + Firestore + Pub/Sub + Cloud Run).
- Ma trận điểm (từ `TODO.md` mục 2): Innovation & Utility 40%, Architectural Discipline 30%, **Demo & Readiness 30%**, Bonus +0.4đ.
- Deadline nộp: 31/8 17:00 PT, tác giả tự đặt luật nộp sớm ≥1 ngày.
- Trạng thái trước phiên review này: tác giả tự đánh giá đã "hoàn thành 100%" qua 7 đợt cải tiến (ĐỢT 1–7) + Phase 0–7, còn Phase 8 (quay video, nộp) chưa làm.

## 2. Vấn đề đã tìm thấy (theo thứ tự phát hiện)

### 2.1 ĐỢT 7 bị phình phạm vi (đã tư vấn, không phải bug)

ĐỢT 7 gốc liệt kê 8 hạng mục "wow-factor" (voice mentor, what-if sandbox, fallacy graph, SSE live feed, v.v.) trong khi 2/3 trục điểm (Innovation, Architecture) đã bão hoà bằng chứng và trục còn thiếu duy nhất là Demo (30%, chưa quay video). Đã khuyến nghị cắt còn 3 mục ROI cao nhất; tác giả đã tự thực hiện điều này (xem `TODO.md` mục 11 — hiện chỉ còn Metacognitive Self-Correction Loop được implement, các mục khác bị đánh dấu ✂️ cắt bỏ có lý do).

**Cần reviewer tự kiểm tra:** confirm không có code nào cho 5 mục đã cắt (voice/audio, what-if sandbox, fallacy graph, SSE, heat-level) lọt vào `src/` — nếu có, đó là scope creep ngoài kế hoạch đã thống nhất.

### 2.2 🔴 BLOCKER — README tuyên bố sai về bảo mật Cloud Run (đã sửa)

**Phát hiện (bằng `curl` trực tiếp vào service live, không suy diễn):**
```
deploy.txt ghi --allow-unauthenticated
GET  /              → 200
POST / (không token) → 500  (nghĩa là request ĐÃ lọt vào container, không bị chặn ở IAM)
grep "Authorization\|OIDC\|id_token" src/eduagent/server.py → 0 kết quả (thời điểm đó)
```
Nhưng README §3.10 và §5 lúc đó khẳng định `--no-allow-unauthenticated` + "Pub/Sub OIDC token" là cơ chế bảo vệ — **sai với thực tế deploy**. Đây là loại lỗi nguy hiểm nhất cho một dự án ăn điểm bằng tính trung thực kiến trúc: một giám khảo tự `curl` sẽ thấy tuyên bố bảo mật sai, gây nghi ngờ lây sang toàn bộ 13 ADR khác dù chúng đúng.

**Đã sửa (commit `c096405`):**
- `src/eduagent/server.py::_verify_pubsub_push_auth()` — verify chữ ký OIDC thật bằng `google.oauth2.id_token.verify_oauth2_token` (không phải shared secret) trước khi `POST /` chạm `process_event()`.
- `src/eduagent/config.py` thêm `PUBSUB.push_audience` / `PUBSUB.push_service_account` (env var, optional pin thêm identity).
- `requirements.txt` thêm `google-auth` tường minh (trước đó chỉ là transitive dependency).
- 7 test mới trong `tests/test_server.py` (thiếu header/token sai/sai service account/token hợp lệ) + sửa 1 test cũ trong `tests/test_server_interactive_api.py`.
- README §3.10 + §5 sửa lại đúng thực tế; thêm **ADR-014** vào bảng ADR.
- **Redeploy thật lên Cloud Run** (revision `eduagent-class-aggregator-00009-mjv`) với code mới + 2 env var mới.

**Reviewer tự kiểm chứng:**
```bash
curl -X POST https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/ -d '{}'
# kỳ vọng: 401 (không phải 500/200)
curl https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/
# kỳ vọng: 200 (Web UI vẫn public cho giám khảo)
pytest tests/ -q -m "not e2e"
# kỳ vọng: 184 passed (tăng từ 179 trước phiên này)
```

### 2.3 🔴 BLOCKER nghiêm trọng hơn — Pub/Sub subscription là PULL mode thật, không phải PUSH (đã sửa)

**Phát hiện:** trong lúc chuẩn bị set env var cho fix ở mục 2.2, kiểm tra hạ tầng thật:
```
gcloud pubsub subscriptions describe class-aggregator-sub --format=json
→ "pushConfig": {}   (rỗng — pull mode)
```
Nghĩa là **toàn bộ luồng "event-driven Tier 2"** mà README/architecture diagram quảng cáo (essay được chấm → Pub/Sub tự trigger Cloud Run → digest tự sinh) **không hề chạy tự động** trên hạ tầng live — Cloud Run service tồn tại và khoẻ mạnh nhưng không có gì gọi vào nó, trừ khi ai đó tự tay chạy `scripts/run_class_aggregator_subscriber.py`. README §3.10 tự ghi chú đây là bước còn treo, chưa từng làm thật.

**Rủi ro nếu không sửa:** quay video demo "nộp essay → tự động có digest" sẽ **không hoạt động** (video unedited, không cắt ghép được) trừ khi chạy tay script pull song song — mà làm vậy tức là giả lập cái được quảng cáo là tự động, rủi ro lộ ra khi giám khảo tự kiểm tra (`gcloud pubsub subscriptions describe` mất 5 giây).

**Đã sửa (commit `87cb9b8`, `41c8f20`), 3 bước hạ tầng thật:**
1. Redeploy Cloud Run (đã làm chung với mục 2.2).
2. `gcloud pubsub subscriptions update class-aggregator-sub --push-endpoint=<url>/ --push-auth-service-account=eduagent-sa@... --push-auth-token-audience=<url>` — chuyển pull→push có OIDC.
3. Verify thật: publish 1 event thử (`event_id=verify-push-1787576568`, `class_id=c1`) vào topic `essay-evaluated` → Cloud Run Logging xác nhận `process_event()` xử lý đúng event này **mà không ai chạy tay pull script**.

**Tác dụng phụ đã quan sát (không phải lỗi mới, nhưng reviewer nên biết):** ngay khi chuyển pull→push, một **backlog message cũ** (đã publish trong 7 ngày retention nhưng chưa từng được ack vì trước đó chỉ chạy pull thủ công không liên tục) bị đẩy về dồn dập trong vài giây. Hệ thống xử lý hết, tự dừng, không lặp vô hạn — nhưng **cần reviewer/tác giả kiểm tra Firestore `class_analytics/digests` và Gmail Drafts folder** xem có draft/digest mới phát sinh ngoài ý muốn từ đợt backlog này không (tôi chưa tự kiểm tra bước này).

**Reviewer tự kiểm chứng:**
```bash
gcloud pubsub subscriptions describe class-aggregator-sub --format=json
# kỳ vọng: pushConfig.pushEndpoint + pushConfig.oidcToken khớp URL/service account đã khai báo

gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="eduagent-class-aggregator"' --freshness=30m
# kiểm tra có log "process_event" gần thời điểm publish thử, không có lỗi 500 lặp lại
```

### 2.4 Việc đã xác nhận KHÔNG phải vấn đề (đã kiểm tra kỹ trước khi kết luận)

- **Secrets hygiene:** `git ls-files | grep -Ei "secret|env|token|credential|key"` → chỉ có `.env.example` (placeholder). `secrets/` (4 file thật: SA key, OAuth token, client_secret) **không** được track. `.gitignore` phủ đúng.
- **Test suite:** `pytest tests/ -q -m "not e2e"` → 184/184 pass, không có test nào bị disable/skip để né lỗi.
- **CI pipeline:** `.github/workflows/ci.yml` chạy test suite + riêng 1 step gate `test_gmail_mcp_never_sends.py` (AST-based, không chỉ code review).
- **ĐỢT 7 code:** ban đầu tưởng chưa commit (372 dòng), nhưng khi kiểm tra lại `git log` thì tác giả đã tự commit (`224c458`) và push trước khi tôi kiểm tra lần 2 — không còn là blocker.

## 3. Việc CHƯA làm / cần reviewer hoặc tác giả tiếp tục kiểm tra

1. **Chưa chạy lại `scripts/doctor.py`** trên GCP thật sau khi đổi auth + subscription mode — nên chạy để xác nhận toàn bộ 6 check (Firestore/Pub/Sub/DLQ/Gmail/Sheets/Vertex AI) vẫn PASS, đặc biệt phần Pub/Sub giờ đã đổi cấu hình.
2. **Chưa kiểm tra Firestore `class_analytics/digests` + Gmail Drafts** xem backlog flush ở mục 2.3 có tạo digest/draft ngoài ý muốn không.
3. **Chưa deep-review logic thật của Metacognitive Self-Correction Loop** (`/api/debate/reflect`, `growth_bonus`, `breakthrough_count` trong `src/eduagent/api.py`/`firestore_memory.py`/`student_profile.py`) — tôi mới xác nhận test pass và tồn tại trên git, chưa đọc kỹ code để tìm bug logic.
4. **Phase 8 hoàn toàn chưa làm:** quay video (`docs/video_script.md` đã soạn sẵn kịch bản), chụp GCP console proof (`docs/gcp_evidence_checklist.md`), điền nốt các chỗ `[...]` trong `docs/devpost_submission_draft.md`, đăng blog/social bonus (`docs/blog_post_draft.md`, `docs/social_post_draft.md`), nộp bài.
5. **Chưa xác nhận phản hồi chính thức từ `cloudhackathons@google.com`** về câu hỏi eligibility tái sử dụng ý tưởng từ dự án CritiqAI cũ (mục 4 trong `TODO.md`, đang theo dõi song song, không block).

## 4. Câu hỏi gợi ý cho reviewer độc lập

- Đọc `README.md` mục 1 (Mandatory disclosure) và `PROJECT_WIKI.md` mục 9 — disclosure về CritiqAI có đủ rõ ràng, đúng tinh thần luật chơi không, hay cần diễn đạt lại?
- Đọc kỹ 14 ADR trong README §4 — có ADR nào mô tả quyết định nhưng **không có bằng chứng verify thật kèm theo** (chỉ là lý luận suông) không?
- Kiểm tra `eval/results/eval_report.md`/`.json` (15/15 pass) — tự chạy lại `scripts/run_eval_suite.py` xem có khớp không, hay là kết quả cũ đã stale.
- Đọc `src/eduagent/nodes/validator.py` — tự xác nhận thật sự không import `eduagent.llm` (đã được tác giả khẳng định qua nhiều đợt, nhưng đáng để double-check bằng `grep -r "import" src/eduagent/nodes/validator.py`).
- Xem toàn bộ diff giữa `224c458` (đầu ĐỢT 8) và `HEAD` hiện tại để nắm chính xác những gì phiên review này đã thay đổi: `git log 224c458..HEAD --oneline` và `git diff 224c458..HEAD --stat`.

## 5. Tóm tắt 1 dòng cho mỗi vấn đề

| # | Vấn đề | Mức độ | Trạng thái |
|---|---|---|---|
| 1 | ĐỢT 7 phình phạm vi (8 mục thay vì 3) | Tư vấn | Đã cắt theo khuyến nghị |
| 2 | README nói `--no-allow-unauthenticated` nhưng thực tế `--allow-unauthenticated`, không OIDC verify | 🔴 Blocker | ✅ Đã sửa + verify thật |
| 3 | `class-aggregator-sub` là pull mode thật, Tier 2 không tự trigger | 🔴 Blocker (nặng hơn #2) | ✅ Đã sửa + verify thật |
| 4 | Backlog message cũ bị flush khi chuyển push — chưa kiểm tra tác dụng phụ trên Firestore/Gmail | 🟡 Cần kiểm tra thêm | Chưa làm |
| 5 | `scripts/doctor.py` chưa chạy lại sau thay đổi | 🟡 Cần kiểm tra thêm | Chưa làm |
| 6 | Metacognitive Loop chưa được deep-review logic | 🟡 Cần kiểm tra thêm | Chưa làm |
| 7 | Phase 8 (video, GCP proof, nộp bài) | 🔴 30% điểm số | Chưa làm — việc thật của tác giả |
