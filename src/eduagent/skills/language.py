"""Language detection -- deterministic, ZERO LLM (deterministic-first, design principle #3:
matching characters to an alphabet is a lookup problem, not a reasoning
problem, so it stays a pure function like persona_selector's keyword match).

Feeds `ctx.state["language"]` which Summarizer/Debate Loop/Scorer use to
answer in the essay's own language instead of always defaulting to English.
"""

from __future__ import annotations

_VIETNAMESE_CHARS = set(
    "đàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹ"
)

# A single stray accented character (a pasted name, a typo) shouldn't flip
# the whole essay to Vietnamese -- require a couple of independent hits
# before committing to it.
_MIN_VIETNAMESE_HITS = 2

LANGUAGE_NAMES = {"vi": "Vietnamese", "en": "English"}


def detect_language(text: str) -> str:
    """Returns 'vi' or 'en'. English is the default/fallback -- an essay with
    no Vietnamese-specific diacritics is treated as English regardless of
    length, since that's the only other language this project supports."""
    if not text:
        return "en"
    hits = sum(1 for ch in text.lower() if ch in _VIETNAMESE_CHARS)
    return "vi" if hits >= _MIN_VIETNAMESE_HITS else "en"


def language_instruction(language: str) -> str:
    """Appended to an agent node's system_instruction so student-facing text
    (debate questions, feedback, rationale) matches the essay's language --
    a Vietnamese essay should get natural Vietnamese Socratic questions, not
    an English question the student then has to translate themselves."""
    name = LANGUAGE_NAMES.get(language, "English")
    return (
        f"CRITICAL LANGUAGE INSTRUCTION: The student's essay is written in {name}. "
        f"You MUST write ALL of your student-facing output (questions, feedback, explanations, and rationale) "
        f"strictly in natural, fluent {name} -- never switch language on the student."
    )

