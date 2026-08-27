# Technical Blog Draft (Bonus Stage Three)

> Publish on Medium/Dev.to with "written for the All Things Agentic Hackathon" at the top of the post. Adjust length and style as desired—this draft provides a complete, evidence-backed technical narrative.

**Title:** *Building a Socratic Debate Agent That Refuses to Give Answers — Lessons from ADK2, Gemini, and a Production-Minded Architecture*

**Subtitle:** *Written for the All Things Agentic Hackathon (Collaborative Partner track).*

---

Most "AI writing tutors" are just glorified ghostwriters. They polish a student's essay until it sounds great, which makes the paper better but leaves the student exactly where they started. 

We decided to build something deliberately challenging instead: an agent designed to poke holes in your arguments, not fix your grammar. 

That single constraint dictated almost every engineering choice we made. Here are five practical lessons—and a few embarrassing mistakes—from building, testing, and deploying it in production.

---

## 🏛️ Architecture: Deterministic by default, LLM as a last resort

If a task didn't strictly require fuzzy reasoning or natural language generation, we kept LLMs completely out of the pipeline.

```
Incoming Request 
  │
  ├── [Python AST / Regex / Rules] ──► Challenge Validator (Deterministic)
  ├── [Rule Engine / Heuristics]    ──► Persona Selector (Deterministic)
  ├── [Math / Priority Queue]      ──► Class Priority Ranker (Deterministic)
  └── [difflib / Levenshtein]      ──► OCR Discrepancy Check (Deterministic)
                                              │
                      ┌───────────────────────┴───────────────────────┐
                      ▼                                               ▼
          [LLM Calls - Gemini / Vertex]                   [Direct DB / Response]
          - Socratic question generation                  - Filtered / Rejected
          - Rubric-based qualitative scoring              - Audit log entries
```

Our Challenge Validator, Persona Selector, Class Priority Ranker (via the Priority Engine), and fallacy clustering are all plain Python functions. Zero LLM calls. 

When a teacher asks, *"Why was Student A flagged before Student B?"*, we don't have to shrug and blame a black box. There is a traceable, deterministic execution path for every single step.

We only invoke the LLM for things deterministic code literally cannot do:
* Parsing unstructured, freeform essay logic.
* Generating context-aware Socratic follow-up questions.
* Scoring against a multi-axis qualitative rubric.
* Formatting structured metrics into readable prose for educators.

---

## 💥 1. OAuth scopes don't work the way you think

We designed our Gmail integration under the assumption that requesting only `gmail.compose` would guarantee our backend couldn't send emails—only create drafts. A clean, least-privilege security story, right?

**Wrong.** Google's documentation defines `gmail.compose` as:
> *"Create, read, update, delete drafts; send messages and drafts."*

During an early test run, our script accidentally fired off two emails directly to our inbox before we realized what happened.

### The Fix: Enforce guarantees at the AST level
We stopped trusting IAM scopes to enforce business logic:

1. We scrubbed `.send()` from our integration codebase entirely.
2. We wrote an AST-based test that parses Python code at build time (using `inspect.getsource()` on our `gmail_mcp` module). If anyone ever imports or calls `.send()` in the integration layer, CI fails immediately:

```python
import ast
import inspect
from eduagent.integrations import gmail_mcp

def test_gmail_mcp_source_has_no_send_call():
    """Parses the AST of gmail_mcp to ensure no actual .send() calls are present."""
    source = inspect.getsource(gmail_mcp)
    tree = ast.parse(source)
    send_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) 
        and isinstance(node.func, ast.Attribute) 
        and node.func.attr == "send"
    ]
    assert not send_calls, "Security violation: .send() call found in gmail_mcp.py!"
```

The only way an email actually goes out is when a human teacher opens their Gmail client and clicks **Send** on the generated draft.

---

## 👁️ 2. Never trust an LLM to self-report OCR confidence

When students upload photos of handwritten essays, degraded scans are inevitable. In our first prototype, we prompted Gemini Vision to self-report a `confidence: "high" | "low"` field alongside its transcription.

**The failure mode:** On degraded test images, the model hallucinated entire paragraphs of clean text while cheerfully reporting `confidence: "high"` in 2 out of 4 manual trials. Prompt engineering alone did not close this gap.

### The Fix: Double-blind deterministic diffing
We call Gemini Vision **twice independently** on the same image, then compare the two outputs using standard string similarity (`difflib`) using a deterministic similarity threshold of `0.75`:

```python
import difflib

_CONSISTENCY_SIMILARITY_THRESHOLD = 0.75
_INCONSISTENCY_MARKER = "[[ocr inconsistent across repeated attempts on this image -- treat transcription as unverified]]"

def _cross_check_consistency(first: dict, second: dict) -> dict:
    similarity = difflib.SequenceMatcher(None, first["transcribed_text"], second["transcribed_text"]).ratio()
    if similarity >= _CONSISTENCY_SIMILARITY_THRESHOLD:
        return first

    return {
        "transcribed_text": first["transcribed_text"],
        "confidence": "low",
        "uncertain_segments": list(first["uncertain_segments"]) + [_INCONSISTENCY_MARKER],
    }
```

If the two passes diverge, confidence is downgraded to `low` regardless of what either model run claims. No LLMs evaluating other LLMs—just basic diffing.

---

## 🧪 3. We accidentally wrote tests that certified basic arithmetic

