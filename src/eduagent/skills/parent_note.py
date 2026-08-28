"""Wave 4 #3 -- Parent Communication Co-Pilot ("Copy Parent Update Note").

This project's own risk analysis rules out auto-sending email to parents
(mass mailing 40+ inboxes on every submission is a FERPA/COPPA risk and
drowns quota, same discipline as Phase 0/3's Gmail HITL gate). Instead
this generates ONE short, encouraging note text for the teacher to
review and copy themselves -- the LLM only phrases what the deterministic
Priority Engine (priority_engine.py) already computed; it never decides
WHO gets flagged (that stays 100% rule-engine, zero-LLM, per
deterministic-first, design principle #3) or sends anything itself.
"""

from __future__ import annotations

import logging

from eduagent.config import GEMINI
from eduagent.llm import LLMGenerationError, generate_text
from eduagent.skills.language import language_instruction

_logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a warm, supportive assistant helping a teacher write a short "
    "note home to a parent about their child's critical-thinking practice. "
    "Rules:\n"
    "- 1-2 sentences only.\n"
    "- Gentle, encouraging tone -- never alarming, never clinical, never "
    "share raw scores or the word 'priority'.\n"
    "- Name ONE concrete thing the parent can do at home (a low-pressure "
    "conversation starter), not a list.\n"
    "- Never mention AI, algorithms, or scoring systems -- write as if the "
    "teacher observed this personally.\n"
)

_FALLBACK_TEMPLATE_EN = (
    "{name} has been working through some challenging debate topics in class lately. "
    "A relaxed chat at home about something {name} feels strongly about -- and gently "
    "asking 'what makes you say that?' -- could help reinforce what we're practicing together."
)

_FALLBACK_TEMPLATE_VI = (
    "{name} gần đây đã rất tích cực tham gia các buổi rèn luyện tư duy phản biện trên lớp. "
    "Ở nhà, gia đình có thể trò chuyện cởi mở cùng {name} về các chủ đề em quan tâm và nhẹ nhàng hỏi 'điều gì khiến con nghĩ như vậy?' để giúp con tự tin hơn trong lập luận."
)


def draft_parent_note(*, student_name: str, reason: dict, language: str = "en") -> tuple[str, bool]:
    """reason: the `reason` block from priority_engine.compute_priority()
    (stuck_streak_count/score_trend/inactivity_days/shared_fallacies) --
    already-computed deterministic facts, phrased here, never re-derived.

    Returns (note_text, degraded). On any LLM failure, returns a generic
    but still genuine fallback rather than blocking the teacher's workflow
    (same graceful-degradation discipline as Phase 4)."""
    facts = []
    if reason.get("stuck_streak_count", 0) >= 2:
        facts.append(f"has repeated the same type of debate challenge {reason['stuck_streak_count']} times without a breakthrough yet")
    if reason.get("score_trend") == "declining":
        facts.append("has seen scores dip over their last few essays")
    # Wave 15 #3: phrased as unevenness, not decline -- "volatile" means the
    # scores swung and recovered, so telling a parent their child is slipping
    # would be false.
    if reason.get("score_trend") == "volatile":
        facts.append("has had one noticeably weaker essay among otherwise steady work")
    if reason.get("inactivity_days", 0) >= 14:
        facts.append(f"hasn't submitted an essay in {reason['inactivity_days']} days")
    if reason.get("shared_fallacies"):
        facts.append(f"could use more practice distinguishing {', '.join(reason['shared_fallacies'][:2])}")

    if not facts:
        facts.append("is actively working through the class's critical-thinking exercises")

    prompt = (
        f"Student: {student_name}\n"
        f"Teacher's private observation notes (do not quote verbatim, just use as context): "
        f"{student_name} {'; '.join(facts)}.\n\n"
        f"Write the 1-2 sentence note home now."
    )
    system_instruction = _SYSTEM_INSTRUCTION + "\n" + language_instruction(language)

    try:
        note = generate_text(model=GEMINI.flash_model, system_instruction=system_instruction, prompt=prompt)
        return note.strip(), False
    except LLMGenerationError:
        _logger.warning("draft_parent_note degraded to fallback for %s", student_name)
        tmpl = _FALLBACK_TEMPLATE_VI if language == "vi" else _FALLBACK_TEMPLATE_EN
        return tmpl.format(name=student_name), True


__all__ = ["draft_parent_note"]
