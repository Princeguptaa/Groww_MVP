"""
Rule-based router for the SIP Pause Guide.

Spec §5.4: keyword and phrase rules per reason (English, Hindi and Hinglish
words), first match by a fixed priority order, otherwise UNCLEAR.

Used as:
  (a) fallback when there is no API key, the API fails, or a cap is hit
  (b) baseline in the evaluation
  (c) default when the quality gate turns AI routing OFF

The rules are written from the reason definitions in the spec (§5.1).
They are NOT tuned on any golden set.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from lib.content import CHIP_REASONS


@dataclass
class RuleResult:
    reason: str
    evidence: str  # the matched keyword/phrase or chip text


# ---------------------------------------------------------------------------
# Keyword lists per reason — from the spec reason definitions only
# Priority order: PAYMENT, CASH, RETURNS, CONFUSION, SWITCH, then UNCLEAR
# ---------------------------------------------------------------------------

def _phrases(words: list[str]) -> re.Pattern:
    """Build a case-insensitive regex that matches any of the given phrases with word boundaries."""
    patterns = [rf"\b{re.escape(w)}\b" for w in words]
    return re.compile("|".join(patterns), re.IGNORECASE)


# PAYMENT: Instalment or payment problem
_PAYMENT = _phrases([
    "instalment failed", "installment failed",
    "payment failed", "payment problem", "payment issue",
    "autopay", "auto pay", "auto-pay",
    "mandate", "nach",
    "debit failed", "deduction failed",
    "transaction failed", "bounced",
    "insufficient balance", "low balance",
    "failed instalment", "failed installment",
    "payment nahi hua", "payment nahi ho raha",
    "kist fail", "kist nahi kata",
    "paisa nahi kata", "paisa kat gaya par",
    "EMI fail", "EMI nahi",
    "instalment looks wrong", "installment looks wrong",
])

# CASH: Cash is tight or money is needed elsewhere
_CASH = _phrases([
    "money is tight", "cash is tight",
    "tight this month", "tight month",
    "need money", "need the money", "need cash",
    "can't afford", "cannot afford",
    "salary delay", "salary late",
    "expense", "expenses",
    "emergency", "medical",
    "loan", "emi",
    "rent", "fees", "fee",
    "job loss", "lost my job", "no income",
    "paise nahi", "paisa nahi", "paise ki zaroorat",
    "paisa chahiye", "paise chahiye",
    "kharcha", "kharche",
    "tangi", "tankhwah",
    "cash problem", "money problem",
    "afford nahi", "budget tight",
    "use this money elsewhere",
    "money elsewhere",
])

# RETURNS: Returns or value look low or worrying
_RETURNS = _phrases([
    "value is below", "value below",
    "returns are low", "returns low", "low returns",
    "loss", "losses", "negative",
    "going down", "went down", "falling",
    "not growing", "no growth",
    "underperforming", "poor performance",
    "market crash", "market down", "market fall",
    "red", "in the red",
    "value kam", "value gir", "giravat",
    "loss ho raha", "loss dikha raha",
    "neeche ja raha", "neeche gaya",
    "fayda nahi", "munafa nahi",
    "return nahi", "return kam",
    "paisa doob", "paisa dub",
])

# CONFUSION: Unsure how it works or where my money is
_CONFUSION = _phrases([
    "don't understand", "do not understand",
    "confused", "confusion",
    "where is my money", "where my money",
    "how does it work", "how it works",
    "what is sip", "what is a sip",
    "nav", "nav date",
    "units not showing", "units not added",
    "order status", "order pending",
    "first instalment gap",
    "samajh nahi", "samajh nahi aa raha",
    "pata nahi", "kaise kaam karta",
    "paisa kahan", "paisa kahan gaya",
    "unit nahi dikha", "unit nahi aaya",
    "kya hota hai",
])

# SWITCH: Want to use the money in another investment or app
_SWITCH = _phrases([
    "another investment", "other investment",
    "another fund", "other fund", "different fund",
    "another app", "other app",
    "switch", "switching",
    "move money", "move to",
    "better fund", "better returns",
    "stock", "stocks", "share market",
    "crypto", "bitcoin",
    "fixed deposit", "fd", "ppf", "nps",
    "real estate", "property", "gold",
    "doosra fund", "doosri jagah",
    "kahin aur", "kisi aur mein",
    "dusra investment", "dusri scheme",
])

# Priority order for matching
_RULES = [
    ("PAYMENT", _PAYMENT),
    ("CASH", _CASH),
    ("RETURNS", _RETURNS),
    ("CONFUSION", _CONFUSION),
    ("SWITCH", _SWITCH),
]


def rule_route(message: str, chip: Optional[str] = None) -> RuleResult:
    """
    Route a message to a reason using keyword rules.

    If a chip was tapped, use its known reason directly.
    Otherwise, first-match by priority order, else UNCLEAR.
    """
    # Chip shortcut
    if chip and chip in CHIP_REASONS:
        return RuleResult(reason=CHIP_REASONS[chip], evidence=chip)

    # Keyword scan
    for reason, pattern in _RULES:
        m = pattern.search(message)
        if m:
            return RuleResult(reason=reason, evidence=m.group(0))

    return RuleResult(reason="UNCLEAR", evidence="")
