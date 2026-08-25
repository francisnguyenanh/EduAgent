# Video Script: eduagent — The Autonomous Collaborative Partner for Critical Thinking

> **Target Duration:** Exactly 3:45 - 4:00 minutes  
> **Narrative Arch:** Problem → Single-Student Adaptive Trajectory (Proof of Partner) → Autonomous Teacher Synthesis → Production Architecture & Deterministic Eval Suite → Vision.

---

## 🥇 The Golden Path (ĐỢT 11/12) — ONE story, told identically everywhere

Video, Devpost, README and slides all follow **this single flow**, in this order. If an artifact tells a different story, the artifact is wrong, not this list.

```
handwritten photo → OCR (self-consistency cross-check) → weak evidence detected
  → SKEPTIC → 3-turn debate → self-correction → memory updated
  → essay 2 → PERSONA CHANGES BECAUSE IT REMEMBERED
  → class-level fallacy pattern → deterministic teacher priority + mini-lesson
  → human approval (teacher clicks Send)
```

**The single most important moment in the video is "the persona changed because it remembered" (~2:10).** Everything else is context for that moment. Do not attempt to demo the whole system.

Two lines worth putting on screen as text, because they land harder read than heard:
* *"We don't trust the model's own confidence score."* (during the OCR beat)
* *"The agent doesn't replace the teacher or the student's thinking. It makes both more scalable."* (closing)

**⏱️ Latency budget — measured, not estimated (ĐỢT 15).** The image path is the slowest thing in the demo. Measured on a real 958 KB handwritten photo against Vertex AI:

| Step | Measured |
|---|---|
| `transcribe_essay_image()` — 2 Vision passes + `difflib` cross-check | **22.5s** |
| Full `/api/debate/start-with-image` (OCR + summarizer + persona + turn 1) | **24.2s** |

An external review predicted a **504 Deadline Exceeded** here. That is not the real risk: the Cloud Run request timeout is **300s** and the per-call LLM timeout is 60s, so there is ~12x headroom and a 504 needs something far worse than a slow photo. The real risk is **24 seconds of dead air in a 240-second video** — 10% of the budget on a spinner.

Mitigations, in order of preference:
1. **Talk over it.** Those 24 seconds are exactly when you explain *"we call Gemini Vision twice and compare the transcriptions, because we don't trust the model's own confidence score"* — the OCR beat has the most to say and nothing to show. Rehearse it as narration over a progress state, not as a wait.
2. **Warm the service first** so cold start is not stacked on top: hit `/health-check` before recording.
3. **If the timing still doesn't fit:** run the live beat with typed text (fast) and show the handwriting path in a second window that was started earlier. Do NOT cut the recording to hide the wait — "unedited live execution" is a scoring requirement.

