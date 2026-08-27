# Quy trình Cập nhật Tài liệu (Documentation Update Rule)

Giao thức bắt buộc cho **code agent** khi được yêu cầu *"cập nhật tài liệu cho khớp code"* trước khi
nộp bài.

> **Đọc mục 0 trước.** Ba quy tắc ở đó quan trọng hơn toàn bộ checklist bên dưới. Dự án này đã trải
> qua 25 đợt self-audit, và **mọi lỗi tài liệu nghiêm trọng từng gặp đều là vi phạm một trong ba quy
> tắc đó** — không phải do thiếu checklist.

---

## 0. BA QUY TẮC BẤT BIẾN — vi phạm là hỏng bài nộp

### 0.1 KHÔNG BAO GIỜ sửa tay file được sinh tự động

Ba file trong `docs/` **là artifact do script sinh ra**, không phải văn bản soạn tay:

| File | Sinh bởi |
|---|---|
| `docs/learning_outcome_eval.md` | `scripts/evaluate_learning_outcomes.py` |
| `docs/experiment_memory_ab.md` | `scripts/experiment_memory_ab.py` |
| `docs/trace_evidence.md` | `scripts/export_trace_evidence.py` |

Cùng nhóm, ngoài `docs/`: `eval/results/*.md`, `eval/results/*.json`.

**Muốn số mới thì CHẠY LẠI SCRIPT**, không gõ tay. Gõ một con số vào báo cáo đo lường chính là lỗi
`+5.62` mà ĐỢT 12–13 mất trọn hai đợt để phát hiện và sửa: một hằng số gõ tay được trình bày như kết
quả đo *"independent re-scoring"*, trong khi không có bài luận nào được chấm và không có model nào
được gọi.

⚠️ `eval/results/learning_outcome_measured.json` là **phụ thuộc bắt buộc** của eval suite Layer 4.
Chạy lại script sẽ ghi đè nó. Nếu chỉ chạy để thử nghiệm, phải
`git checkout -- eval/results/ docs/learning_outcome_eval.md` ngay sau đó. Đã xảy ra thật ở ĐỢT 24:
một lần Ctrl-C đúng chỗ để lại artifact ở kết quả benchmark, và ba tài liệu nộp bài suýt trích một
con số không còn tồn tại.

### 0.2 Doc và code mâu thuẫn → DỪNG LẠI, BÁO CÁO. Không tự chọn bên.

**Code không mặc nhiên đúng.** Đôi khi tài liệu mô tả hành vi *đúng* mà code chưa làm được — khi đó
phải sửa **code**, không phải sửa doc cho khớp bug.

Ca thật, ĐỢT 16: docstring ghi *"prevents double-click race condition"* trong khi hàm bên dưới là
read-modify-write **không** transaction. Nếu agent lúc đó "cập nhật doc cho khớp code", nó đã **xoá
mất một bug thật** và biến một lỗi bảo mật thành tài liệu chính xác.

Khi phát hiện lệch, viết ra: *claim trong doc là gì · code thật làm gì · lệnh chứng minh · đề xuất
sửa bên nào* — rồi **hỏi người dùng**. Đây là điểm dừng bắt buộc, không phải gợi ý.

### 0.3 Mọi con số viết vào tài liệu phải kèm lệnh đã chạy ra nó

Không chép số từ file khác. Không suy ra. **Chạy, đọc output, viết đúng cái đọc được.**

Nếu không chạy được (cần quyền GCP không có), ghi thẳng **"KHÔNG VERIFY ĐƯỢC — cần lệnh X"** thay vì
để nó trôi qua như một kết luận chắc chắn.

Áp dụng cả cho lệnh mà bạn *viết vào* tài liệu như bằng chứng: phải chạy thử lệnh đó trước. ĐỢT 24
suýt để lọt câu *"verifiable with `git log --all --name-only | grep -i critq` → returns nothing"* vào
`eligibility_statement.md`; chạy thử thì nó **không** rỗng (`--name-only` in cả commit message), lệnh
đúng phải là `git rev-list --all --objects | grep -i critq`.

