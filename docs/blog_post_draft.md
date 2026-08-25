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

Instead, our eval suite's answer-leak and prompt-injection groups re-run the actual production validator and sanitizer functions directly (the same code the live pipeline uses — not a re-implementation that could drift). The tenancy group calls the real `_verify_class_auth()` the HTTP routes use. The persona-fidelity group calls the production prompt builder, `nodes/debate.py::build_system_instruction()`, and verifies the persona anchor is present in the instruction actually sent to Gemini on all 3 escalation turns, that each anchor is unique, and that no persona's keyword signature also matches another persona's anchor. No LLM ever grades another LLM's text in this suite. Our latest run is **50/50 deterministic test cases passed** across 4 layers: Safety & Security, Behavioral Discipline, Long-Term Memory, and Learning Outcomes. That is a green test suite — not a claim that the system is 100% correct.

But writing this section is what exposed our own worst bug, and it's the most useful thing in this post.

**The eval that couldn't fail.** An earlier version of that persona-fidelity check built the system instruction *inside the test*, then asserted the anchor was in the string it had just concatenated. It was a tautology: green no matter what the production code did. Worse, Layer 4's eight "cognitive growth" cases subtracted two integer literals declared in the test fixture file itself and asserted `8 - 2 >= 4`. Those cases would have passed with the entire `src/` tree deleted. We had 12 test cases certifying arithmetic.

The lesson generalizes past evals: **reward hacking doesn't require a reward model.** A human writing an assertion that restates its own setup produces the same failure — a metric that goes up without the system getting better. The fix we now apply to every case is a sabotage test: break the production code on purpose and confirm the test goes red. When we deleted persona anchoring from the real builder, 4 of 4 cases failed. When we removed the measurement artifact, 4 of 4 Layer 4 cases failed. Before that rework, both would have stayed green.

**And then the honest test told us something we didn't want to hear.** Since we'd claimed to run live debates, we built the mode that actually does it (`--live-persona`, opt-in, written to a separate report so the zero-LLM guarantee of the main suite stays intact): the real 3-turn debate against Gemini, with the model's actual questions matched against each persona's lexicon. Two of four personas — the Devil's Advocate and the Nitpicker — **drifted into the Skeptic's voice** on a hard essay, asking about evidence and causation instead of arguing the opposing side or auditing the logic. Anchoring keeps the instruction in the prompt; it does not guarantee the model obeys it. We could have widened the lexicons until the test went green. That would have been the same reward hacking in a new costume, so we left the failure in the report and wrote it down here instead.

## Finding #4: platform conventions aren't always safe assumptions

Deploying to Cloud Run, we named our health-check endpoint `/healthz` — the conventional name from Kubernetes and many other platforms. It consistently returned a generic Google-branded 404, *before* the request ever reached our container or even the IAM authorization check, while every other path (including `/healthz/` with a trailing slash) worked correctly. Cloud Run's underlying Knative/Istio serving stack apparently reserves that exact literal path. Renaming to `/health-check` fixed it immediately. The lesson: verify a "well-known convention" against the actual deployed platform, not just against general documentation from a different ecosystem.

## Finding #5: the blast radius of a fix is usually smaller than the blast radius of the bug

Late in the project we audited our own repo against its own documentation and found that the deployed service was signing teacher session tokens with a key committed to the public repository — the environment variable overriding it had never been set. Anyone who read the repo could mint a `role=teacher` token for any class and read that class's student records. We fixed it properly: the key moved to Secret Manager, and the process now refuses to boot on Cloud Run while the committed default is still in effect, because a missing environment variable is a silent failure and a container that won't start is a loud one.

We considered secrets handled after that. They weren't.

An outside reviewer looked at our deploy script and pointed at two lines passing the Gmail and Sheets OAuth tokens through `--env-vars-file`. Cloud Run stores plain environment variables in the revision spec in cleartext, so `gcloud run services describe` printed both **refresh tokens in full** — exposed to anyone with `run.services.get`, a read permission granted much more freely than `secretmanager.versions.access`. We ran the command against the live service before touching anything, and there they were.

The same shape had already bitten us once. When we added authentication, we secured every `/api/classes/*` route and left all five student-facing debate endpoints completely open, so any caller could write into any student's profile. Both times: we fixed the instance in front of us and never asked what else belonged to the same class of problem. Both times, the second half was found by someone else.

The uncomfortable part is that "be more thorough" is not a fix. What actually works is converting the question into something that runs without us:

- An AST-based test fails the build if any credential is ever inlined as a plain environment variable again. We verified it by reintroducing the bug on purpose and watching it go red.
- `doctor.py`, our preflight command, now inspects the *deployed* revision and reports any credential still stored in cleartext. It correctly reported FAIL on our live service until we redeployed — which is exactly the moment such a check earns its keep.

Worth noting what the good fix cost: nothing. Mounting the secrets via `--update-secrets` required **zero application code changes**, because Cloud Run injects the value into the same environment variable the integrations already read. We deliberately skipped the more elaborate option of calling the Secret Manager API from inside the app — it would have added a dependency, a cold-start API call, and code to maintain, in exchange for no additional protection.

## Designing for Measurable Pedagogical Outcomes (Empirical Proof)

To stand out in the *Collaborative Partner* track, we had to prove that our memory-driven adaptation actually improves student outcomes:
1. **Memory A/B Experiment:** We ran a student through 3 consecutive essays with recurring reasoning flaws. In Branch A (Stateless), the agent kept repeating the same persona and questions (a frustrating pedagogical dead-end). In Branch B (eduagent Persistent Memory), the agent dynamically rotated personas based on past progress and proactively injected historical context (e.g., *"In your last essay on this topic, you lacked evidence..."*). 
2. **Learning Outcome Delta Measurement:** we push 8 controlled thesis pairs (a weak thesis and its Socratically-revised form) through the *real* production path — `summarize_essay()` then `score_essay()` against Vertex AI — and record the per-axis delta. The scorer sees one text at a time, never the Socratic probe, and is never told which text is the revision, so it can't infer that a higher score is expected. Measured result: the targeted axis improved in **7 of 8 scenarios**, mean **+2.75 points** on the targeted axis and **+2.05** across all four.

   This number replaced a **+5.62** we had been quoting, and the story behind that swap is the same lesson as Finding #3. The `+5.62` came from a script whose `before_scores` and `after_scores` were hand-typed literals; it did the subtraction and printed the mean of 16 integers we had chosen ourselves. No essay was scored. No model was called. The report even claimed "independent re-scoring" for behaviour that did not exist anywhere in the code. Rewiring it to the real scorer cost us half the headline number and one of the eight scenarios — and that is the version worth publishing. Note also what the honest number *doesn't* claim: n = 8 author-written thesis pairs, not 8 students, with no control group. It measures whether the scorer detects the improvement each persona targets. It is not evidence about real classroom learning gains.

## Closing

None of these findings came from reading documentation more carefully — they came from actually running the system against real Gmail accounts, real blurry photos, real Cloud Run deployments, and treating every "should work" assumption as something to verify, not assume. That discipline is, we'd argue, the actual differentiator between a demo and a system.

*Repo, architecture diagram, and full ADR log: `[link tới GitHub repo]`.*

---

`#AllThingsAgenticHackathon` `#GoogleCloud` `#GenAI` `#Gemini` `#AgenticAI`