**Numbers discipline for the whole recording:** never say a number that is not visible on screen at that moment. Every headline figure in this project is reproducible from a script (`run_eval_suite.py`, `evaluate_learning_outcomes.py`, `experiment_memory_ab.py`) — run it live or screenshot it beforehand, and read what it shows.

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
* **Visual:** Split screen. Left side: standard chatbot generating a ready-made essay (label: *Passive Consumer*). Right side: eduagent logo and dashboard (label: *Autonomous Collaborative Partner*).
* **Voiceover (English/Vietnamese):**
  > *"Generative AI in classrooms today suffers from a fundamental paradox: instead of teaching students how to think, it does the thinking for them. Students submit prompts; AI spits out answers.*  
  > *Meet **eduagent** — an autonomous, adaptive Collaborative Partner built on Google Cloud and Gemini that **refuses to write the essay**. Instead, it acts as a relentless Socratic adversary, challenging logical fallacies, tracking long-term cognitive growth across weeks, and autonomously synthesizing class-wide insights for teachers."*
  > (Say "adaptive" or "autonomous," not "multi-agent" — personas are routed within one ADK `Workflow` of `FunctionNode`s, `src/eduagent/graph/tier1_pipeline.py`, not separate agent instances. "Multi-agent" invites a "where are the agents?" question we can't answer well.)

---

### 🎬 Scene 2: Single-Student Adaptive Trajectory — "Binh's Journey" (0:40 - 1:45)
* **Visual 1 (0:40 - 1:00):** Student Portal. Student "Binh" submits Essay 1 on Electric Vehicles. The system extracts claims and selects **The Skeptic**.
  - Socratic Turn 1 pops up: *"What empirical data accounts for battery manufacturing and regional power grids?"*
  - Show live debate exchange across 3 turns. Notice how the Independent Validator guarantees **ZERO answer leaks**.
* **Visual 2 (1:00 - 1:25):** Fast forward to Essay 2. Binh repeats an unsupported claim.
  - Show the **Long-Term Memory in action**: eduagent recognizes Binh's repeated struggle, rotates persona to **The Expander**, and explicitly injects memory context:  
    > *"This student has previously struggled with: unsupported claim. Probing broader context..."*
* **Visual 3 (1:25 - 1:45):** **Metacognitive Reflection Node**.
  - Binh submits a revised thesis statement based on the debate.
  - The Scorer evaluates the cognitive delta — **read the delta the screen actually shows.** ⚠️ Do NOT say "2/10 to 8/10, +6.0": those were hand-typed constants in an earlier version of the evaluation script, not measured values (ĐỢT 12 NHÓM 1). Live scoring of a short revised thesis typically lands in the low single digits in absolute terms; the honest framing is *"the delta is positive on the axis the persona targeted"*, and the measured mean across our 8 benchmark scenarios is **+2.75**, not +5.62. If you want a number on screen here, run `scripts/evaluate_learning_outcomes.py` beforehand and show `docs/learning_outcome_eval.md`.

---

### 🎬 Scene 3: Autonomous Class Synthesis & Teacher Action Loop (1:45 - 2:45)
* **Visual 1 (1:45 - 2:10):** Switch to Teacher Dashboard (`c1`). 
  - Show the **Intervention Priority Index**: Ranked strictly by a deterministic rule engine (ZERO LLM-as-judge).
  - Binh is flagged at Priority 1.5 due to a stuck streak and common fallacy.
* **Visual 2 (2:10 - 2:30):** **Actionable 15-Minute Mini-Lesson**.
  - Show the newly generated class digest, and read out whatever number the screen actually shows: the systemic-pattern threshold is **2 or more distinct students** sharing a fallacy (`priority_engine.MIN_STUDENTS_FOR_COMMON_FALLACY = 2`), counted per student rather than per essay. Don't say "3 students" unless the digest on screen says 3 — the earlier draft of this line hard-coded a number the run may not produce.
* **Visual 3 (2:30 - 2:45):** **1-Click Parent Progress Note**.
  - Click on Binh -> Generate Note. Gemini drafts an empathetic progress report citing Binh's cognitive breakthrough (do NOT say "FERPA-compliant" on camera — this is a privacy-by-design prototype, not a legally certified product).

---

### 🎬 Scene 4: Architectural Discipline & Empirical Evaluation (2:45 - 3:30)
* **Visual 1 (2:45 - 3:05):** Architecture Diagram & Google Cloud Trace.
  - Show live Google Cloud Run deployment (`asia-southeast1`), Firestore Memory, Pub/Sub Event Ingestion, and W3C Trace context propagation across nodes.
  - **Optional 5-second security beat, if the pacing allows** — run `python scripts/doctor.py` and let the 10-check report land on screen. It is a single command that shows the deployed revision is healthy, the Firestore TTL policy is ACTIVE, and no credential is stored in cleartext. If you'd rather say one sentence than show a table: *"Every credential reaches the container as a Secret Manager reference, and a preflight check refuses to deploy without them."* ⚠️ Only show this **after** redeploying — on the current revision that check reports FAIL, which is the opposite of the point. (Do NOT say "sub-250ms" on camera — that number is from a `time.sleep()` simulation script, not measured Gemini latency; see `docs/trace_evidence.md` caveat. If a real Cloud Trace screenshot is captured before recording, use the real number instead — otherwise just show the span hierarchy/order, no latency claim.)
* **Visual 2 (3:05 - 3:20):** **4-Layer Deterministic ADK Eval Suite — 50/50 deterministic test cases passed**.
  - Show terminal output of `scripts/run_eval_suite.py --strict`:
    1. Safety & Security (15/15)
    2. Behavioral Discipline (15/15)
    3. Long-Term Memory (10/10)
    4. Learning Outcomes (10/10)
  - Say "**50 out of 50 deterministic test cases passed**", never "the system is 100% correct" — a judge will hear the difference.
  - **Strongest 15 seconds available if you have them:** *"We audited our own suite and found twelve tests that could not fail — one group was asserting that eight minus two is at least four. We rewired them to production code and now prove every case can go red by breaking the code on purpose."* This is a credibility gain, not an admission; it is also the core of the bonus blog post (ADR-019).
* **Visual 3 (3:20 - 3:30):** **Memory A/B Experiment Evidence**.
  - Show comparative graph: Stateless Baseline (repeated stagnant persona) vs. eduagent Persistent Memory (0% repeated stagnant interventions, 100% contextual adaptation).

---

### 🎬 Scene 5: Conclusion & Live Verification (3:30 - 4:00)
* **Visual:** Live Cloud Run URL, GitHub repository badge, and Judge 1-Click Showcase screen.
* **Voiceover:**
  > *"eduagent bridges the gap between individual Socratic coaching and scalable classroom intelligence. Fully deployed on Google Cloud, MIT/Apache-licensed, and verified with deterministic rigor.*  
  > *Experience eduagent live at our Cloud Run showcase link today."*

---

## 📋 Production Checklist for Video Recording

- [x] Full HD 1080p / 60 FPS recording.
- [x] Clear voiceover audio with subtitle captions.
- [x] Live Cloud Run instance demonstrated (no localhost-only captures).
- [x] Displaying OpenTelemetry Trace graph and Eval report summary table.
