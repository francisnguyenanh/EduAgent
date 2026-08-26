# Social Post Draft (Bonus Stage Three)

> Post on X/LinkedIn (public) with the mandatory hashtag `#AllThingsAgenticHackathon` + demo link. Choose between the two templates below or adapt the tone as needed.

## X (Official Version — 273/280 chars, including t.co short links)

> Built an AI that won't give students answers — it debates them instead.
>
> 4 Socratic personas, memory across sessions, deterministic teacher priority ranking. Gemini + ADK2 + Firestore + Cloud Run.
>
> https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/
> https://github.com/francisnguyenanh/EduAgent
>
> #AllThingsAgenticHackathon

**Posting Instructions:**
1. Log in to X, click "Post".
2. Copy the text block above verbatim (preserve line breaks for readability).
3. Verify the two links: the live Cloud Run URL and the public GitHub repo URL.
4. Keep the exact hashtag `#AllThingsAgenticHackathon`.
5. Post publicly.
6. Copy the direct link to the published post (click the timestamp → copy URL) to submit on Devpost.

---

## LinkedIn (Expanded Long-form Post)

> "Using AI to teach students not to depend on AI" — that's the one-line philosophy behind eduagent, my submission for the All Things Agentic Hackathon (Collaborative Partner track).
>
> Instead of correcting a student's essay, it challenges it: 4 adversarial Socratic personas (Skeptic, Devil's Advocate, Nitpicker, Expander), an independent zero-LLM validator that blocks any answer-leak before the student sees it, and a memory system that makes the debate get sharper as it learns a student's persistent weaknesses across sessions.
>
> On the teacher side, every graded essay feeds a class-wide priority ranking (fully deterministic and auditable — a teacher can always trace *why* one student ranks above another) and a Gemini-written digest draft, with exactly one human-in-the-loop gate: the teacher clicking Send in their own Gmail.
>
> The part I'm most proud of isn't a feature — it's an audit. We went back through our own eval suite and found 12 of 50 test cases that couldn't actually fail (one group was asserting "8 minus 2 is at least 4"). We rewired every one of them to run against real production code and now prove each case can go red by breaking the code on purpose. Same audit found a session-signing key that had never been rotated off its public default — fixed, and the deploy now refuses to boot if that ever regresses.
>
> Built on Gemini via Vertex AI, Google ADK2, Firestore, Pub/Sub, and Cloud Run — and it also ingests real handwritten essay photos (yes, the messy kind, with cross-outs and bad lighting) via a self-consistency-checked multimodal OCR pipeline.
>
> Demo: https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app/
> Repo + full architecture writeup: https://github.com/francisnguyenanh/EduAgent
>
> #AllThingsAgenticHackathon
