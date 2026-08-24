# Social Post Draft (Bonus Stage Three, +0.2đ)

> Đăng trên X/LinkedIn, public, kèm hashtag bắt buộc `#AllThingsAgenticHackathon` + link demo. Chọn 1 trong 2 bản dưới tuỳ nền tảng (X ngắn, LinkedIn dài hơn) hoặc chỉnh giọng văn tuỳ ý.

## X (ngắn, có giới hạn ký tự)

> Built an AI agent that refuses to give students answers — it debates them instead. 4 Socratic personas, memory across sessions, and a teacher co-pilot that ranks a whole class by who needs help first (deterministically, not by LLM vibes). Built on Gemini + Google ADK2 + Firestore + Cloud Run.
>
> Demo: [link video] · Repo: [link repo]
>
> #AllThingsAgenticHackathon

## LinkedIn (dài hơn)

> "Using AI to teach students not to depend on AI" — that's the one-line philosophy behind eduagent, my submission for the All Things Agentic Hackathon (Collaborative Partner track).
>
> Instead of correcting a student's essay, it challenges it: 4 adversarial Socratic personas (Skeptic, Devil's Advocate, Nitpicker, Expander), an independent zero-LLM validator that blocks any answer-leak before the student sees it, and a memory system that makes the debate get sharper as the system learns a student's persistent weaknesses across sessions.
>
> On the teacher side, every graded essay feeds a class-wide priority ranking (fully deterministic and auditable — a teacher can always trace *why* one student ranks above another) and a Gemini-written digest draft, with exactly one human-in-the-loop gate: the teacher clicking Send in their own Gmail.
>
> Built on Gemini via Vertex AI, Google ADK2, Firestore, Pub/Sub, and Cloud Run — and it also ingests real handwritten essay photos (yes, the messy kind, with cross-outs and bad lighting) via a self-consistency-checked multimodal OCR pipeline.
>
> Demo video: [link] | Repo + full architecture writeup: [link]
>
> #AllThingsAgenticHackathon
