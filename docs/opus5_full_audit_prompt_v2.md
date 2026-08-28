# PROMPT — ĐỢT 24: Full-System Pre-Submission Audit (EduAgent)

> Copy toàn bộ nội dung dưới đây, paste cho Opus 5 chạy trong môi trường có quyền đọc repo thật +
> chạy shell + (nếu có) `gcloud`/`gh` (ví dụ Claude Code). File này được viết lại sau khi đọc
> `TODO.md` thật của dự án — **đã trải qua 23 đợt audit** (ĐỢT 1–22 đã thi công, ĐỢT 23 là task
> Gemma đã lên kế hoạch nhưng **chưa thực thi**). Đây không phải audit đầu tiên — nó là **ĐỢT 24**,
> và phải cư xử đúng như vậy: không dò lại cái đã đóng, không lặp lại sai lầm mà chính các đợt
> trước đã ghi lại làm bài học.

---

## BẠN ĐANG THAM GIA MỘT QUY TRÌNH ĐÃ CÓ TIỀN LỆ — ĐỌC PHẦN NÀY TRƯỚC KHI LÀM BẤT CỨ GÌ

`TODO.md` của dự án tự nó là nhật ký của 22 đợt self-audit trước, viết bởi các phiên AI trước
(bao gồm cả các "review ngoài" tự xưng, review lần 1/2/3, "Senior Staff Engineer Audit" giả lập).
Trước khi viết bất kỳ finding nào, **đọc toàn bộ `TODO.md`** (không chỉ đọc lướt) — nó nặng nhưng
là nguồn sự thật duy nhất về việc gì đã làm, việc gì đã bị từ chối và tại sao. Việc không đọc nó sẽ
khiến bạn lặp lại đúng những gì các đợt trước đã tốn hàng giờ để tìm ra rồi sửa.

### Các bài học đã trả giá đắt — coi đây là kính lúc để soi lại, không phải danh sách đã xong

Những class lỗi này đã xuất hiện **nhiều lần độc lập** qua các đợt khác nhau — nghĩa là chúng là xu
hướng lỗi tự nhiên của chính dự án này, không phải sự cố ngẫu nhiên. Ưu tiên săn lại đúng các class
này ở phần code/docs mới nhất hoặc chưa từng bị soi:

1. **"Tài liệu/comment mô tả một hành vi, code thật làm khác."** (ĐỢT 8, ĐỢT 12, ĐỢT 16 — lặp lại
   3 lần). Ví dụ kinh điển: docstring nói "prevents double-click race condition" trong khi hàm bên
   dưới là read-modify-write không transaction (ĐỢT 16, ADR-022 vs `firestore_session.py`).
2. **"Thêm cờ/bảng lưu trữ mới, nhưng đường đọc thật không dùng nó."** — bug ADR-015 (cache cục bộ
   làm mất lượt tranh biện đa-instance) và lặp lại y hệt kiểu ở `/reflect` (đặt cờ *trước* khi gọi
   LLM ≠ đặt cờ *atomic*). Khi thấy một "durable store" hay "flag" mới, luôn hỏi: đường đọc có thật
   sự phụ thuộc vào nó, hay chỉ được ghi mà không ai đọc?
3. **"Số liệu/bằng chứng gõ tay giả làm bằng chứng đo lường thật."** — Learning Outcome ban đầu là
   hằng số gõ tay (`+5.62`), 11 "Trace Attribute" trong `failure_matrix.md` không tồn tại trong code.
   Bất kỳ bảng số liệu nào trong `docs/` phải bị `grep` để xác nhận nguồn — nếu không grep ra được
   trong `src/`, đó là bằng chứng bịa.
4. **"README bị ghi đè, mất đính chính của đợt trước"** — đã xảy ra thật ở ĐỢT 17 (mất sửa ĐỢT 16).
   Không được tin README chỉ vì nó "đã được sửa ở đợt trước" — luôn đọc lại **hiện tại**, so với số
   liệu bạn tự chạy ra.
