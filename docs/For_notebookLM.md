# EduAgent — Comprehensive NotebookLM Reference Document
> Comprehensive summary of architecture, design philosophy, empirical results, and engineering decisions for **EduAgent**.
> Prepared for hackathon presentation slides, video demos, and project review.

---

## SECTION 1: CONTEXT & CORE PROBLEM

### 1.1 Real-World Problem (BYOF — Bring Your Own Friction)

**Classroom Reality:**
- Overcrowded classrooms (40+ students per educator).
- Teachers lack the time to provide granular, classroom-wide, individualized Socratic feedback on writing assignments.
- Mainstream AI writing assistants (ChatGPT, bare LLM wrappers) act as **Answer Machines**, short-circuiting learning by delivering ready-made text that students copy-paste rather than think through.
- The students who need intervention the most are often in **rural or under-resourced schools** with high student-to-teacher ratios. Physical geography should not be a barrier to high-quality pedagogical mentorship.

**Critical Consequences:**
- Students learn how to prompt an AI for answers rather than construct logical arguments.
- Independent critical-thinking and reasoning skills atrophy.
- Educators lose visibility into which students are struggling with fundamental conceptual gaps.

### 1.2 Core Project Philosophy

> **"Using AI to teach students how NOT to depend on AI."**

A modern Socratic pedagogical framework:
- The agent **NEVER** supplies the answer and **NEVER** writes or fixes the essay for the student.
- The agent acts as an adversarial Collaborative Partner, asking probing questions that compel students to self-diagnose and correct their reasoning.
- Every question targets the student's persistent argumentative weaknesses derived from long-term memory.

### 1.3 Project & Hackathon Metadata

| Information | Details |
|---|---|
| **Project Name** | EduAgent — Collaborative Partner Socratic Mentor |
| **Hackathon** | All Things Agentic Hackathon (Google Cloud) |
| **Track** | Collaborative Partner |
| **Submission Window** | August 3, 2026 – August 31, 2026 |
| **Live Demo URL** | https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/ |
| **Demo Passcodes** | Student `eduagent2026` / Teacher `eduagent-teacher-2026` (separate by design, ADR-025) |

### 1.4 Equitable Access Mission

**Core Philosophy:** AI was born in the cloud—but its power shouldn't be limited by geography. Every student, rural or urban, deserves **a true cognitive partner**—not a ready-made answer engine.
- **Equitable Access:** EduAgent does not discriminate between urban and rural students—with just an internet connection, any student can access high-quality Socratic mentoring.
- **No Teacher Replacement:** The system amplifies the capability of overloaded teachers instead of replacing them. The teacher remains the final decision-maker.
- **Pedagogical Goal:** **Don't give every student an answer. Give every student a reason to think.** This is the architectural bet we make.

---

## SECTION 2: SYSTEM ARCHITECTURE — 2-TIER EVENT-DRIVEN DESIGN

### 2.1 Architectural Overview

The system is split into **two decoupled tiers**, communicating asynchronously via Pub/Sub:

```
TIER 1: Per-Student Adaptive Socratic Pipeline
→ Individualized processing upon essay submission (Typed text, Google Doc, or handwritten photo).
→ Implemented as an automated ADK2 Graph Workflow.

TIER 2: Class Aggregator & Teacher Co-Pilot
→ Aggregates class-wide data and ranks student intervention urgency deterministically.
→ Synthesizes actionable 15-minute mini-lesson plans, streams audit log rows to Google Sheets, and drafts Gmail digests.
```

**End-to-End Data Flow:**
> Student submits essay (Text / Photo) $\rightarrow$ OCR extracts verbatim text $\rightarrow$ Student reviews and may correct it before the debate opens (ADR-029) $\rightarrow$ Sanitizer strips prompt injections $\rightarrow$ Summarizer diagnoses argument flaws $\rightarrow$ Persona Selector picks adaptive persona $\rightarrow$ 3-turn Socratic debate $\rightarrow$ 4-axis cognitive scoring $\rightarrow$ Profile Mutator writes to Firestore $\rightarrow$ Pub/Sub event published $\rightarrow$ Cloud Run Aggregator receives event $\rightarrow$ Priority Engine calculates ranking $\rightarrow$ Gmail Draft (HITL gate) & Google Sheets audit row created.

