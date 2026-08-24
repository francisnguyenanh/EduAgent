# Technical Blog Draft (Bonus Stage Three, +0.2đ)

> Đăng lên Medium/Dev.to. Ghi rõ "written for the All Things Agentic Hackathon" ngay đầu bài, để public. Chỉnh giọng văn/độ dài tuỳ ý — đây là khung nội dung kỹ thuật đầy đủ đã có sẵn bằng chứng thật, không phải claim suông.

**Title:** *Building a Socratic Debate Agent That Refuses to Give Answers — Lessons from ADK2, Gemini, and a Production-Minded Architecture*

**Subtitle:** *Written for the All Things Agentic Hackathon (Collaborative Partner track).*

---

## The problem with "helpful" AI tutors

Most AI writing tools optimize for making the student's essay better. We optimized for making the *student* better — which meant building an agent whose job is to challenge, not correct. That single framing decision drove almost every architecture choice below.

## Architecture: deterministic-first, LLM only where reasoning is actually required

[Nhúng sơ đồ Mermaid từ README.md mục 2 vào đây]

Every piece of logic that didn't need LLM reasoning — the Challenge Validator, the Persona Selector, the Class Aggregator's priority ranking, the fallacy clustering — is a plain Python function, zero LLM calls, fully unit-testable and auditable. A teacher asking "why is student A ranked above student B?" always has a traceable, deterministic answer.

The LLM only runs where actual reasoning/generation is needed: extracting essay structure, generating the next Socratic question, scoring against a rubric, and turning a pre-computed ranking into readable prose for a teacher.

## Finding #1: OAuth scopes don't guarantee what you think they do

We designed Gmail delivery around the assumption that requesting only the `gmail.compose` scope would technically prevent the agent from ever sending an email — a clean, scope-enforced least-privilege story. Real testing (not documentation-reading) proved this wrong: `gmail.compose` is documented by Google as *"create, read, update, delete drafts; send messages and drafts"* — it includes send.

We had two email accidentally sent to our own inbox during that test before we caught it.

The fix: move the guarantee to the code layer. The Gmail integration module never calls `.send()` anywhere, and we wrote an AST-based test — not a regex, an actual Python `ast` parse — that fails the build the moment anyone adds a `.send()` call to that file. The real human-in-the-loop gate is the teacher opening their own Gmail and clicking Send, a human action entirely outside our code path. We say this explicitly in our demo video rather than claiming a technical wall that doesn't exist.

## Finding #2: a single LLM confidence score isn't enough for OCR

Multimodal ingestion (a photo of a handwritten essay) needed a way to know when the transcription wasn't trustworthy. Our first pass asked Gemini Vision to self-report a `confidence` field alongside the transcription, with an explicit anti-hallucination instruction in the prompt.

On a genuinely degraded test image, this failed in a specific, dangerous way: the model self-reported `confidence: "high"` while transcribing completely unrelated, fabricated content, in 2 of our 4 manual trials. Prompt engineering alone did not close this gap.

The fix: a deterministic backstop. We call Gemini Vision *twice*, independently, on the same image, and compare the two transcriptions with plain string similarity (`difflib`). If they disagree substantially, we force the confidence down to `low` regardless of what either call claims — the decision logic itself never involves another LLM judging the first one. After adding this, the same failure mode was caught 3 out of 3 times. Essays with low OCR confidence are routed to a review queue instead of ever silently entering a student's permanent record.

## Finding #3: reward-hacking risk isn't just a training-time concern

We were warned to be careful about reward hacking when building our eval suite. The most tempting fast path — using an LLM to grade whether our persona stayed in character, or whether a debate question leaked an answer — is *exactly* that risk: an LLM judging its own system's output.

Instead, our eval suite's answer-leak and prompt-injection groups re-run the actual production validator and sanitizer functions directly (the same code the live pipeline uses — not a re-implementation that could drift). The persona-fidelity group runs the real 3-turn debate against live Gemini calls, then scores the real output against a fixed keyword lexicon per persona via plain substring matching. No LLM ever grades another LLM's text in this suite. Last real run: 15/15 cases pass (100%).

## Finding #4: platform conventions aren't always safe assumptions

Deploying to Cloud Run, we named our health-check endpoint `/healthz` — the conventional name from Kubernetes and many other platforms. It consistently returned a generic Google-branded 404, *before* the request ever reached our container or even the IAM authorization check, while every other path (including `/healthz/` with a trailing slash) worked correctly. Cloud Run's underlying Knative/Istio serving stack apparently reserves that exact literal path. Renaming to `/health-check` fixed it immediately. The lesson: verify a "well-known convention" against the actual deployed platform, not just against general documentation from a different ecosystem.

## Closing

None of these findings came from reading documentation more carefully — they came from actually running the system against real Gmail accounts, real blurry photos, real Cloud Run deployments, and treating every "should work" assumption as something to verify, not assume. That discipline is, we'd argue, the actual differentiator between a demo and a system.

*Repo, architecture diagram, and full ADR log: `[link tới GitHub repo]`.*

---

`#AllThingsAgenticHackathon`