5. **"Review ngoài chấm điểm cao trên repo, không đo trên deployment thật"** — 2 lần review giả lập
   (ĐỢT 14, ĐỢT 15) cho điểm Architecture/Demo readiness cao trong khi `doctor.py` đang FAIL trên
   live revision thật. **Luôn đo trên Cloud Run đang chạy thật, không chỉ đọc repo.**
6. **"Review ngoài tự gán điểm số cho một hạng mục mà điều lệ không hề định lượng"** — xảy ra 2 lần
   (ĐỢT 14 và ĐỢT 15, cùng đề xuất thêm Gemma cho bonus không tồn tại theo cách hiểu khi đó). Ngược
   lại, ĐỢT 21 phát hiện điều lệ **thật sự** có ghi rõ +0.2/model tới +0.6 — tức: đừng tự suy đoán
   luật điểm, luôn trích nguyên văn điều lệ (`Rules`, `Judging_Criteria`) trước khi kết luận.

### Các mẫu quyết định đã bị từ chối — đừng đề xuất lại

- Tách microservice riêng cho push endpoint (ĐỢT 17): từ chối vì phình phạm vi sát deadline, không
  sửa lỗi thật nào.
- Thêm Cloud Armor / hạ tầng WAF: cùng lý do, ngoài phạm vi hackathon.
- Chèn Imagen/Veo/Lyria "để có ảnh đẹp" không phục vụ 2 câu hỏi chấm điểm của track (*synthesize/
  mutate data*, *messy unstructured input*): từ chối 2 lần (ĐỢT 14, ĐỢT 15). Imagen thậm chí
  **không tồn tại** trong project sau khi kiểm mọi location (ĐỢT 22).
- Viết lại timeline video theo đề xuất review ngoài: từ chối 2 lần vì làm mất khoảnh khắc
  "persona đổi vì nó nhớ" — câu trả lời trực tiếp cho track Collaborative Partner.
- Re-rank fallacy bằng LLM để "dùng thêm model": từ chối vì phá chính thuộc tính zero-LLM của
  ranking đang được đánh giá 5.0/5.0.

**Nếu review của bạn định đề xuất lại bất kỳ ý nào ở trên, phải nêu rõ lý do vì sao lần này khác —
không được lặp lại đề xuất mà không biết nó đã bị từ chối.**

---

## MỤC TIÊU

Tối đa hoá điểm số thật theo **điều lệ chính thức** (`Rules`, `Judging_Criteria`, `Requirements`,
`TRACKS`, `What_to_Submit_` trong project knowledge) — không theo trực giác "dự án hackathon tốt"
chung chung. Thang điểm xác nhận ở ĐỢT 21: **Final score 1–6** = Stage Two (1–5, chia Innovation
40% / Architecture 30% / Demo 30%) **+ tối đa 1.0 bonus** (blog +0.2, social +0.2, mỗi model Google
AI phụ +0.2 tới tối đa +0.6). Trần điểm dự án đang nhắm: **5.6/6.0** *(ĐỢT 27 đính chính: trước ghi 5.8 — sai số học; 5.0 + 0.2 blog + 0.2 social + 0.2 Gemma = 5.6)* (ĐỢT 22 — không lấy Veo/Lyria
vì không hợp lý cho app tranh luận văn nghị luận).

## TRẠNG THÁI ĐÃ BIẾT NGAY TRƯỚC ĐỢT 24 — verify lại còn đúng không, đừng dò lại từ số 0

Đây là danh sách các việc **còn mở** theo ghi nhận cuối `TODO.md` (ĐỢT 21–23). Việc đầu tiên của
bạn là **xác minh lại từng dòng bằng lệnh thật** (có thể ai đó đã làm xong từ lúc ghi tới giờ) —
sau đó mới đi tìm cái mới. Đừng viết lại các phát hiện này như thể bạn vừa tìm ra chúng.

