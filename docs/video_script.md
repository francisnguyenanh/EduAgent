# Video Script: EduAgent — The Autonomous Collaborative Partner for Critical Thinking

> **Target Duration:** Exactly 3:45 - 4:00 minutes  
> **Narrative Arch:** Problem → Single-Student Adaptive Trajectory (Proof of Partner) → Autonomous Teacher Synthesis → Production Architecture & Deterministic Eval Suite → Vision.

---

## 🥇 The Golden Path — ONE story, told identically everywhere

Video, Devpost, README and slides all follow **this single flow**, in this order:

```
handwritten photo → OCR (Gemini + Gemma cross-MODEL check) → student reads & approves
     the transcription (ADR-029) → weak evidence detected
  → SKEPTIC → 3-turn debate → self-correction → memory updated
  → essay 2 → PERSONA CHANGES BECAUSE IT REMEMBERED
  → class-level fallacy pattern → deterministic teacher priority + mini-lesson
  → digest shown on the dashboard as composed (ADR-030)
  → human approval (teacher clicks Send)
```

> **Audit Wave 25/26 — two beats changed shape since the last recording.**
> **(a) Ingest is two clicks now (ADR-029).** The photo beat is *Extract OCR* → the transcription
> appears in an editable box → *Start debate*. Say why out loud: *"the student reads the
> transcription before the AI argues with it."* It also gives you something on screen during the
> OCR wait discussed below, which the one-call flow did not.
> **(b) The digest is visible on the dashboard (ADR-030).** You no longer have to cut to a Gmail
> mailbox to prove the agent composed something — the Analytics tab renders the draft's own body
> with the badge `Draft created ✓ — awaiting human Send`. Show that, *then* click through to the
> real draft. The badge is the HITL claim made visible; read it aloud.

**The single most important moment in the video is "the persona changed because it remembered" (~1:10).** Everything else is context for that moment. Do not attempt to demo the whole system.

> *(Audit Wave 24 correction: this line used to say `~2:10`, left over from an earlier cut of the
> timeline. In the current script that beat is **Scene 2, Visual 2 (1:00 – 1:25)**; 2:10 is now the
> mini-lesson. Rehearsing to the old marker would have put the emphasis on the wrong beat — the
> exact beat two prior reviews were rejected for proposing to cut.)*

Two lines worth putting on screen as text, because they land harder read than heard:
* *"We don't trust the model's own confidence score."* (during the OCR beat)
* *"The agent composed this. It did not send it."* (during the digest beat — pointing at the badge)
* *"The agent doesn't replace the teacher or the student's thinking. It makes both more scalable."* (closing)

**⏱️ Latency budget — measured, not estimated (Audit Wave 15).** The image path is the slowest thing in the demo. Measured on a real 958 KB handwritten photo against Vertex AI:

| Step | Measured |
|---|---|
| `transcribe_essay_image()` — Gemini Vision + Gemma 4 cross-model check (ADR-028) | **22.5s** measured Wave 15 on the same-model version; **must be re-measured on the deployed service** — see the note below |
| Full `/api/debate/start-with-image` (OCR + summarizer + persona + turn 1) | **24.2s** |

> ⚠️ **Audit Wave 24 — re-measure before you record.** ADR-028 moved the second transcription pass
> to Gemma 4, which adds a call to the image path. Measured locally in a contemporaneous A/B (same
> code, toggled by `EDUAGENT_OCR_CROSS_CHECK_GEMMA`) over the 12 real samples: mean per-image OCR
> **7.30s → 8.82s, +21%**. The 22.5s / 24.2s figures above were measured at Wave 15 on the
> *same-model* version against the deployed service and have **not** been re-measured since. Run the
> image beat once on the live service and read the real number before you rehearse the timing —
> per the numbers-discipline rule below, never say a figure you have not just seen.

An external review predicted a **504 Deadline Exceeded** here. That is not the real risk: the Cloud Run request timeout is **300s** and the per-call LLM timeout is 60s, so there is ~12x headroom and a 504 needs something far worse than a slow photo. The real risk is **24 seconds of dead air in a 240-second video** — 10% of the budget on a spinner.

Mitigations, in order of preference:
1. **Talk over it.** Those 24 seconds are exactly when you explain *"we transcribe the photo twice — once with Gemini Vision, once with Gemma, a different model family — and compare them, because we don't trust a model's own confidence score, and two passes of the SAME model share the same blind spot"* — the OCR beat has the most to say and nothing to show. Rehearse it as narration over a progress state, not as a wait.
2. **Warm the service first** so cold start is not stacked on top: hit `/health-check` before recording.
3. **If the timing still doesn't fit:** run the live beat with typed text (fast) and show the handwriting path in a second window that was started earlier. Do NOT cut the recording to hide the wait — "unedited live execution" is a scoring requirement.

**Numbers discipline for the whole recording:** never say a number that is not visible on screen at that moment. Every headline figure in this project is reproducible from a script (`run_eval_suite.py`, `evaluate_learning_outcomes.py`, `experiment_memory_ab.py`) — run it live or screenshot it beforehand, and read what it shows.