### 2.2 Tier 1 — Graph Nodes Breakdown

```
[Essay Input] → intake → [OCR if image → student reviews/corrects the transcription, ADR-029] → sanitizer → summarizer
               → persona_selector → debate_loop ↔ challenge_validator
               → cognitive_scorer → profile_mutator → [Firestore]
                                                          ↓
                                                 [Pub/Sub event]
```

| Node | Implementation Type | Function |
|---|---|---|
| **intake** | FunctionNode (deterministic) | Ingests input, detects format (text/image/gdoc), routes execution |
| **multimodal_ocr** | FunctionNode (Gemini Vision + Gemma 4) | Transcribes handwriting verbatim, then re-transcribes with a different model family and compares the two with `difflib` (cross-model consistency check, ADR-028) |
| **sanitizer** | FunctionNode (regex) | Guards against prompt injection; enforces payload size limits |
| **summarizer** | FunctionNode (Gemini Flash) | Extracts claims and structures fallacy taxonomy |
| **persona_selector** | FunctionNode (deterministic) | Selects debate persona based on score trajectory and newly diagnosed flaws |
| **debate_loop** | FunctionNode (Gemini Flash) | Manages 3-turn Socratic questioning with strict persona anchoring |
| **challenge_validator** | FunctionNode (ZERO LLM) | Validates outputs: intercepts answer leaks, multi-question output, formatting breaches |
| **cognitive_scorer** | FunctionNode (Gemini Flash) | Evaluates 4-axis argumentative cognitive rubric |
| **profile_mutator** | FunctionNode (Firestore) | Commits atomic updates to longitudinal student profile |

> **Architectural Rigor (Audit Wave 12):** All **9/9 nodes are `FunctionNode` instances**—there is no `AgentNode` anywhere in `src/` (`grep -rn "AgentNode" src/` returns 0 matches; see `src/eduagent/graph/tier1_pipeline.py`). While three nodes call Gemini, they do so *inside* deterministic Python functions with explicit timeouts, retry policies, and graceful fallback paths.

#### 4 Socratic Debate Personas

- **The Skeptic:** Triggered by unsourced empirical claims. Demands verifiable data and citations.
- **The Devil's Advocate:** Triggered by one-sided bias. Argues the opposing perspective.
- **The Nitpicker:** Triggered by logical leaps and non sequitur fallacies. Probes premises.
- **The Expander:** Triggered by hasty generalizations. Explores edge cases and context boundaries.

#### Cognitive Radar Chart — 4 Reasoning Axes

Evaluates student progression across a 4-dimensional SVG radar polygon:
1. **Logical Coherence:** Tightness of inferences and validity of conclusions.
2. **Evidence Quality:** Reliance on verifiable empirical data over anecdotal claims.
3. **Counterargument Handling:** Capacity to anticipate and refute opposing viewpoints.
4. **Scope Awareness:** Nuance and recognition of boundary conditions.

---

## SECTION 3: EMPIRICAL PEDAGOGICAL EVIDENCE

### 3.1 Memory A/B Experiment

Empirical validation across a controlled 3-essay trajectory for student "Binh" exhibiting persistent reasoning flaws:

| Comparative Metric | Branch A: Stateless Baseline (No Memory) | Branch B: EduAgent (Long-Term Memory) |
|---|---|---|
| **Intervention Sequence** | `skeptic → skeptic → nitpicker` (Stagnant loop) | `skeptic → expander → nitpicker` (Adaptive rotation) |
| **Repeated Stagnant Interventions** | **1 occurrence** (Repeated Skeptic causing fatigue) | **0 occurrences** (100% streak-breaking adaptation) |
| **Prior Weakness Context Injection** | **0/3 essays** (History-blind) | **2/3 essays** (Explicit longitudinal prompting) |
| **Teacher Priority Ranking** | **0.0** (No accumulation) | **1.5** (Accurate multi-dimensional flag) |

### 3.2 Learning-Outcome Delta Measurement

**Measurement Methodology:** 8 controlled thesis pairs (weak thesis vs. Socratically-revised form) are evaluated through the **real production pipeline**: `summarize_essay()` → `score_essay()` against Vertex AI. The scorer evaluates one text at a time, blind to the Socratic dialogue and blind to which text represents the revision.

