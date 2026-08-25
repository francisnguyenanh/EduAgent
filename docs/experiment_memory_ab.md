# Memory A/B Experiment: Empirical Proof of Pedagogical Adaptation

> **Evaluation Hypothesis:** Trí nhớ dài hạn (Long-Term Memory) không chỉ lưu trữ dữ liệu thụ động, mà **trực tiếp thay đổi quyết định sư phạm**, triệt tiêu can thiệp lặp vô ích và tiêm ngữ cảnh lịch sử vào cuộc tranh biện.

---

## 1. Kết Quả Định Lượng Tổng Hợp (Summary Metrics)

| Chỉ số Đánh Giá (Metric) | Nhánh A: Stateless Baseline (Không Trí Nhớ) | Nhánh B: eduagent (Trí Nhớ Dài Hạn) | Ý Nghĩa Sư Phạm |
|---|:---:|:---:|---|
| **Chuỗi Persona Can Thiệp** | `skeptic → skeptic → nitpicker` | `skeptic → expander → nitpicker` | Nhánh B tự động thích ứng luân phiên persona khi phát hiện điểm yếu cũ |
| **Số lần can thiệp lặp bế tắc (Repeated Stagnant Interventions)** | **1 lần** (Lặp Skeptic) | **0 lần** (0% lặp) | Loại bỏ tình trạng hỏi cùng 1 góc nhìn khiến học sinh nản lòng |
| **Tiêm Ngữ Cảnh Điểm Yếu Cũ vào Prompt** | **0/3 bài** (0%) | **2/3 bài** (100% khi có lịch sử) | Agent nhắc nhở học sinh về lỗi đã gặp ở bài trước |
| **Nhận diện Xu hướng Điểm số (Score Trend)** | `insufficient_data` (Mù lịch sử) | `improving` (Nhận diện chính xác) | Cung cấp dữ liệu cho giáo viên can thiệp kịp thời |
| **Intervention Priority Index (Sau 3 Bài)** | **0.0** (Đánh giá cô lập) | **1.5** (Tổng hợp đa chiều) | Giáo viên biết chính xác học sinh nào cần hỗ trợ |

---

## 2. Chi Tiết Tiến Trình Từng Bài Luận (Essay Trajectory Breakdown)

### 📝 Bài Luận 1: `Essay 1: EVs are Bad (Unsourced Claims)`
* **Nội dung:** Bài viết thiếu hoàn toàn dẫn chứng về xe điện, lập luận cảm tính.
* **Nhánh A (No Memory):** Chọn `skeptic` (The Skeptic). Không có lịch sử.
* **Nhánh B (Memory ON):** Chọn `skeptic` (The Skeptic). Ghi nhận điểm yếu ban đầu: `unsupported claim`.

### 📝 Bài Luận 2: `Essay 2: EV Battery Failures (Persistent Weakness)`
* **Nội dung:** Học sinh vẫn mắc lỗi thiếu dẫn chứng, lấy ví dụ cá nhân (anecdotal evidence) để khái quát hóa.
* **Nhánh A (No Memory):** Tiếp tục chọn `skeptic` (The Skeptic) một cách máy móc. **Không nhận ra học sinh đang kẹt ở điểm yếu này**.
* **Nhánh B (Memory ON):** Nhận diện học sinh vừa dùng Skeptic ở bài 1, tự thích ứng chuyển sang `expander` (The Expander) để tiếp cận từ góc độ phản biện đối lập.
* **Prompt Injection (Nhánh B):**
  > *"This student has previously struggled with: unsupported claim, hasty generalization, anecdotal evidence. If this essay repeats one of these patterns, consider probing it directly..."*

### 📝 Bài Luận 3: `Essay 3: Battery Recycling (Evidence Added, Hasty Generalization)`
* **Nội dung:** Học sinh đã biết trích dẫn nghiên cứu Stanford 2025 (Evidence tăng vọt từ 1 lên 8 điểm), nhưng phạm lỗi khái quát hóa vội vàng (hasty generalization).
* **Nhánh A (No Memory):** Chọn `nitpicker`. Không biết rằng học sinh vừa có bước tiến lớn về dẫn chứng.
* **Nhánh B (Memory ON):** Chọn `nitpicker` (The Nitpicker) tập trung rèn tính chặt chẽ logic. Nhận diện `score_trend: improving`.

---

## 3. Kết Luận Kiến Trúc (Architectural Conclusion)

1. **Proof of Adaptive Partnership:** eduagent đã chứng minh tính năng cốt lõi của *Collaborative Partner*: agent **học từ tương tác quá khứ** để điều chỉnh phương pháp sư phạm thay vì hoạt động như một chatbot stateless trả lời từng lượt đơn lẻ.
2. **Deterministic Governance:** Toàn bộ quá trình chọn persona và tính toán Priority Index hoàn toàn **deterministic (ZERO LLM-as-judge)**, bảo đảm 100% khả năng tái lập và minh bạch kiểm toán.
