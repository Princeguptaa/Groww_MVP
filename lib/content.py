"""
All fixed, human-written text for the SIP Pause Guide.

Spec §7: the AI never writes or edits advice text.
Everything the user sees (except the one AI-generated sentence) comes from here.
"""
from __future__ import annotations

import datetime

# ---------------------------------------------------------------------------
# Reasons (spec §5.1)
# ---------------------------------------------------------------------------
REASONS = ["CASH", "RETURNS", "CONFUSION", "SWITCH", "PAYMENT", "UNCLEAR"]

REASON_LABELS = {
    "CASH": "Cash is tight or money is needed elsewhere",
    "RETURNS": "Returns or value look low or worrying",
    "CONFUSION": "Unsure how it works or where my money is",
    "SWITCH": "Want to use the money in another investment or app",
    "PAYMENT": "Instalment or payment problem",
    "UNCLEAR": "Unclear or not a stop reason",
}

# Plain-language phrase used in the "It sounds like ..." sentence (Step 2)
REASON_PHRASES = {
    "CASH": "cash is tight right now",
    "RETURNS": "the returns or value look low",
    "CONFUSION": "you are unsure how it works or where your money is",
    "SWITCH": "you want to use the money somewhere else",
    "PAYMENT": "there is an instalment or payment problem",
    "UNCLEAR": "your situation is not clear to us",
}

# ---------------------------------------------------------------------------
# Reason blocks — shown first in Step 3 (spec §7)
# ---------------------------------------------------------------------------
REASON_BLOCKS = {
    "CASH": (
        "A tight month happens to many people. You do not have to stop to get "
        "breathing room. You can skip one instalment or lower the amount for a "
        "while. Your units stay invested either way."
    ),
    "RETURNS": (
        "A value below what you put in is common in the first months of a "
        "market-linked fund. Returns are not guaranteed and short-term moves "
        "do not predict what comes next. Each SIP instalment buys units at "
        "that day\u2019s price. This tool cannot tell you whether to keep or "
        "leave a fund. It can show you your options."
    ),
    "CONFUSION": (
        "After a debit, the instalment goes through an order and units are "
        "added after the fund\u2019s NAV date, which can take a few working days. "
        "Check the order status in your SIP details. The first instalment of "
        "a new SIP often has a gap of at least 30 days before the second. "
        "The Groww Help links below explain each step."
    ),
    "SWITCH": (
        "Stopping future instalments does not sell units you already hold. "
        "Moving money to another investment is your decision. This tool "
        "cannot compare investments or recommend any."
    ),
    "PAYMENT": (
        "Instalments can fail when the bank balance is low or the autopay is "
        "not approved. Groww Help advises keeping enough balance a few days "
        "before the SIP date and lets you pay a missed instalment once. If "
        "several instalments fail in a row, the fund house may cancel the SIP."
    ),
    "UNCLEAR": (
        "No problem. Here are all your options. You can also tap one of the "
        "reasons above to see more."
    ),
}

# ---------------------------------------------------------------------------
# Context strip and Screen captions (spec §4.1)
# ---------------------------------------------------------------------------
CONTEXT_STRIP = "Groww > My SIPs > Example SIP"
CONTEXT_CAPTION = "Prototype of a feature inside Groww. It is not connected to any account."
SCREEN_A_CAPTION = (
    "Your message is sent to an AI service (Google Gemini) to work out the reason. "
    "This tool does not store it. Please do not enter personal or account details."
)

# ---------------------------------------------------------------------------
# Tile summary lines — Screen B (spec §7)
# ---------------------------------------------------------------------------
TILE_SUMMARIES = {
    "skip": "Skip one instalment. Your SIP stays active.",
    "reduce": "Lower the amount for a while. Your SIP stays active.",
    "break": "Skip as each month comes, or stop and start again later.",
    "stop": "Stop future instalments. Your units stay.",
}

