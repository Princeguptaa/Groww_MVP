"""
Golden-set evaluation script for the SIP Pause Guide (spec §6, Batch 2).

Runs:
1. AI router (with gates) on every item.
2. Rule-based baseline router on every item.

Outputs eval/results.json with:
- item_count
- ai_calls_ok
- is_demo (false only for the real run)
- ai_accuracy
- baseline_accuracy
- abstain_rate (UNCLEAR when human label was not UNCLEAR)
- per-reason precision and recall
- confusion_table
- model used
- prompt_version
- date (ISO 8601 UTC)
- gate_passed and gate_status

Strict evaluation rules:
1. Never falls back to any demo file. If eval/golden_set.csv is missing, stops with a clear message.
2. Stops if GEMINI_API_KEY is not set. Stops and fails the run if AI router falls back to the rule router for any item.
3. Records ai_calls_ok and fails if ai_calls_ok != item_count.
4. Gate is ON only if item_count >= 30 AND ai_calls_ok == item_count AND ai_accuracy >= 0.75 AND ai_accuracy > baseline_accuracy.
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
    is_demo: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Run evaluation on the dataset and save results to output_path.
    """
    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Dataset '{dataset_path}' is missing. Please provide the labelled golden set CSV."
        )

    # Stop if GEMINI_API_KEY is not set (and no mock client_factory provided)
    if not api_key and client_factory is None:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Cannot run evaluation.")

    # is_demo is false only for the real run
    if is_demo is None:
        is_demo = dataset_path.name != "golden_set.csv"

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
    ai_calls_ok = 0

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

        # Fail run if AI router fell back to rule router
        if not (ai_out.raw_result and ai_out.raw_result.ok):
            fallback_reason = ai_out.raw_result.reason if ai_out.raw_result else "unknown"
            raise RuntimeError(
                f"Evaluation failed on item {idx} ('{text[:30]}...'): "
                f"AI router fell back to rule router (reason: {fallback_reason}). "
                f"ai_calls_ok={ai_calls_ok} != item_count={len(items)}."
            )

        ai_calls_ok += 1
        ai_predictions.append(ai_out.reason)

        print(
            f"[{idx}/{len(items)}] Actual: {actual:<10} | "
            f"AI: {ai_out.reason:<10} | Rule: {rule_res.reason:<10}"
        )

        if sleep_sec > 0 and idx < len(items) and api_key and client_factory is None:
            time.sleep(sleep_sec)

    # Fail run if ai_calls_ok does not equal item count
    total = len(items)
    if ai_calls_ok != total:
        raise RuntimeError(
            f"Evaluation failed: ai_calls_ok ({ai_calls_ok}) does not equal item_count ({total})."
        )

    # Compute metrics
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

    # Gate logic: ON only if item_count >= 30 AND ai_calls_ok equals item_count AND ai_accuracy >= 0.75 AND ai_accuracy > baseline_accuracy AND is_demo is False
    gate_passed = (
        (not is_demo)
        and (total >= 30)
        and (ai_calls_ok == total)
        and (ai_accuracy >= 0.75)
        and (ai_accuracy > baseline_accuracy)
    )
    gate_status = (
        "AI routing is ON"
        if gate_passed
        else "AI routing is OFF: did not pass the quality check"
    )

    results_data: Dict[str, Any] = {
        "item_count": total,
        "ai_calls_ok": ai_calls_ok,
        "is_demo": is_demo,
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
    print(f"Total Items:       {total}")
    print(f"AI Calls OK:       {ai_calls_ok}/{total}")
    print(f"Is Demo:           {is_demo}")
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
        default=Path("eval/golden_set.csv"),
        help="Path to golden set CSV (defaults to eval/golden_set.csv)",
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
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Explicitly mark run as demo",
    )
    args = parser.parse_args()

    # Rule 1: Never fall back to demo file. If golden set CSV is missing, stop with clear message.
    dataset_path = args.dataset
    if not dataset_path.is_file():
        sys.exit(
            f"Error: Golden set file '{dataset_path}' is missing. "
            "run_eval.py does not use any demo file. Please provide the labelled golden set CSV."
        )

    # Rule 2: Stop if GEMINI_API_KEY is not set
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "Error: GEMINI_API_KEY environment variable is not set. "
            "Please set GEMINI_API_KEY before running evaluation."
        )

    try:
        run_evaluation(
            dataset_path=dataset_path,
            output_path=args.output,
            api_key=api_key,
            sleep_sec=args.wait,
            is_demo=args.demo,
        )
    except Exception as e:
        sys.exit(f"Evaluation failed: {e}")


if __name__ == "__main__":
    main()
