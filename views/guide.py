"""
Guide page — three-screen SIP pause/stop flow.

Spec §4:
Screen A: What is going on? (context strip, text box, chips, Continue button)
Screen B: What we heard, and your options (We heard card, reason block, 4 equal tiles)
Screen C: One option in detail (tapped option only, steps, link, arithmetic / calendar)
"""
from __future__ import annotations

import datetime
import streamlit as st

from lib.content import (
    CHIPS,
    CONTEXT_CAPTION,
    CONTEXT_STRIP,
    DECLINE_TEXT,
    GROWW_HELP_LINK,
    OPTION_CARDS,
    REASONS,
    REASON_BLOCKS,
    REASON_LABELS,
    REASON_PHRASES,
    SCREEN_A_CAPTION,
    TILE_SUMMARIES,
    create_ics,
)
from lib.guards import pre_check
from lib.router_ai import is_ai_gate_passed, route_ai
from lib.router_rules import rule_route


def render() -> None:
    """Render the active screen of the three-screen flow."""
    screen = st.session_state.get("guide_screen", "A")
    if screen == "B":
        _render_screen_b()
    elif screen == "C":
        _render_screen_c()
    else:
        _render_screen_a()


# ---------------------------------------------------------------------------
# Screen A: What is going on? (spec §4.1)
# ---------------------------------------------------------------------------
def _render_screen_a() -> None:
    """Render Screen A: text box, six tap chips, single primary Continue button."""
    # Context strip (spec §4.1)
    st.caption(f"**{CONTEXT_STRIP}**")
    st.caption(CONTEXT_CAPTION)

    st.title("Thinking about pausing or stopping your SIP?")

    # Tap chips that fill the box and skip typing (spec §4.1)
    st.write("Tap a reason to fill the box:")
    for i in range(0, len(CHIPS), 2):
        c1, c2 = st.columns(2)
        with c1:
            chip_0 = CHIPS[i]
            if st.button(chip_0, key=f"chip_btn_{i}", use_container_width=True):
                st.session_state["guide_text_area"] = chip_0
                st.session_state["message"] = chip_0
                st.session_state["selected_chip"] = chip_0
                st.rerun()
        with c2:
            if i + 1 < len(CHIPS):
                chip_1 = CHIPS[i + 1]
                if st.button(chip_1, key=f"chip_btn_{i+1}", use_container_width=True):
                    st.session_state["guide_text_area"] = chip_1
                    st.session_state["message"] = chip_1
                    st.session_state["selected_chip"] = chip_1
                    st.rerun()

    # Text box (max 400 characters, spec §4.1)
    current_text = st.session_state.get("guide_text_area", "")
    message = st.text_area(
        "What is going on? Write in your own words (English or Hinglish).",
        value=current_text,
        max_chars=400,
        height=120,
        key="guide_text_area",
    )

    # One clear primary button (spec §4.1)
    if st.button("Continue", type="primary", use_container_width=True, key="screen_a_continue"):
        trimmed = message.strip()
        if not trimmed:
            st.warning("Please write what is going on or tap one of the chips above.")
            return

        st.session_state["message"] = trimmed
        if trimmed in CHIPS:
            st.session_state["selected_chip"] = trimmed
        else:
            st.session_state["selected_chip"] = None

        # Pre-check gate (spec §5.3 gate 4)
        guard = pre_check(trimmed)
        if not guard.passed:
            st.session_state["pre_check_failed"] = True
            st.session_state["detected_reason"] = "UNCLEAR"
            st.session_state["detected_evidence"] = ""
            st.session_state["decline_text"] = guard.decline_text or DECLINE_TEXT
            st.session_state["ai_banner"] = None
        else:
            st.session_state["pre_check_failed"] = False
            st.session_state["decline_text"] = None
            ai_on, _ = is_ai_gate_passed()
            if ai_on:
                ai_out = route_ai(
                    trimmed,
                    st.session_state,
                    getattr(st, "secrets", {}),
                    chip=st.session_state.get("selected_chip"),
                )
                st.session_state["detected_reason"] = ai_out.reason
                st.session_state["detected_evidence"] = ai_out.evidence
                st.session_state["ai_banner"] = ai_out.banner
            else:
                res = rule_route(trimmed, chip=st.session_state.get("selected_chip"))
                st.session_state["detected_reason"] = res.reason
                st.session_state["detected_evidence"] = res.evidence
                st.session_state["ai_banner"] = None

        st.session_state["guide_screen"] = "B"
        st.rerun()

    # One small caption under the button (spec §4.1)
    st.caption(SCREEN_A_CAPTION)


