"""
Tests for Phase 3: AI router, gates, caps, model chain, and fallback banner.

Verifies:
1. Valid AI response produces routed reason and evidence.
2. BAD_JSON produces reason="UNCLEAR", evidence="", and the BAD_JSON banner.
3. NO_KEY, SESSION_CAP, DAILY_CAP, API_ERROR fall back to rule router with their respective banners.
4. Hallucinated evidence (not in message) fails Gate 2 and turns into UNCLEAR.
5. Evaluation gate check logic (is_ai_gate_passed).
"""
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from lib.ai_client import (
    API_ERROR,
    BAD_JSON,
    DAILY_CAP,
    NO_KEY,
    SESSION_CAP,
    DailyQuota,
)
from lib.router_ai import (
    PROMPT_VERSION,
    is_ai_gate_passed,
    route_ai,
)


def _make_mock_client_factory(response_text: str):
    """Create a client factory that returns a client producing the given text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return lambda api_key: mock_client


def test_ai_router_successful_routing():
    msg = "I lost my job and money is tight this month"
    json_resp = json.dumps({"reason": "CASH", "evidence": "money is tight", "language": "English"})
    factory = _make_mock_client_factory(json_resp)

    state = {}
    secrets = {"GEMINI_API_KEY": "fake_test_key"}
    quota = DailyQuota(limit=50)

    out = route_ai(msg, state, secrets, quota=quota, client_factory=factory)
    assert out.reason == "CASH"
    assert out.evidence == "money is tight"
    assert out.language == "English"
    assert out.banner == ""
    assert state.get("ai_call_count") == 1


def test_ai_router_bad_json_shows_unclear():
    msg = "my salary is delayed this month"
    factory = _make_mock_client_factory("Sorry, I cannot return JSON right now.")

    state = {}
    secrets = {"GEMINI_API_KEY": "fake_test_key"}
    quota = DailyQuota(limit=50)

    out = route_ai(msg, state, secrets, quota=quota, client_factory=factory)
    # Spec / batch notes: BAD_JSON shows UNCLEAR (all options)
    assert out.reason == "UNCLEAR"
    assert out.evidence == ""
    assert "unexpected format" in out.banner
    # BAD_JSON is not counted against session cap
    assert state.get("ai_call_count", 0) == 0


def test_ai_router_no_key_falls_back_to_rules():
    msg = "Autopay failed and instalment missed"
    state = {}
    secrets = {}  # No key
    quota = DailyQuota(limit=50)

    out = route_ai(msg, state, secrets, quota=quota)
    assert out.reason == "PAYMENT"
    assert out.evidence != ""
    assert "Using simple matching" in out.banner


def test_ai_router_session_cap_falls_back_to_rules():
    msg = "Salary delayed and budget tight"
    state = {"ai_call_count": 10}  # Cap reached
    secrets = {"GEMINI_API_KEY": "fake_test_key"}
    quota = DailyQuota(limit=50)

    out = route_ai(msg, state, secrets, quota=quota)
    assert out.reason == "CASH"
    assert "used all 10 AI checks" in out.banner


def test_ai_router_daily_cap_falls_back_to_rules():
    msg = "Market crash and panic"
    state = {}
    secrets = {"GEMINI_API_KEY": "fake_test_key"}
    quota = DailyQuota(limit=0)  # Daily quota exhausted

    out = route_ai(msg, state, secrets, quota=quota)
    assert out.reason == "RETURNS"
    assert "daily AI limit has been reached" in out.banner


def test_ai_router_api_error_falls_back_to_rules():
    msg = "Money is tight right now"

    def error_factory(api_key: str):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API unavailable")
        return mock_client

    state = {}
    secrets = {"GEMINI_API_KEY": "fake_test_key"}
    quota = DailyQuota(limit=50)

    out = route_ai(msg, state, secrets, quota=quota, client_factory=error_factory)
    assert out.reason == "CASH"
    assert "Using simple matching" in out.banner


def test_ai_router_hallucinated_evidence_fails_gate2():
    msg = "I do not understand NAV and unit allocation"
    # AI returned evidence that is NOT in the user's message
    json_resp = json.dumps({"reason": "CONFUSION", "evidence": "something totally fabricated", "language": "English"})
    factory = _make_mock_client_factory(json_resp)

    state = {}
    secrets = {"GEMINI_API_KEY": "fake_test_key"}
    quota = DailyQuota(limit=50)

    out = route_ai(msg, state, secrets, quota=quota, client_factory=factory)
    assert out.reason == "UNCLEAR"
    assert out.evidence == ""


def test_is_ai_gate_passed(tmp_path: Path):
    # Missing file -> Gate is OFF
    missing_file = tmp_path / "nonexistent.json"
    passed, msg = is_ai_gate_passed(missing_file)
    assert passed is False
    assert "OFF" in msg

    # Accuracy below 0.75 -> OFF
    low_acc_file = tmp_path / "low_acc.json"
    low_acc_file.write_text(json.dumps({
        "item_count": 30,
        "ai_calls_ok": 30,
        "is_demo": False,
        "ai_accuracy": 0.70,
        "baseline_accuracy": 0.60,
    }))
    passed, msg = is_ai_gate_passed(low_acc_file)
    assert passed is False
    assert "OFF" in msg

    # Accuracy >= 0.75 but not higher than baseline -> OFF
    lower_than_base_file = tmp_path / "lower_than_base.json"
    lower_than_base_file.write_text(json.dumps({
        "item_count": 30,
        "ai_calls_ok": 30,
        "is_demo": False,
        "ai_accuracy": 0.80,
        "baseline_accuracy": 0.85,
    }))
    passed, msg = is_ai_gate_passed(lower_than_base_file)
    assert passed is False
    assert "OFF" in msg

    # item_count < 30 -> OFF
    small_count_file = tmp_path / "small_count.json"
    small_count_file.write_text(json.dumps({
        "item_count": 29,
        "ai_calls_ok": 29,
        "is_demo": False,
        "ai_accuracy": 0.90,
        "baseline_accuracy": 0.60,
    }))
    passed, msg = is_ai_gate_passed(small_count_file)
    assert passed is False
    assert "OFF" in msg

    # ai_calls_ok != item_count -> OFF
    failed_call_file = tmp_path / "failed_call.json"
    failed_call_file.write_text(json.dumps({
        "item_count": 30,
        "ai_calls_ok": 29,
        "is_demo": False,
        "ai_accuracy": 0.90,
        "baseline_accuracy": 0.60,
    }))
    passed, msg = is_ai_gate_passed(failed_call_file)
    assert passed is False
    assert "OFF" in msg

    # is_demo is True -> OFF
    demo_file = tmp_path / "demo.json"
    demo_file.write_text(json.dumps({
        "item_count": 30,
        "ai_calls_ok": 30,
        "is_demo": True,
        "ai_accuracy": 0.90,
        "baseline_accuracy": 0.60,
    }))
    passed, msg = is_ai_gate_passed(demo_file)
    assert passed is False
    assert "OFF" in msg

    # All criteria met -> ON
    pass_file = tmp_path / "pass.json"
    pass_file.write_text(json.dumps({
        "item_count": 30,
        "ai_calls_ok": 30,
        "is_demo": False,
        "ai_accuracy": 0.82,
        "baseline_accuracy": 0.71,
    }))
    passed, msg = is_ai_gate_passed(pass_file)
    assert passed is True
    assert "ON" in msg

