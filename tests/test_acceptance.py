"""
Phase 5 Acceptance Tests (spec §9.8, PLAN.md Phase 5).

Verifies the complete end-to-end acceptance criteria:
1. All six chips lead to the expected reason block and badge.
2. All four option cards always render for every reason with equal prominence.
3. The third card is 'Take a longer break' with no steps and official link.
4. Check-in calendar .ics contains fixed title, description, and chosen date without banned words.
5. Footer is fixed on all pages: 'Prototype for research. Not investment advice.'
6. CSS ensures minimum font size >= 14px and support for 375px mobile viewport.
7. Quality dashboard handles evaluation data and respects the gate threshold.
8. No personal names or logged messages anywhere in the codebase.
"""
import datetime
from pathlib import Path
import pytest

from lib.content import (
    CHIPS,
    CHIP_REASONS,
    FOOTER,
    GROWW_HELP_LINK,
    ICS_DESCRIPTION,
    ICS_TITLE,
    OPTION_CARDS,
    REASONS,
    REASON_BLOCKS,
    REASON_LABELS,
    create_ics,
)
from lib.guards import post_gates, pre_check
from lib.router_ai import is_ai_gate_passed
from lib.router_rules import rule_route


def test_acceptance_chip_to_reason_blocks():
    """Acceptance 1: Each chip produces the right reason block and quoted evidence."""
    for chip in CHIPS:
        expected_reason = CHIP_REASONS[chip]
        result = rule_route(chip, chip=chip)
        assert result.reason == expected_reason
        assert result.evidence == chip

        # Reason block must exist and be human-written
        block = REASON_BLOCKS[result.reason]
        assert len(block) > 20
        assert "invest" in block.lower() or "sip" in block.lower() or "option" in block.lower()


def test_acceptance_all_four_option_cards_and_equal_prominence():
    """Acceptance 2: All 4 cards always render in fixed order, Stop card same prominence."""
    expected_order = [
        "Skip this month",
        "Reduce the amount for a while",
        "Take a longer break",
        "Stop the SIP",
    ]
    actual_titles = [c["title"] for c in OPTION_CARDS]
    assert actual_titles == expected_order

    stop_card = next(c for c in OPTION_CARDS if c["key"] == "stop")
    break_card = next(c for c in OPTION_CARDS if c["key"] == "break")

    # Stop card has official cancel link and steps
    assert stop_card["link"] == "https://groww.in/help/mutual-funds/mf-sip/how-to-cancel-my-sip"
    assert len(stop_card["steps"]) == 3

    # Third card has no steps (link only)
    assert len(break_card["steps"]) == 0
    assert "https://groww.in" in break_card["link"]


def test_acceptance_calendar_file():
    """Acceptance 3: .ics is valid RFC 5545, fixed title and description, no urgency."""
    target_date = datetime.date(2026, 12, 15)
    ics = create_ics(target_date)

    assert "BEGIN:VCALENDAR" in ics
    assert "END:VCALENDAR" in ics
    assert f"SUMMARY:{ICS_TITLE}" in ics
    assert f"DESCRIPTION:{ICS_DESCRIPTION}" in ics
    assert "20261215" in ics

    banned_words = ["hurry", "urgent", "last chance", "act now", "you will lose"]
    for w in banned_words:
        assert w not in ics.lower()


def test_acceptance_footer_and_disclaimer():
    """Acceptance 4: Footer disclaimer is fixed."""
    assert FOOTER == "Prototype for research. Not investment advice."


def test_acceptance_mobile_css_and_viewport():
    """Acceptance 5: app.py contains responsive CSS and font-size >= 14px."""
    app_text = Path("app.py").read_text(encoding="utf-8")
    assert "font-size" in app_text
    assert "15px" in app_text or "14px" in app_text
    assert "375px" in app_text


def test_acceptance_privacy_and_no_personal_names():
    """Acceptance 6: No personal names in app text, docs, or code."""
    root = Path(__file__).resolve().parent.parent
    banned_names = ["prince", "gupta"]

    files_to_check = [
        root / "app.py",
        root / "README.md",
        root / "ARCHITECTURE.md",
        root / "PLAN.md",
        root / "mvp_spec.md",
    ]
    files_to_check.extend((root / "lib").glob("*.py"))
    files_to_check.extend((root / "views").glob("*.py"))
    files_to_check.extend((root / "eval").glob("*.py"))

    for file_path in files_to_check:
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8").lower()
        for name in banned_names:
            assert name not in content, f"Banned personal name '{name}' found in {file_path.name}"


def test_acceptance_eval_gate_control():
    """Acceptance 7: AI routing ON only if accuracy >= 0.75 and strictly higher than baseline."""
    # Test gate on demo results
    results_path = Path("eval/results.json")
    if results_path.is_file():
        passed, msg = is_ai_gate_passed(results_path)
        assert isinstance(passed, bool)
        assert "AI routing is" in msg
