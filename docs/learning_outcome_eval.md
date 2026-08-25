# Learning-Outcome Measurement: Does the scorer register cognitive growth?

> **What this measures:** each of 8 controlled thesis pairs (a weak thesis and
> its Socratically-revised form) is put through the **real production path** --
> `summarize_essay()` then `score_essay()` (`src/eduagent/nodes/scorer.py`,
> Gemini via Vertex AI) -- and the per-axis delta is recorded.
>
> **What this does NOT measure:** real classroom learning gains. n = 8 author-written
> thesis pairs, not 8 students. See "Measurement design & limitations" below before
> quoting any number from this file.

*Measured at 2026-08-25T12:44:52.468025+00:00 · 2 scoring run(s) per text · scorer: `nodes/scorer.py::score_essay (production prompt/schema, Gemini via Vertex AI)`*

---

## 1. Measured Summary

| Metric | Measured value | Threshold | Result |
|---|:---:|:---:|:---:|
| Scenarios where the targeted axis improved | **7/8 (88%)** | > 0 delta | **PARTIAL** |
| Mean delta on the targeted axis | **+2.75 / 10** | > +1.0 | **PASS** |
| Mean delta across all 4 axes | **+2.05 / 10** | > +0.5 | **PASS** |
| Independent re-scoring (no debate transcript, no cross-text context) | **Yes -- both texts scored by the same production scorer** | — | **VERIFIED** |

---

## 2. Per-scenario measurement (all values produced by live scorer calls)

| Scenario & topic | Targeted axis | Persona | Before | After | Delta | Status |
|---|---|---|:---:|:---:|:---:|:---:|
| **Electric Vehicle Emissions** | `evidence_quality` | `skeptic` | 0.5/10 | 2.5/10 | **+2.0** | PASS |
| **AI in High School Classrooms** | `counterargument_handling` | `devils_advocate` | 1.0/10 | 1.0/10 | **+0.0** | FAIL |
| **Homework Policy Reform** | `logical_coherence` | `nitpicker` | 2.0/10 | 4.0/10 | **+2.0** | PASS |
| **Social Media Age Restrictions** | `scope_awareness` | `expander` | 1.0/10 | 2.0/10 | **+1.0** | PASS |
| **Renewable Energy Transition** | `evidence_quality` | `skeptic` | 1.0/10 | 5.5/10 | **+4.5** | PASS |
| **Nuclear Energy in Clean Grids** | `counterargument_handling` | `devils_advocate` | 0.0/10 | 3.5/10 | **+3.5** | PASS |
| **Video Games and Academic Performance** | `logical_coherence` | `nitpicker` | 1.5/10 | 5.0/10 | **+3.5** | PASS |
| **Universal Remote Work** | `scope_awareness` | `expander` | 1.0/10 | 6.5/10 | **+5.5** | PASS |

### Full 4-axis breakdown

| Scenario | Axis | Before | After | Delta |
|---|---|:---:|:---:|:---:|
| `scenario_01_evidence_skeptic` | `logical_coherence` | 1.5 | 4.0 | +2.5 |
| `scenario_01_evidence_skeptic` | `evidence_quality` ⟵ targeted | 0.5 | 2.5 | +2.0 |
| `scenario_01_evidence_skeptic` | `counterargument_handling` | 0.5 | 3.0 | +2.5 |
| `scenario_01_evidence_skeptic` | `scope_awareness` | 0.5 | 4.5 | +4.0 |
| `scenario_02_counterarg_devils_advocate` | `logical_coherence` | 2.0 | 2.5 | +0.5 |
| `scenario_02_counterarg_devils_advocate` | `evidence_quality` | 1.0 | 1.0 | +0.0 |
| `scenario_02_counterarg_devils_advocate` | `counterargument_handling` ⟵ targeted | 1.0 | 1.0 | +0.0 |
| `scenario_02_counterarg_devils_advocate` | `scope_awareness` | 1.0 | 1.5 | +0.5 |
| `scenario_03_logic_nitpicker` | `logical_coherence` ⟵ targeted | 2.0 | 4.0 | +2.0 |
| `scenario_03_logic_nitpicker` | `evidence_quality` | 1.0 | 1.0 | +0.0 |
| `scenario_03_logic_nitpicker` | `counterargument_handling` | 0.0 | 1.0 | +1.0 |
| `scenario_03_logic_nitpicker` | `scope_awareness` | 1.0 | 3.0 | +2.0 |
| `scenario_04_scope_expander` | `logical_coherence` | 1.5 | 2.5 | +1.0 |
| `scenario_04_scope_expander` | `evidence_quality` | 0.5 | 1.0 | +0.5 |
| `scenario_04_scope_expander` | `counterargument_handling` | 0.5 | 1.0 | +0.5 |
| `scenario_04_scope_expander` | `scope_awareness` ⟵ targeted | 1.0 | 2.0 | +1.0 |
| `scenario_05_evidence_popularity` | `logical_coherence` | 2.0 | 4.5 | +2.5 |
| `scenario_05_evidence_popularity` | `evidence_quality` ⟵ targeted | 1.0 | 5.5 | +4.5 |
| `scenario_05_evidence_popularity` | `counterargument_handling` | 0.5 | 1.0 | +0.5 |
| `scenario_05_evidence_popularity` | `scope_awareness` | 1.0 | 2.5 | +1.5 |
| `scenario_06_counterarg_nuclear` | `logical_coherence` | 1.5 | 4.5 | +3.0 |
| `scenario_06_counterarg_nuclear` | `evidence_quality` | 0.0 | 1.0 | +1.0 |
| `scenario_06_counterarg_nuclear` | `counterargument_handling` ⟵ targeted | 0.0 | 3.5 | +3.5 |
| `scenario_06_counterarg_nuclear` | `scope_awareness` | 0.5 | 4.0 | +3.5 |
| `scenario_07_logic_correlation` | `logical_coherence` ⟵ targeted | 1.5 | 5.0 | +3.5 |
| `scenario_07_logic_correlation` | `evidence_quality` | 1.0 | 2.0 | +1.0 |
| `scenario_07_logic_correlation` | `counterargument_handling` | 0.0 | 2.5 | +2.5 |
| `scenario_07_logic_correlation` | `scope_awareness` | 1.0 | 5.0 | +4.0 |
| `scenario_08_scope_remote_work` | `logical_coherence` | 2.0 | 6.5 | +4.5 |
| `scenario_08_scope_remote_work` | `evidence_quality` | 0.0 | 1.5 | +1.5 |
| `scenario_08_scope_remote_work` | `counterargument_handling` | 0.0 | 3.0 | +3.0 |
| `scenario_08_scope_remote_work` | `scope_awareness` ⟵ targeted | 1.0 | 6.5 | +5.5 |

