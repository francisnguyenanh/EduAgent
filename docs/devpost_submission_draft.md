# Devpost Submission Draft

> Copy-paste vào form Devpost. Điền chỗ `[...]` trước khi nộp (link video, link repo, link hosted service). Đọc lại 1 lần trước khi nộp — đặc biệt đoạn Mandatory Disclosure và Track, đây là 2 chỗ sai sẽ ảnh hưởng eligibility.

---

## Project name

**eduagent** — Collaborative Partner Socratic Mentor

*(Không dùng tên "Evolving Knowledge Engine" hay bất kỳ tên nào khác — chỉ dùng tên phản ánh đúng track Collaborative Partner.)*

## Track

**Collaborative Partner**

## Elevator pitch (1–2 câu, nếu form yêu cầu)

An adversarial Socratic debate agent that challenges students' essays instead of correcting them — remembering each student's persistent weaknesses across sessions, and automatically triaging an entire class for the teacher via a deterministic priority ranking and a human-approved digest draft.

## Inspiration

Rural and overcrowded classrooms often have one teacher for 40+ students with no time to give individualized critical-thinking feedback. Existing AI writing tools tend to just hand students corrected answers — which teaches dependency, not thinking. Our philosophy: *use AI to teach students not to depend on AI.*

## What it does

**Tier 1 — Per-student adaptive Socratic pipeline.** A student submits an essay — typed text, or a photo of a handwritten one. The system:
- Ingests messy input via **Multimodal OCR** (Gemini Vision): verbatim transcription (preserves the student's own spelling/grammar mistakes), with a **self-consistency cross-check** (two independent Vision calls compared deterministically) that catches cases where the model would otherwise hallucinate confidently on a degraded photo.
- Extracts claim/evidence/fallacy structure, then selects one of 4 adversarial personas (Skeptic, Devil's Advocate, Nitpicker, Expander) based on the student's **persistent weakness history read from Firestore** — not just the current essay.
- Runs a 3-turn escalating Socratic debate, with **persona anchoring** re-injected every turn (a known failure mode in earlier single-prompt approaches: personas drifting into a generic agreeable assistant mid-conversation).
- Every generated question passes through an **independent, zero-LLM Challenge Validator** before the student sees it — blocking answer-leaks, multi-part questions, and out-of-bounds length, in both English and Vietnamese.
- Scores the essay on 4 rubric axes and writes **constructive, encouraging student-facing feedback** — then mutates the student's Firestore profile (streak tracking, `needs_attention` flagging, score-trend detection), which is the concrete "become more helpful over time" evidence: persona choice and debate context visibly change based on what a student struggled with last time.

**Tier 2 — Class Aggregator & Teacher Co-Pilot.** Every graded essay fires a Pub/Sub event to a Cloud Run service that:
- Clusters shared logical fallacies across the whole class and computes a deterministic **Intervention Priority Index** (zero LLM — a rule engine a teacher can actually audit: "why is student A ranked above student B?" always has a traceable answer).
- Synthesizes a natural-language **Teacher Digest** (Gemini) that only explains the pre-computed ranking — the system instruction explicitly forbids the LLM from re-ranking.
- Drafts an email in the teacher's Gmail (compose-only — the codebase has **no code path to `.send()`**, enforced by an AST-based test, not just review discipline) and appends an audit row to a Google Sheet.
- The **only human-in-the-loop gate**: the teacher opens their own Gmail and clicks Send.

## How we built it

Google ADK2 Graph Workflow (real conditional routing, not if/else — e.g. text vs. image essays branch via `ctx.route`), Gemini via Vertex AI (Flash for most calls, a newer Flash release for the heavier digest-synthesis task), Firestore (Native mode, transactional read-modify-write for profile mutation), Pub/Sub (topic + dead-letter queue, idempotent event processing), Cloud Run (FastAPI push subscriber for Tier 2), Cloud Trace + structured JSON logging, and a hand-written deterministic ADK Eval Suite (answer-leak prevention, prompt-injection resistance, persona fidelity — all scored without an LLM judging another LLM's output, to avoid reward-hacking).

## Technologies used

Google ADK2 (Graph Workflow, FunctionNode, conditional routing), Gemini 3.5/3.7 Flash via Vertex AI (text, JSON-schema, and multimodal/vision calls), Google Cloud Firestore, Google Cloud Pub/Sub, Google Cloud Run, Google Cloud Trace, Gmail API (compose-only OAuth scope), Google Sheets API (append-only), Python, FastAPI, tenacity (retry), OpenTelemetry, pytest.

## Other data sources

12 real handwritten essay photos (neat, messy with cross-outs, cursive, pencil, tilted, low-light/faded, bullet-point notes) used to validate multimodal ingestion end-to-end — no external dataset, all captured specifically for this project.

## Findings & learnings

- **Least-privilege can't always be enforced at the OAuth-scope layer.** Real testing proved Gmail's `gmail.compose` scope does *not* block `messages.send()` — Google's own docs describe it as including send. We had to move the guarantee to the code layer (an AST-based test that fails the build if `.send()` ever appears) and be honest in this write-up that the real HITL gate is a human clicking Send, not a technical wall.
- **A single LLM self-report of confidence isn't reliable enough for OCR.** On a genuinely degraded test photo, Gemini Vision confidently hallucinated unrelated content while self-reporting "high" confidence in 2 of 4 manual trials. We added a deterministic self-consistency cross-check (two independent Vision calls, compared via plain string similarity) as a backstop — it caught the failure 3/3 times afterward.
- **Reward-hacking risk applies to eval suites too.** Grading this system's own LLM output with another LLM call would be the exact risk we were warned about, so our ADK Eval Suite re-runs the real production validator/sanitizer directly and scores persona fidelity by keyword-matching real model output — no LLM ever judges another LLM here.
- **A platform's own "standard" path names aren't always safe.** `/healthz`, a very common health-check convention, turned out to be intercepted by Cloud Run's underlying serving infrastructure before ever reaching our container — found only by testing the real deployed service, not by reading documentation.

## Mandatory disclosure

*"This architecture is inspired by the author's personal prior project, CritiqAI (entered in a different, earlier competition). All code in this submission was written from scratch during this hackathon's Submission Period."*

## Links

- GitHub repo: `[link tới repo, đảm bảo đã share cho testing@devpost.com và cloudhackathons@google.com nếu repo private]`
- Demo video (YouTube/Vimeo, public): `[link]`
- Hosted Cloud Run service: `https://eduagent-class-aggregator-s6pcepa2cq-as.a.run.app` (yêu cầu Bearer token — service này là Pub/Sub push subscriber nội bộ, không phải web app công khai; giám khảo xem hoạt động qua video demo + `eval/results/eval_report.md` trong repo)
- Architecture diagram: nhúng trong `README.md` (Mermaid, render trực tiếp trên GitHub)

---

*Đính kèm theo yêu cầu "What to Submit": repo ✅, video ✅ (sau khi upload), hosted URL ✅, architecture diagram ✅ (trong README).*
