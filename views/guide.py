"""
Guide page — three-step SIP pause/stop flow.

Spec §4:
Step 1: Tell us what is going on (text, chips, optional numbers)
Step 2: What we understood (reason phrase + quoted evidence, badge, selector)
Step 3: Your options (reason block, 4 cards in fixed order, arithmetic, steps, .ics)
"""
from __future__ import annotations

import datetime
import streamlit as st

from lib.content import (
    AI_DISCLOSURE,
    CHIPS,
    DECLINE_TEXT,
    GROWW_HELP_LINK,
    OPTION_CARDS,
    PRIVACY_NOTICE,
    REASONS,
    REASON_BLOCKS,
    REASON_LABELS,
    REASON_PHRASES,
    create_ics,
)
from lib.guards import pre_check
from lib.router_ai import is_ai_gate_passed, route_ai
from lib.router_rules import rule_route


def render() -> None:
    """Render the three-step Guide flow."""
    st.title("Thinking about pausing or stopping your SIP?")
    st.caption("A small prototype to explore lighter options before making a final decision.")

    # -----------------------------------------------------------------------
    # Step 1: Tell us what is going on (spec §4.1)
    # -----------------------------------------------------------------------
    st.subheader("1. Tell us what is going on")

    # Tap chips that fill the box and skip typing
    st.write("Tap a reason to fill the box:")
    chip_cols = st.columns(2)
    for idx, chip_text in enumerate(CHIPS):
        with chip_cols[idx % 2]:
            if st.button(chip_text, key=f"chip_{idx}", use_container_width=True):
                st.session_state["message"] = chip_text
                st.session_state["selected_chip"] = chip_text
                st.session_state["submitted"] = True
                st.session_state["show_my_steps_active"] = False
                st.rerun()

    # Text box (max 400 characters)
    current_msg = st.session_state.get("message", "")
    message = st.text_area(
        "What is going on? Write in your own words (English or Hinglish).",
        value=current_msg,
        max_chars=400,
        height=100,
        key="guide_text_area",
    )

    # Disclosures under text box (Note 3 and spec §3 hard rule 4)
    st.caption(AI_DISCLOSURE)
    st.caption(PRIVACY_NOTICE)

    # Optional numbers
    col_amt, col_mo = st.columns(2)
    with col_amt:
        amount = st.number_input(
            "Monthly SIP amount (₹, optional)",
            min_value=0,
            value=int(st.session_state.get("amount", 0)),
            step=500,
            key="guide_amount_input",
        )
    with col_mo:
        months = st.number_input(
            "Months since you started (optional)",
            min_value=0,
            value=int(st.session_state.get("months", 0)),
            step=1,
            key="guide_months_input",
        )

    # Continue button
    if st.button("Continue", type="primary", use_container_width=True, key="guide_continue_btn"):
        trimmed = message.strip()
        if not trimmed:
            st.warning("Please write what is going on or tap one of the chips above.")
            return
        st.session_state["message"] = trimmed
        st.session_state["amount"] = amount
        st.session_state["months"] = months
        st.session_state["submitted"] = True
        st.session_state["show_my_steps_active"] = False
        if trimmed in CHIPS:
            st.session_state["selected_chip"] = trimmed
        else:
            st.session_state["selected_chip"] = None
        st.rerun()

    if not st.session_state.get("submitted", False):
        return

    active_message = st.session_state.get("message", "")
    active_chip = st.session_state.get("selected_chip")

    # -----------------------------------------------------------------------
    # Gate 4 Pre-check (spec §5.3 gate 4)
    # -----------------------------------------------------------------------
    guard = pre_check(active_message)
    if not guard.passed:
        st.divider()
        st.warning(guard.decline_text or DECLINE_TEXT)
        st.subheader("Your options")
        _render_option_cards(active_reason="UNCLEAR", user_amount=st.session_state.get("amount", 0))
        _render_start_over()
        return

    # -----------------------------------------------------------------------
    # Routing (Phase 3: AI router with evaluation gate check & rule fallback)
    # -----------------------------------------------------------------------
    ai_on, _ = is_ai_gate_passed()
    if ai_on:
        ai_out = route_ai(
            active_message,
            st.session_state,
            getattr(st, "secrets", {}),
            chip=active_chip,
        )
        detected_reason = ai_out.reason
        detected_evidence = ai_out.evidence
        if ai_out.banner:
            st.info(ai_out.banner)
    else:
        routing_result = rule_route(active_message, chip=active_chip)
        detected_reason = routing_result.reason
        detected_evidence = routing_result.evidence

    # -----------------------------------------------------------------------
    # Step 2: What we understood (spec §4.2, Note 2)
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("2. What we understood")

    reason_phrase = REASON_PHRASES.get(detected_reason, "your situation is not clear to us")
    if detected_evidence:
        understood_text = f"It sounds like {reason_phrase}. You wrote: \u2018{detected_evidence}\u2019."
    else:
        understood_text = f"It sounds like {reason_phrase}."

    st.markdown(f"**{understood_text}**")

    # Badge (spec §4.2)
    if detected_reason == "UNCLEAR" or not detected_evidence:
        st.info("Not sure, so we show every option")
    else:
        st.success("Checked: quoted from your message")

    # Selector override (spec §4.2)
    default_idx = REASONS.index(detected_reason) if detected_reason in REASONS else 5
    selected_reason = st.selectbox(
        "Not right? Choose another reason",
        options=REASONS,
        index=default_idx,
        format_func=lambda r: f"{r} — {REASON_LABELS[r]}",
        key="reason_override_select",
    )
    active_reason = selected_reason

    # -----------------------------------------------------------------------
    # Step 3: Your options (spec §4.3)
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("3. Your options")

    # Reason block first (spec §4.3, §7)
    st.info(REASON_BLOCKS[active_reason])

    # Option cards
    _render_option_cards(active_reason=active_reason, user_amount=st.session_state.get("amount", 0))

    # Action selector & show steps
    _render_action_section()

    _render_start_over()