---

## 3. Case studies (thesis text is the input; scores are the measurement)

### 🔬 evidence_quality (`skeptic`)
* **Before:** *"Electric cars are completely clean and produce zero pollution anywhere."* — measured **0.5/10**
* **After Socratic revision:** *"While EVs produce zero tailpipe emissions, lifecycle studies show a 40-60% net reduction in carbon emissions depending on whether regional grid electricity comes from renewables."* — measured **2.5/10**
* **Measured delta:** **+2.0 points**

### 😈 counterargument_handling (`devils_advocate`)
* **Before:** *"AI writing tools must be encouraged for all assignments because technology is the future."* — measured **1.0/10**
* **After Socratic revision:** *"AI tools should be integrated as collaborative brainstorming aids rather than essay generators, paired with oral defenses to preserve critical reasoning."* — measured **1.0/10**
* **Measured delta:** **+0.0 points**

### 🔍 logical_coherence (`nitpicker`)
* **Before:** *"Students feel stressed on Mondays, so all homework across K-12 education should be abolished immediately."* — measured **2.0/10**
* **After Socratic revision:** *"Because excessive repetitive homework correlates with stress without improving retention in early grades, daily homework should be capped at 10 minutes per grade level and focused on conceptual practice."* — measured **4.0/10**
* **Measured delta:** **+2.0 points**

### 🌌 scope_awareness (`expander`)
* **Before:** *"Social media destroys every teenager's mental health without exception."* — measured **1.0/10**
* **After Socratic revision:** *"High-frequency consumption of algorithmic feeds with engagement-maximizing loops significantly increases adolescent anxiety, while moderated interest-based communities show neutral to positive peer support effects."* — measured **2.0/10**
* **Measured delta:** **+1.0 points**

---

## 4. Measurement design & limitations (read this before quoting a number)

**How it was measured.** For each scenario, both the initial thesis and the revised
thesis are pushed through the production summarizer and then the production scorer
with an **empty debate transcript**. The scorer sees one text at a time, is never
told which one is the revision, and never sees the Socratic probe -- so it cannot
infer that a higher score is expected. Every number in this document is the output
of a live Gemini call; none is written by hand.

**What the numbers support.** That the deterministic-first pipeline's scorer
*detects* the specific cognitive improvement each persona targets, at a mean of
+2.75 points on the targeted axis across 8 scenarios.

**What the numbers do NOT support.**
1. **n = 8 controlled thesis pairs, not 8 students.** The revised theses were
   written by the project author as exemplars of a successful Socratic outcome. This
   is a measurement of the *scorer*, on controlled inputs -- not evidence that real
   students improve by this much.
2. **No control group and no longitudinal data.** A classroom study would need real
   student revisions, a control condition, and repeated measurement over time.
3. **LLM scoring is non-deterministic.** This run used 2 scoring run(s) per text;
   re-running will move the numbers. That is why the run count and timestamp are
   stamped at the top of this file rather than the numbers being treated as fixed.

**Related, and stronger, evidence.** `scripts/experiment_memory_ab.py` A/B-tests the
real `choose_persona()` and `compute_priority()` production logic, and the ADK Eval
Suite's Layers 1-3 assert against real production functions. Those are deterministic
and reproducible; this document is a live-model measurement and should be cited as one.
