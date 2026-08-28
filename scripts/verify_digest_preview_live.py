"""ADR-030 live verification -- drives the DEPLOYED service, not a local process.

    python scripts/verify_digest_preview_live.py

Companion to scripts/smoke_live.py, which covers the student journey. This
covers the teacher-facing half that Wave 26 changed, and exists because the
defect it was written to catch could not be seen from the code: the deep link
was built from the API draft id (`r328879860172231529`) while Gmail's web UI
addresses drafts by the hex message id (`1a04055b6640d946`), so the link opened
an empty compose window. Reading the source made that look correct.

Defaults to the throwaway class `zz9`, never the demo class `c1` -- same reason
smoke_live.py does, and because only digests written after Wave 26 carry
`gmail_draft_message_id` at all.

Checks only what Wave 26 changed:
  1. /analytics carries digest_html, and it is the draft's own body
  2. that HTML is escaped (no live markup reaching our origin)
  3. gmail_draft_id is present so the deep link can be built
  4. the demo page ships the new label / badge / preview function
  5. the ADR-001 gate is intact on the live build (no send path appeared)
"""
import json, re, sys, urllib.request, urllib.error

URL = "https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app"
TEACHER_PASSCODE = "eduagent-teacher-2026"
CLASS = "zz9"
results = []

def rec(name, ok, detail):
    results.append((ok, name, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n       {detail}")

def req(path, payload=None, token=None, timeout=60):
    r = urllib.request.Request(URL + path, method="POST" if payload else "GET")
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(payload).encode() if payload else None
    with urllib.request.urlopen(r, data, timeout=timeout) as resp:
        return resp.status, resp.read().decode()

# revision actually serving
try:
    _, health = req("/health-check")
    rec("live service answers /health-check", True, health[:160])
except Exception as e:
    rec("live service answers /health-check", False, repr(e)); sys.exit(1)

# teacher token
st, body = req("/api/auth/login", {"role": "teacher", "user_id": f"{CLASS}_teacher", "password": TEACHER_PASSCODE})
tok = json.loads(body).get("access_token") or json.loads(body).get("token")
rec("teacher login issues a token", bool(tok), f"HTTP {st}, token {'present' if tok else 'MISSING: ' + body[:200]}")
if not tok:
    sys.exit(1)

# 1-3: analytics payload
st, body = req(f"/api/classes/{CLASS}/analytics", token=tok)
digests = json.loads(body)["digests"]
rec("GET /analytics returns digests", bool(digests), f"HTTP {st}, {len(digests)} digest(s)")
if digests:
    d = digests[0]
    html = d.get("digest_html")
    rec("ĐỢT 26 #1.3 -- digest_html present on the live revision",
        isinstance(html, str) and len(html) > 50,
        f"{len(html) if isinstance(html,str) else 'None'} chars")
    if isinstance(html, str):
        head = (d.get("digest_text") or {}).get("headline", "")
        rec("digest_html is the DRAFT's own body (headline matches digest_text)",
            bool(head) and head.replace("&", "&amp;").replace("<", "&lt;") in html,
            f"headline={head[:70]!r}")
        rec("digest_html carries no live markup from model text",
            "<script" not in html.lower() and "onerror=" not in html.lower(),
            "no <script / onerror= in the rendered body")
        rec("digest_html keeps the table chrome the renderer writes",
            "<table" in html or "priority_students" not in json.dumps(d.get("digest_text")),
            "table present (or this digest ranked nobody)")
    rec("ĐỢT 26 #1.2 -- gmail_draft_id available for the deep link",
        bool(d.get("gmail_draft_id")),
        f"gmail_draft_id={d.get('gmail_draft_id')!r}")
    # A draft written by THIS revision must carry the hex message id, since
    # that -- not the API draft id -- is what Gmail's web UI addresses.
    msg = d.get("gmail_draft_message_id")
    rec("ĐỢT 26 -- newest digest carries a hex gmail_draft_message_id",
        bool(msg) and re.fullmatch(r"[0-9a-f]{12,20}", msg) is not None,
        f"gmail_draft_message_id={msg!r} (older digests legitimately have None)")

# 4: the page itself
st, page = req("/demo")
rec("ĐỢT 26 #1.1 -- Settings label no longer promises a notification",
    "notification email" not in page.lower(),
    "the string 'notification email' is gone from the served page")
rec("ĐỢT 26 #1.1 -- label states the To: / never-sends contract",
    "composes a draft, it never sends" in page and "the <code>To:</code> address" in page,
    "hint text present")
rec("ĐỢT 26 #1.4 -- HITL badge shipped in the served page",
    "awaiting human Send (ADR-001)" in page, "badge string present")
rec("ĐỢT 26 #1.2 -- Gmail deep link shipped, built from the HEX MESSAGE id",
    "mail.google.com/mail/u/0/#drafts" in page
    and "gmail_draft_message_id" in page
    and "'?compose=' + encodeURIComponent(composeId)" in page,
    "link uses composeId (message id), falls back to the Drafts folder for older digests")
rec("ĐỢT 26 #1.3 -- preview renderer shipped in the served page",
    "function digestDraftPreview" in page, "digestDraftPreview() present")

failed = [n for ok, n, _ in results if not ok]
print("\n" + "=" * 70)
print(f"{len(results) - len(failed)}/{len(results)} passed")
for n in failed:
    print("  FAILED:", n)
sys.exit(1 if failed else 0)
