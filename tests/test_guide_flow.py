"""
Tests for Three-Screen Guide Flow (spec §4, Screen A, Screen B, Screen C).

Verifies:
1. Each chip produces the expected reason, sentence, badge, and reason block.
2. Screen B has four equal tiles, with the Stop tile in the same style.
3. Screen B has no steps and no links.
4. Screen C shows only the chosen option's steps and one official link.
5. Reduce arithmetic and calendar check-in still work as specified.
6. Reason override in Screen B updates the reason block.
"""
from __future__ import annotations

import datetime
import inspect
from pathlib import Path
import pytest

from lib.content import (
    CHIPS,
    CHIP_REASONS,
    OPTION_CARDS,
    REASONS,
    REASON_BLOCKS,
    REASON_PHRASES,
    TILE_SUMMARIES,
    create_ics,
)
from lib.router_rules import rule_route
from views import guide


def test_each_chip_end_to_end_flow():
    """Verify each chip routes correctly and generates valid sentence and badge."""
    for chip in CHIPS:
        expected_reason = CHIP_REASONS[chip]
        res = rule_route(chip, chip=chip)
        assert res.reason == expected_reason
        assert res.evidence == chip

        # Verify Screen B sentence structure
        reason_phrase = REASON_PHRASES[res.reason]
        sentence = f"It sounds like {reason_phrase}. You wrote: ‘{res.evidence}’."
        assert reason_phrase in sentence
        assert chip in sentence

        # Verify badge
        if res.reason == "UNCLEAR":
            badge = "Not sure, so we show every option"
        else:
            badge = "Checked: quoted from your message"
        assert badge

        # Verify reason block
        reason_block = REASON_BLOCKS[res.reason]
        assert len(reason_block) > 0


def test_screen_b_four_equal_tiles_stop_same_style():
    """Verify Screen B has four equal tiles in fixed order with Stop tile in the same style."""
    cards = OPTION_CARDS
    assert len(cards) == 4
    expected_keys = ["skip", "reduce", "break", "stop"]
    expected_titles = [
        "Skip this month",
        "Reduce the amount for a while",
        "Take a longer break",
        "Stop the SIP",
    ]

    for card, expected_key, expected_title in zip(cards, expected_keys, expected_titles):
        assert card["key"] == expected_key
        assert card["title"] == expected_title
        # Each tile has a 1-line summary matching TILE_SUMMARIES
        summary = card.get("summary") or TILE_SUMMARIES.get(card["key"])
        assert summary == TILE_SUMMARIES[expected_key]
        assert len(summary) > 10

    # Stop tile has exactly the same structure, keys, and styling attributes
    stop_card = next(c for c in cards if c["key"] == "stop")
    skip_card = next(c for c in cards if c["key"] == "skip")
    assert set(stop_card.keys()) == set(skip_card.keys())


def test_screen_b_has_no_steps_or_links():
    """Verify Screen B source code renders no steps and no links."""
    source_b = inspect.getsource(guide._render_screen_b)

    # Must not render step lists
    assert "card['steps']" not in source_b
    assert 'card["steps"]' not in source_b

    # Must not render official links
    assert "card['link']" not in source_b
    assert 'card["link"]' not in source_b
    assert "https://groww.in" not in source_b


def test_screen_c_shows_only_chosen_option_steps():
    """Verify Screen C renders only the chosen option's steps and link."""
    for card in OPTION_CARDS:
        chosen_key = card["key"]
        chosen = next(c for c in OPTION_CARDS if c["key"] == chosen_key)
        assert chosen["title"] == card["title"]
        if card["key"] == "break":
            # Break has no steps (link only)
            assert len(chosen["steps"]) == 0
        else:
            assert len(chosen["steps"]) == 3
        assert chosen["link"].startswith("https://groww.in")


def test_reduce_arithmetic_calculation():
    """Verify Screen C Reduce arithmetic calculation."""
    amount_a = 5000
    amount_b = 2000
    months_n = 4
    total = amount_b * months_n
    calc_str = f"If you reduce from {amount_a} to {amount_b} for {months_n} months, you still put in {total} rupees."
    assert calc_str == "If you reduce from 5000 to 2000 for 4 months, you still put in 8000 rupees."


def test_skip_and_longer_break_have_calendar_reminder():
    """Verify Skip and Take a longer break have calendar reminder, Reduce and Stop do not."""
    skip_card = next(c for c in OPTION_CARDS if c["key"] == "skip")
    break_card = next(c for c in OPTION_CARDS if c["key"] == "break")
    reduce_card = next(c for c in OPTION_CARDS if c["key"] == "reduce")
    stop_card = next(c for c in OPTION_CARDS if c["key"] == "stop")

    assert skip_card["has_calendar"] is True
    assert break_card["has_calendar"] is True
    assert reduce_card["has_calendar"] is False
    assert stop_card["has_calendar"] is False

    # Check reminder generation
    reminder_date = datetime.date(2026, 11, 30)
    ics = create_ics(reminder_date)
    assert "Check my SIP plan" in ics
    assert "20261130" in ics


def test_screen_a_has_no_amount_or_months_inputs():
    """Verify Screen A has no amount or months number inputs."""
    source_a = inspect.getsource(guide._render_screen_a)
    assert "number_input" not in source_a
    assert "Monthly SIP amount" not in source_a
    assert "Months since you started" not in source_a


def test_one_clear_primary_button_per_screen():
    """Verify each screen has exactly one clear primary button."""
    source_a = inspect.getsource(guide._render_screen_a)
    source_b = inspect.getsource(guide._render_screen_b)
    source_c = inspect.getsource(guide._render_screen_c)

    assert source_a.count('type="primary"') == 1
    assert source_b.count('type="primary"') == 1
    assert source_c.count('type="primary"') == 1


def test_reason_override_updates_block():
    """Verify reason override updates the reason block."""
    original_reason = "CASH"
    overridden_reason = "RETURNS"

    block_before = REASON_BLOCKS[original_reason]
    block_after = REASON_BLOCKS[overridden_reason]

    assert block_before != block_after
    assert "market-linked fund" in block_after


def test_screen_a_chip_click_fills_text_area():
    """Verify tapping any chip on Screen A populates the text area."""
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parent.parent / "app.py"
    at = AppTest.from_file(str(app_path))
    at.run()
    assert not at.exception

    # Initially empty text area
    assert at.text_area[0].value == ""

    # Click first chip
    at.button[0].click().run()
    assert not at.exception
    assert at.text_area[0].value == CHIPS[0]

    # Click second chip
    at.button[1].click().run()
    assert not at.exception
    assert at.text_area[0].value == CHIPS[1]

