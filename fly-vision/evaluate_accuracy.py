"""
Ground Truth Evaluation Script

Compares vision pipeline estimates against ground truth JSON files.
Produces pass/fail report based on accuracy thresholds.

Usage:
    python evaluate_accuracy.py [estimate_file.json] [--verbose]
"""

import json
import os
from pathlib import Path
from typing import List, Dict


# Thresholds
PASS_THRESHOLD = 0.15   # 80% must be within ±15%
WARN_THRESHOLD = 0.25   # 95% must be within ±25%


def load_ground_truth(test_piles_dir: str = "test_piles") -> Dict[str, dict]:
    """Load all ground truth JSON files."""
    ground_truths = {}
    for f in Path(test_piles_dir).glob("*.json"):
        if f.name.startswith("_"):
            continue  # Skip schema
        with open(f) as fp:
            data = json.load(fp)
            ground_truths[data["pile_id"]] = data
    return ground_truths


def evaluate_estimate(estimate_yd3: float, ground_truth: dict) -> dict:
    """Evaluate a single estimate against ground truth."""
    gt = ground_truth["ground_truth"]
    likely = gt["likely_yd3"]
    min_yd3 = gt["min_yd3"]
    max_yd3 = gt["max_yd3"]
    
    # Error relative to likely
    error_pct = abs(estimate_yd3 - likely) / likely
    
    # In range?
    in_range = min_yd3 <= estimate_yd3 <= max_yd3
    
    # Status
    if error_pct <= PASS_THRESHOLD:
        status = "PASS"
    elif error_pct <= WARN_THRESHOLD:
        status = "WARN"
    else:
        status = "FAIL"
    
    return {
        "pile_id": ground_truth["pile_id"],
        "estimate": estimate_yd3,
        "likely": likely,
        "min": min_yd3,
        "max": max_yd3,
        "error_pct": round(error_pct * 100, 1),
        "in_range": in_range,
        "status": status
    }


def run_evaluation(estimates: Dict[str, float], ground_truths: Dict[str, dict]) -> dict:
    """Run full evaluation across all test piles."""
    results = []
    
    for pile_id, gt in ground_truths.items():
        if pile_id not in estimates:
            results.append({
                "pile_id": pile_id,
                "status": "MISSING",
                "error_pct": None
            })
            continue
        
        result = evaluate_estimate(estimates[pile_id], gt)
        results.append(result)
    
    # Summary
    total = len([r for r in results if r["status"] != "MISSING"])
    passed = len([r for r in results if r["status"] == "PASS"])
    warned = len([r for r in results if r["status"] == "WARN"])
    failed = len([r for r in results if r["status"] == "FAIL"])
    
    pass_rate = passed / total if total > 0 else 0
    pass_warn_rate = (passed + warned) / total if total > 0 else 0
    
    return {
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "pass_rate": round(pass_rate * 100, 1),
            "pass_warn_rate": round(pass_warn_rate * 100, 1),
            "threshold_met": pass_rate >= 0.80 and pass_warn_rate >= 0.95
        }
    }


def print_report(evaluation: dict):
    """Print human-readable evaluation report."""
    print("\n" + "=" * 60)
    print("GROUND TRUTH EVALUATION REPORT")
    print("=" * 60)
    
    for r in evaluation["results"]:
        if r["status"] == "MISSING":
            print(f"  ⏭️  {r['pile_id']}: MISSING (no estimate provided)")
            continue
        
        icon = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}[r["status"]]
        in_range = "✓" if r["in_range"] else "✗"
        print(f"  {icon} {r['pile_id']}: {r['estimate']} yd³ "
              f"(expect {r['likely']}, err {r['error_pct']}%, range {in_range})")
    
    s = evaluation["summary"]
    print("-" * 60)
    print(f"  Pass rate: {s['pass_rate']}% ({s['passed']}/{s['total']}) - target 80%")
    print(f"  Pass+Warn: {s['pass_warn_rate']}% ({s['passed']+s['warned']}/{s['total']}) - target 95%")
    print(f"  OVERALL: {'✅ PASSED' if s['threshold_met'] else '❌ FAILED'}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    import sys
    
    # Load ground truth
    script_dir = Path(__file__).parent
    gt = load_ground_truth(script_dir / "test_piles")
    print(f"Loaded {len(gt)} ground truth files")
    
    # Example usage with mock estimates
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            estimates = json.load(f)
    else:
        # Demo mode with sample estimates
        estimates = {
            "TEST1": 3.5,
            "JUNKPILE1": 5.2,
            "JUNKPILE2": 6.0,
            "JUNKPILE3": 7.8
        }
        print("Using demo estimates (pass real JSON file as argument)")
    
    # Evaluate
    evaluation = run_evaluation(estimates, gt)
    print_report(evaluation)
