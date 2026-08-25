# Phase 8 — Final Submission Checklist & Devpost Reminders

> [!IMPORTANT]
> Mọi nội dung văn bản (script, mô tả Devpost, blog, social post) đã soạn sẵn trong thư mục `docs/`. Đây là checklist các bước **THI CÔNG THỰC TẾ** cuối cùng — đều là hành động của bạn (quay video, upload, bấm nộp), không tự động hóa được. Hãy kiểm tra kỹ trước khi hạn chót đóng lại.

---

## 1. Quay video Demo (dùng `docs/video_script.md`)
- [ ] Chạy `python scripts/doctor.py` ngay trước khi quay. Hiện có **10 check** (ĐỢT 13 thêm `Session signing secret` + `Firestore TTL policy`; ĐỢT 14 thêm `No plaintext credentials on Cloud Run`). Kỳ vọng: **0 FAIL**. Check `Session signing secret` báo **WARN khi chạy local là ĐÚNG** (local dùng khoá default có chủ đích) — nó chỉ phải PASS trên revision Cloud Run đã deploy.
- [ ] 🔴 **Trước khi quay: đã REDEPLOY Cloud Run chưa?** Toàn bộ bản sửa bảo mật ĐỢT 13 (ADR-016/017/018) chỉ có hiệu lực sau redeploy. Nếu chưa, service live vẫn ký token bằng khoá công khai trong repo và 5 endpoint học sinh vẫn không có xác thực — đúng thứ giám khảo có thể tự thử. Chạy `python scripts/deploy_to_cloud_run.py` (đã có preflight kiểm tra **cả 3** secret) hoặc `deploy.txt` STEP 1 → STEP 3 → STEP 4.
- [ ] 🔴 **Sau redeploy, verify không còn credential cleartext:** `python scripts/doctor.py` → check *"No plaintext credentials on Cloud Run"* phải **PASS**. Hiện đang **FAIL** vì revision live vẫn để `GMAIL_COMPOSE_TOKEN_JSON` và `SHEETS_TOKEN_JSON` ở dạng plaintext (ĐỢT 14 / ADR-020).
- [ ] 🟡 **ROTATE 2 token OAuth** (Gmail + Sheets) vì chúng đã từng bị phơi dưới dạng env var cleartext — chuyển sang Secret Manager là cần nhưng chưa đủ, giá trị cũ vẫn nên bị vô hiệu. Xem hướng dẫn rotate ở cuối `deploy.txt` STEP 1.
- [ ] 🟢 **Demo: set `EDUAGENT_DIGEST_DEBOUNCE_SECONDS=0`** trước khi quay (mặc định 120s sẽ coalesce digest → Gmail draft **không xuất hiện** đúng lúc cần show). Lệnh cụ thể ở README §3.10(c). Nhớ đặt lại 120 sau khi quay.
- [ ] Diễn tập toàn bộ kịch bản **ít nhất 2 lần** trước khi quay thật (kiểm soát timing ≤ 4:00, tránh lỗi phát sinh).
- [ ] Quay **live, không cắt ghép**, bảo đảm video thể hiện rõ:
  - Vấn đề & Giá trị giải pháp.
  - Tên Gemini model và agent framework đã dùng (Google ADK2).
  - Agent thực tế chạy: Log terminal, Firestore update, Gmail draft được tạo.
  - Bằng chứng chạy trên Google Cloud (Console, Cloud Run dashboard, URL `.run.app`).
- [ ] Kiểm tra không để lộ bất kỳ API keys, JSON key file hoặc dữ liệu nhạy cảm nào trên màn hình khi quay.

## 2. Upload Video
- [ ] Upload lên YouTube hoặc Vimeo ở chế độ **Public** (không dùng Private hoặc Unlisted vì giám khảo sẽ không truy cập được).
- [ ] Đảm bảo ngôn ngữ là tiếng Anh hoặc có phụ đề tiếng Anh chuẩn.
- [ ] Copy link video điền vào mục `7. Video demo link` trong `docs/devpost_submission_draft.md`.

## 3. Chuẩn bị Repository trước khi nộp
- [ ] `git push` toàn bộ các commit lên remote repository.
- [ ] Kiểm tra tính riêng tư của repo:
  - Nếu là **Public**: Thử mở bằng cửa sổ Incognito để đảm bảo hiển thị đúng.
  - Nếu là **Private**: Bắt buộc phải share quyền cộng tác viên cho: `testing@devpost.com` và `cloudhackathons@google.com`.