# ---------------------------------------------------------------------------
# Option cards — fixed order, always all four (spec §7)
# ---------------------------------------------------------------------------
OPTION_CARDS = [
    {
        "key": "skip",
        "title": "Skip this month",
        "summary": "Skip one instalment. Your SIP stays active.",
        "what": (
            "Skip one instalment. Groww says that once an instalment is skipped, "
            "your investments continue as is. Your units stay invested."
        ),
        "steps": [
            "Open My SIPs and select the SIP.",
            "Tap Edit SIP.",
            "Choose Skip Installment and confirm the month.",
        ],
        "link": "https://groww.in/help/mutual-funds/order/can-i-pause-sip-for-next-month",
        "has_calendar": True,
    },
    {
        "key": "reduce",
        "title": "Reduce the amount for a while",
        "summary": "Lower the amount for a while. Your SIP stays active.",
        "what": (
            "Lower the monthly amount, then raise it again if you wish. "
            "Your SIP stays active."
        ),
        "steps": [
            "Open My SIPs and select the SIP.",
            "Tap Edit SIP, then Edit Amount & Date.",
            "Change the amount and tap Save Changes.",
        ],
        "link": "https://groww.in/blog/how-to-edit-sip-on-groww",
        "has_calendar": False,
    },
    {
        "key": "break",
        "title": "Take a longer break",
        "summary": "Skip as each month comes, or stop and start again later.",
        "what": (
            "Groww lets you skip an instalment when you wish. For a longer break "
            "you can skip as each month comes, or stop the SIP and start a new one later."
        ),
        "steps": [],
        "note": "See the Groww Help page for the exact options.",
        "link": "https://groww.in/help/mutual-funds/order/can-i-pause-sip-for-next-month",
        "has_calendar": True,
    },
    {
        "key": "stop",
        "title": "Stop the SIP",
        "summary": "Stop future instalments. Your units stay.",
        "what": (
            "Stop future instalments. Units you already hold stay in your "
            "account. You can start a new SIP any time."
        ),
        "steps": [
            "In Mutual Funds, open the SIPs tab.",
            "Choose the SIP.",
            "Tap Cancel SIP in the top right.",
        ],
        "link": "https://groww.in/help/mutual-funds/mf-sip/how-to-cancel-my-sip",
        "has_calendar": False,
    },
]

# ---------------------------------------------------------------------------
# Tap chips — six phrases (spec §4.1)
# ---------------------------------------------------------------------------
CHIPS = [
    "Money is tight this month",
    "My value is below what I invested",
    "I don\u2019t understand where my money or instalment is",
    "I want to use this money elsewhere",
    "An instalment failed or looks wrong",
    "I\u2019m just not sure",
]

# Expected reason for each chip (used by the rule router as a shortcut)
CHIP_REASONS = {
    "Money is tight this month": "CASH",
    "My value is below what I invested": "RETURNS",
    "I don\u2019t understand where my money or instalment is": "CONFUSION",
    "I don't understand where my money or instalment is": "CONFUSION",
    "I want to use this money elsewhere": "SWITCH",
    "An instalment failed or looks wrong": "PAYMENT",
    "I\u2019m just not sure": "UNCLEAR",
    "I'm just not sure": "UNCLEAR",
}

# ---------------------------------------------------------------------------
# Decline text (spec §5.3 gate 4)
# ---------------------------------------------------------------------------
DECLINE_TEXT = (
    "This tool can\u2019t recommend funds or give investment advice. "
    "It can help you understand your options for your SIP."
)

# ---------------------------------------------------------------------------
# Footer and disclaimers (spec §4, hard rule 1)
# ---------------------------------------------------------------------------
FOOTER = "Prototype for research. Not investment advice."

PRIVACY_NOTICE = "Do not enter personal or account details."

AI_DISCLOSURE = (
    "Your message is sent to an AI service (Google Gemini) to work out the reason. "
    "This tool does not store it."
)

# ---------------------------------------------------------------------------
# Check-in .ics fixed strings (spec §4.3)
# ---------------------------------------------------------------------------
ICS_TITLE = "Check my SIP plan"
ICS_DESCRIPTION = (
    "A calm moment to look at my plan. Not investment advice."
)


def create_ics(check_in_date: datetime.date) -> str:
    """Generate RFC 5545 compliant .ics calendar content."""
    dt_str = check_in_date.strftime("%Y%m%d")
    next_day = (check_in_date + datetime.timedelta(days=1)).strftime("%Y%m%d")
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//SIP Pause Guide//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"SUMMARY:{ICS_TITLE}\r\n"
        f"DESCRIPTION:{ICS_DESCRIPTION}\r\n"
        f"DTSTART;VALUE=DATE:{dt_str}\r\n"
        f"DTEND;VALUE=DATE:{next_day}\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


# ---------------------------------------------------------------------------
# Groww Help link
# ---------------------------------------------------------------------------
GROWW_HELP_LINK = "https://groww.in/help"
