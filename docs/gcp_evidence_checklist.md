# GCP Evidence Checklist (Phase 7 — Verification & Artifact Collection)

> Purpose: Collect GCP Native evidence artifacts for the README and demo video. Log in to the Cloud Console using the project account and ensure the active project is `project-4fc36103-f4ca-49f6-883`.
>
> Per hackathon guidelines, proof of Google Cloud deployment can be demonstrated via the live `.run.app` URL and screen captures/recordings of the Cloud Console (Cloud Run dashboard, Vertex AI logs, Cloud Trace, etc.).
> Save all screenshots/clips in `assets/gcp_evidence/` for reuse in the demo video.

**Live Cloud Run Service URL:** `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app`
*Note: Opening this URL directly in a browser opens the Web Demo (Student/Teacher Portal), deployed with `--allow-unauthenticated`.*

---

## 🚀 Execution Plan for Generating Live Telemetry & Traces

Run the following scenarios to generate real traffic, logs, traces, and Firestore records before capturing evidence:

### Scenario 1: Execute Tier 1 Pipeline (Generate Trace Spans & Firestore History)
Run the demo script to trigger the full 9-node pipeline with Gemini and Firestore:
```bash
# Run Tier 1 demo with 3 consecutive essays to demonstrate memory adaptation & tracing
python scripts/demo_tier1_run.py
```
*Generated output:* 
- Live traces with nested `@traced_node` spans exported to **Google Cloud Trace**.
- Longitudinal student profile mutations written to **Firestore** (`student_profiles`).

### Scenario 2: Dispatch Events to Cloud Run & Pub/Sub (Generate Cloud Run Metrics & Logs)
Send requests directly to the deployed Cloud Run service:
```bash
# Verify Cloud Run health-check endpoint
curl -X GET https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/health-check

# Or verify subscriber & aggregator functionality
python scripts/verify_firestore.py
```

### Scenario 3: Access the Live Web Portal on Cloud Run
1. Open the browser and navigate to: `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app`
2. Test the Student Portal (submit an essay and engage in debate) and inspect the Teacher Dashboard.

---

## 📸 Capture Checklist & Screenshot Guidance

> [!TIP]
> Save all high-resolution screenshots into `assets/gcp_evidence/` in PNG format.

| # | Suggested Filename | GCP Service | Evidence Target |
|:---|:---|:---|:---|
| 1 | `01_cloud_trace_e2e_spans.png` | **Cloud Trace** | Real-time span waterfall hierarchy showing OpenTelemetry W3C tracing |
| 2 | `02_cloud_run_service_metrics.png` | **Cloud Run** | Live service in `asia-southeast1` showing Request/Latency/Memory graphs |
| 3 | `03_firestore_live_data.png` | **Firestore** | Schema of `student_profiles` & `class_analytics` documents |
| 4 | `04_pubsub_topic_dlq.png` | **Pub/Sub** | Topic `essay-evaluated` + Dead Letter Queue (DLQ) configuration |
| 5 | `05_cloud_logging_structured.png` | **Cloud Logging** | Structured JSON logs correlated with `logging.googleapis.com/trace` |
| 6 | `06_web_portal_live.png` | **Web UI** | Live UI running on the `.run.app` domain |
| 7 | `07_secret_manager_all_credentials.png` | **Secret Manager** | All 3 secrets present (`eduagent-session-secret`, `eduagent-gmail-token`, `eduagent-sheets-token`) mounted as secret references (`secretKeyRef`), not plaintext (ADR-016 & ADR-020) |
| 8 | `08_firestore_ttl_policy.png` | **Firestore** | TTL policy on `debate_sessions.expire_at` in **ACTIVE** state |
| 9 | `09_rate_limit_429.png` | **Cloud Run / Terminal** | HTTP **429 + `Retry-After` header** upon burst traffic (ADR-017) |
| 10 | `10_student_endpoint_401.png` | **Cloud Run / Terminal** | `curl` POST `/api/debate/start` without token returning **401**, and with mismatched student token returning **403** (ADR-018) |

---

### Step-by-Step Screenshot Instructions:

### 1. Cloud Trace — End-to-End Span Waterfall (`01_cloud_trace_e2e_spans.png`)
* **Navigation:** GCP Console $\rightarrow$ Search **Trace** (Trace Explorer).
* **Steps:** 
  1. Set time filter to **"Last 1 hour"**.
  2. Click a trace beginning with `eduagent.pipeline.essay_evaluation` or `eduagent.node.class_aggregator`.
  3. Expand the full waterfall span tree.
* **Key visible details:**
  - Span sequence: `intake` $\rightarrow$ `sanitizer` $\rightarrow$ `summarizer` $\rightarrow$ `persona_selector` $\rightarrow$ `debate_loop` $\rightarrow$ `cognitive_scorer` $\rightarrow$ `profile_mutator`.
  - Right drawer: Span attributes (`eduagent.student_id`, `eduagent.class_id`, `gemini.model`).
  - Actual measured pipeline duration.

