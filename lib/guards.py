"""
Pre-AI and post-AI gates for the SIP Pause Guide.

Spec §5.3: run in code, not in the AI prompt.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from lib.content import REASONS, DECLINE_TEXT


@dataclass
class GuardResult:
    passed: bool
    reason: Optional[str] = None       # override reason if gate failed
    decline_text: Optional[str] = None  # shown instead of normal flow


# ---------------------------------------------------------------------------
# Gate 4 (pre-AI): advice / out-of-scope check
# ---------------------------------------------------------------------------
_ADVICE_PATTERNS = re.compile(
    r"which fund|which stock|what (?:should i|to) (?:invest|buy)|"
    r"recommend|best fund|best stock|buy fund|buy stock|"
    r"konsa fund|kaun sa fund|kisme invest|kya kharidun|kisme lagaun",
    re.IGNORECASE,
)


def pre_check(message: str) -> GuardResult:
    """
    Gate 4: if the message asks for fund/stock advice or is off-topic,
    return decline text. No AI call should be made.
    """
    if _ADVICE_PATTERNS.search(message):
        return GuardResult(passed=False, decline_text=DECLINE_TEXT)
    return GuardResult(passed=True)


# ---------------------------------------------------------------------------
# Post-AI gates (run after AI returns)
# ---------------------------------------------------------------------------

def post_gates(
    ai_data: dict,
    message: str,
    chip_used: bool = False,
) -> tuple[str, str]:
    """
    Apply gates 1-3, 5, 7 to the AI result.

    Returns (reason, evidence) — possibly overridden to UNCLEAR.
    """
    reason = ai_data.get("reason", "")
    evidence = ai_data.get("evidence", "")

    # Gate 1: reason code must be one of the six
    if reason not in REASONS:
        return "UNCLEAR", ""

    # Gate 7: strip any confidence number (never show it)
    # Just remove the key if present; we never surface it
    ai_data.pop("confidence", None)

    # Gate 3: message < 3 words and no chip → UNCLEAR
    word_count = len(message.strip().split())
    if word_count < 3 and not chip_used:
        return "UNCLEAR", ""

    # Gate 2: evidence must appear in the message (case-insensitive, whitespace-trimmed)
    if evidence:
        ev_clean = " ".join(evidence.strip().split()).lower()
        msg_clean = " ".join(message.strip().split()).lower()
        if ev_clean not in msg_clean:
            return "UNCLEAR", ""

    # Gate 5: UNCLEAR → show "I'm just not sure" block + all four cards
    # (handled in the view layer — here we just pass it through)

    return reason, evidence