- [ ] Chạy thử quy trình cài đặt từ máy sạch theo hướng dẫn trong `README.md` để đảm bảo tính tái lập 100%.

## 4. Nộp bài trên Devpost (Sử dụng `docs/devpost_submission_draft.md`)
- [ ] Copy nội dung đã soạn sẵn từ `docs/devpost_submission_draft.md` vào form đăng ký.
- [ ] Điền đầy đủ các thông tin thực tế vào các chỗ trống `[...]` (Link video, link repo, quốc gia, ngày bắt đầu `08-03-26`).
- [ ] Xác minh 2 thông tin quan trọng nhất để tránh bị loại (disqualification):
  - **Mandatory Disclosure:** Giữ đúng nguyên văn khai báo bản quyền.
  - **Category/Track:** Chọn chính xác duy nhất track **Collaborative Partner**.
- [ ] Thêm đầy đủ thông tin: Hosted URL (`https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app`), test credentials (nếu có), danh sách Google SDK, Cloud Services, và tải lên file sơ đồ kiến trúc hệ thống (`Architecture diagram`).
- [ ] **Teammates:** Đảm bảo toàn bộ thành viên trong đội (nếu có) đã bấm chấp nhận lời mời tham gia trên Devpost (Unaccepted invite là nguyên nhân phổ biến nhất khiến thành viên bị rớt khỏi trang dự án khi nộp bài).

## 5. Tối ưu điểm thưởng (Bonus Stage Three — **+0.4đ định lượng được**)

> ⚠️ **Sửa lại con số (ĐỢT 14):** mục này từng ghi "tối đa +0.6đ" bằng cách tính thêm +0.2 cho "Google AI Models". Rules (xem `PROJECT_WIKI.md` mục 4, Stage Three) chỉ nêu **hai** hạng mục có điểm cụ thể — blog **+0.2** và social post **+0.2** — còn "tích hợp thêm Google AI model khác (Gemma, Veo, Lyria)" được xếp vào *Optional Developer Contributions* **không kèm số điểm**. Đừng tự cộng điểm cho mình trong tài liệu nội bộ; nó dẫn tới kỳ vọng sai khi quyết định cắt việc gì.
- [ ] **Đăng bài viết kỹ thuật (Blog/Content):** Đăng bài viết từ `docs/blog_post_draft.md` lên Medium/Dev.to (hoặc LinkedIn Article) ở chế độ công khai, đính kèm câu khẳng định: *"Tôi viết bài này cho mục đích tham gia All Things Agentic Hackathon"*. (+0.2đ)
- [ ] **Đăng Social Post:** Đăng bài giới thiệu kèm link dự án lên LinkedIn (hoặc X) có gắn hashtag `#AllThingsAgenticHackathon`. (+0.2đ)
- [ ] *(Không tính điểm — chỉ để khai báo chính xác trên Devpost)* **Google AI Models đang dùng:** `gemini-3.5-flash` (mặc định) và `gemini-3.7-flash` (heavy model, cho Teacher Digest). **Đây là 2 biến thể của CÙNG họ Gemini, KHÔNG phải "tích hợp thêm một mô hình Google AI khác"** theo nghĩa Gemma/Veo/Lyria mà rules nêu — nên không claim +0.2 ở đây. Khai đúng 2 model ID này trong phần "technologies used" (ADR-002 giải thích vì sao không có Pro-tier: `gemini-3.5-pro` không tồn tại trong project/region này).
- [ ] Copy link bài viết và bài đăng social điền vào form Devpost.

## 6. Khóa tài nguyên sau khi nộp (Deadline)
- [ ] **Nộp bài sớm ít nhất 1 ngày** trước thời hạn chót: **31/8 lúc 5:00 PM PT** (Tránh nghẽn mạng do lượng traffic nộp bài lớn).
- [ ] **TUYỆT ĐỐI KHÔNG sửa đổi** repository, video demo hoặc bất kỳ tài liệu liên kết nào sau khi hết hạn cho đến khi kết quả được công bố (Bất kỳ thay đổi nhỏ nào cũng có thể khiến dự án bị hủy tư cách tham gia).
- [ ] *Mẹo:* Nếu muốn tiếp tục code cải tiến sau deadline, hãy **Fork repository** ra một bản sao độc lập khác để phát triển, giữ nguyên repo đã nộp không chỉnh sửa.
