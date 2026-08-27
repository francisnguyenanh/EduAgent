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
  - Model names (`gemini-3.5-flash`, `gemini-3.7-flash`) and framework (Google ADK2).
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
> work on the belief it scored nothing. `grep -rniE "gemma|veo|lyria|imagen" src/ scripts/` returns
> zero, so **0.6 points — 10% of the maximum — is currently unclaimed.**
- [x] **Technical Blog Post:** Published at https://dev.to/eiki_tomobe_927fe44127f66/building-a-socratic-debate-agent-that-refuses-to-give-answers-354p (+0.2 pts).
- [ ] **Social Media Post:** Publish a project summary with demo link on LinkedIn or X with hashtag `#AllThingsAgenticHackathon` (+0.2 pts).
- [ ] **Additional Google AI models (+0.2 each, max +0.6):** currently **0 integrated**
      (`grep -rniE "gemma" src/ scripts/ tests/` → empty, re-checked 2026-08-27).

  > **The candidate list that used to sit here was superseded by Audit Wave 22, which measured what
  > this project can actually call instead of guessing.** Do not re-derive it:
  >
  > - ~~**Imagen**~~ — **does not exist in this project.** Wave 22 enumerated the model catalogue at
  >   `global`, `us-central1` and `asia-southeast1`; Imagen appears at none of them. Not a judgement
  >   call, a `404`.
  > - ~~**Gemma for `skills/language.py`**~~ — dropped for a better target, not for effort. Wave 22
  >   also measured that Gemma **ignores `response_schema`** (asked for `{resolved, reason}`, got
  >   `{"answer": ...}`), so it belongs somewhere the output is compared as raw text.
  > - ~~**Veo / Lyria**~~ — video and music generation in an essay-debate app. Declined twice before
  >   (Waves 14, 15) and again in Wave 22: the 40% Innovation criterion asks *"does the system
  >   eliminate real-world friction?"*, and a judge who asks "why is Veo here?" costs more than 0.4.

  - [ ] **The one integration worth doing: ADR-028 — Gemma 4 as the second OCR pass.** Full 10-step
        plan in `TODO.md` Wave 23. `gemma-4-26b-a4b-it-maas` on the `global` endpoint the project
        already uses — no GPU, no new region, no new credential (proven callable in Wave 22).
        The argument is architectural, not point-farming: ADR-007 currently runs *the same model
        twice*, so a systematic misread survives both passes and the cross-check reports consensus;
        a different model family makes the two errors uncorrelated.
        ⚠️ **Timing gate (Audit Wave 24):** this changes the OCR latency that `video_script.md`
        quotes (22.5s / 24.2s) and that the video's pacing is built around. Do it **before**
        recording or **not at all** — never between recording and submitting.

> **Discipline note:** integrate only what survives the same standard as every other feature here —
> it must do real work, have a test, and be defensible in Q&A. A judge who asks "why is Veo in an
> essay-debate app?" and hears "for bonus points" costs more on the 40% Innovation criterion than
> the 0.2 is worth.
- [ ] **Models Disclosed:** `gemini-3.5-flash` (default) and `gemini-3.7-flash` (heavy model for Teacher Digest). Declared accurately under technologies used.
- [/] Add blog and social post links to the Devpost form (Blog added, pending social post).

## 6. Freeze Resources After Submission Deadline
- [ ] **Submit early:** Submit at least 24 hours ahead of the final deadline: **August 31 at 5:00 PM PT**.
- [ ] **DO NOT modify** the repository, demo video, or linked assets once submitted until winners are announced.
- [ ] *Tip:* If you wish to continue development after the deadline, **Fork the repository** into a separate repository and keep the submission repo untouched.
