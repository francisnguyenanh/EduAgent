# Hackathon Eligibility & Originality Boundary Statement

> **Submission Certification:** All code, prompts, schemas, workflows, and evaluation suites in the
> **EduAgent** repository were written from scratch during the All Things Agentic Hackathon
> Submission Period.

## 0. Mandatory Disclosure — the author's prior work

*(Added in Audit Wave 24. This document previously described its prior art only as a generic
"single-turn Q&A chatbot" and never named the author's own earlier project — which, read on its own,
implied there was no prior work to disclose. Rules §6 "New Projects Only" requires the opposite:
"must disclose any other pre-existing code or work incorporated into the Project.")*

**This architecture is inspired by the author's prior hackathon entry, CritiqAI** — a multi-agent AI
debate coach built with ADK, which placed in the top 12 of 6000+ teams at the Kaggle/Google AI Agents
Intensive Vibe Coding Capstone (Agents for Good — Education track). What carried over is **experience
and pedagogical principle, not source code**:

| Carried over | Not carried over |
|---|---|
| The core pedagogical thesis — challenge the student's reasoning rather than correct their text | Any line of CritiqAI's source, prompts, schemas, or evals |
| Architectural lessons learned, documented as a case study in `overview/PROJECT_WIKI.md` §9 | Its agent graph, persona definitions, data model, or infrastructure |

CritiqAI's source was kept locally as reference material only and is excluded from this repository's
git history by the **first line** of `.gitignore` (`CritqAI-main/`). Verified 2026-08-27 —
`git rev-list --all --objects | grep -i critq` returns **no results**, i.e. no object with that path
has ever entered this repository at any commit on any branch. Everything in the table in §1 below was
designed and built during this Submission Period.

---

## 1. Original Contribution Boundary Statement

To provide full transparency to judges, the table below delineates the baseline prior art — both the
generic state of the art and, where relevant, the author's own earlier work disclosed in §0 — from
the novel architectural contributions developed during this hackathon:

| Area | Baseline / Prior Art | Novel EduAgent Contribution |
|---|---|---|
| **Interaction Paradigm** | Single-turn Q&A chatbot / direct answer generator | **Autonomous 3-Turn Socratic Debate Loop** with 4 specialized pedagogical personas and a strict zero-answer-leak constraint. |
| **Agent Memory** | Stateless (each session is isolated and forgotten) | **Persistent Long-Term Memory (Firestore)**: Tracks longitudinal student profiles across weeks, resolves persona stagnation streaks, and computes empirical score trajectories. |
| **Class-Level Synthesis** | None (students are isolated islands) | **Class-Wide Systemic Fallacy Clustering & Intervention Priority Index**: 100% deterministic ranking algorithm (ZERO LLM-as-judge). |
| **Teacher Co-Pilot Tools** | None | **Autonomous Teacher Action Loop**: Automatically synthesizes 15-minute targeted mini-lesson plans, streams Google Sheets audit rows, generates Gmail drafts, and drafts parent outreach updates. |
| **Evaluation Rigor** | Subjective LLM-as-judge evaluation | **4-Layer Deterministic ADK Eval Suite (50/50 tests passed)**: Falsifiable, sabotage-tested deterministic verification across Security, Behavior, Memory, and Cognitive Growth. |
| **Production Architecture** | Localhost mock scripts | **Google Cloud Native Microservices**: Cloud Run (`asia-southeast1`), Cloud Trace distributed tracing, Event-driven Pub/Sub with DLQ, and Firestore TTL policies. |

---

## 2. Codebase Standards & Licensing

* **License:** **All Rights Reserved** (Copyright (c) 2026 francisnguyenanh). The repository is
  public for evaluation and transparency; that is deliberately *not* the same as an open-source
  grant. `LICENSE` carries one explicit exception: a perpetual, irrevocable, royalty-free licence
  to Google, Devpost and the judges to use, reproduce, adapt and promote this Project for contest
  evaluation — mirroring Official Rules §12, and written so this notice cannot be read as
  restricting the unrestricted testing access §6 requires.
  > *Audit Wave 27 correction: this section was headed "Open Source Licensing" and asserted "MIT
  > License / Open Source". The Official Rules impose no licensing requirement on an entrant's own
  > work; MIT had been adopted only because this document already claimed it. Since MIT actively
  > permits closed-source commercial reuse, which is not the author's intent, both the licence and
  > this claim were corrected. All third-party dependencies remain under their own licences, and
  > the project still contains zero proprietary closed-source dependencies.*
* **Code Standards:** 100% type-annotated Python (FastAPI, Google GenAI SDK, Pydantic v2, OpenTelemetry), structured error boundaries, and measured test coverage — **327 pytest cases** (`pytest -q -m "not e2e"`, re-measured 2026-08-28) and **88% statement coverage** over `src/eduagent`, measured 2026-08-27 when the suite stood at 309 tests. Coverage requires a tool that is deliberately *not* a runtime dependency, so reproduce it with `pip install pytest-cov && pytest --cov=src/eduagent --cov-report=term -q -m "not e2e"`. Plus **50 deterministic eval benchmarks**, every one of them sabotage-verified as capable of failing (ADR-019).

> *Audit Wave 27 correction: this line previously read "274 pytest cases, 86% statement coverage" while `README.md` said "309 tests, 88%" — two different figures for the same measurement on the same date, and the command quoted as evidence failed with `unrecognized arguments: --cov` because `pytest-cov` is not declared in `requirements.txt`. Both numbers and the reproduction instructions are now stated accurately.*
* **Compliance Commitment:** Built strictly with standard public Google Cloud Platform services and open APIs, containing zero proprietary closed-source dependencies.