### 2. Cloud Run — Dashboard & Metrics (`02_cloud_run_service_metrics.png`)
* **Navigation:** GCP Console $\rightarrow$ **Cloud Run** $\rightarrow$ select `eduagent-class-aggregator`.
* **Steps:**
  1. Service details view showing URL `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app` and green Active checkmark.
  2. Select **Metrics** tab $\rightarrow$ capture charts for **Request count**, **Request latency**, and **Container CPU/Memory allocation**.
* **Key visible details:** Active service in `asia-southeast1` processing traffic (2xx responses).

### 3. Firestore Database — Student Profiles (`03_firestore_live_data.png`)
* **Navigation:** GCP Console $\rightarrow$ **Firestore** $\rightarrow$ **Data**.
* **Steps:**
  1. Collection: `student_profiles`.
  2. Document: Select a student record (e.g. `stu_stuck` or newly evaluated test student).
  3. Fields: Expand `essay_history`, `weakness_tags`, `flags`, and `persona_streak`.
* **Key visible details:** Persistent NoSQL long-term memory document structure.

### 4. Pub/Sub & Dead Letter Queue (`04_pubsub_topic_dlq.png`)
* **Navigation:** GCP Console $\rightarrow$ **Pub/Sub**.
* **Steps:**
  1. Select **Subscriptions** $\rightarrow$ `class-aggregator-sub`.
  2. Scroll to **Dead lettering** section showing forwarded topic `essay-evaluated-dlq` and max delivery attempts = 5.
* **Key visible details:** Resilient event-driven architecture with DLQ failover.

### 5. Cloud Logging — Structured Logs (`05_cloud_logging_structured.png`)
* **Navigation:** GCP Console $\rightarrow$ **Logging** $\rightarrow$ **Logs Explorer**.
* **Steps:**
  1. Filter: `resource.type="cloud_run_revision" AND resource.labels.service_name="eduagent-class-aggregator"`
  2. Expand a successful JSON log entry.
* **Key visible details:** `logging.googleapis.com/trace` field correlating logs to Cloud Trace spans.

### 6. Live Web Portal on Cloud Run (`06_web_portal_live.png`)
* **Navigation:** Open browser in incognito mode $\rightarrow$ navigate to `.run.app` URL.
* **Steps:** Full screenshot showing the address bar domain `.asia-southeast1.run.app` and the active portal interface.

---

## Fast CLI Verification for Security Evidence (Reproducible by Judges)

The security protections (items #7–#10) can be verified directly via CLI/curl without console access:

```bash
URL=https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app

# (7) Verify all 3 secrets exist with zero plaintext credentials
gcloud secrets list --format='table(name.basename())' | grep eduagent
python scripts/doctor.py   # "No plaintext credentials on Cloud Run" must PASS

# Inspect revision spec to confirm secret references (secretKeyRef):
gcloud run services describe eduagent-class-aggregator --region asia-southeast1 --format=json \
  | python -c 'import json,sys; [print(("PLAINTEXT " if "value" in e else "secretRef  ")+e["name"]) for e in json.load(sys.stdin)["spec"]["template"]["spec"]["containers"][0].get("env",[])]'

# (8) Verify Firestore TTL policy is ACTIVE
gcloud firestore fields ttls list --collection-group=debate_sessions

# (9) Test Rate Limiting: burst 15 requests to observe 429 status codes
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST $URL/api/debate/start \
    -H 'Content-Type: application/json' -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'
done; echo

# (10a) Student Endpoint Auth: missing token returns 401
curl -s -o /dev/null -w "no-token: %{http_code}\n" -X POST $URL/api/debate/start \
  -H 'Content-Type: application/json' -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'

# (10b) Student submitting for another student returns 403
TOK=$(curl -s -X POST $URL/api/auth/login -H 'Content-Type: application/json' \
  -d '{"role":"student","user_id":"c1_stu99","password":"eduagent2026"}' \
  | python -c "import json,sys; print(json.load(sys.stdin).get('token',''))")
curl -s -o /dev/null -w "mismatched student token: %{http_code}\n" -X POST $URL/api/debate/start \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOK" \
  -d '{"essay_text":"x","student_id":"c1_stu01","class_id":"c1"}'

# (10c) Student attempting to access teacher routes returns 403
curl -s -o /dev/null -w "student accessing teacher route: %{http_code}\n" \
  -X GET "$URL/api/classes/c1/priority" -H "Authorization: Bearer $TOK"
```

**Measured Output:**

```
(7) doctor.py -> [PASS] No plaintext credentials on Cloud Run
    All credentials mounted as Secret Manager references (secretKeyRef):
    ['EDUAGENT_SESSION_SECRET', 'GMAIL_COMPOSE_TOKEN_JSON', 'SHEETS_TOKEN_JSON']

(10a) no-token: 401
(10b) mismatched student token: 403
(10c) student accessing teacher route: 403
```

---

## Cost Optimization & Scale-to-Zero Best Practices

1. **Evidence Collection:**
   - Record a 5-10 second clip accessing the live `.run.app` URL and dashboard.
   - Reference `https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app` in the submission.
2. **Cloud Run Scale-to-Zero Configuration:**
   - Ensure the service is configured to scale to 0 instances when idle (`--min-instances=0`).
3. **Billing Management:**
   - Verify active project link to the billing account and set Budget Alerts at 50%/90% to avoid unexpected overages.