---

## 1. Phân tầng tài liệu — sửa cái nào, và vì sao

Tiêu chí khách quan: **giám khảo có với tới file đó được không.** Kiểm bằng
`grep -c "<tên file>" README.md docs/devpost_submission_draft.md`.

### TẦNG 1 — Nội dung nộp bài thật (bắt buộc đồng bộ, ưu tiên cao nhất)

| File | Vì sao |
|---|---|
| **`README.md`** *(gốc repo, KHÔNG nằm trong `docs/`)* | Điều lệ chấm trực tiếp: *"Does the **public GitHub repository** feature a clean architecture diagram and reproducible setup instructions?"* (`overview/rule.txt:203`). Chứa Mandatory Disclosure, bảng ADR, số test/coverage, bằng chứng OCR |
| **`docs/devpost_submission_draft.md`** | Văn bản dán thẳng vào form Devpost. Chứa khai báo model (quyết định bonus +0.2/model), "other data sources", Mandatory Disclosure |

> ⚠️ **`README.md` ở gốc repo, không phải trong `docs/`.** Quy trình nào giới hạn phạm vi ở `docs/`
> sẽ bỏ sót đúng file quan trọng nhất. ĐỢT 17 đã ghi đè README và làm **mất đính chính của ĐỢT 16** —
> đây không phải rủi ro giả định.

### TẦNG 2 — Phục vụ quay video & lấy điểm bonus (đồng bộ khi liên quan)

| File | Đồng bộ khi |
|---|---|
| `docs/video_script.md` | Đổi độ trễ, đổi luồng demo, đổi passcode/dữ liệu hiện trên màn hình, đổi revision live |
| `docs/submission_checklist.md` | Đổi trạng thái các mục nộp bài, số liệu `doctor.py`/`smoke_live.py`, trạng thái bonus |
| `docs/blog_post_draft.md`, `docs/social_post_draft.md` | **Chỉ khi CHƯA đăng.** Đã đăng rồi thì file draft là bản ghi lịch sử — sửa nó không đổi được bài đã public, và làm draft lệch bài thật còn tệ hơn để nguyên |
| `docs/For_notebookLM.md` | Đổi kiến trúc, node, ADR. *(ĐỢT 24 đã bỏ sót file này khi thi công ADR-028 — nó mô tả cơ chế OCR cũ suốt một ngày)* |

### TẦNG 3 — Bằng chứng kỹ thuật, README trỏ tới (đồng bộ khi logic liên quan đổi)

Cập nhật 2026-08-28: bốn file này **từng mồ côi** — `README.md` và `devpost_submission_draft.md`
không nhắc tới dòng nào, nên bằng chứng Architecture 30% mạnh nhất của dự án không có đường nào để
giám khảo tới. Đã xử lý bằng **teaser 2–4 dòng inline trong README §6 + link**, thay vì chèn nguyên
nội dung (bảng của chúng rộng 1376–1644 ký tự, gấp 5–6 lần bảng rộng nhất của README, và sẽ làm
README phồng 58%).

| File | Trỏ từ | Đồng bộ khi |
|---|---|---|
| `docs/failure_matrix.md` | README §6 | Đổi đường degrade/fallback/retry, thêm bớt component phụ thuộc ngoài. **Số 20 component trong teaser README phải khớp** — đếm bằng `grep -cE "^\| \*\*[0-9]+[a-z]?\*\*" docs/failure_matrix.md` |
| `docs/data_lifecycle_and_privacy.md` | README §6 | Đổi cách/nơi lưu dữ liệu, TTL, STRIDE |
| `docs/trace_evidence.md` | README §6 **kèm nhãn cảnh báo** | Đổi cấu trúc span/`@traced_node`. ⚠️ Artifact sinh tự động (mục 0.1) **và** latency là **simulated** — mọi chỗ trích nó **bắt buộc** kèm câu đính chính, nếu không là tự tạo overclaim |
| `docs/eligibility_statement.md` | *(chưa trỏ — không cần)* | Nội dung cốt lõi (Mandatory Disclosure) đã nằm ở README §1 **và** Devpost. File này là bản mở rộng; chỉ cần **không mâu thuẫn** với hai nơi kia |