---

## 🔑 Credentials & data you will actually type on camera (re-verified 2026-08-27 against live revision `00037-6h4`)

**The two portals now take DIFFERENT passcodes (ADR-025, Audit Wave 18).** Typing the student
passcode into the Teacher Portal returns `401 Incorrect password.` on camera.

| Portal | ID | Passcode |
|---|---|---|
| Student | `c1_stu01` (or any `c1_<name>`) | `eduagent2026` |
| Teacher | `c1_teacher` | `eduagent-teacher-2026` |

**⚠️ There are TWO students named "Binh" in class `c1`.** The one the script is about is
`stu_stuck` — 4 essays, all on The Skeptic, `needs_attention = true`, ranked **#1**. The other
(`c1_stu02`, also "Binh") sits at #3. On the Teacher Dashboard, click the **top row**. Verified
live ranking:

```
1. stu_stuck          | Binh | priority=14.29   <-- the story
2. c1_stu01           | An   | priority=8.50
3. c1_stu02           | Binh | priority=8.50    <-- NOT this one
4. stu_inactive       | Duc  | priority=5.50
```

Re-check on the day of recording (the ranking moves as data is added):

```bash
URL=https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app
T=$(curl -s -X POST $URL/api/auth/login -H 'Content-Type: application/json' \
  -d '{"role":"teacher","user_id":"c1_teacher","password":"eduagent-teacher-2026"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s "$URL/api/classes/c1/priority" -H "Authorization: Bearer $T" | python3 -m json.tool | head -20
```

---

## ⏱️ Timeline & Shot Breakdown

```mermaid
timeline
    title 4-Minute Submission Video Arc
    00:00 - 00:40 : The Problem (AI as Cheat Engine vs Cognitive Partner)
    00:40 - 01:45 : Single-Student Proof Sequence (Socratic Debate, Memory Adaptation, Metacognition)
    01:45 - 02:45 : Autonomous Class Synthesis (Priority Engine, Mini-Lesson, Parent Note)
    02:45 - 03:30 : Architectural Rigor (Cloud Run, Trace, 4-Layer ADK Eval 50/50 deterministic cases, Memory A/B)
    03:30 - 04:00 : Summary & Live Verification Links
```

---

### 🎬 Scene 1: The Problem & The Paradigm Shift (0:00 - 0:40)
* **Visual:** Split screen. Left side: standard chatbot generating a ready-made essay (label: *Passive Consumer*). Right side: EduAgent logo and dashboard (label: *Autonomous Collaborative Partner*).
  `[VISUAL: cloud-to-classroom transition, or fallback to text-only "EduAgent" reveal — let the image carry the geography idea, voice carries the words.]`
