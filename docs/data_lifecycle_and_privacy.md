# Student Data Lifecycle & Privacy Threat Model

> **Core Commitment:** `eduagent` is built following **Privacy by Design** principles, referencing educational data protection frameworks (such as FERPA & COPPA) as architectural north stars. Student data is never used to train foundation models, and multi-tenant isolation prevents cross-class data leakage.
>
> **Transparency Disclaimer:** These represent architectural privacy-by-design considerations, NOT formal legal compliance certifications for FERPA/COPPA.

---

## 1. Student Data Lifecycle

```mermaid
flowchart LR
    A["1. Ingestion<br>Text / OCR Submission"] --> B["2. In-Transit Processing<br>Sanitizer & Debate Loop"]
    B --> C["3. Session State<br>Firestore TTL 24h"]
    C --> D["4. Profile Memory<br>Taxonomy & Scores (Max 50)"]
    D --> E["5. Class Aggregation<br>Teacher Digest & Priority Index"]
    E --> F["6. Archival & Purge<br>Right-to-be-Forgotten"]
```

| Phase | Data Type | Storage Location | Retention Policy | Security Measures |
|---|---|---|---|---|
| **1. Ingestion** | Handwritten essay photo, raw text | RAM / Temp Buffer | Released immediately upon extraction | No persistent raw image storage on disk |
| **2. In-Transit** | Debate prompts, token streams | Google Cloud Run RAM | Request duration only (<10s) | TLS in-transit encryption managed by Google Cloud |
| **3. Session** | Debate turns 1–3 | `debate_sessions/{id}` | Automated 24h purge (TTL policy) | Scoped access strictly via `session_id` |
| **4. Profile Memory** | 4-axis cognitive scores, fallacy tags | `student_profiles/{id}` | Bounded to 50 most recent essays | Strict multi-tenant isolation by `class_id` |
| **5. Class Analytics** | Priority rankings, 15m mini-lesson | `class_digests/{class_id}` | 90 days (one semester) | Accessible solely by authorized teacher tokens |
| **6. Archival / Deletion** | All student identifiers & records | N/A | Hard deletion upon request (Right-to-be-Forgotten) | Batch deletion supported via administrative endpoints |

---

## 2. Data Classification Matrix

| Security Level | Data Fields | Operational Purpose | Access & Processing Controls |
|---|---|---|---|
| 🔴 **PII (Personally Identifiable Information)** | `name`, `student_id`, `class_id` | Student roster identification | Never forwarded in raw LLM prompts; scoped to local auth headers |
| 🟡 **Cognitive Metadata** | 4-axis scores, persona history, fallacy tags | Priority Index calculation & Socratic adaptation | Normalized categorical & numerical metrics, non-sensitive |
| 🟢 **Pedagogical Digest** | Class summary, 15m lesson plan | Teacher small-group intervention | Aggregated class-level data or anonymized student clusters |

---

## 3. STRIDE Security & Threat Model

| Threat | Attack Vector | eduagent Defense Architecture |
|---|---|---|
| **S - Spoofing** *(Identity Spoofing)* | Malicious actor impersonates a student or teacher to submit essays or read scores | HMAC-SHA256 tokens (`auth.py`) binding `user_id`, `class_id`, `role`, and `exp`. Signing secret **must** be supplied from Secret Manager in production: `auth.py::_resolve_session_secret()` causes the process to **fail boot** if running on Cloud Run (`K_SERVICE`) with a missing or default key (ADR-016). |
| **T - Tampering** *(Data Tampering)* | Student A overwrites records/scores of Student B via API | Server-side scoring at the Scorer node + deterministic ranking; `server.py::_verify_student_auth()` enforces that `role=student` tokens can only submit for their own `user_id`. For `/turn`, ownership is resolved from the session record itself (ADR-018). |
| **R - Repudiation** *(Action Repudiation)* | Student claims they never submitted an essay or participated in debate | Every turn logs an Idempotent Event ID, ISO UTC Timestamp, and OpenTelemetry Trace ID. |
| **I - Information Disclosure** *(Information Leakage)* | Student in Class A inspects scores or submissions from Class B (IDOR) | Scoped RBAC tokens: all `/api/classes/*` endpoints verify `token.class_id == target.class_id`. `/api/debate/turn` validates authorization **prior** to session lookup to prevent timing/existence oracle attacks. |
| **D - Denial of Service** *(Resource Exhaustion)* | `curl` loop on public endpoints exhausts Vertex AI quotas (cost-DoS) | Hard cap of 3 debate turns (`VALIDATOR.max_debate_turns`); **per-IP token bucket rate limiting** (`rate_limit.py`: burst 10 / 1 req per 5s for debate; burst 5 / 1 per 10s for login) returning `429` + `Retry-After`; strict payload size caps. Per-process buckets bound cost; production environments place Cloud Armor / API Gateway in front (ADR-017). |
| **E - Elevation of Privilege** *(Privilege Escalation)* | Student elevates role to teacher to inspect class dashboards | Role claim is protected within the HMAC-signed token; all teacher routes strictly require `required_role="teacher"` at the routing layer. |

> **Audit Note (Audit Wave 14 — Credential Storage):** An audit identified OAuth refresh tokens in plain environment variables. This was resolved (ADR-020): all 3 secrets are mounted from **Secret Manager** via `--update-secrets`, leaving only `valueFrom.secretKeyRef` pointers in the revision spec. An AST test (`tests/test_deploy_never_inlines_secrets.py`) and a check in `doctor.py` enforce this regression gate.
>
> **Audit Note (Audit Wave 12 — Threat Model Alignment):** Rate limiting and strict HMAC verification were fully implemented and validated with automated regression suites in `tests/test_student_endpoint_auth.py`.

---

## 4. Privacy & Regulatory Considerations

1. **Zero Foundation Model Training:** `eduagent` utilizes Google Cloud Vertex AI / Gemini Enterprise APIs configured with **Zero Data Retention** policies for model training.
2. **No Advertising or Monetization:** 100% of processed data is strictly used for school instructional workflows.
3. **Auditable Pedagogical Logic:** Teachers and administrators can inspect the reasoning and fallacy rules behind any intervention recommendation at any time.
4. **Design Boundaries:** This document details architectural privacy-by-design measures rather than formal statutory certifications.
