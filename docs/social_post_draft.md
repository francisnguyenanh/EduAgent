# Social Post Draft (Bonus Stage Three, +0.2đ)

> Đăng trên X/LinkedIn, public, kèm hashtag bắt buộc `#AllThingsAgenticHackathon` + link demo. Chọn 1 trong 2 bản dưới tuỳ nền tảng (X ngắn, LinkedIn dài hơn) hoặc chỉnh giọng văn tuỳ ý.

## X (bản chính thức — 273/280 ký tự, đã tính link rút gọn t.co)

> Built an AI that won't give students answers — it debates them instead.
>
> 4 Socratic personas, memory across sessions, deterministic teacher priority ranking. Gemini + ADK2 + Firestore + Cloud Run.
>
> https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/
> https://github.com/francisnguyenanh/EduAgent
>
> #AllThingsAgenticHackathon

**Cách đăng:**
1. Đăng nhập X, bấm "Post".
2. Copy nguyên văn khối trên (giữ đúng xuống dòng — nó tạo nhịp đọc, X không tự xuống dòng cho bạn).
3. Thay 2 link nếu cần: dòng demo dùng URL Cloud Run thật, dòng repo dùng URL GitHub thật (đều đã điền đúng ở trên, chỉ cần xác nhận repo đang **Public**).
4. **Không gõ tay hashtag riêng** — cứ để `#AllThingsAgenticHackathon` y như trong bài, gõ liền không dấu cách mới ăn thành thẻ.
5. Đăng ở chế độ public (mặc định của tài khoản public đã là public — không cần chỉnh gì thêm trừ khi tài khoản bạn đặt "Protected posts").
6. Copy link bài đăng vừa lên (bấm vào timestamp của post → copy URL từ address bar) để dán vào form Devpost.

**Nếu muốn thread dài hơn** (X cho đăng nhiều tweet nối tiếp, không giới hạn 280 mỗi cái nếu bạn có Premium, hoặc cứ tách thành 2-3 tweet nối "🧵"): dùng bản LinkedIn dưới, cắt thành 2 đoạn.

## LinkedIn (dài hơn, không giới hạn ký tự chặt)

> "Using AI to teach students not to depend on AI" — that's the one-line philosophy behind eduagent, my submission for the All Things Agentic Hackathon (Collaborative Partner track).
>
> Instead of correcting a student's essay, it challenges it: 4 adversarial Socratic personas (Skeptic, Devil's Advocate, Nitpicker, Expander), an independent zero-LLM validator that blocks any answer-leak before the student sees it, and a memory system that makes the debate get sharper as it learns a student's persistent weaknesses across sessions.
>
> On the teacher side, every graded essay feeds a class-wide priority ranking (fully deterministic and auditable — a teacher can always trace *why* one student ranks above another) and a Gemini-written digest draft, with exactly one human-in-the-loop gate: the teacher clicking Send in their own Gmail.
>
> The part I'm most proud of isn't a feature — it's an audit. We went back through our own eval suite and found 12 of 50 test cases that couldn't actually fail (one group was asserting "8 minus 2 is at least 4"). We rewired every one of them to run against real production code and now prove each case can go red by breaking the code on purpose. Same audit found a session-signing key that had never been rotated off its public default — fixed, and the deploy now refuses to boot if that ever regresses.
>
> Built on Gemini via Vertex AI, Google ADK2, Firestore, Pub/Sub, and Cloud Run — and it also ingests real handwritten essay photos (yes, the messy kind, with cross-outs and bad lighting) via a self-consistency-checked multimodal OCR pipeline.
>
> Demo: https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/
> Repo + full architecture writeup: https://github.com/francisnguyenanh/EduAgent
>
> #AllThingsAgenticHackathon
