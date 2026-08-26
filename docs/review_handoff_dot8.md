# Review Handoff — EduAgent (All Things Agentic Hackathon, Track: Collaborative Partner)

> Purpose of this document: Summarize the issues identified and resolved during the audit review window (Waves 6→8), allowing an external reviewer to **independently verify** all claims. Every "resolved" item includes concrete CLI commands to re-verify.
>
> ⚠️ **HISTORICAL AUDIT SNAPSHOT (WAVES 6→8).** Retained intentionally for engineering provenance. Do not use legacy numbers in this document as current status. The codebase has evolved: `doctor.py` now includes **10 checks**, the test suite has **>240 tests**, and there are **21 ADRs**. Subsequent audit waves (Waves 11→15) caught additional critical items (sabotage testing for eval falsifiability, production signing key rotation, and Secret Manager credential mounting). See `README.md` Section 4 for current status.

---

## 1. Context & Scoring Rubric

- Repo: `eduagent` — two-tier system (ADK2 + Gemini/Vertex AI + Firestore + Pub/Sub + Cloud Run).
- Score Matrix: Innovation & Utility 40%, Architectural Discipline 30%, **Demo & Readiness 30%**, Bonus +0.4 pts.
- Target Deadline: August 31, 5:00 PM PT (with target submission 24h prior).

---

## 2. Findings & Resolutions

### 2.1 Scope Management
Original brainstorming included speculative features (voice mentors, sandbox simulators, SSE live feed) which threatened submission focus. Scope was pruned to prioritize the high-impact **Metacognitive Self-Correction Loop** while keeping core architecture tight and verifiable.

### 2.2 🔴 BLOCKER — Cloud Run Authentication Architecture Alignment
**Discovery:**
The deployed Cloud Run service was configured with `--allow-unauthenticated` for public demo evaluation, but `POST /` received unauthenticated webhook hits without signature verification.

**Resolution:**
- Implemented `src/eduagent/server.py::_verify_pubsub_push_auth()` using `google.oauth2.id_token.verify_oauth2_token` to verify Google-signed OIDC push tokens before executing `process_event()`.
- Added test coverage in `tests/test_server.py`.
- Formulated **ADR-014**.

**Independent Verification:**
```bash
curl -X POST https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/ -d '{}'
# Expect: 401 Unauthorized
curl https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/
# Expect: 200 OK (Public UI remains accessible)
pytest tests/ -q -m "not e2e"
```

### 2.3 🔴 BLOCKER — Pub/Sub Subscription Push Migration
**Discovery:**
The Pub/Sub subscription `class-aggregator-sub` was initially created in pull mode, preventing automated trigger execution on Cloud Run.

**Resolution:**
- Updated subscription configuration to push mode targeting the deployed Cloud Run endpoint with authenticated OIDC service account headers:
  `gcloud pubsub subscriptions update class-aggregator-sub --push-endpoint=<url>/ --push-auth-service-account=eduagent-sa@...`
- Verified end-to-end event triggering with a published test event.

---

## 3. Verified Security & Infrastructure Baseline

- **Secrets Hygiene:** `.env` and `secrets/` are fully gitignored; repository history scanned for leaked credentials.
- **Continuous Integration:** Automated GitHub Actions workflow enforces test runs and the AST gate (`test_gmail_mcp_never_sends.py`).
- **Deterministic Eval Suite:** 50/50 tests passing across all 4 layers without LLM-as-judge dependency.

---

## 4. Summary Matrix

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | Scope control on extra features | Advisory | Trimmed to high-ROI features |
| 2 | Pub/Sub push authentication verification | 🔴 Blocker | ✅ Resolved & verified |
| 3 | Pub/Sub subscription push mode transition | 🔴 Blocker | ✅ Resolved & verified |
| 4 | Secret Manager migration for all credentials | 🔴 Blocker | ✅ Resolved & verified (ADR-020) |
| 5 | Falsifiable test suite verification | 🟡 Rigor | ✅ Sabotage tested (ADR-019) |