**Quy tắc teaser:** khi sửa các file này, kiểm luôn teaser tương ứng trong README §6 — teaser chứa
**kết luận** (con số, ngoại lệ đáng nhớ) chứ không chỉ một dòng "xem thêm", vì phần lớn giám khảo sẽ
không bấm link. Teaser sai lệch còn tệ hơn không có teaser.

### TẦNG 4 — Vận hành & hiện vật lịch sử (KHÔNG đồng bộ)

| File | Bản chất |
|---|---|
| `docs/gcp_evidence_checklist.md`, `docs/gcp_screenshot_guide.md` | Hướng dẫn thao tác chụp bằng chứng. Chỉ sửa khi đổi tên tài nguyên GCP |
| `docs/review_handoff_dot8.md` | Bàn giao ĐỢT 8. **Hiện vật lịch sử — đừng đụng** |
| `docs/opus5_full_audit_prompt_v2.md` | Prompt audit một lần của ĐỢT 24. **Hiện vật lịch sử — đừng đụng.** *(Không nhầm với system prompt trong code: những cái đó nằm ở `src/eduagent/nodes/*.py::_SYSTEM_INSTRUCTION`)* |
| `docs/DOC_UPDATE_RULE.md` | Chính file này |
| `TODO.md`, `overview/PROJECT_WIKI.md` | **Nhật ký 25 đợt audit — CHỈ ĐƯỢC NỐI THÊM, không sửa/xoá phần cũ.** Là nguồn sự thật về việc gì đã làm và việc gì đã bị từ chối |

---

## 2. Bảng ánh xạ: đổi code gì → sửa file nào

Kiến trúc thật: **Google ADK2** (`google.adk`, 15 điểm dùng trong `src/`). Dự án **không** dùng
LangGraph — đừng đi tìm.

| Thay đổi trong code | File Tầng 1 | File Tầng 2 | Ghi chú |
|---|---|---|---|
| Thêm/bỏ node ADK (`src/eduagent/nodes/`, `graph/tier1_pipeline.py`) | README §2 mermaid + bảng ADR | `For_notebookLM.md` bảng node | Sửa **cả** mermaid lẫn phần mô tả chữ |
| Đổi model (`config.py::GEMINI`) | README badge + Devpost §8 *"Which Google AI Models"* | `video_script.md` (đọc tên model trên camera) | Devpost §8 là chỗ tính **bonus +0.2/model** |
| Đổi ngưỡng / hằng số (`config.py`, `nodes/*.py`) | README ADR liên quan | `failure_matrix.md` (Tầng 3) | Ngưỡng đã hiệu chỉnh phải kèm **phân bố đo được** |
| Thêm ADR mới | README: **dòng bảng + block chi tiết + dòng lịch sử ADR** (3 chỗ) | `For_notebookLM.md` mục ADR | Ba chỗ, thiếu một là lệch |
| Đổi đường degrade/retry | README §threat model | `failure_matrix.md` | |
| Thêm/bớt test | README §Test Suite Coverage (số test + coverage) | `submission_checklist.md` | **Phải chạy lại**, không cộng nhẩm |
| Đổi độ trễ | — | `video_script.md` bảng latency **+ ngân sách beat** | Beat OCR nằm trong video 240s |
| Đổi passcode/route/dữ liệu demo | README §Judge Quickstart + Devpost §5, §8 | `video_script.md` §Credentials | Nhập sai trên camera là hỏng take |
| Đổi dịch vụ GCP / cách lưu dữ liệu | Devpost §8 *"Which Google Cloud Service(s)"* | `data_lifecycle_and_privacy.md` (Tầng 3) | |

---

## 3. Quy trình thực thi