def _render_option_cards(active_reason: str, user_amount: int) -> None:
    """Render all 4 option cards in fixed order with equal size and prominence."""
    for card in OPTION_CARDS:
        with st.container(border=True):
            st.markdown(f"### {card['title']}")
            st.markdown(f"**What it does & what stays the same:** {card['what']}")
            if card["steps"]:
                st.markdown("**How to do it on Groww:**")
                for step in card["steps"]:
                    st.markdown(f"- {step}")
            else:
                st.markdown("See the Groww Help page for the exact options.")
            st.markdown(f"[See Groww Help page]({card['link']})")

            # Arithmetic for Reduce card if amount given (spec §4.3)
            if card["key"] == "reduce" and user_amount > 0:
                st.markdown("---")
                st.markdown("**Example reduction calculation:**")
                calc_col1, calc_col2 = st.columns(2)
                with calc_col1:
                    b_amount = st.number_input(
                        "Lower monthly amount (₹)",
                        min_value=1,
                        max_value=max(1, user_amount),
                        value=max(1, user_amount // 2),
                        step=500,
                        key="reduce_b_val",
                    )
                with calc_col2:
                    n_months = st.number_input(
                        "For how many months",
                        min_value=1,
                        max_value=60,
                        value=3,
                        step=1,
                        key="reduce_n_val",
                    )
                total_invested = b_amount * n_months
                st.markdown(
                    f"If you reduce from {user_amount} to {b_amount} for "
                    f"{n_months} months, you still put in {total_invested} rupees."
                )


def _render_action_section() -> None:
    """Render the 'Choose what to do' radio and 'Show my steps' action."""
    st.divider()
    st.subheader("Choose what to do")
    action_titles = [c["title"] for c in OPTION_CARDS]
    chosen_title = st.radio(
        "Select an option to see your steps:",
        options=action_titles,
        index=0,
        key="chosen_action_radio",
    )

    if st.button("Show my steps", type="primary", key="show_steps_btn"):
        st.session_state["show_my_steps_active"] = True

    if st.session_state.get("show_my_steps_active", False):
        chosen_card = next(c for c in OPTION_CARDS if c["title"] == chosen_title)
        with st.container(border=True):
            st.markdown(f"### Steps for: {chosen_card['title']}")
            st.markdown(f"**Summary:** {chosen_card['what']}")
            if chosen_card["steps"]:
                st.markdown("**Groww Steps:**")
                for idx, step in enumerate(chosen_card["steps"], 1):
                    st.markdown(f"{idx}. {step}")
            else:
                st.markdown("See the Groww Help page for the exact options.")
            st.markdown(f"[Official Groww Help Page]({chosen_card['link']})")

            # Check-in calendar for Skip or Take a longer break (spec §4.3)
            if chosen_card["has_calendar"]:
                st.markdown("---")
                st.markdown("#### Optional check-in reminder")
                today = datetime.date.today()
                default_date = today + datetime.timedelta(days=60)
                picked_date = st.date_input(
                    "Pick a day to check in on your plan",
                    value=default_date,
                    min_value=today,
                    key="checkin_date_input",
                )
                ics_data = create_ics(picked_date)
                st.download_button(
                    label="Download calendar reminder",
                    data=ics_data,
                    file_name="sip_plan_checkin.ics",
                    mime="text/calendar",
                    key="download_calendar_btn",
                )

    st.markdown("---")
    st.markdown(f"Need more help? [Visit official Groww Help]({GROWW_HELP_LINK})")


def _render_start_over() -> None:
    """Option to start over and reset the guide."""
    st.markdown("---")
    if st.button("Start over", key="guide_start_over"):
        for key in [
            "message",
            "amount",
            "months",
            "submitted",
            "selected_chip",
            "show_my_steps_active",
        ]:
            st.session_state.pop(key, None)
        st.rerun()
