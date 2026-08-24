# Phase 8 — Final Submission Checklist & Devpost Reminders

> [!IMPORTANT]
> Mọi nội dung văn bản (script, mô tả Devpost, blog, social post) đã soạn sẵn trong thư mục `docs/`. Đây là checklist các bước **THI CÔNG THỰC TẾ** cuối cùng — đều là hành động của bạn (quay video, upload, bấm nộp), không tự động hóa được. Hãy kiểm tra kỹ trước khi hạn chót đóng lại.

---

## 1. Quay video Demo (dùng `docs/video_script.md`)
- [ ] Chạy `python scripts/doctor.py` ngay trước khi quay để đảm bảo **6/6 Checks PASS**.
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
- [ ] Thêm đầy đủ thông tin: Hosted URL (`https://eduagent-class-aggregator-s6pcepa2cq-as.a.run.app`), test credentials (nếu có), danh sách Google SDK, Cloud Services, và tải lên file sơ đồ kiến trúc hệ thống (`Architecture diagram`).
- [ ] **Teammates:** Đảm bảo toàn bộ thành viên trong đội (nếu có) đã bấm chấp nhận lời mời tham gia trên Devpost (Unaccepted invite là nguyên nhân phổ biến nhất khiến thành viên bị rớt khỏi trang dự án khi nộp bài).

## 5. Tối ưu điểm thưởng (Bonus Stage Three - Tối đa +0.6đ)
- [ ] **Đăng bài viết kỹ thuật (Blog/Content):** Đăng bài viết từ `docs/blog_post_draft.md` lên Medium/Dev.to (hoặc LinkedIn Article) ở chế độ công khai, đính kèm câu khẳng định: *"Tôi viết bài này cho mục đích tham gia All Things Agentic Hackathon"*. (+0.2đ)
- [ ] **Đăng Social Post:** Đăng bài giới thiệu kèm link dự án lên LinkedIn (hoặc X) có gắn hashtag `#AllThingsAgenticHackathon`. (+0.2đ)
- [ ] **Google AI Models:** Xác nhận đã tích hợp bổ sung mô hình (đã dùng Gemini 3.5 Flash làm mặc định & Gemini 3.7 Flash làm heavy model). (+0.2đ)
- [ ] Copy link bài viết và bài đăng social điền vào form Devpost.

## 6. Khóa tài nguyên sau khi nộp (Deadline)
- [ ] **Nộp bài sớm ít nhất 1 ngày** trước thời hạn chót: **31/8 lúc 5:00 PM PT** (Tránh nghẽn mạng do lượng traffic nộp bài lớn).
- [ ] **TUYỆT ĐỐI KHÔNG sửa đổi** repository, video demo hoặc bất kỳ tài liệu liên kết nào sau khi hết hạn cho đến khi kết quả được công bố (Bất kỳ thay đổi nhỏ nào cũng có thể khiến dự án bị hủy tư cách tham gia).
- [ ] *Mẹo:* Nếu muốn tiếp tục code cải tiến sau deadline, hãy **Fork repository** ra một bản sao độc lập khác để phát triển, giữ nguyên repo đã nộp không chỉnh sửa.
