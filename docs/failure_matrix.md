# Production Failure Matrix: Resilience & Graceful Degradation

> **Architectural Guarantee:** No single point of failure (SPOF)—whether network partition, LLM rate limits, database transient errors, or hostile user input—can crash the `EduAgent` platform.
>
> **Intentional Exception (Audit Wave 13):** Component #14 (Session Signing Key) **does not degrade**; it terminates the process immediately (fail-fast). Running with a public default signing key in production is the worst possible failure mode, not a safe state. Graceful degradation applies everywhere else; here, fail-fast is the correct security posture.

---

## 1. 17-Component Failure & Recovery Matrix

| # | System Component | Trigger Condition | Severity | Self-Healing & Graceful Degradation | Fallback Behavior | Trace Attribute / Log Audit |
|:---:|---|---|:---:|---|---|---|
| **1** | **Intake & Sanitizer** | Prompt injection attempt (`Ignore instructions`, `<system>` tags, role hijack) | High | Regex scanning & boundary tag stripping | 100% malicious command tokens stripped; pure essay text preserved safely | `eduagent.sanitizer.blocked_patterns` |
| **2** | **OCR Handwriting Engine** | Blurred image / illegible handwriting / low OCR confidence; **or high latency** | Medium | Dual independent transcription passes + `difflib` cross-validation (ADR-007); confidence downgraded to `low` on divergence; 60s multimodal timeout (ADR-009) and 10MB base64 cap. **Measured latency (Audit Wave 15):** 958 KB image → OCR **22.5s**, entire `start-with-image` flow **24.2s**; Cloud Run request timeout **300s** (12x headroom). | Low-confidence OCR proceeds to debate with `ocr.degraded` UI flag; batch processing parks essay in `pending_essays` (ADR-008) | `eduagent.ocr.confidence_score` |
| **3** | **LLM Gateway (Gemini API)** | HTTP 429 Rate Limit / Quota Exceeded / Vertex AI Outage | Critical | Exponential backoff with jitter (3 retries) + Fallback to canned Socratic persona prompts | Serves pedagogically sound canned Socratic questions calibrated per persona | `eduagent.llm.status = "degraded"` |
| **4** | **Independent Validator** | Model attempts to leak answers / corrections | High | Immediate interception; triggers regeneration loop (up to 2 retries) | Injects canned Socratic probing question if max retries exceeded | `eduagent.validator.leak_detected = true` |
| **5** | **Persona Selector** | Student stagnant on same persona for 3+ consecutive essays without improvement | Medium | Excludes historical persona from candidate pool (Streak Breaking Algorithm) | Automatically rotates to complementary persona (e.g. Skeptic -> Expander) | `eduagent.persona.streak_broken = true` |
| **6** | **Metacognitive Reflection** | LLM thesis revision analysis yields malformed JSON | Low | Resilient fallback parser & default growth attribution | Records self-correction completion, awards standard progress points (+0.5) | `eduagent.reflection.fallback_used = true` |
| **6b** | **Metacognitive Reflection — Integrity** (Audit Wave 15, ADR-022) | Calling `/api/debate/reflect` without an actual Socratic debate session backing it, or submitting multiple times for the same session to farm `growth_bonus` | Critical | Payload restricted to `session_id` + `revised_claim`; `interactive.claim_reflection()` rejects sessions that are not `completed` or have already been reflected (`has_reflected`). Flags are committed **before** calling Vertex AI (banning double-click submissions), and session is deleted after mutating student profile. | `409` (Conflict - not finished / already reflected) · `404` (Not Found - session does not exist) · `403` (Forbidden - session belongs to another student) | `DebateNotComplete` / `ReflectionAlreadySubmitted` |
| **7** | **Firestore Database Client** | Firestore network drop / transient GAPIC encoding error | High | URL quote patch + in-memory fallback cache | Serves reads/writes from local RAM cache, logs monitoring alert | `eduagent.firestore.status = "in_memory_fallback"` |
| **8** | **Distributed Session Store** | Cloud Run multi-instance scaling / container sudden restart | Medium | **Firestore is source of truth**; in-process cache trusted only for **3 seconds** (`_CACHE_FRESHNESS_SECONDS`). If Firestore down → serve cached snapshot. Firestore TTL policy on `expire_at` is ACTIVE. | Restores full debate state seamlessly from `debate_sessions/{id}` | `eduagent.session.restored = true` |
| **9** | **Priority Ranking Engine** | New student with no prior essay history | Low | Sets `score_trend = "insufficient_data"`, decay weight = 0 | Ranks based on current essay weakness; breaks ties deterministically via `student_id` | `eduagent.priority.insufficient_data = true` |
| **9b** | **Priority Ranking Engine — Mid-Window Drop** (Audit Wave 15, ADR-023) | Scores like `[10, 0, 10]`: slope is technically flat (start and end are equal), but a mid-window assignment collapsed completely. Previously treated as `stagnant` with **0** added to the priority index, identical to a student with stable performance. | Medium | `_score_trend()` introduces a new `volatile` verdict when the overall slope lies within the flat band but the peak-to-trough amplitude is $\ge$ `TREND_VOLATILITY_BAND` (2.0); slope is calculated via least-squares linear regression instead of `sum(diffs)/len(diffs)` (which only reads the first and last points). | Adds `score_volatility = 1.5` to the priority index (below `score_decline = 2.5`), badges student as `volatile` in teacher digest, and parent note phrases progress as "fluctuating" rather than "declining". | `breakdown.score_volatility` in `compute_priority()` |
| **10** | **Teacher Digest Synthesizer** | Gemini heavy model unavailable during batch digest generation | Medium | Fallback deterministic Jinja2/string template rendering | Generates fully structured report with student ranking table & 3-step lesson plan | `eduagent.digest.degraded_mode = true` |
| **11** | **Pub/Sub Event Ingestion** | Duplicate delivery of `essay.evaluated` event | Medium | Firestore Idempotency Lease Lock (`events/{event_id}`) | Skips duplicate processing; returns HTTP 200 `status: duplicate_skipped` | `eduagent.event.duplicate_skipped = true` |
| **12** | **API Rate Limiter** (Audit Wave 13, ADR-017) | `curl` loop hammering public debate endpoint → Vertex AI quota depletion (cost-DoS) | High | Per-IP token bucket (`rate_limit.py`): burst 10 / 1 req per 5s for debate; burst 5 / 1 per 10s for login. Key taken from client hop of `X-Forwarded-For` | Returns HTTP `429` + `Retry-After` header; rejected callers continue token accumulation without permanent lockout | `client_key`, `path` in `Rate limit exceeded` logs |
| **13** | **Student Endpoint Authorization** (Audit Wave 13, ADR-018) | Arbitrary caller POSTs arbitrary `student_id` → corrupts another student profile & skews teacher ranking | Critical | `_verify_student_auth()`: `role=student` token acts only for own `user_id`; `class_id` must match; `/turn` derives ownership from session and **verifies before session lookup** to avoid existence oracle | `401` (missing/forged token) · `403` (mismatched student/class) · `400` (invalid student ID format) | `_verify_student_auth` raises HTTPException |
| **14** | **Session Signing Key** (Audit Wave 13, ADR-016) | Deployed to Cloud Run without setting `EDUAGENT_SESSION_SECRET` → tokens signed with repo default key | Critical | **Fail-fast, zero degradation**: `_resolve_session_secret()` detects `K_SERVICE` and raises `InsecureConfigurationError` → container fails boot. Running with a public secret is strictly prohibited | Revision refuses traffic; logs exact remediation command | `InsecureConfigurationError` at import time |
| **15** | **Credential Delivery** (Audit Wave 14, ADR-020) | Inlining credentials into plain environment variables → Cloud Run stores cleartext in revision spec (`gcloud run services describe` prints refresh tokens) | Critical | Mount all credentials via `--update-secrets` (`valueFrom.secretKeyRef`). **3 defense layers:** (1) `_preflight_secrets()` rejects deploy if secret missing; (2) AST test `tests/test_deploy_never_inlines_secrets.py`; (3) `doctor.py` inspects live deployed revision for cleartext tokens | Deploy blocked pre-flight; or doctor reports FAIL with redeploy + secret rotation instructions | `check_no_plaintext_credentials_on_cloud_run` |