* **Voiceover:**
  > *"AI was born in the cloud. But its power shouldn't be limited by geography. Every student, rural or urban, deserves a partner that makes them think.*
  >
  > *Generative AI in classrooms today suffers from a fundamental paradox: instead of teaching students how to think, it does the thinking for them. Students submit prompts; AI spits out answers.*  
  > *Meet **EduAgent** — an autonomous, Collaborative Partner built on Google Cloud and Gemini that **refuses to write the essay**. Instead, it acts as a relentless Socratic adversary, challenging logical fallacies, tracking long-term cognitive growth across weeks, and autonomously synthesizing class-wide insights for teachers."*
  > (Say "autonomous," not "multi-agent" — personas are routed within one ADK `Workflow` of `FunctionNode`s, `src/eduagent/graph/tier1_pipeline.py`, not separate agent instances. "Multi-agent" invites a "where are the agents?" question we can't answer well. "adaptive" is also trimmed here per timing note above.)

---

### 🎬 Scene 2: Single-Student Adaptive Trajectory — "Binh's Journey" (0:40 - 1:45)
* **Visual 1 (0:40 - 1:00):** Student Portal. Student "Binh" submits Essay 1 on Electric Vehicles. The system extracts claims and selects **The Skeptic**.
  - Socratic Turn 1 pops up: *"What empirical data accounts for battery manufacturing and regional power grids?"*
  - Show live debate exchange across 3 turns. Notice how the Independent Validator guarantees **ZERO answer leaks**.
* **Visual 2 (1:00 - 1:25):** Fast forward to Essay 2. Binh repeats an unsupported claim.
  - Show the **Long-Term Memory in action**: EduAgent recognizes Binh's repeated struggle, rotates persona to **The Expander**, and explicitly injects memory context:  
    > *"This student has previously struggled with: unsupported claim. Probing broader context..."*
* **Visual 3 (1:25 - 1:45):** **Metacognitive Reflection Node**.
  - Binh submits a revised thesis statement based on the debate.
  - The Scorer evaluates the cognitive delta — **read the delta the screen actually shows.** ⚠️ Do NOT say "2/10 to 8/10, +6.0": those were hand-typed constants in an earlier version of the evaluation script, not measured values (Audit Wave 12). Live scoring of a short revised thesis typically lands in the low single digits in absolute terms; the honest framing is *"the delta is positive on the axis the persona targeted"*, and the measured mean across our 8 benchmark scenarios is **+2.75**, not +5.62. If you want a number on screen here, run `scripts/evaluate_learning_outcomes.py` beforehand and show `docs/learning_outcome_eval.md`.

---

### 🎬 Scene 3: Autonomous Class Synthesis & Teacher Action Loop (1:45 - 2:45)
* **Visual 1 (1:45 - 2:10):** Switch to Teacher Dashboard (`c1`). 
  - Show the **Intervention Priority Index**: Ranked strictly by a deterministic rule engine (ZERO LLM-as-judge).
  - Binh (`stu_stuck`) is ranked **#1**. ⚠️ Do NOT say "Priority 1.5": `1.5` is only the
    `shared_fallacy` *component* of the score, not the score. The measured total on 2026-08-26 was
    **14.29**, broken down as `stuck_streak 9.0 + score_decline 2.5 + inactivity 1.29 +
    shared_fallacy 1.5`. Per the numbers-discipline rule above, read whatever total the screen shows
    — the components move with the data, and `inactivity` grows every day you do not re-seed.
* **Visual 2 (2:10 - 2:30):** **Actionable 15-Minute Mini-Lesson**.
  - Show the newly generated class digest, and read out whatever number the screen actually shows: the systemic-pattern threshold is **2 or more distinct students** sharing a fallacy (`priority_engine.MIN_STUDENTS_FOR_COMMON_FALLACY = 2`), counted per student rather than per essay. Don't say "3 students" unless the digest on screen says 3 — the earlier draft of this line hard-coded a number the run may not produce.
* **Visual 3 (2:30 - 2:45):** **1-Click Parent Progress Note**.
  - Click on Binh -> Generate Note. Gemini drafts an empathetic progress report citing Binh's cognitive breakthrough (do NOT say "FERPA-compliant" on camera — this is a privacy-by-design prototype, not a legally certified product).

---

### 🎬 Scene 4: Architectural Discipline & Empirical Evaluation (2:45 - 3:30)
* **Visual 1 (2:45 - 3:05):** Architecture Diagram & Google Cloud Trace.
  - Show live Google Cloud Run deployment (`asia-southeast1`), Firestore Memory, Pub/Sub Event Ingestion, and W3C Trace context propagation across nodes.
  - **Optional 5-second security beat, if the pacing allows** — run `python scripts/doctor.py` and let the **11-check** report land on screen (10 PASS / 1 WARN / 0 FAIL as of Audit Wave 18 — the WARN is the local signing key, which is correct for a laptop; say so if it is visible). It is a single command that shows the deployed revision is healthy, the Firestore TTL policy is ACTIVE, and no credential is stored in cleartext. If you'd rather say one sentence than show a table: *"Every credential reaches the container as a Secret Manager reference, and a preflight check refuses to deploy without them."*
* **Visual 2 (3:05 - 3:20):** **4-Layer Deterministic ADK Eval Suite — 50/50 deterministic test cases passed**.
  - Show terminal output of `scripts/run_eval_suite.py --strict`:
    1. Safety & Security (15/15)
    2. Behavioral Discipline (15/15)
    3. Long-Term Memory (10/10)
    4. Learning Outcomes (10/10)
  - Say "**50 out of 50 deterministic test cases passed**", never "the system is 100% correct" — a judge will hear the difference.
  - **Strongest 15 seconds available if you have them:** *"We audited our own suite and found twelve tests that could not fail — one group was asserting that eight minus two is at least four. We rewired them to production code and now prove every case can go red by breaking the code on purpose."* This is a credibility gain, not an admission; it is also the core of the bonus blog post (ADR-019).
* **Visual 3 (3:20 - 3:30):** **Memory A/B Experiment Evidence**.
  - Show comparative graph: Stateless Baseline (1 repeated stagnant Skeptic) vs. EduAgent Persistent
    Memory (**0 repeated stagnant interventions**). Say prior-weakness context was injected in
    **2 of 3 essays — 100% of the essays that had any history to draw on**, which is what
    `docs/experiment_memory_ab.md` measures. Dropping the qualifier turns a real result into an
    overclaim a judge can check.

---

### 🎬 Scene 5: Conclusion & Live Verification (3:30 - 4:00)
* **Visual:** Live Cloud Run URL, GitHub repository badge, and Judge 1-Click Showcase screen.
  `[VISUAL: "EduAgent / Powered by Gemini & Google Cloud" text lockup appears on screen simultaneously with QR code.]`
* **Voiceover:**
  > *"EduAgent bridges the gap between individual Socratic coaching and scalable classroom intelligence. Fully deployed on Google Cloud, MIT-licensed, and verified with deterministic rigor.*
  >
  > *Don't give every student an answer. Give every student a reason to think.*
  >
  > *Experience EduAgent live at our Cloud Run showcase link today."*
  > (CTA "Experience EduAgent..." remains the final line. Say **MIT**, not "MIT/Apache" — `LICENSE` in the repo root is MIT, and only MIT; naming a licence the repo does not carry is a free credibility hit.)
