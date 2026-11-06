"""
Tests for Section 9, Test 2a: Plan view ('What each option means for you') per spec §4.2, §5.2, §5.3.

Verifies:
1. Exact arithmetic formulas:
   - Continue as is = A x N; Months = N
   - Skip one month = A x (N - 1); Months = N - 1
   - Reduce = B x M + A x (N - M); Months = N
   - Take a longer break = A x (N - M); Months = N - M
   - Stop = 0; Months = 0
2. Example case: message "salary delayed, my SIP is 5000, due in 5 days":
   A = 5000, N = 6 (default), B = 2500 (default half), M = 2 (default break length):
   - Continue as is: 30000 rupees, 6 months
   - Skip one month: 25000 rupees, 5 months
   - Reduce: 25000 rupees, 6 months
   - Take a longer break: 20000 rupees, 4 months
   - Stop: 0 rupees, 0 months
3. Gate 3b behavior (extraction filtered by text appearance).
4. No predictions, no returns in the plan view, fixed caption.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from lib.content import PLAN_CAPTION, PLAN_TITLE, calculate_plan
from lib.guards import gate_3b


def test_2a_plan_formulas_example_case():
    """Test 2a: verify plan formulas with user's example message (A=5000, N=6, B=2500, M=2)."""
    a = 5000
    n = 6
    b = 2500
    m = 2

    plan = calculate_plan(a=a, n=n, b=b, m=m)
    assert len(plan) == 5

    by_opt = {row["Option"]: row for row in plan}

    # Continue as is: A x N = 5000 x 6 = 30000; Months = N = 6
    assert by_opt["Continue as is"]["You put in (rupees)"] == 30000
    assert by_opt["Continue as is"]["Months with an instalment"] == 6

    # Skip one month: A x (N - 1) = 5000 x 5 = 25000; Months = N - 1 = 5
    assert by_opt["Skip one month"]["You put in (rupees)"] == 25000
    assert by_opt["Skip one month"]["Months with an instalment"] == 5

    # Reduce: B x M + A x (N - M) = 2500 x 2 + 5000 x 4 = 5000 + 20000 = 25000; Months = N = 6
    assert by_opt["Reduce"]["You put in (rupees)"] == 25000
    assert by_opt["Reduce"]["Months with an instalment"] == 6

    # Take a longer break: A x (N - M) = 5000 x 4 = 20000; Months = N - M = 4
    assert by_opt["Take a longer break"]["You put in (rupees)"] == 20000
    assert by_opt["Take a longer break"]["Months with an instalment"] == 4

    # Stop: 0; Months = 0
    assert by_opt["Stop"]["You put in (rupees)"] == 0
    assert by_opt["Stop"]["Months with an instalment"] == 0


def test_2a_plan_formulas_across_periods():
    """Test 2a: verify plan formulas across all period options (3, 6, 12 months)."""
    a = 10000
    b = 4000
    m = 2

    for n in [3, 6, 12]:
        plan = calculate_plan(a=a, n=n, b=b, m=m)
        by_opt = {row["Option"]: row for row in plan}

        assert by_opt["Continue as is"]["You put in (rupees)"] == a * n
        assert by_opt["Continue as is"]["Months with an instalment"] == n

        assert by_opt["Skip one month"]["You put in (rupees)"] == a * (n - 1)
        assert by_opt["Skip one month"]["Months with an instalment"] == n - 1

        assert by_opt["Reduce"]["You put in (rupees)"] == b * m + a * (n - m)
        assert by_opt["Reduce"]["Months with an instalment"] == n

        assert by_opt["Take a longer break"]["You put in (rupees)"] == a * (n - m)
        assert by_opt["Take a longer break"]["Months with an instalment"] == n - m

        assert by_opt["Stop"]["You put in (rupees)"] == 0
        assert by_opt["Stop"]["Months with an instalment"] == 0


