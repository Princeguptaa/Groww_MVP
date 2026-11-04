"""
Tests for rule-based router (spec §5.4).

Verifies:
1. Each of the six chips maps to its expected reason.
2. English, Hindi, and Hinglish keywords from reason definitions map correctly.
3. Priority ordering (PAYMENT > CASH > RETURNS > CONFUSION > SWITCH > UNCLEAR).
4. Unrecognized phrases default to UNCLEAR.
"""
import pytest
from lib.content import CHIPS, CHIP_REASONS
from lib.router_rules import rule_route


def test_each_chip_routes_to_expected_reason():
    for chip in CHIPS:
        expected = CHIP_REASONS[chip]
        result = rule_route(chip, chip=chip)
        assert result.reason == expected
        assert result.evidence == chip


def test_payment_keywords():
    examples = [
        "My instalment failed yesterday",
        "Autopay deduction was rejected by bank",
        "NACH mandate error occurred",
        "Paisa nahi kata account se",
        "payment nahi hua",
    ]
    for ex in examples:
        res = rule_route(ex)
        assert res.reason == "PAYMENT", f"Failed for: {ex}"
        assert res.evidence != ""


def test_cash_keywords():
    examples = [
        "Money is tight this month due to unexpected expense",
        "Salary delay, cannot afford current expenses",
        "Medical emergency and rent is due",
        "Paise ki zaroorat hai right now",
        "Budget tight chal raha hai",
    ]
    for ex in examples:
        res = rule_route(ex)
        assert res.reason == "CASH", f"Failed for: {ex}"
        assert res.evidence != ""


def test_returns_keywords():
    examples = [
        "Current value is below what I invested",
        "My fund is showing negative returns and loss",
        "Market crash made my portfolio red",
        "Loss dikha raha hai portfolio me",
        "Return kam aa raha hai",
        "Market is in severe crash",
        "The NAV is constantly falling",
        "I am scared of what is happening to my investment",
        "Market panic is making me nervous",
    ]
    for ex in examples:
        res = rule_route(ex)
        assert res.reason == "RETURNS", f"Failed for: {ex}"
        assert res.evidence != ""


def test_confusion_keywords():
    examples = [
        "I do not understand where my money is right now",
        "NAV date has passed and units not added",
        "Samajh nahi aa raha kaise kaam karta hai",
        "Paisa kahan gaya units nahi dikha",
    ]
    for ex in examples:
        res = rule_route(ex)
        assert res.reason == "CONFUSION", f"Failed for: {ex}"
        assert res.evidence != ""


def test_switch_keywords():
    examples = [
        "I want to move money to fixed deposit",
        "Looking to switch to another fund or stocks",
        "Kahin aur invest karna chahta hoon like crypto",
        "Dusra investment try karna hai",
    ]
    for ex in examples:
        res = rule_route(ex)
        assert res.reason == "SWITCH", f"Failed for: {ex}"
        assert res.evidence != ""


def test_unclear_for_random_text():
    examples = [
        "The sky is blue today",
        "Hello good morning",
        "Testing 1 2 3",
    ]
    for ex in examples:
        res = rule_route(ex)
        assert res.reason == "UNCLEAR"
        assert res.evidence == ""