# ---------------------------------------------------------------------------
# Screen B: What we heard, and your options (spec §4.2)
# ---------------------------------------------------------------------------
def _render_screen_b() -> None:
    """Render Screen B: We heard card, reason block, 4 equal tiles without steps or links."""
    # Context strip
    st.caption(f"**{CONTEXT_STRIP}**")
    st.caption(CONTEXT_CAPTION)

    st.title("Thinking about pausing or stopping your SIP?")

    if st.session_state.get("pre_check_failed"):
        st.warning(st.session_state.get("decline_text") or DECLINE_TEXT)

    if st.session_state.get("ai_banner"):
        st.info(st.session_state["ai_banner"])

    # Determine current reason and evidence
    active_reason = (
        st.session_state.get("reason_override")
        or st.session_state.get("detected_reason", "UNCLEAR")
    )
    evidence = st.session_state.get("detected_evidence", "")
    reason_phrase = REASON_PHRASES.get(active_reason, REASON_PHRASES["UNCLEAR"])

    # "We heard" card (spec §4.2)
    with st.container(border=True):
        if evidence:
            st.markdown(f"**We heard:** It sounds like {reason_phrase}. You wrote: ‘{evidence}’.")
        else:
            st.markdown(f"**We heard:** It sounds like {reason_phrase}.")

        if active_reason == "UNCLEAR" or not evidence:
            st.caption("ℹ️ Not sure, so we show every option")
        else:
            st.caption("✅ Checked: quoted from your message")

    # Expander: "Not right? Choose another reason" (spec §4.2)
    with st.expander("Not right? Choose another reason"):
        default_idx = REASONS.index(active_reason) if active_reason in REASONS else 5
        selected_override = st.radio(
            "Choose another reason:",
            options=REASONS,
            format_func=lambda r: f"{r} — {REASON_LABELS[r]}",
            index=default_idx,
            key="screen_b_reason_override_radio",
        )
        if selected_override != active_reason:
            st.session_state["reason_override"] = selected_override
            st.rerun()

    # Reason block first (spec §4.2, §7)
    st.info(REASON_BLOCKS[active_reason])

    # Heading (spec §4.2)
    st.subheader("Your options. Tap one to see how.")

    # 4 equal tiles in a 2x2 grid (stacked on a phone), in fixed order
    # Stop tile has exactly the same size and style. No steps, no links.
    if "selected_option" not in st.session_state:
        st.session_state["selected_option"] = "skip"

    for row_start in (0, 2):
        col1, col2 = st.columns(2)
        pair = [OPTION_CARDS[row_start], OPTION_CARDS[row_start + 1]]
        for col, card in zip([col1, col2], pair):
            with col:
                with st.container(border=True):
                    st.markdown(f"### {card['title']}")
                    summary_text = card.get("summary") or TILE_SUMMARIES.get(card["key"], "")
                    st.write(summary_text)
                    if st.button(
                        f"Choose: {card['title']}",
                        key=f"tile_select_{card['key']}",
                        use_container_width=True,
                    ):
                        st.session_state["selected_option"] = card["key"]
                        st.session_state["guide_screen"] = "C"
                        st.rerun()

    # One clear primary button on Screen B
    chosen_opt = st.session_state.get("selected_option", "skip")
    chosen_card = next((c for c in OPTION_CARDS if c["key"] == chosen_opt), OPTION_CARDS[0])
    if st.button(
        f"See how to: {chosen_card['title']}",
        type="primary",
        use_container_width=True,
        key="screen_b_primary_see_how",
    ):
        st.session_state["guide_screen"] = "C"
        st.rerun()

    # Start over button (secondary)
    st.markdown("---")
    if st.button("Start over", key="screen_b_start_over"):
        _reset_state()
        st.rerun()