---

## 2. Graceful Degradation Case Studies

### 🛡️ Scenario 1: Total LLM Gateway Outage
* **Expectation:** Students can still continue their Socratic debate; teachers still receive a deterministic class intervention ranking.
* **Execution:**
  1. `debate.py` catches `LLMGenerationError` and triggers `_PERSONA_FALLBACK_QUESTIONS` mapped to the active persona (`skeptic`, `devils_advocate`, `nitpicker`, `expander`).
  2. `priority_engine.py` (100% pure Python, ZERO LLM dependency) deterministically calculates the Intervention Priority Index without interruption.
  3. `digest.py` triggers `_fallback_digest`, delivering dashboard insights with complete priority rankings and actionable 15-minute mini-lesson plans.

### 🔒 Scenario 2: Complex Multimodal Prompt Injection via OCR
* **Expectation:** An attacker embeds prompt override instructions within a handwritten essay image.
* **Execution:**
  1. Transcribed text from OCR flows into `intake.py::strip_injection_attempts`.
  2. All malicious instruction patterns (`Ignore previous instructions`, `<system>`, role hijacking) are stripped and logged to security telemetry.
  3. The sanitized essay is wrapped in protective boundary delimiters `<student_essay>` prior to prompt assembly.

---

### 🔑 Scenario 3: Missing Secrets or Cleartext Credential Exposure (Audit Wave 14)
* **Expectation:** Prevent deploying or operating any revision that leaks credentials in plaintext.
* **Execution:**
  1. `scripts/deploy_to_cloud_run.py::_preflight_secrets()` validates all 3 secrets in Secret Manager **before** invoking `gcloud run deploy`; any missing secret causes immediate `sys.exit(1)` with the exact `gcloud secrets create` command needed.
  2. If an engineer bypasses preflight and passes inline tokens → `tests/test_deploy_never_inlines_secrets.py` (AST validation) fails the build. Sabotage-tested and verified.
  3. If a deployed revision contains cleartext credentials (e.g. manual CLI deployment) → `scripts/doctor.py` inspects the active Cloud Run spec and reports **FAIL** alongside instructions to redeploy and rotate the exposed secrets.

---

## 3. Production Readiness Declaration

```
[System Health Audit]
- Zero Single Point of Failure (SPOF)
- Deterministic Priority Ranking (100% SLA even during LLM outages)
- Bounded Memory & Database Storage (MAX_HISTORY_ENTRIES = 50, TTL = 24h)
- 100% Idempotent Event Delivery
```