1. **Xác định thay đổi thật.** `git diff` / `git status`. Đọc code đã đổi — **không** hỏi người dùng
   tóm tắt rồi tin theo.
2. **Đo lại, đừng chép.** Chạy những lệnh mà con số trong tài liệu đến từ đó:
   ```bash
   pytest -q -m "not e2e"                      # số test
   pytest --cov=src/eduagent --cov-report=term -q   # coverage (README dùng bản CÓ e2e)
   python scripts/run_eval_suite.py --strict   # 50/50
   python scripts/doctor.py                    # PASS/WARN/FAIL
   python scripts/smoke_live.py                # deployment thật
   ```
3. **Phân tích tác động** theo bảng mục 2. Liệt kê file sẽ sửa **trước khi** sửa.
4. **Sửa**, tuân thủ:
   - **Giữ nguyên giọng văn**, nhất là `blog_post_draft.md` và `video_script.md`.
   - **Giữ giọng tự phê bình candid.** Các đoạn thừa nhận lỗi (12 eval case chết, `+5.62` bịa,
     secret lộ cleartext) là **tài sản**, không phải khuyết điểm — chúng là bằng chứng của kỷ luật
     kỹ thuật. **KHÔNG "làm mượt" thành ngôn ngữ marketing.**
   - **Không overclaim.** ĐỢT 11 dành trọn một đợt để gỡ overclaim. Chữ *"chỉ"*, *"luôn luôn"*,
     *"không bao giờ"* phải grep ra được bằng chứng trong `src/`, nếu không thì bỏ.
   - **Không viết đè nội dung đã chốt**: slogan, câu thesis *"we use AI to teach students how not to
     depend on AI"*, cao trào video *"persona đổi vì nó nhớ"*. Đã thống nhất qua nhiều đợt.
   - Số liệu nào không tái tạo được thì ghi **"KHÔNG VERIFY ĐƯỢC"**, đừng bỏ trống cũng đừng đoán.
5. **Kiểm chứng trước khi báo cáo** — bước này bắt buộc, không được bỏ:
   ```bash
   pytest -q -m "not e2e"                   # không được đỏ thêm
   python scripts/run_eval_suite.py --strict
   git status -s eval/ docs/learning_outcome_eval.md docs/experiment_memory_ab.md docs/trace_evidence.md
   #  ^ PHẢI TRỐNG. Có thay đổi = đã lỡ sửa tay artifact sinh tự động (mục 0.1)
   ```
   Sau đó **grep ngược từng con số vừa viết** để chắc nó tồn tại thật trong `src/` hoặc trong output
   của một script.
6. **Báo cáo**: file nào, sửa gì, **lệnh nào chứng minh**. Nêu riêng những chỗ đã áp dụng mục 0.2
   (dừng lại vì doc-code mâu thuẫn) và những chỗ ghi "KHÔNG VERIFY ĐƯỢC".

---

## 4. Tự kiểm trước khi chốt

- [ ] Có con số nào tôi **chép lại** thay vì chạy ra không?
- [ ] `git status -s eval/` có trống không? (nếu không → đã sửa tay artifact)
- [ ] Có chỗ nào doc-code lệch mà tôi **tự chọn bên** thay vì báo cáo không?
- [ ] `README.md` — file ngoài `docs/` — đã được rà chưa?
- [ ] Có đoạn thừa nhận lỗi nào bị tôi "làm mượt" đi không?
- [ ] Nếu bị hỏi *"chứng minh ngay"* cho từng claim vừa viết, tôi có lệnh thật để show không?

---

**[SYSTEM PROMPT INSTRUCTION FOR AI AGENT]**
*When asked to update documentation for this project, treat Section 0 as hard constraints, not
guidance. Never hand-edit the three script-generated reports in `docs/` or anything under
`eval/results/`. When documentation and code disagree, STOP and report — do not assume the code is
correct. Every number you write must come from a command you actually ran in this session. The
project's README.md lives at the repository root, outside `docs/`, and is the highest-priority
document.*
