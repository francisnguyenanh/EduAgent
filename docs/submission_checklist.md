# Phase 8 — Final Submission Checklist & Devpost Reminders

> [!IMPORTANT]
> All draft copy (video script, Devpost text, blog post, social post) is prepared in `docs/`. This checklist covers the final **ACTIONABLE EXECUTION STEPS** (recording the demo, uploading assets, submitting on Devpost) that must be verified before the deadline.

---

## 1. Record Demo Video (using `docs/video_script.md`)
- [ ] Run `python scripts/doctor.py` immediately prior to recording. Expect **0 FAIL**. (Note: `Session signing secret` reporting **WARN when running locally is normal and expected** because local dev uses the fallback default; it must PASS on the deployed Cloud Run revision).
- [ ] 🔴 **Verify Cloud Run Deployment:** Confirm that the latest security updates (Audit Waves 13 & 14, ADR-016/017/018/020) are live. Run `python scripts/deploy_to_cloud_run.py` (which preflights all 3 secrets in Secret Manager) or follow README section 3.4.
- [x] ✅ **Redeployed & Verified (re-measured 2026-08-27, Audit Wave 24):** `doctor.py` → **10 PASS / 1 WARN / 0 FAIL** (was 9 PASS before Wave 16 added the `push_config` check and Wave 19 added the live-revision check); **4/4** credentials mounted via `secretRef` (`EDUAGENT_SESSION_SECRET`, `GMAIL_COMPOSE_TOKEN_JSON`, `SHEETS_TOKEN_JSON`, `EDUAGENT_TEACHER_PASSWORD`); `smoke_live.py` → **13/13 PASS** against live revision `eduagent-class-aggregator-00037-6h4`, including the 401 (unauthenticated) and 403 (IDOR) probes.
- [x] ✅ **Rotate OAuth Tokens:** Both Gmail and Sheets tokens are stored in Secret Manager `:latest`.
- [ ] 🟢 **Demo Setup: set `EDUAGENT_DIGEST_DEBOUNCE_SECONDS=0`** prior to recording (default 120s debouncing coalesces digests; set to 0 so the Gmail draft creates immediately during the demo). See README §3.10(c). Remember to revert to 120 afterwards.
- [ ] Rehearse the script **at least twice** before final recording (target timing ≤ 4:00).
- [ ] Record a **single-take, unedited live run** showing:
  - Problem & core value proposition.
  - Model names (`gemini-3.5-flash`, `gemini-3.7-flash`, `gemma-4-26b-a4b-it-maas`) and framework (Google ADK2).
  - Live agent in action: Terminal logs, Firestore real-time profile mutation, Gmail draft creation.
  - Proof of Google Cloud infrastructure (Console, Cloud Run dashboard, live `.run.app` URL).
- [ ] Ensure no secret API keys, JSON credentials, or private data are visible on screen.

## 2. Upload Video
- [ ] Upload to YouTube or Vimeo set to **Public** (avoid Private or Unlisted so judges can access without permissions issues).
- [ ] Ensure audio is clear English or includes accurate English subtitles.
- [ ] Copy the video URL into Section 7 of `docs/devpost_submission_draft.md`.

## 3. Prepare Repository Prior to Submission
- [ ] `git push` all commits to the remote repository.
- [ ] Check repository access:
  - If **Public**: Open in an Incognito browser window to verify public readability.
  - If **Private**: Add collaborator permissions for: `testing@devpost.com` and `cloudhackathons@google.com`.
- [ ] Verify clean-machine installation instructions from `README.md` to guarantee 100% reproducibility.

## 4. Submit on Devpost (using `docs/devpost_submission_draft.md`)
- [ ] Copy prepared content from `docs/devpost_submission_draft.md` into the Devpost registration form.
- [ ] Fill in all remaining placeholders `[...]` (Video URL, Repo URL, Country, Start Date `08-03-26`).
- [ ] Double-check key eligibility items:
  - **Mandatory Disclosure:** Retain originality disclosure text.
  - **Category / Track:** Select **Collaborative Partner**.
- [ ] Fill in Hosted URL (`https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app`), demo credentials (student `eduagent2026`, teacher `eduagent-teacher-2026`), Google SDK list, Cloud Services, and attach the architecture diagram image.
- [ ] **Teammates:** Confirm all team members have accepted invitations on Devpost before final submission.

## 5. Bonus Criteria Verification (Bonus Stage Three — up to **+1.0 Points**)

