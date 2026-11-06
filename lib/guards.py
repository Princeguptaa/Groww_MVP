"""
Pre-AI and post-AI gates for the SIP Pause Guide.

Spec §5.3: run in code, not in the AI prompt.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from lib.content import REASONS, DECLINE_TEXT


@dataclass
class GuardResult:
    passed: bool
    reason: Optional[str] = None        # override reason if gate failed
    decline_text: Optional[str] = None  # shown instead of normal flow


# ---------------------------------------------------------------------------
# Gate 4 (pre-AI): advice / out-of-scope check
# ---------------------------------------------------------------------------
_DECLINE_PATTERNS = [
    re.compile(
        r"\b(best|top|good)\b.*?\b(mutual\s+funds?|funds?|stocks?|etfs?|schemes?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bbuy\b.*?\b(funds?|stocks?|shares?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\bignore\b.*?\b(rules?|instructions?)\b",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(which fund|which stock|what fund|what stock|what (?:should i|to) (?:invest|buy)|"
        r"recommend|best fund|best stock|buy fund|buy stock|fund is best|stock is best|"
        r"konsa fund|kaun sa fund|kisme invest|kya kharidun|kisme lagaun)\b",
        re.IGNORECASE | re.DOTALL,
    ),
]


def pre_check(message: str) -> GuardResult:
    """
    Gate 4: if the message asks for fund/stock advice, attempts instruction override,
    or is off-topic, return decline text. No AI call should be made.
    """
    if not message or not isinstance(message, str):
        return GuardResult(passed=True)
    for pat in _DECLINE_PATTERNS:
        if pat.search(message):
            return GuardResult(passed=False, decline_text=DECLINE_TEXT)
    return GuardResult(passed=True)


# ---------------------------------------------------------------------------
# Post-AI gates (run after AI returns)
# ---------------------------------------------------------------------------

def _number_appears_in_text(val: int, text: str) -> bool:
    """Check if a number appears in text as digits, formatted, or words."""
    if not isinstance(val, int) or val <= 0:
        return False
    text_lower = text.lower()

    # 1. Exact digits with word boundaries or punctuation boundaries
    cleaned = re.sub(r"[,₹$]", "", text_lower)
    if re.search(rf"\b{val}\b", cleaned):
        return True

    # 2. Check "k" suffix for thousands (e.g. 5k -> 5000)
    if val >= 1000 and val % 1000 == 0:
        k = val // 1000
        if re.search(rf"\b{k}\s*k\b", text_lower):
            return True
        if re.search(rf"\b{k}\s*(?:thousand|hazar|hazaar)\b", text_lower):
            return True

    # 3. Small numbers (1-12) written in words
    small_words: dict[int, list[str]] = {
        1: ["one", "ek"],
        2: ["two", "do"],
        3: ["three", "teen"],
        4: ["four", "char", "chaar"],
        5: ["five", "paanch", "panch"],
        6: ["six", "chhah", "che"],
        7: ["seven", "saat"],
        8: ["eight", "aath"],
        9: ["nine", "nau"],
        10: ["ten", "das"],
        11: ["eleven", "gyarah"],
        12: ["twelve", "barah"],
    }
    if val in small_words:
        for w in small_words[val]:
            if re.search(rf"\b{w}\b", text_lower):
                return True

    # 4. English words for round thousands (e.g. 5000 -> "five thousand")
    if val >= 1000 and val % 1000 == 0:
        k = val // 1000
        if k in small_words:
            for w in small_words[k]:
                if re.search(rf"\b{w}\s*(?:thousand|hazar|hazaar)\b", text_lower):
                    return True

    return False


def gate_3b(
    amount_inr: Any,
    months: Any,
    message: str,
) -> tuple[Optional[int], Optional[int]]:
    """
    Gate 3b (spec §5.3):
    amount_inr and months are kept only if the number appears in the message text;
    otherwise set to null. They are used only to prefill the inputs, never shown as facts.
    """
    if not message or not isinstance(message, str):
        return None, None

    gated_amount: Optional[int] = None
    if isinstance(amount_inr, (int, float)) and not isinstance(amount_inr, bool):
        try:
            int_amount = int(amount_inr)
            if int_amount > 0 and _number_appears_in_text(int_amount, message):
                gated_amount = int_amount
        except (ValueError, OverflowError):
            pass

    gated_months: Optional[int] = None
    if isinstance(months, (int, float)) and not isinstance(months, bool):
        try:
            int_months = int(months)
            if int_months > 0 and _number_appears_in_text(int_months, message):
                gated_months = int_months
        except (ValueError, OverflowError):
            pass

    return gated_amount, gated_months


def post_gates(
    ai_data: Any,
    message: str,
    chip_used: bool = False,
) -> tuple[str, str]:
    """
    Apply gates 1-3, 3b, 5, 7 to the AI result.

    Returns (reason, evidence) — possibly overridden to UNCLEAR.
    Also filters amount_inr and months in ai_data via Gate 3b.
    """
    if not isinstance(ai_data, dict):
        return "UNCLEAR", ""

    # Gate 7: strip any confidence number (never show it)
    ai_data.pop("confidence", None)

    # Gate 3b: filter amount_inr and months
    amt, mo = gate_3b(ai_data.get("amount_inr"), ai_data.get("months"), message)
    ai_data["amount_inr"] = amt
    ai_data["months"] = mo

    reason = ai_data.get("reason", "")
    evidence = ai_data.get("evidence", "")

    # Gate 1: reason code must be one of the six
    if reason not in REASONS:
        return "UNCLEAR", ""

    # Gate 3: message < 3 words and no chip chosen → UNCLEAR
    msg_words = message.strip().split() if isinstance(message, str) else []
    if len(msg_words) < 3 and not chip_used:
        return "UNCLEAR", ""

    # Gate 2: evidence must appear in the message (case-insensitive, whitespace-trimmed)
    if evidence:
        ev_clean = " ".join(str(evidence).strip().split()).lower()
        msg_clean = " ".join(str(message).strip().split()).lower()
        if ev_clean not in msg_clean:
            return "UNCLEAR", ""

    # Gate 5: UNCLEAR passes through as UNCLEAR
    return reason, evidence