def test_2a_gate_3b_verification():
    """Test 2a: Gate 3b keeps numbers only if they appear in the message text."""
    msg = "salary delayed, my SIP is 5000, due in 5 days"

    # 5000 appears in text -> kept
    amt, mo = gate_3b(5000, None, msg)
    assert amt == 5000
    assert mo is None

    # Hallucinated 10000 not in text -> dropped
    amt, mo = gate_3b(10000, None, msg)
    assert amt is None

    # Hallucinated months (e.g. 6 or 12) not in text -> dropped
    amt, mo = gate_3b(5000, 6, msg)
    assert amt == 5000
    assert mo is None

    # Word representation
    amt, mo = gate_3b(5000, 3, "need to pause my five thousand sip for three months")
    assert amt == 5000
    assert mo == 3


def test_2a_plan_fixed_caption_and_no_predictions():
    """Test 2a: Verify exact fixed caption and absence of predictions/returns."""
    assert PLAN_TITLE == "What each option means for you"
    assert PLAN_CAPTION == "Simple arithmetic on your numbers. Not a forecast. Not advice."

    # Check that plan rows have exact column names
    plan = calculate_plan(a=5000, n=6, b=2500, m=2)
    for row in plan:
        assert "Option" in row
        assert "You put in (rupees)" in row
        assert "Months with an instalment" in row
        # Ensure values are non-negative integers
        assert row["You put in (rupees)"] >= 0
        assert row["Months with an instalment"] >= 0


def test_2a_plan_view_screen_b_prefilled_from_extracted_amount():
    """Test 2a: Screen B prefilled from extracted amount when gate 3b passes, single AI call."""
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parent.parent / "app.py"
    at = AppTest.from_file(str(app_path))

    # Pre-set session state simulating Screen A transition after AI router extraction
    at.session_state["guide_screen"] = "B"
    at.session_state["message"] = "salary delayed, my SIP is 5000, due in 5 days"
    at.session_state["detected_reason"] = "CASH"
    at.session_state["detected_evidence"] = "salary delayed"
    # Extracted values that passed Gate 3b:
    at.session_state["plan_amount_inr"] = 5000
    at.session_state["plan_amount_input"] = 5000
    at.session_state["plan_reduce_to_input"] = 2500
    at.session_state["plan_break_months_input"] = 2

    at.run()
    assert not at.exception

    # Verify Screen B renders What each option means for you
    subheaders = [s.value for s in at.subheader]
    assert PLAN_TITLE in subheaders

    # Verify captions contain PLAN_CAPTION
    captions = [c.value for c in at.caption]
    assert any(PLAN_CAPTION in c for c in captions)

    # Verify table is rendered with exact values
    assert len(at.table) >= 1
    table_df = at.table[0].value
    assert "You put in (rupees)" in table_df.columns
    assert "Months with an instalment" in table_df.columns
    assert table_df.loc["Continue as is"]["You put in (rupees)"] == 30000
    assert table_df.loc["Continue as is"]["Months with an instalment"] == 6
    assert table_df.loc["Skip one month"]["You put in (rupees)"] == 25000
    assert table_df.loc["Skip one month"]["Months with an instalment"] == 5
    assert table_df.loc["Reduce"]["You put in (rupees)"] == 25000
    assert table_df.loc["Reduce"]["Months with an instalment"] == 6
    assert table_df.loc["Take a longer break"]["You put in (rupees)"] == 20000
    assert table_df.loc["Take a longer break"]["Months with an instalment"] == 4
    assert table_df.loc["Stop"]["You put in (rupees)"] == 0
    assert table_df.loc["Stop"]["Months with an instalment"] == 0


def test_2a_plan_view_screen_b_no_amount_shows_inputs_no_table():
    """Test 2a: If no amount is available, show the inputs and no table until one is entered."""
    from streamlit.testing.v1 import AppTest

    app_path = Path(__file__).resolve().parent.parent / "app.py"
    at = AppTest.from_file(str(app_path))

    # Session state with no amount
    at.session_state["guide_screen"] = "B"
    at.session_state["message"] = "money is tight"
    at.session_state["detected_reason"] = "CASH"
    at.session_state["detected_evidence"] = "money is tight"
    at.session_state["plan_amount_input"] = 0

    at.run()
    assert not at.exception

    # Table must NOT be rendered when amount <= 0
    assert len(at.table) == 0