| # | Việc | Trạng thái ghi nhận gần nhất | Cách verify lại |
|---|---|---|---|
| 1 | Repo GitHub đang PRIVATE, chưa mời `testing@devpost.com` / `cloudhackathons@google.com` | 🔴 Blocker Stage One (ĐỢT 21) | `gh repo view <owner>/<repo> --json visibility,isPrivate` + `gh api repos/<owner>/<repo>/invitations` |
| 2 | Có commit local chưa push (`ahead 1` tại thời điểm ĐỢT 21) | 🔴 Blocker — giám khảo đọc GitHub, không đọc máy | `git status -sb`, `git log origin/master..HEAD --oneline` |
| 3 | Ghi chú bonus sai (+0.4 thay vì tối đa +1.0) trong `submission_checklist.md` | Đã phát hiện sai ở ĐỢT 21, cần xác nhận đã sửa | `grep -n "Bonus Stage Three" docs/submission_checklist.md` — số phải khớp điều lệ, không phải +0.4 |
| 4 | ADR-028 (Gemma làm OCR lượt hai) — kế hoạch 10 bước ở ĐỢT 23, **checklist toàn bộ `[ ]`, chưa code** | Chưa thực thi | `grep -rniE "gemma" src/ scripts/` — nếu vẫn rỗng thì bonus model +0.2 chưa lấy được |
| 5 | `assets/architecture_diagram.png` chưa export (mục Stage One bắt buộc theo §6, không phải trang trí) | Chưa làm (ĐỢT 19 #9, nhắc lại ĐỢT 21 #4) | `ls -la assets/architecture_diagram.png` |
| 6 | Social media post (+0.2 bonus) chưa đăng, blog đã đăng | Đang làm | Kiểm URL trong `docs/submission_checklist.md` mục Bonus |
| 7 | Video demo chưa quay/upload | Chưa làm — phụ thuộc các mục trên | Kiểm URL YouTube trong `devpost_submission_draft.md` §7 |
| 8 | Diễn tập buổi quay + chạy `scripts/smoke_live.py` ngay trước khi quay | Chưa làm | — |

Nếu bất kỳ mục nào ở trên **đã được giải quyết** từ lúc TODO.md được cập nhật lần cuối tới giờ, ghi
rõ "ĐÃ XÁC NHẬN GIẢI QUYẾT — [bằng chứng]" thay vì bỏ qua im lặng, để đợt sau không phải dò lại.

## NHỮNG GÌ ĐÃ ĐÓNG — KHÔNG DÒ LẠI TRỪ KHI CÓ DẤU HIỆU CỤ THỂ NÓ BỊ HỎNG

ĐỢT 12–20 đã xử lý dứt điểm (kèm test + sabotage-verify ADR-019) các nhóm sau — coi là đóng, chỉ mở
lại nếu bạn tìm thấy bằng chứng cụ thể nó đã regressed (ví dụ: code đổi từ lúc đó, hoặc test bảo vệ
nó đang đỏ):

- Learning Outcome Evaluation và ADK Eval Suite Layer 4 — đã làm cho đo thật (ĐỢT 13).
- HMAC secret giáo viên hardcode, endpoint học sinh không xác thực, STRIDE claim rate-limit giả —
  đã sửa + có ADR-016/017/018 (ĐỢT 13).
- Secret Manager cho OAuth token Gmail/Sheets (ĐỢT 14, ADR-020).
- Metacognitive Self-Correction Loop (`growth_bonus` không kẹp biên, `/reflect` ghi vĩnh viễn kết
  quả bịa khi Vertex sập, `claim_reflection()` không atomic) — 8/8 mục ĐỢT 16 đã sửa, deploy, đo lại
  trên live (ĐỢT 16 thi công + phần "ĐỢT 16 — DEPLOY & KIỂM CHỨNG TRÊN LIVE").
- `doctor.py` không kiểm `push_config` — đã sửa (ĐỢT 16, mục 7).
- X-Forwarded-For lấy sai hop (đầu thay vì cuối) — đã vá + deploy + đo lại (ĐỢT 17, revision
  `00035-r9j`).
- Passcode giáo viên tách khỏi mặc định, dọn dữ liệu demo trùng tên — ĐỢT 18, 20.
- LICENSE: **không phải yêu cầu bắt buộc** theo điều lệ (đính chính ĐỢT 20) — không đề xuất lại
  việc này như một gap.

## QUY TẮC BẤT BIẾN KHI AUDIT (từ `TODO.md` mục 0 + rút ra từ 22 đợt)

1. **Verify bằng lệnh thật, không tin tài liệu.** Mọi số liệu bạn viết vào báo cáo phải kèm lệnh đã
   chạy + output thật. Nếu không chạy được (cần quyền GCP bạn không có), ghi rõ "KHÔNG VERIFY ĐƯỢC
   — cần lệnh X chạy bởi người có quyền" thay vì suy đoán.
2. **Không sửa test để nó pass.** Test đỏ là finding, không phải thứ để nới lỏng assertion.
3. **Mọi test mới phải được sabotage để chứng minh nó CÓ THỂ FAIL** (ADR-019, dùng nhất quán từ
   ĐỢT 16). Một test luôn xanh không bảo vệ gì cả.
4. **Không phình phạm vi.** Còn rất ít ngày tới deadline (31/08 17:00 PT) — bất kỳ đề xuất nào cần
   thêm service/dependency/feature mới phải tự trả lời: có phục vụ trực tiếp 1 trong 2 câu hỏi của
   track Collaborative Partner (synthesize/mutate data; xử lý messy unstructured input) không, và
   có đáng đánh đổi với rủi ro demo bị hỏng sát ngày quay không.
5. **Không viết đè nội dung đã chốt.** Slogan, câu thesis (*"we use AI to teach students how not to
   depend on AI"*), Golden Path video (~2:10 "persona đổi vì nó nhớ" là cao trào) đã được thống nhất
   qua nhiều đợt — không đề xuất viết lại trừ khi phát hiện nó sai sự thật.
6. **Giữ giọng văn tự phê bình candid đã có** trong các phần ĐỢT trước — không "làm mượt" các đoạn
   thừa nhận lỗi thành ngôn ngữ marketing.
7. **Đo trên deployment thật trước khi kết luận về Architecture/Demo readiness**, không chỉ đọc
   repo — đây là lỗi mà 2 review giả lập trước đã mắc.

## PHẠM VI ĐỢT 24 — ưu tiên theo thứ tự

### 1. Xác minh lại 8 mục "còn mở" ở bảng trên — bằng lệnh thật, không suy đoán

### 2. Săn lại 6 class lỗi đã liệt kê ở trên, tập trung vào phần code/docs mới nhất

Đặc biệt: bất kỳ thay đổi nào xảy ra **sau** thời điểm ĐỢT 22/23 được ghi (nếu `git log` cho thấy
commit mới hơn) chưa từng bị audit — đó là nơi có xác suất cao nhất còn lỗi các class 1–4.

### 3. Đối chiếu lại toàn bộ số liệu định lượng trong 4 file nộp bài chính

`devpost_submission_draft.md`, `README.md`, `blog_post_draft.md`, `docs/social_post_draft.md` (nếu
đã có nội dung) — dựng bảng: mỗi con số → VERIFIED (kèm lệnh) / STALE / SIMULATED-KHÔNG-DISCLOSE /
KHÔNG-VERIFY-ĐƯỢC. `trace_evidence.md` đã tự nhận latency là simulated — bất kỳ chỗ nào trích lại số
đó ở nơi khác mà không kèm disclaimer là finding.

### 4. Kiểm tra sự nhất quán 3 chiều: điều lệ ↔ tài liệu nộp bài ↔ code/deployment thật

Không chỉ kiểm tra tài liệu tự nhất quán với nhau (đã làm nhiều đợt) — kiểm tra cả 3 chiều cùng lúc
cho từng yêu cầu ở `Rules` §6, đặc biệt các mục chưa từng bị đối chiếu 3 chiều: "Other data sources
used" (đã có chưa, đúng vị trí Devpost form chưa), Mandatory Disclosure CritiqAI (đã ở đúng cả 2 nơi
— `eligibility_statement.md` và "How we built it" — chưa, hay chỉ 1 nơi).

### 5. Functionality thật (Innovation 40% — trục nặng nhất)

Với từng agent trong pipeline (Intake → Sanitizer → Summarizer → Persona Selector → Debate Loop →
Challenge Validator → Cognitive Scorer/Mutator → Class Aggregator → Teacher Digest), xác nhận qua
trace code thật (không phải đọc mô tả) rằng nó làm đúng như narrative — đặc biệt lời hứa cốt lõi
"tranh biện chứ không đưa đáp án" không có đường vòng nào tự trả lời trực tiếp.

### 6. Reproducibility

Nếu môi trường cho phép: venv sạch → `pip install -r requirements.txt` → `pytest -q -m "not e2e"` →
`python scripts/doctor.py`. So số test/PASS-WARN-FAIL với con số đang in trong README — lệch là
finding (README từng bị ghi đè mất đính chính, đây là lý do phải đo lại chứ không tin số cũ).

## OUTPUT — ghi vào `TODO.md`, đúng format các đợt trước, nối tiếp làm **ĐỢT 24**

Thêm một section mới ở cuối `TODO.md`:

```markdown
## ĐỢT 24 — [tiêu đề mô tả trọng tâm đợt này] (2026-08-2X)

> [2-3 câu bối cảnh: kế thừa gì từ ĐỢT 21-23, trọng tâm đợt này khác gì]

### Xác minh lại các mục "còn mở" từ ĐỢT 21-23
[bảng: # | việc | trạng thái ghi nhận | kết quả verify hôm nay | lệnh dùng]

### Phát hiện mới — xếp theo mức ảnh hưởng điểm số
#### [🔴/🟡/🟢] — [tiêu đề 1 dòng]
- **Trục điều lệ ảnh hưởng:** [Innovation 40% / Architecture 30% / Demo 30% / Bonus / Eligibility]
- **Vị trí:** `path:line`
- **Phát hiện:** [claim vs thực tế, kèm lệnh verify + output]
- **Vì sao mất điểm:** [bám điều lệ, không phải cảm tính]
- **Đề xuất:** [cụ thể, làm được trước deadline] — hoặc **Từ chối, vì:** [nếu trùng mẫu đã bị từ chối]
- **Effort:** S/M/L

### Bảng số liệu đã đối chiếu
| Claim | File nguồn | Trạng thái | Cách verify |

### TỔNG KẾT ĐỢT 24
[bảng ngắn: X Blocker mở, Y ngày tới deadline, revision live hiện tại, việc ưu tiên #1 nếu chỉ chọn 1]
```

Sắp xếp finding theo mức ảnh hưởng điểm thật (trọng số 40/30/30 + bonus), không theo độ dễ sửa.
Việc dễ sửa nhưng ảnh hưởng Eligibility (Stage One pass/fail) luôn đứng đầu bảng — mất Stage One thì
mọi điểm số khác vô nghĩa.

## KIỂM TRA CUỐI CÙNG TRƯỚC KHI CHỐT ĐỢT 24

Trước khi ghi dòng cuối vào `TODO.md`, tự hỏi: *nếu bị hỏi "chứng minh" ngay bây giờ cho từng con số
và từng claim "đã xác nhận" trong báo cáo này, mình có lệnh thật để show không?* Nếu không, hạ mức
xuống "KHÔNG VERIFY ĐƯỢC" thay vì để nó trôi qua như một kết luận chắc chắn — đây chính là tiêu
chuẩn mà 22 đợt trước đã tự đặt ra cho chính mình, và là lý do dự án này khác các review hời hợt đã
bị từ chối trước đó.