* **Improvement Rate on Targeted Axis:** **7/8 scenarios (88%)** — the `AI in High School Classrooms` scenario did not improve (1.0 → 1.0), and this exact result is preserved rather than hand-tuned.
* **Mean Targeted Axis Delta ($\Delta_{\text{targeted}}$):** **+2.75 / 10 points**.
* **Mean Overall Score Delta ($\Delta_{\text{overall}}$):** **+2.05 / 10 points**.
* **Concrete Example (Evidence Quality):**
  - *Initial:* *"Electric cars are completely clean and produce zero pollution anywhere."* → scored **0.5/10**.
  - *Revised:* *"While EVs produce zero tailpipe emissions, lifecycle studies show a 40-60% net reduction..."* → scored **2.5/10** (delta **+2.0**).
* **Limitations:** $n = 8$ author-constructed thesis pairs, not 8 live classroom students; no separate control group. This benchmark tests whether the production scorer registers the specific cognitive shifts targeted by each persona.

---

## SECTION 4: SECURITY & PRIVACY BY DESIGN

### 4.1 Student Data Lifecycle

1. **Ingestion:** Text and images processed in Cloud Run memory.
2. **In-Transit:** TLS encryption managed by Google Cloud; no raw images persisted to disk.
3. **Session State:** Debate turns stored in Firestore with an automated 24h TTL policy.
4. **Persistent Profile Memory:** Bounded storage capping history to the 50 most recent essays per student.
5. **Class Analytics:** Class digests retained for 90 days (one semester) before archiving.

### 4.2 STRIDE Threat Model & Mitigations

- **Spoofing:** HMAC-SHA256 tokens binding `user_id`, `class_id`, `role`, and `exp`. Signing secret loaded from Secret Manager; `auth.py` **refuses to boot** on Cloud Run if the default public secret is detected (ADR-016).
- **Tampering:** Scoring logic executes strictly server-side; student debate endpoints verify that `role=student` tokens match the target `user_id` (ADR-018).
- **Repudiation:** Immutable logging of Pub/Sub Event IDs, UTC timestamps, and OpenTelemetry trace headers.
- **Information Disclosure:** Tenant scoping rejects requests where `token.class_id != path.class_id`. `/api/debate/turn` verifies auth prior to session lookup to avoid existence oracles.
- **Denial of Service:** Hard cap of 3 debate turns, input size bounds, and **per-IP token-bucket rate limiting** (`rate_limit.py`) returning `429` + `Retry-After` (ADR-017).
- **Elevation of Privilege:** HMAC payload prevents role tampering; teacher routes enforce `role == "teacher"`.

> **Deployment Security (Audit Wave 14):** All credentials (session secret, Gmail token, Sheets token) are mounted from Secret Manager via `--update-secrets` (ADR-020), eliminating cleartext tokens from Cloud Run revision specs. Enforced via AST build tests and preflight diagnostic scripts.

---

## SECTION 5: OPERATIONAL PRODUCTION FEATURES

### 5.1 Dual-Pass OCR Self-Consistency Check
- **Issue:** Vision models can hallucinate plausible text from blurry photos while self-reporting "high" confidence.
- **Solution:** Transcribe twice independently — first pass Gemini Vision, second pass **Gemma 4** so the two errors are uncorrelated — and compute a `difflib` similarity ratio on the raw texts, using a threshold calibrated separately for cross-model (0.50) vs same-model (0.75) comparison. If diverged, downgrade confidence to `low` and park in `pending_essays` review queue without polluting student profile records (ADR-007, ADR-008, ADR-028).

### 5.2 Automated 15-Minute Actionable Mini-Lesson Plan
- Triggered when $\ge 2$ distinct students exhibit a shared fallacy pattern (`priority_engine.MIN_STUDENTS_FOR_COMMON_FALLACY = 2`):
  - Actionable topic title and pedagogical objective.
  - Structured 3-step classroom activity.
  - 1 Fallacy example + 1 Exemplar counter-model for board dissection.

### 5.3 Gmail Human-In-The-Loop (HITL) Gate
- Drafts are composed and injected directly into the teacher's Gmail **Drafts** folder.
- The teacher must manually review and press "Send". An AST test (`test_gmail_mcp_never_sends.py`) gates against `.send()` calls in the codebase (ADR-001).

