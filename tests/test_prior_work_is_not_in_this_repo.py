"""Hard gate for the "New Projects Only" rule.

Rules §6 requires every submission to be newly created during the Submission
Period, and requires any pre-existing work to be disclosed. This project does
disclose its prior art (see `docs/eligibility_statement.md` §0 and README §1):
the author's earlier hackathon entry was kept on disk as reading material while
this system was designed, and **none of its source was carried over**.

That claim is only worth as much as its enforcement. Previously the enforcement
was a passive `.gitignore` rule, which had two problems:

  1. It only prevents a mistake; it never *detects* one. If a single file had
     slipped in through `git add -f` or a path the rule did not cover, nothing
     would have failed.
  2. Naming the prior project's directory in a public `.gitignore` reads as an
     ambiguous signal to anyone who sees it without the surrounding disclosure
     -- it hints that the old code was nearby without showing that it stayed
     out, which is the opposite of reassuring.

So the rule is enforced here instead: an assertion that fails the build. It
checks the repository itself rather than trusting an ignore rule, and it travels
with the repo, so it holds in any clone on any machine.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent

# The prior project is "CritiqAI", written CritqAI in its own repository path.
# Matching on the distinctive stem catches both spellings and any casing.
_PRIOR_WORK_STEM = "critq"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=_ROOT, capture_output=True, text=True, check=True
    ).stdout


def _is_repo() -> bool:
    try:
        _git("rev-parse", "--git-dir")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


requires_git = pytest.mark.skipif(not _is_repo(), reason="not a git checkout")


def _offending(paths: str) -> list[str]:
    """Paths carrying the prior project's stem, excluding this test itself and
    the disclosure documents, which are *supposed* to name it."""
    allowed_suffixes = (
        "tests/test_prior_work_is_not_in_this_repo.py",
        "docs/eligibility_statement.md",
    )
    hits = []
    for line in paths.splitlines():
        p = line.strip()
        if not p or _PRIOR_WORK_STEM not in p.lower():
            continue
        if p.endswith(allowed_suffixes):
            continue
        hits.append(p)
    return hits


@requires_git
def test_no_tracked_file_comes_from_the_prior_project() -> None:
    """The check that matters: nothing from the earlier project is in the tree
    that gets cloned."""
    offenders = _offending(_git("ls-files"))
    assert not offenders, (
        "These tracked paths come from the author's prior project, which Rules §6 "
        f"requires to stay out of this submission: {offenders}. Remove them from the "
        "index (`git rm --cached <path>`) before committing."
    )


@requires_git
def test_the_prior_project_never_entered_git_history() -> None:
    """A file removed today is still readable from an old commit, and the
    disclosure claims it was never committed *at all* -- so verify the claim
    that is actually written down, across every commit on every branch."""
    objects = _git("rev-list", "--all", "--objects")
    offenders = _offending("\n".join(line.partition(" ")[2] for line in objects.splitlines()))
    assert not offenders, (
        "The disclosure in docs/eligibility_statement.md states the prior project never "
        f"entered this repository's history, but these objects contradict it: {offenders[:20]}. "
        "The statement must be corrected, or the history rewritten."
    )


def test_the_detector_can_actually_fire() -> None:
    """Guards the guard (ADR-019). Both assertions above pass by finding nothing,
    which is exactly how a broken detector also behaves -- so prove the matcher
    recognises the pattern it exists for, and that the allow-list does not
    swallow an arbitrary path."""
    assert _offending("CritqAI-main/README.md") == ["CritqAI-main/README.md"]
    assert _offending("src/eduagent/critqai_helper.py") == ["src/eduagent/critqai_helper.py"]
    assert _offending("src/eduagent/server.py") == []
    # The disclosure documents may name it; nothing else may.
    assert _offending("docs/eligibility_statement.md") == []