# ---------------------------------------------------------------------------
# Screen C: One option in detail (spec §4.3)
# ---------------------------------------------------------------------------
def _render_screen_c() -> None:
    """Render Screen C: shows only the tapped option, its steps, link, arithmetic / calendar."""
    # Context strip
    st.caption(f"**{CONTEXT_STRIP}**")
    st.caption(CONTEXT_CAPTION)

    chosen_key = st.session_state.get("selected_option", "skip")
    card = next((c for c in OPTION_CARDS if c["key"] == chosen_key), OPTION_CARDS[0])

    # Header and what it does
    st.title(card["title"])
    st.markdown(f"**What it does & what stays the same:** {card['what']}")

    # How to do it on Groww (spec §4.3)
    st.markdown("### How to do it on Groww")
    if card["steps"]:
        for idx, step in enumerate(card["steps"], 1):
            st.markdown(f"{idx}. {step}")
    else:
        st.markdown("See the Groww Help page for the exact options.")

    # One official link (spec §4.3)
    st.markdown(f"[Official Groww Help Page]({card['link']})")

    # Reduce only: three number inputs and the arithmetic line (spec §4.3)
    if card["key"] == "reduce":
        st.markdown("---")
        st.markdown("#### Calculate your reduced SIP")
        col_a, col_b, col_n = st.columns(3)
        with col_a:
            amount_a = st.number_input(
                "Current monthly amount (₹)",
                min_value=100,
                value=int(st.session_state.get("reduce_amt_a", 5000)),
                step=500,
                key="reduce_amt_a",
            )
        with col_b:
            amount_b = st.number_input(
                "New monthly amount (₹)",
                min_value=100,
                value=int(st.session_state.get("reduce_amt_b", 2000)),
                step=500,
                key="reduce_amt_b",
            )
        with col_n:
            months_n = st.number_input(
                "Number of months",
                min_value=1,
                max_value=60,
                value=int(st.session_state.get("reduce_months_n", 3)),
                step=1,
                key="reduce_months_n",
            )

        total = amount_b * months_n
        st.info(
            f"If you reduce from {amount_a} to {amount_b} for {months_n} months, "
            f"you still put in {total} rupees."
        )

    # Skip and Take a longer break only: calendar reminder (spec §4.3)
    if card["has_calendar"]:
        st.markdown("---")
        st.markdown("#### Optional check-in reminder")
        today = datetime.date.today()
        default_date = today + datetime.timedelta(days=60)
        picked_date = st.date_input(
            "Pick a day to check in on your plan",
            value=default_date,
            min_value=today,
            key="screen_c_date_input",
        )
        ics_data = create_ics(picked_date)
        st.download_button(
            label="Download calendar reminder",
            data=ics_data,
            file_name="sip_plan_checkin.ics",
            mime="text/calendar",
            key="screen_c_download_calendar",
        )

    # Navigation buttons: Back to options (primary), Start over (secondary)
    st.markdown("---")
    col_back, col_reset = st.columns(2)
    with col_back:
        if st.button("Back to options", type="primary", use_container_width=True, key="screen_c_back"):
            st.session_state["guide_screen"] = "B"
            st.rerun()
    with col_reset:
        if st.button("Start over", use_container_width=True, key="screen_c_start_over"):
            _reset_state()
            st.rerun()

    # Footer link
    st.markdown(f"Need more help? [Visit official Groww Help]({GROWW_HELP_LINK})")


# ---------------------------------------------------------------------------
# State reset helper
# ---------------------------------------------------------------------------
def _reset_state() -> None:
    """Clear all session state keys related to the guide flow."""
    keys_to_clear = [
        "guide_screen",
        "message",
        "guide_text_area",
        "selected_chip",
        "detected_reason",
        "detected_evidence",
        "reason_override",
        "ai_banner",
        "pre_check_failed",
        "decline_text",
        "selected_option",
        "reduce_amt_a",
        "reduce_amt_b",
        "reduce_months_n",
        "screen_c_date_input",
        "screen_b_reason_override_radio",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    st.session_state["guide_screen"] = "A"