---

## SECTION 6: 4-LAYER DETERMINISTIC ADK EVAL SUITE (50/50 PASSED)

Zero LLM-as-judge dependency to eliminate reward-hacking loops. Output validated using deterministic assertions and regex pattern matching.

**Automated Benchmark Results (`scripts/run_eval_suite.py --strict`):**

| Evaluation Layer | Passed Cases | Total Cases | Pass Rate |
|---|:---:|:---:|:---:|
| **Layer 1: Safety & Security** (Answer leak, Prompt injection, IDOR Isolation) | 15 | 15 | **100%** |
| **Layer 2: Behavioral Discipline** (Persona fidelity, Single-Q constraint, Bounds, Escalation) | 15 | 15 | **100%** |
| **Layer 3: Long-Term Memory** (Streak breaking, Trend slope, Context injection) | 10 | 10 | **100%** |
| **Layer 4: Learning Outcomes** (Metacognitive Delta, Breakthrough tracking) | 10 | 10 | **100%** |
| **TOTAL** | **50** | **50** | **100% PASS** |

---

## SECTION 7: SUMMARY OF ARCHITECTURE DECISION RECORDS (ADRs)

* **ADR-001:** Code-level Gmail least-privilege enforcement (AST test gating `.send()`).
* **ADR-002:** `gemini-3.5-flash` & `gemini-3.7-flash` selection for Vertex AI availability.
* **ADR-003:** Pub/Sub `max_delivery_attempts = 5` honoring platform limits.
* **ADR-004:** English taxonomy persistence in `fallacies_draft` for deterministic persona matching.
* **ADR-005 / ADR-015:** Durable Firestore session storage with 3-second bounded in-memory cache.
* **ADR-006:** Zero LLM-as-judge deterministic evaluation harness.
* **ADR-007:** Dual-pass OCR self-consistency cross-check with `difflib` (extended cross-*model* by ADR-028).
* **ADR-008:** Routing degraded OCR to `pending_essays` to protect profile integrity.
* **ADR-009:** 60s multimodal API timeout accommodating complex vision payloads.
* **ADR-010:** Reusing Pub/Sub `event_id` as `digest_id` for idempotent dedup.
* **ADR-011:** `/health-check` path avoiding Knative/Istio `/healthz` interception.
* **ADR-012:** Layered REST API boundary sanitization and payload limits.
* **ADR-013:** Stateless HMAC-signed scoped access tokens preventing IDOR.
* **ADR-014:** Application-layer OIDC token verification for Pub/Sub push endpoints.
* **ADR-016:** Mandatory Secret Manager session secret with fail-fast boot protection.
* **ADR-017:** Per-IP token-bucket rate limiting bounding Vertex AI costs.
* **ADR-018:** Bearer token authentication required on all student debate endpoints.
* **ADR-019:** Falsifiable evaluation cases validated via sabotage testing.
* **ADR-020:** Mounting all credentials via Secret Manager references (`secretKeyRef`).
* **ADR-021:** Purpose-built interactive debate bridge over complex agent loops.
* **ADR-022:** `/api/debate/reflect` bound to a completed session; single-use claim prevents `growth_bonus` farming.
* **ADR-023:** Least-squares slope + `volatile` verdict so a mid-window score collapse is not read as `stagnant`.
* **ADR-024:** An LLM outage records the reflection as *unevaluated* (`resolved=false`) instead of minting a breakthrough; `growth_bonus` clamped to 0.0-1.0; the reflection claim is transactional.
* **ADR-025:** Teacher token *issuance* separated from the public demo passcode (`EDUAGENT_TEACHER_PASSWORD`), closing the half of ADR-016 that stayed open.
* **ADR-026:** Rate-limit key taken from the **last** `X-Forwarded-For` hop; the first entry is caller-supplied and made the limiter bypassable with one header.
* **ADR-027:** Session reads prefer Firestore; a second unbounded in-process cache had shadowed ADR-015's 3-second bound on the path every request takes.
* **ADR-028:** The OCR cross-check's second pass runs **Gemma 4** (a different model family), not a second Gemini call; the cross-model similarity threshold is a separate constant (0.50) because 0.75 sits inside the cross-model legible cluster.
* **ADR-029:** Image/Doc ingest split into `extract` then `start`, so a student reads and corrects the transcription before it becomes the essay of record. `cross_check_model` is surfaced by the `extract-image` response.
* **ADR-030:** The teacher dashboard renders the Gmail draft's own body (`digest_html`) plus a deep link, because the draft is created in the system mailbox. Auto-send was rejected as it would remove the ADR-001 gate.