> ⚠️ **Scoring Correction (Audit Wave 21 — the Wave 14 note here was wrong).** Wave 14 recorded that
> "additional model usage is noted under optional contributions without separate numeric points."
> The official rules say the opposite, verbatim:
>
> > *"Earn **0.2 bonus points for each additional Google AI model** successfully integrated (such as
> > Gemma, Veo, or Lyria), **up to a maximum of 0.6 total bonus points**"*
>
> The arithmetic corroborates it: the rules state *"Each Submission will receive a Final score from
> 1 to 6"*, which is 5 (Stage Two maximum) **+ 1.0 bonus** = 0.2 blog + 0.2 social + **0.6 models**.
>
> Acting on the Wave 14 note capped this submission at **5.4/6.0** and led us to decline extra-model
> work on the belief it scored nothing. **Wave 24 closed the first 0.2 of that gap:**
> `grep -rniE "gemma" src/ tests/` is no longer empty — see the Gemma 4 entry below. The remaining
> **0.4 is deliberately left on the table** (Veo/Lyria), for the reason in the discipline note.
- [x] **Technical Blog Post:** Published at https://dev.to/eiki_tomobe_927fe44127f66/building-a-socratic-debate-agent-that-refuses-to-give-answers-354p (+0.2 pts).
- [x] **Social Media Post:** Published on X at https://x.com/EikiTomobe/status/2092985071435395283 (+0.2 pts).
  - ⚠️ **NOT machine-verified (Audit Wave 24).** x.com refuses unauthenticated fetches (HTTP 402), so
        unlike the blog post — whose live text WAS read back and checked against the rule — this one
        could not be. **Open it in a logged-out / incognito browser and confirm three things yourself:**
        (1) it loads without signing in — the rules require public, and a protected or deleted post
        scores nothing; (2) the hashtag reads exactly `#AllThingsAgenticHackathon`, no space (note
        `rule.txt:150` prints it with a stray space and `rule.txt:213` without — the no-space form is
        what the draft and the published blog tags use); (3) the demo and repo links resolve.
        `rule.txt:213`: *"Publish a social media post… include the hashtag #AllThingsAgenticHackathon.
        A maximum of 0.2 points will be added"*.
- [x] ✅ **Additional Google AI models (+0.2 each, max +0.6): 1 integrated — Gemma 4.**
      `gemma-4-26b-a4b-it-maas` runs the second transcription pass of the OCR consistency check
      (ADR-028), replacing what used to be a second Gemini call. Implemented, tested and measured on
      2026-08-27 (Audit Wave 24):
  - [x] Code: `config.py` (`gemma_model`, `gemma_location` pinned to `global`), `llm.py`
        (`generate_text_from_image` + a 429-specific retry), `nodes/ocr.py`
        (`_transcribe_second_opinion` + mandatory fallback + `cross_check_model` signal).
  - [x] Tests: **10 new cases**, each proven falsifiable by sabotage (ADR-019) — 7 sabotages run,
        every one red on the intended test. Suite: **284 passed**, coverage **87%**, `nodes/ocr.py` 100%.
  - [x] Quality: contemporaneous A/B over the 12 real handwriting samples — confidence distribution
        **identical** (10 high / 0 medium / 2 low both ways). Gemma reached on **12/12** images, 0 fallbacks.
  - [x] Latency: mean per-image OCR **7.30s → 8.82s (+21%)**. ⚠️ **Not yet re-measured on the
        deployed service** — do that before recording (see `video_script.md`).
  - [ ] 🔴 **Deploy to Cloud Run** — the integration is in the repo but NOT yet on the live revision.
        Until it is deployed, a judge testing the hosted URL is not exercising Gemma.
  - **Rollback lever:** `EDUAGENT_OCR_CROSS_CHECK_GEMMA=false` puts the second pass back on Gemini
        with no code change.
- [x] ~~**Imagen**~~ — does not exist in this project at any location (Wave 22 enumerated the
      catalogue at `global`, `us-central1`, `asia-southeast1`). Not a judgement call, a `404`.
- [x] ~~**Veo / Lyria**~~ — declined three times. A video or music model in an essay-debate app is a
      bolt-on, and the 40% Innovation criterion punishes that harder than 0.2 rewards it.

> **Discipline note:** integrate only what survives the same standard as every other feature here —
> it must do real work, have a test, and be defensible in Q&A. A judge who asks "why is Veo in an
> essay-debate app?" and hears "for bonus points" costs more on the 40% Innovation criterion than
> the 0.2 is worth.
- [x] **Models Disclosed:** `gemini-3.5-flash` (default), `gemini-3.7-flash` (heavy model for Teacher Digest), and `gemma-4-26b-a4b-it-maas` (OCR cross-model second pass, ADR-028). All three declared under §8 of `devpost_submission_draft.md`, with the reason Gemma is present — a judge who asks "why?" gets an architectural answer, not "for the bonus".
- [x] Add blog and social post links to the Devpost form (Blog and X post added).

## 6. Freeze Resources After Submission Deadline
- [ ] **Submit early:** Submit at least 24 hours ahead of the final deadline: **August 31 at 5:00 PM PT**.
- [ ] **DO NOT modify** the repository, demo video, or linked assets once submitted until winners are announced.
- [ ] *Tip:* If you wish to continue development after the deadline, **Fork the repository** into a separate repository and keep the submission repo untouched.