Eval suites are dangerously easy to game without realizing it.

In our early eval harness:
* Our persona-fidelity check constructed the prompt *inside the test fixture*, concatenated strings, and asserted that the persona string existed in the string it had just built. A complete tautology.
* Even worse: Layer 4's "cognitive growth" test was literally subtracting two hardcoded integer literals and asserting `8 - 2 >= 4`. You could have deleted the entire `src/` directory and all 12 test cases would have passed with flying colors.

### The Fix: The Sabotage Test
Before trusting any eval rule, we now deliberately break production code to verify that the test turns red. 

When we removed persona anchoring from the actual production prompt builder, the tests failed (4/4). When we removed the measurement artifact, our Layer 4 cases failed (4/4).

```
   [Pass / Green] ────► Sabotage production code ────► Must turn [Fail / Red]
         ▲                                                     │
         └───────────── Restore & Verify ──────────────────────┘
```

Our main suite remains a green **50/50 deterministic test cases passed** across 4 layers (Safety & Security, Behavioral Discipline, Long-Term Memory, and Learning Outcomes), while the opt-in `--live-persona` suite exposes the raw compliance limits of live prompts.

### The uncomfortable reality of live prompts
When we finally wired up `--live-persona` to evaluate multi-turn debates against real Gemini outputs, two of our four personas (*Devil's Advocate* and *Nitpicker*) drifted into the *Skeptic* persona during complex essays. 

Prompt anchoring keeps instructions in context, but it doesn't guarantee compliance under cognitive load. We could have widened the regex matchers to keep our CI dashboard green, but that would just be reward hacking in disguise. We kept the failure in the report and documented it instead.

---

## ☁️ 4. Cloud Run reserves `/healthz`

Coming from Kubernetes, we naturally set our container health-check endpoint to `/healthz`. 

It consistently returned a generic Google-branded `404 Not Found` before incoming requests ever reached our container or IAM checks.

**Why:** Cloud Run's underlying Knative/Istio serving layer intercepts and reserves that exact literal path. 

Renaming the route to `/health-check` fixed it immediately. **Lesson:** Never assume cloud platform runtimes respect conventions from adjacent ecosystems.

---

## 🔐 5. "Be more careful with secrets" is not a strategy

We hit two credential pitfalls during development:
1. We committed a default signing key to the repo and forgot to set the overriding environment variable in production. Anyone inspecting our repo could mint valid `role=teacher` tokens.
2. We passed OAuth refresh tokens via `--env-vars-file`. On Cloud Run, plain environment variables are visible in plaintext inside the revision spec via `gcloud run services describe`, exposing tokens to anyone with basic service read permissions (`run.services.get`).

### The Fix: Automated guardrails & Secret Manager
Hoping developers "remember next time" doesn't scale. We automated the solution:

* An AST check fails CI if secrets are ever passed in cleartext configurations.
* A preflight script (`doctor.py`) checks the deployed revision spec and halts deployment if any secret is exposed.
* We mounted secrets via Cloud Secret Manager using `--update-secrets`:

```bash
gcloud run deploy eduagent-service \
  --image gcr.io/my-project/eduagent:latest \
  --update-secrets GMAIL_COMPOSE_TOKEN_JSON=eduagent-gmail-token:latest,SHEETS_TOKEN_JSON=eduagent-sheets-token:latest
```

This required **zero lines of application code changes**, because Cloud Run injects mounted secrets into standard environment variables at runtime.

---

## 📊 Did it actually improve student learning?

To verify whether persistent Socratic memory helps students improve, we ran two evaluations:

1. **Stateful vs. Stateless:** In a stateless setup, the tutor repeatedly asks generic questions and gets stuck in loops. With persistent memory, it references past arguments (*"In your previous essay on this topic, you lacked empirical evidence for claim X..."*) and dynamically adapts its persona.
2. **Empirical Scoring Delta:** We passed 8 weak-versus-revised thesis pairs through our production pipeline (`summarize_essay()` → Vertex AI rubric evaluation). The evaluator scored drafts blindly without seeing prior tutor prompts.

| Metric | Measured Delta |
| :--- | :--- |
| **Targeted Axis Improvement** | **+2.75 points** (Improved in 7/8 scenarios) |
| **Overall Average Delta** | **+2.05 points** across all axes |

*(Earlier in the project, we quoted an impressive `+5.62` gain. When we audited our eval code, we discovered that number came from a dummy script that averaged 16 hardcoded numbers without calling the model. The `+2.75` number is real, tested against an n=8 thesis benchmark, and far more honest.)*

---

## 🎯 Key Takeaways & Closing

None of these findings came from reading documentation more carefully — they came from actually running the system against real Gmail accounts, real blurry photos, real Cloud Run deployments, and treating every "should work" assumption as something to verify, not assume. That discipline is, we'd argue, the actual differentiator between a demo and a system.

Don't give every student an answer. Give every student a reason to think. That's the bet this architecture makes.

*Repo, architecture diagram, and full ADR log: [https://github.com/francisnguyenanh/EduAgent](https://github.com/francisnguyenanh/EduAgent).*

*How are you structuring your LLM evaluation pipelines and guardrails in production? Let me know in the comments below!*

---

`#AllThingsAgenticHackathon` `#GoogleCloud` `#GenAI` `#Gemini` `#AgenticAI`
