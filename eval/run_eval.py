"""
Golden-set evaluation script for the SIP Pause Guide (spec §6, Batch 2).

Runs:
1. AI router (with gates) on every item.
2. Rule-based baseline router on every item.

Outputs eval/results.json with:
- item_count
- ai_accuracy
- baseline_accuracy
- abstain_rate (UNCLEAR when human label was not UNCLEAR)
- per-reason precision and recall
- confusion_table
- model used
- prompt_version
- date (ISO 8601 UTC)
- gate_passed and gate_status

Batch 2 requirements:
- Uses its own empty session state per item
- Uses its own large daily quota object
- Reads GEMINI_API_KEY from os.environ (not st.secrets)
- Waits about 4 seconds between calls
- Stores prompt version in results.json
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.ai_client import DailyQuota
from lib.content import REASONS
from lib.router_ai import PROMPT_VERSION, route_ai
from lib.router_rules import rule_route


def run_evaluation(
    dataset_path: Path,
    output_path: Path,
    api_key: Optional[str] = None,
    client_factory: Optional[Callable[[str], Any]] = None,
    sleep_sec: float = 4.0,
    model: str = "gemini-3.1-flash-lite",
) -> Dict[str, Any]:
    """
    Run evaluation on the dataset and save results to output_path.
    """
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    # Read items
    items: List[Dict[str, str]] = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)

    if not items:
        raise ValueError(f"No rows found in {dataset_path}")

    # Dedicated large quota for eval
    eval_quota = DailyQuota(limit=100000)

    ai_predictions: List[str] = []
    rule_predictions: List[str] = []
    ground_truth: List[str] = []

    print(f"Running evaluation on {len(items)} items from {dataset_path.name}...")

    for idx, item in enumerate(items, 1):
        text = item["text"]
        actual = item["human_reason"].strip().upper()
        ground_truth.append(actual)

        # Baseline rule router
        rule_res = rule_route(text)
        rule_predictions.append(rule_res.reason)

        # AI router with empty session state per item (Batch 2 requirement)
        item_session_state: Dict[str, Any] = {}
        ai_out = route_ai(
            text,
            state=item_session_state,
            secrets={"GEMINI_API_KEY": api_key or ""},
            quota=eval_quota,
            client_factory=client_factory,
            models=[model],
        )
        ai_predictions.append(ai_out.reason)

        print(
            f"[{idx}/{len(items)}] Actual: {actual:<10} | "
            f"AI: {ai_out.reason:<10} | Rule: {rule_res.reason:<10}"
        )

        if sleep_sec > 0 and idx < len(items) and api_key and client_factory is None:
            time.sleep(sleep_sec)

    # Compute metrics
    total = len(items)
    ai_correct = sum(1 for p, a in zip(ai_predictions, ground_truth) if p == a)
    rule_correct = sum(1 for p, a in zip(rule_predictions, ground_truth) if p == a)

    ai_accuracy = round(ai_correct / total, 4)
    baseline_accuracy = round(rule_correct / total, 4)

    # Abstain rate: predicted UNCLEAR when human label was not UNCLEAR
    abstain_count = sum(
        1 for p, a in zip(ai_predictions, ground_truth) if p == "UNCLEAR" and a != "UNCLEAR"
    )
    abstain_rate = round(abstain_count / total, 4)

    # Confusion table: actual -> {predicted: count}
    confusion_table: Dict[str, Dict[str, int]] = {
        r: {p: 0 for p in REASONS} for r in REASONS
    }
    for p, a in zip(ai_predictions, ground_truth):
        if a in confusion_table and p in confusion_table[a]:
            confusion_table[a][p] += 1

    # Per-reason precision, recall, f1
    per_reason: Dict[str, Dict[str, Any]] = {}
    for r in REASONS:
        tp = sum(1 for p, a in zip(ai_predictions, ground_truth) if p == r and a == r)
        fp = sum(1 for p, a in zip(ai_predictions, ground_truth) if p == r and a != r)
        fn = sum(1 for p, a in zip(ai_predictions, ground_truth) if p != r and a == r)

        precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        per_reason[r] = {
            "precision": precision,
            "recall": recall,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": sum(1 for a in ground_truth if a == r),
        }

    # Gate logic: AI accuracy >= 0.75 AND AI accuracy > baseline accuracy
    gate_passed = (ai_accuracy >= 0.75) and (ai_accuracy > baseline_accuracy)
    gate_status = (
        "AI routing is ON"
        if gate_passed
        else "AI routing is OFF: did not pass the quality check"
    )

    results_data: Dict[str, Any] = {
        "item_count": total,
        "ai_accuracy": ai_accuracy,
        "baseline_accuracy": baseline_accuracy,
        "abstain_rate": abstain_rate,
        "per_reason": per_reason,
        "confusion_table": confusion_table,
        "model": model,
        "prompt_version": PROMPT_VERSION,
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gate_passed": gate_passed,
        "gate_status": gate_status,
        "dataset_name": dataset_path.name,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    print(f"\nEvaluation complete!")
    print(f"AI Accuracy:       {ai_accuracy * 100:.1f}%")
    print(f"Baseline Accuracy: {baseline_accuracy * 100:.1f}%")
    print(f"Abstain Rate:      {abstain_rate * 100:.1f}%")
    print(f"Gate Status:       {gate_status}")
    print(f"Results saved to:  {output_path}")

    return results_data


def main():
    parser = argparse.ArgumentParser(description="Evaluate SIP Pause Guide routing")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to golden set CSV (defaults to eval/golden_set.csv or eval/golden_set_demo.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/results.json"),
        help="Output path for results JSON",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=4.0,
        help="Wait time in seconds between API calls (default 4.0)",
    )
    args = parser.parse_args()

    # Determine dataset path
    dataset_path = args.dataset
    if dataset_path is None:
        primary = Path("eval/golden_set.csv")
        demo = Path("eval/golden_set_demo.csv")
        dataset_path = primary if primary.is_file() else demo

    # Read API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "Note: GEMINI_API_KEY environment variable is not set. "
            "AI routing will fall back to rule router."
        )

    run_evaluation(
        dataset_path=dataset_path,
        output_path=args.output,
        api_key=api_key,
        sleep_sec=args.wait,
    )


if __name__ == "__main__":
    main()