---

## SECTION 8: 10-SLIDE PRESENTATION STRUCTURE

### Slide 1: The Problem — AI as an "Answer Machine"
- Direct generation tools bypass critical thinking; students copy-paste rather than reason.
- Overworked teachers cannot give individualized feedback to 40+ students.
- Video Hook: *"AI was born in the cloud. But its power shouldn't be limited by geography. Every student, rural or urban, deserves a partner that makes them think."*

### Slide 2: The Vision — EduAgent: Collaborative Socratic Partner
- *"Using AI to teach students how NOT to depend on AI."*
- Adversarial questioning model targeting argumentative blind spots.
- Action Philosophy: *"Don't give every student an answer. Give every student a reason to think."*

### Slide 3: 2-Tier Event-Driven Architecture
- Tier 1: Per-Student Adaptive Socratic Pipeline (Google ADK2 Workflow).
- Tier 2: Class Aggregator & Teacher Co-Pilot (Cloud Run + Pub/Sub).

### Slide 4: Adaptive Socratic Pipeline (Tier 1)
- 9-node graph: Ingest $\rightarrow$ OCR $\rightarrow$ Sanitize $\rightarrow$ Summarize $\rightarrow$ Debate / Validate $\rightarrow$ Score $\rightarrow$ Mutate.

### Slide 5: Long-Term Memory & Adaptation Proof
- Memory A/B experiment: Dynamic persona rotation, context injection, zero stagnant repetition.

### Slide 6: Metacognitive Self-Correction Loop & Delta Scoring
- Objective metric: $\Delta = \text{Score}_{\text{after}} - \text{Score}_{\text{before}}$.
- Production scorer evaluation: mean $+2.75/10$ improvement on targeted axis; 7/8 scenarios positive.
- The metric refuses to inflate itself (ADR-024): a Vertex AI outage records the attempt as *unevaluated* rather than as a breakthrough, and the model-supplied `growth_bonus` is clamped to its declared 0.0-1.0 range instead of trusted. `breakthrough_count` only ever counts evaluations that actually happened.

### Slide 7: Tier 2: Teacher Co-Pilot Dashboard
- Deterministic Intervention Priority Index ranking students by urgency.
- Automated synthesis of class-wide 15-minute mini-lesson plans.

### Slide 8: Human-in-the-Loop & Security Controls
- Gmail Draft Creator (HITL Gate): Teacher reviews before sending.
- HMAC-signed scoped tokens, AST code gates, and Secret Manager credential isolation.

### Slide 9: 4-Layer Deterministic ADK Eval Suite (50/50 Passed)
- 50 test cases covering Security, Behavioral Discipline, Memory, and Learning Outcomes without LLM-as-judge.

### Slide 10: GCP Evidence & Live Demo
- Cloud Run live at `asia-southeast1` $\rightarrow$ Concurrency 80, event-driven design allowing Tier 1 and Tier 2 to scale independently under concurrent submission load.
- Google Sheets audit log automatically recorded when student completes.

---

## SECTION 9: ORIGINALITY BOUNDARY

To ensure complete transparency to hackathon judges:
- **Novel Contribution Statement:**
  > *"EduAgent's core contribution is NOT merely another Socratic debate chatbot. The breakthrough lies in the **2-Tier Event-Driven Agent Architecture** combining Student Long-Term Adaptive Memory, a Deterministic Teacher Pedagogical Dashboard, and a Metacognitive Self-Correction Loop that measures cognitive jumps."*
- **Source Availability:** 100% open-source under MIT/Apache licensing, with zero proprietary closed-source dependencies.

---

*Tài liệu được cập nhật đồng bộ với mã nguồn và kết quả thực nghiệm mới nhất của dự án EduAgent — All Things Agentic Hackathon 2026.*
