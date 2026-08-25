# Video Script: eduagent — The Autonomous Collaborative Partner for Critical Thinking

> **Target Duration:** Exactly 3:45 - 4:00 minutes  
> **Narrative Arch:** Problem → Single-Student Adaptive Trajectory (Proof of Partner) → Autonomous Teacher Synthesis → Production Architecture & Deterministic Eval Suite → Vision.

---

## ⏱️ Timeline & Shot Breakdown

```mermaid
timeline
    title 4-Minute Submission Video Arc
    00:00 - 00:40 : The Problem (AI as Cheat Engine vs Cognitive Partner)
    00:40 - 01:45 : Single-Student Proof Sequence (Socratic Debate, Memory Adaptation, Metacognition)
    01:45 - 02:45 : Autonomous Class Synthesis (Priority Engine, Mini-Lesson, Parent Note)
    02:45 - 03:30 : Architectural Rigor (Cloud Run, Trace, 4-Layer ADK Eval 50/50, Memory A/B)
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
  - The Scorer evaluates the cognitive delta: **Evidence Quality leaps from 2/10 to 8/10 ($\Delta = +6.0$)**.

---

### 🎬 Scene 3: Autonomous Class Synthesis & Teacher Action Loop (1:45 - 2:45)
* **Visual 1 (1:45 - 2:10):** Switch to Teacher Dashboard (`c1`). 
  - Show the **Intervention Priority Index**: Ranked strictly by a deterministic rule engine (ZERO LLM-as-judge).
  - Binh is flagged at Priority 1.5 due to a stuck streak and common fallacy.
* **Visual 2 (2:10 - 2:30):** **Actionable 15-Minute Mini-Lesson**.
  - Show the newly generated class digest: The system detected 3 students struggling with *Unsupported Claims* and synthesized a 3-step in-class workshop with concrete examples and counterexamples.
* **Visual 3 (2:30 - 2:45):** **1-Click Parent Progress Note**.
  - Click on Binh -> Generate Note. Gemini drafts an empathetic progress report citing Binh's cognitive breakthrough (do NOT say "FERPA-compliant" on camera — this is a privacy-by-design prototype, not a legally certified product).

---

### 🎬 Scene 4: Architectural Discipline & Empirical Evaluation (2:45 - 3:30)
* **Visual 1 (2:45 - 3:05):** Architecture Diagram & Google Cloud Trace.
  - Show live Google Cloud Run deployment (`asia-southeast1`), Firestore Memory, Pub/Sub Event Ingestion, and W3C Trace context propagation across nodes. (Do NOT say "sub-250ms" on camera — that number is from a `time.sleep()` simulation script, not measured Gemini latency; see `docs/trace_evidence.md` caveat. If a real Cloud Trace screenshot is captured before recording, use the real number instead — otherwise just show the span hierarchy/order, no latency claim.)
* **Visual 2 (3:05 - 3:20):** **4-Layer Deterministic ADK Eval Suite (50/50 PASS)**.
  - Show terminal output of `scripts/run_eval_suite.py --strict`:
    1. Safety & Security (15/15)
    2. Behavioral Discipline (15/15)
    3. Long-Term Memory (10/10)
    4. Learning Outcomes (10/10)
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
