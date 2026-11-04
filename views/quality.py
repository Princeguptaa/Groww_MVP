"""
Quality page — Golden-set evaluation dashboard and AI governance transparency.

Spec §4.4, §6, and Batch 2 notes:
- Shows the latest golden-set evaluation from eval/results.json
- Number of items, AI accuracy, baseline accuracy, abstain rate, confusion table
- Gate status ("AI routing is ON" or "AI routing is OFF: did not pass the quality check")
- Mentions that the golden set is mostly real review text, not typed exit-moment messages
- Short text on where AI is used, what a non-AI version would miss, and limits
- No raw golden-set message text shown (counts and metrics only)
"""
from __future__ import annotations

import json
from pathlib import Path
import streamlit as st

from lib.content import REASONS, REASON_LABELS
from lib.router_ai import is_ai_gate_passed

RESULTS_FILE = Path("eval/results.json")


def render() -> None:
    """Render the Quality evaluation dashboard."""
    st.title("Quality & Evaluation")
    st.caption("Performance metrics, evaluation gate status, and AI governance transparency.")

    # -----------------------------------------------------------------------
    # Evaluation gate status
    # -----------------------------------------------------------------------
    gate_passed, gate_message = is_ai_gate_passed(RESULTS_FILE)

    if gate_passed:
        st.success(f"**Gate Status:** {gate_message}")
    else:
        st.warning(f"**Gate Status:** {gate_message}")

    st.markdown(
        "> **Evaluation Gate Criteria (Spec §6):** AI routing is activated only when AI accuracy "
        "is at least **75%** AND strictly outperforms the rule-based baseline. Otherwise, "
        "the tool safely routes all requests using the rule-based router."
    )

    # -----------------------------------------------------------------------
    # Results data loading
    # -----------------------------------------------------------------------
    if not RESULTS_FILE.is_file():
        st.info(
            "No evaluation results found yet. Run `python eval/run_eval.py` to evaluate the golden set."
        )
        _render_ai_context_section()
        return

    try:
        data = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        st.error(f"Error reading evaluation results: {e}")
        _render_ai_context_section()
        return

    item_count = data.get("item_count", 0)
    ai_acc = data.get("ai_accuracy", 0.0)
    base_acc = data.get("baseline_accuracy", 0.0)
    abstain_rate = data.get("abstain_rate", 0.0)
    model = data.get("model", "gemini-3.1-flash-lite")
    prompt_version = data.get("prompt_version", "v1")
    eval_date = data.get("date", "Unknown")

    # -----------------------------------------------------------------------
    # Top-line metrics
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Latest Evaluation Metrics")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Golden Set Items", f"{item_count}")
    with col2:
        st.metric("AI Accuracy", f"{ai_acc * 100:.1f}%")
    with col3:
        st.metric("Baseline Accuracy", f"{base_acc * 100:.1f}%")
    with col4:
        st.metric("Abstain Rate", f"{abstain_rate * 100:.1f}%")

    st.caption(
        f"**Model:** `{model}` | **Prompt Version:** `{prompt_version}` | "
        f"**Evaluated (UTC):** {eval_date[:19] if len(eval_date) >= 19 else eval_date}"
    )

    # -----------------------------------------------------------------------
    # Dataset nature disclaimer (Batch 2 requirement)
    # -----------------------------------------------------------------------
    st.info(
        "**Note on Dataset:** The golden set used for evaluation is mostly real user review text "
        "gathered from public feedback, not typed exit-moment messages. In live usage, "
        "users may type shorter or more specific phrases at the moment of pausing or stopping."
    )

    # -----------------------------------------------------------------------
    # Confusion table
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Confusion Matrix (Actual vs Predicted)")
    st.caption("Rows: Human-labelled Actual Reason | Columns: AI Predicted Reason")

    confusion = data.get("confusion_table", {})
    if confusion:
        header_cols = ["Actual \\ Predicted"] + REASONS
        table_rows = []
        for actual in REASONS:
            row_data = [actual]
            for pred in REASONS:
                cnt = confusion.get(actual, {}).get(pred, 0)
                row_data.append(str(cnt))
            table_rows.append(row_data)

        # Render as markdown table
        md_table = "| " + " | ".join(header_cols) + " |\n"
        md_table += "| " + " | ".join(["---"] * len(header_cols)) + " |\n"
        for row in table_rows:
            md_table += "| " + " | ".join(row) + " |\n"
        st.markdown(md_table)

    # -----------------------------------------------------------------------
    # Per-reason precision & recall
    # -----------------------------------------------------------------------
    per_reason = data.get("per_reason", {})
    if per_reason:
        st.divider()
        st.subheader("Per-Reason Performance")
        pr_header = ["Reason", "Description", "Precision", "Recall", "Support"]
        pr_rows = []
        for r in REASONS:
            m = per_reason.get(r, {})
            prec = f"{m.get('precision', 0.0) * 100:.1f}%"
            rec = f"{m.get('recall', 0.0) * 100:.1f}%"
            supp = str(m.get("support", 0))
            desc = REASON_LABELS.get(r, "")
            pr_rows.append([r, desc, prec, rec, supp])

        md_pr = "| " + " | ".join(pr_header) + " |\n"
        md_pr += "| " + " | ".join(["---"] * len(pr_header)) + " |\n"
        for row in pr_rows:
            md_pr += "| " + " | ".join(row) + " |\n"
        st.markdown(md_pr)

    _render_ai_context_section()


def _render_ai_context_section() -> None:
    """Render explanatory context on AI role, advantages, and limits (spec §4.4)."""
    st.divider()
    st.subheader("AI Role, Capabilities & Limitations")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Where AI is Used")
        st.markdown(
            "- **Intent Classification:** Understands the user's typed message in English or Hinglish "
            "and maps it to one of six defined reasons.\n"
            "- **Evidence Quoting:** Extracts the verbatim shortest phrase from the user's message "
            "to show back what was understood.\n"
            "- **Defensive Gates:** Outputs are verified by code gates (JSON schema, verbatim check, "
            "word count)."
        )

        st.markdown("#### What a Non-AI Version Misses")
        st.markdown(
            "- **Conversational Nuance:** Users express financial stress in varied, informal Hinglish "
            "(e.g., 'paisa nahi bacha', 'job issue') that static keyword lists often miss.\n"
            "- **Spelling & Typos:** Real messages contain typos and informal abbreviations.\n"
            "- **Contextual Separation:** Distinguishes between wanting to switch funds vs experiencing "
            "a temporary bank debit failure."
        )

    with col_b:
        st.markdown("#### Strict Boundaries & Limitations")
        st.markdown(
            "- **No Advice or Recommendations:** The AI never recommends, ranks, or suggests funds, "
            "stocks, or strategies. It only classifies reasons.\n"
            "- **Fixed Content:** All options, consequences, Groww steps, and links are 100% human-written "
            "and verified against official Groww Help.\n"
            "- **No Data Retention:** User messages are treated strictly as data, never stored or logged.\n"
            "- **Deterministic Fallback:** If the API key is missing, limits are reached, or quality drops, "
            "the system instantly switches to rule-based routing."
        )

    st.markdown("---")
    st.caption(
        "Privacy Notice: In accordance with Hard Rule 4 and Spec §6, raw golden-set messages "
        "and user inputs are never exposed on this page. Only aggregated metric counts are shown."
    )
