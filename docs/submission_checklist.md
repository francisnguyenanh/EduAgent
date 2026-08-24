# Phase 8 — Final Submission Checklist

> Mọi nội dung văn bản (script, mô tả Devpost, blog, social post) đã soạn sẵn trong `docs/`. Đây là checklist các bước THI CÔNG THẬT còn lại — đều là hành động của bạn (quay video, upload, bấm nộp), tôi không tự làm thay được.

## 1. Quay video (dùng `docs/video_script.md`)

- [ ] Chạy `python scripts/doctor.py` ngay trước khi quay — 6/6 PASS.
- [ ] Diễn tập toàn bộ kịch bản **ít nhất 2 lần** trước khi quay thật (timing, tránh lỗi bất ngờ).
- [ ] Quay **live, không cắt ghép**, ≤ 4:00 cho phần nội dung chính giám khảo chấm.
- [ ] Kiểm tra không lộ bất kỳ secret/token nào trên màn hình khi quay (API key, service-account JSON, `.env`).

## 2. Upload video

- [ ] Upload YouTube/Vimeo, chế độ **Public** (không Unlisted/Private).
- [ ] Tiếng Anh hoặc có phụ đề tiếng Anh.
- [ ] Copy link vào `docs/devpost_submission_draft.md` mục Links.

## 3. Chuẩn bị repo trước khi nộp

- [ ] `git push` toàn bộ commit lên remote (hiện tại local đang chậm hơn `origin/master` — kiểm tra `git status`).
- [ ] Nếu repo **private**: share quyền đọc cho `testing@devpost.com` và `cloudhackathons@google.com`.
- [ ] Test spin-up từ máy sạch/incognito 1 lần cuối theo README.md mục 3 (mục còn nợ trong Phase 7).
- [ ] Quét lại `git log --all` lần cuối trước khi nộp (đã làm ở Phase 7, làm lại nếu có commit mới sau đó).

## 4. Nộp Devpost

- [ ] Copy nội dung từ `docs/devpost_submission_draft.md` vào form, điền các chỗ `[...]` (link video, link repo, link hosted URL).
- [ ] Kiểm tra lại 2 chỗ dễ sai: **Mandatory Disclosure** đúng nguyên văn, **Track** ghi đúng "Collaborative Partner".
- [ ] Đính kèm đầy đủ: repo, video, hosted URL, architecture diagram (đã có trong README).

## 5. Bonus Stage Three (+0.4đ, không bắt buộc nhưng nên làm)

- [ ] Đăng blog từ `docs/blog_post_draft.md` lên Medium/Dev.to, để **public**, ghi rõ làm cho hackathon này. (+0.2đ)
- [ ] Đăng social post từ `docs/social_post_draft.md` lên X/LinkedIn kèm `#AllThingsAgenticHackathon` + link demo. (+0.2đ)
- [ ] Copy 2 link này (blog + social post) vào Devpost submission nếu form có mục riêng cho bonus.

## 6. Deadline

- [ ] **Nộp sớm ít nhất 1 ngày** trước 31/8 17:00 PT.
- [ ] Sau deadline: **tuyệt đối không sửa** repo/video/link nữa.

---

*File tham khảo liên quan: `docs/video_script.md`, `docs/devpost_submission_draft.md`, `docs/blog_post_draft.md`, `docs/social_post_draft.md`, `docs/gcp_evidence_checklist.md`.*
