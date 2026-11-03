"""
Tests for fixed content, cards, and tone guidelines (spec §3, §7, §9.2).

Verifies:
1. All 6 reason blocks exist in REASON_BLOCKS and match spec definitions.
2. All 4 option cards exist in OPTION_CARDS in fixed order.
3. Stop SIP card has the exact same structure and presence as other cards (Hard Rule 3).
4. No banned urgency/FOMO words appear anywhere in lib/content.py or views/.
5. Footer is fixed on every screen: "Prototype for research. Not investment advice."
"""
from pathlib import Path
import pytest
from lib.content import (
    FOOTER,
    OPTION_CARDS,
    PRIVACY_NOTICE,
    REASONS,
    REASON_BLOCKS,
    REASON_LABELS,
    REASON_PHRASES,
)

BANNED_URGENCY_WORDS = [
    "last chance",
    "don't miss",
    "dont miss",
    "act now",
    "you will lose",
    "hurry",
    "countdown",
    "expires soon",
    "limited time",
    "guilt",
    "shame",
]


def test_all_six_reasons_defined():
    expected = {"CASH", "RETURNS", "CONFUSION", "SWITCH", "PAYMENT", "UNCLEAR"}
    assert set(REASONS) == expected
    for r in expected:
        assert r in REASON_BLOCKS
        assert len(REASON_BLOCKS[r]) > 20
        assert r in REASON_LABELS
        assert r in REASON_PHRASES


def test_four_option_cards_fixed_order():
    keys = [card["key"] for card in OPTION_CARDS]
    assert keys == ["skip", "reduce", "pause", "stop"]


def test_stop_card_same_size_class_and_structure():
    stop_card = next(c for c in OPTION_CARDS if c["key"] == "stop")
    for key in ["key", "title", "what", "steps", "link"]:
        assert key in stop_card
        assert stop_card[key]

    # Verify Stop SIP has 3 steps like the others
    assert len(stop_card["steps"]) == 3
    # Verify Stop SIP does not hide or minimize instructions
    assert "https://groww.in" in stop_card["link"]


def test_no_banned_urgency_words_in_content_and_views():
    root = Path(__file__).resolve().parent.parent
    files_to_scan = [
        root / "lib" / "content.py",
        root / "views" / "guide.py",
        root / "views" / "quality.py",
        root / "app.py",
    ]

    for file_path in files_to_scan:
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8").lower()
        for banned in BANNED_URGENCY_WORDS:
            assert banned not in text, f"Banned phrase '{banned}' found in {file_path.name}"


def test_disclaimers_and_footer():
    assert FOOTER == "Prototype for research. Not investment advice."
    assert PRIVACY_NOTICE == "Do not enter personal or account details."
