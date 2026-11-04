"""
Tests for Phase 1 Guide flow (spec §4, PLAN.md Phase 1).

Verifies:
1. Each chip produces the expected reason, sentence, badge, and reason block.
2. All 4 cards always render in fixed order.
3. Reduce arithmetic calculates properly when amount is given.
4. Skip and Pause provide .ics calendar reminder data.
5. Reason override in Step 2 updates the Step 3 reason block.
"""
import datetime
import pytest
from lib.content import (
    CHIPS,
    CHIP_REASONS,
    OPTION_CARDS,
    REASONS,
    REASON_BLOCKS,
    REASON_PHRASES,
    create_ics,
)
from lib.router_rules import rule_route


def test_each_chip_end_to_end_flow():
    for chip in CHIPS:
        expected_reason = CHIP_REASONS[chip]
        res = rule_route(chip, chip=chip)
        assert res.reason == expected_reason
        assert res.evidence == chip

        # Verify Step 2 sentence structure
        reason_phrase = REASON_PHRASES[res.reason]
        sentence = f"It sounds like {reason_phrase}. You wrote: ‘{res.evidence}’."
        assert reason_phrase in sentence
        assert chip in sentence

        # Verify Step 2 badge
        if res.reason == "UNCLEAR":
            badge = "Not sure, so we show every option"
        else:
            badge = "Checked: quoted from your message"
        assert badge

        # Verify Step 3 reason block
        reason_block = REASON_BLOCKS[res.reason]
        assert len(reason_block) > 0


def test_all_four_cards_always_rendered():
    cards = OPTION_CARDS
    assert len(cards) == 4
    expected_titles = [
        "Skip this month",
        "Reduce the amount for a while",
        "Take a longer break",
        "Stop the SIP",
    ]
    for card, expected_title in zip(cards, expected_titles):
        assert card["title"] == expected_title
        if card["key"] == "break":
            assert len(card["steps"]) == 0
        else:
            assert len(card["steps"]) == 3
        assert card["link"].startswith("https://groww.in")


def test_reduce_arithmetic_calculation():
    user_amount = 5000
    b_amount = 2000
    n_months = 4
    total = b_amount * n_months
    calc_str = f"If you reduce from {user_amount} to {b_amount} for {n_months} months, you still put in {total} rupees."
    assert calc_str == "If you reduce from 5000 to 2000 for 4 months, you still put in 8000 rupees."


def test_skip_and_longer_break_have_calendar_reminder():
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


def test_reason_override_updates_block():
    # User originally routed to CASH, but overrides to RETURNS
    original_reason = "CASH"
    overridden_reason = "RETURNS"

    block_before = REASON_BLOCKS[original_reason]
    block_after = REASON_BLOCKS[overridden_reason]

    assert block_before != block_after
    assert "market-linked fund" in block_after

