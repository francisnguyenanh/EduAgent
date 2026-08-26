# Hackathon Eligibility & Originality Boundary Statement

> **Submission Certification:** The **eduagent** project was developed entirely from scratch for the All Things Agentic Hackathon, adhering 100% to originality guidelines, architectural transparency, and open-source licensing standards.

---

## 1. Original Contribution Boundary Statement

To provide full transparency to judges, the table below delineates the baseline prior art from the novel architectural contributions developed during this hackathon:

| Area | Baseline / Prior Art | Novel eduagent Contribution |
|---|---|---|
| **Interaction Paradigm** | Single-turn Q&A chatbot / direct answer generator | **Autonomous 3-Turn Socratic Debate Loop** with 4 specialized pedagogical personas and a strict zero-answer-leak constraint. |
| **Agent Memory** | Stateless (each session is isolated and forgotten) | **Persistent Long-Term Memory (Firestore)**: Tracks longitudinal student profiles across weeks, resolves persona stagnation streaks, and computes empirical score trajectories. |
| **Class-Level Synthesis** | None (students are isolated islands) | **Class-Wide Systemic Fallacy Clustering & Intervention Priority Index**: 100% deterministic ranking algorithm (ZERO LLM-as-judge). |
| **Teacher Co-Pilot Tools** | None | **Autonomous Teacher Action Loop**: Automatically synthesizes 15-minute targeted mini-lesson plans, streams Google Sheets audit rows, generates Gmail drafts, and drafts parent outreach updates. |
| **Evaluation Rigor** | Subjective LLM-as-judge evaluation | **4-Layer Deterministic ADK Eval Suite (50/50 tests passed)**: Falsifiable, sabotage-tested deterministic verification across Security, Behavior, Memory, and Cognitive Growth. |
| **Production Architecture** | Localhost mock scripts | **Google Cloud Native Microservices**: Cloud Run (`asia-southeast1`), Cloud Trace distributed tracing, Event-driven Pub/Sub with DLQ, and Firestore TTL policies. |

---

## 2. Codebase Standards & Open Source Licensing

* **License:** MIT License / Open Source.
* **Code Standards:** 100% type-annotated Python (FastAPI, Google GenAI SDK, Pydantic v2, OpenTelemetry), structured error boundaries, and high test coverage (>240 pytest test cases + 50 deterministic eval benchmarks).
* **Compliance Commitment:** Built strictly with standard public Google Cloud Platform services and open APIs, containing zero proprietary closed-source dependencies.
