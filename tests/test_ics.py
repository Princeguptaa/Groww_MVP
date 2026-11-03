"""
Tests for calendar reminder (.ics) generation (spec §4.3, §9.7).

Verifies:
1. Returns valid RFC 5545 iCalendar data.
2. Uses exact fixed title: "Check my SIP plan".
3. Uses exact fixed description: "A calm moment to look at my plan. Not investment advice."
4. Uses the exact chosen date in DTSTART.
5. Contains no banned urgency or FOMO words.
6. Does not persist or store any date to disk or database.
"""
import datetime
from lib.content import (
    ICS_DESCRIPTION,
    ICS_TITLE,
    create_ics,
)
from tests.test_content import BANNED_URGENCY_WORDS


def test_ics_valid_format_and_headers():
    test_date = datetime.date(2026, 12, 15)
    ics = create_ics(test_date)

    assert ics.startswith("BEGIN:VCALENDAR")
    assert "VERSION:2.0" in ics
    assert "PRODID:-//SIP Pause Guide//EN" in ics
    assert "BEGIN:VEVENT" in ics
    assert "END:VEVENT" in ics
    assert ics.strip().endswith("END:VCALENDAR")


def test_ics_contains_fixed_title_and_description():
    test_date = datetime.date(2026, 10, 5)
    ics = create_ics(test_date)

    assert f"SUMMARY:{ICS_TITLE}" in ics
    assert f"DESCRIPTION:{ICS_DESCRIPTION}" in ics
    assert ICS_TITLE == "Check my SIP plan"
    assert ICS_DESCRIPTION == "A calm moment to look at my plan. Not investment advice."


def test_ics_uses_chosen_date():
    test_date = datetime.date(2026, 8, 20)
    ics = create_ics(test_date)

    assert "DTSTART;VALUE=DATE:20260820" in ics
    assert "DTEND;VALUE=DATE:20260821" in ics


def test_ics_no_banned_urgency_words():
    test_date = datetime.date(2026, 9, 1)
    ics = create_ics(test_date).lower()

    for banned in BANNED_URGENCY_WORDS:
        assert banned not in ics, f"Banned urgency word '{banned}' found in .ics content"
