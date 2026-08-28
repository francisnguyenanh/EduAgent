"""Live smoke test -- exercises the DEPLOYED service end to end, not a local process.

Wave 19 #8. `scripts/doctor.py` answers "are the dependencies healthy?"; this
answers the different and equally important question "does a student's whole
journey actually work on the URL a judge will open?" Every audit wave that
found a real blocker (Pub/Sub pull mode in Wave 8, the fabricated breakthrough
in Wave 16, the X-Forwarded-For bypass in Wave 17) found it by driving the live
service, not by reading code -- so that sequence is worth having as one command
rather than as a chain of curls retyped from a chat log.

Run it before recording. It calls real Gemini and writes a real profile, so it
costs a few Flash requests and leaves an essay in the target student's history.

It therefore defaults to a student in the **throwaway class `zz9`**, never the
demo class `c1`. That default is not cosmetic: `class_id` is the prefix of the
student id, so a smoke run against `c1_...` creates a student that then appears
in the Teacher Dashboard's priority ranking -- on camera, during the demo. This
was found the honest way, by doing it (`c1_smoke01` showed up ranked #7).

    python scripts/smoke_live.py
    python scripts/smoke_live.py --student zz9_rehearsal
    python scripts/smoke_live.py --url https://... --skip-debate   # cheap checks only

Exit code is 0 only if every check passed.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_URL = "https://eduagent-class-aggregator-636767063018.asia-southeast1.run.app"
STUDENT_PASSCODE = "eduagent2026"
TEACHER_PASSCODE = "eduagent-teacher-2026"

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, str, str]] = []


def _record(name: str, ok: bool, detail: str) -> bool:
    _results.append((name, PASS if ok else FAIL, detail))
    print(f"[{PASS if ok else FAIL}] {name}\n       {detail}")
    return ok


def _post(url: str, payload: dict, token: str | None = None, timeout: int = 120):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw or b"{}")
        except ValueError:
            return exc.code, {"raw": raw.decode(errors="replace")[:200]}


def _get(url: str, token: str | None = None, timeout: int = 60):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument(
        "--student",
        default="zz9_smoke01",
        help="throwaway student id to debate as. Keep it OUT of class c1: the id prefix is the "
        "class, and anything written to c1 shows up in the demo Teacher Dashboard.",
    )
    ap.add_argument("--skip-debate", action="store_true", help="skip the Gemini-billed journey")
    ap.add_argument(
        "--allow-demo-class",
        action="store_true",
        help="permit --student in class c1. Off by default so a rehearsal cannot add a fake "
        "student to the ranking the demo is about to show.",
    )
    args = ap.parse_args()
    url = args.url.rstrip("/")

    if args.student.split("_", 1)[0] == "c1" and not args.allow_demo_class and not args.skip_debate:
        sys.exit(
            f"Refusing to run the debate journey as {args.student!r}: class 'c1' is the demo class, and "
            "this test writes a real essay + profile that would then appear in the Teacher Dashboard "
            "ranking. Use a throwaway class (e.g. zz9_smoke01), or pass --allow-demo-class if you "
            "really mean it."
        )

    status, body = _get(f"{url}/health-check")
    _record("Service reachable", status == 200 and body.get("status") == "ok", f"GET /health-check -> {status} {body}")

    # ADR-014: the push endpoint must reject a caller with no OIDC token.
    status, body = _post(f"{url}/", {"message": {"data": "e30="}}, timeout=30)
    _record(
        "Pub/Sub push endpoint rejects unauthenticated callers (ADR-014)",
        status == 401,
        f"POST / without OIDC -> {status} {body.get('detail', '')}",
    )

    # ADR-025: the two portals must not share a passcode.
    status, _ = _post(f"{url}/api/auth/login", {"role": "teacher", "user_id": "c1_teacher", "password": STUDENT_PASSCODE}, timeout=30)
    _record(
        "Student passcode cannot mint a teacher token (ADR-025)",
        status == 401,
        f"teacher login with the student passcode -> {status} (expected 401)",
    )

    status, teacher = _post(f"{url}/api/auth/login", {"role": "teacher", "user_id": "c1_teacher", "password": TEACHER_PASSCODE}, timeout=30)
    t_token = teacher.get("token", "")
    _record("Teacher login with its own passcode", status == 200 and bool(t_token), f"-> {status}")

    status, student = _post(f"{url}/api/auth/login", {"role": "student", "user_id": args.student, "password": STUDENT_PASSCODE}, timeout=30)
    s_token = student.get("token", "")
    _record("Student login", status == 200 and bool(s_token), f"-> {status}")

    if t_token:
        status, ranking = _get(f"{url}/api/classes/c1/priority", t_token)
        rows = ranking.get("ranking", [])
        top = f"{rows[0]['name']} ({rows[0]['student_id']}) = {rows[0]['priority']}" if rows else "none"
        _record("Teacher priority ranking is populated", status == 200 and bool(rows), f"-> {status}, {len(rows)} students, top: {top}")

    # ADR-013: a token scoped to c1 must not read another class.
    if t_token:
        status, _ = _get(f"{url}/api/classes/zz9/students", t_token)
        _record("Cross-class read is refused (ADR-013 IDOR)", status == 403, f"c1 token reading class zz9 -> {status} (expected 403)")

    # ADR-022: reflect must be bound to a real, finished session.
    if s_token:
        status, body = _post(f"{url}/api/debate/reflect", {"session_id": "does-not-exist", "revised_claim": "x"}, s_token, timeout=60)
        _record("Reflection on a bogus session is refused (ADR-022)", status == 404, f"-> {status} {body.get('detail','')}")

    if args.skip_debate or not s_token:
        print("\n(skipping the Gemini-billed student journey)")
    else:
        essay = (
            "Social media is entirely responsible for the decline in teenage attention spans. "
            "Everyone I know who uses it cannot focus, so the cause is obvious."
        )
        # class_id must come from the student id, not be hardcoded: the token is
        # scoped to the student's own class (ADR-018), so a hardcoded "c1" here
        # made the whole journey 403 the moment the default moved off c1.
        student_class = args.student.split("_", 1)[0]
        status, started = _post(
            f"{url}/api/debate/start",
            {"essay_text": essay, "student_id": args.student, "class_id": student_class, "name": "Smoke Test"},
            s_token,
        )
        session_id = started.get("session_id", "")
        persona = started.get("persona_name", "?")
        ok = status == 200 and bool(session_id) and bool((started.get("turn") or {}).get("question"))
        _record("Debate starts and produces a Socratic question", ok, f"-> {status}, persona: {persona}, session: {session_id[:8]}...")

        if session_id:
            reply = "Fair -- my sample is small and I did not control for sleep or workload."
            completed = False
            for i in range(3):
                status, turn = _post(f"{url}/api/debate/turn", {"session_id": session_id, "student_reply": reply}, s_token)
                completed = bool(turn.get("completed"))
                if completed:
                    break
            _record("Debate runs to completion (3 turns)", completed, f"completed after turn {i + 1}")

            status, refl = _post(
                f"{url}/api/debate/reflect",
                {"session_id": session_id, "revised_claim": "Heavy social media use may contribute, but my sample cannot establish cause."},
                s_token,
            )
            has_flag = "degraded" in refl
            _record(
                "Reflection returns a degraded flag (ADR-024)",
                status == 200 and has_flag,
                f"-> {status}, resolved={refl.get('resolved')}, growth_bonus={refl.get('growth_bonus')}, degraded={refl.get('degraded')}",
            )
            bonus = refl.get("growth_bonus")
            _record(
                "growth_bonus is inside its declared range (ADR-024)",
                isinstance(bonus, (int, float)) and 0.0 <= float(bonus) <= 1.0,
                f"growth_bonus = {bonus} (must be 0.0-1.0)",
            )
            status, _ = _post(f"{url}/api/debate/reflect", {"session_id": session_id, "revised_claim": "farming a second bonus"}, s_token, timeout=60)
            _record("A session's reflection is single-use (ADR-022)", status in (404, 409), f"second reflect -> {status} (expected 404/409)")

    failed = [r for r in _results if r[1] == FAIL]
    print("\n" + "=" * 60)
    print(f"{len(_results) - len(failed)} passed, {len(failed)} failed.")
    if failed:
        print("\nNOT READY -- fix these before recording:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    print("\nLive service behaves as documented.")


if __name__ == "__main__":
    main()
