#!/usr/bin/env python3
"""
Inspect dataset composition, provenance, splits, and baseline accuracy.
Python 3.12, standard library only.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
GOLDEN_PATH = BASE_DIR / "tests" / "evals" / "golden_dataset.json"
GOLDEN_V2_PATH = BASE_DIR / "tests" / "evals" / "golden_dataset_v2.json"


def analyze_dataset(items: List[Dict[str, Any]], dataset_name: str) -> Dict[str, Any]:
    n_total = len(items)
    node_counts = {"skeptic": 0, "verifier": 0, "analyst": 0, "editor": 0}
    skeptic_classes: Dict[str, int] = {}
    verifier_classes: Dict[str, int] = {}
    analyst_classes: Dict[str, int] = {}
    provenance_counts: Dict[str, int] = {}
    split_counts: Dict[str, int] = {}
    legacy_count = 0
    positive_cases = 0
    positive_published = 0

    for it in items:
        gt = it.get("ground_truth", {}) or {}
        if gt.get("skeptic"):
            node_counts["skeptic"] += 1
            dec = gt["skeptic"].get("expected_decision", "UNKNOWN")
            skeptic_classes[dec] = skeptic_classes.get(dec, 0) + 1
            if dec == "KEEP":
                positive_cases += 1
                if it.get("provenance") == "pipeline_published":
                    positive_published += 1

        if gt.get("verifier"):
            node_counts["verifier"] += 1
            st = gt["verifier"].get("expected_status", "UNKNOWN")
            verifier_classes[st] = verifier_classes.get(st, 0) + 1
            if st == "VALID":
                positive_cases += 1
                if it.get("provenance") == "pipeline_published":
                    positive_published += 1

        if gt.get("analyst"):
            node_counts["analyst"] += 1
            vd = gt["analyst"].get("expected_verdict", "UNKNOWN")
            analyst_classes[vd] = analyst_classes.get(vd, 0) + 1

        if gt.get("editor"):
            node_counts["editor"] += 1

        prov = it.get("provenance")
        if not prov:
            legacy_count += 1
            provenance_counts["(none/legacy)"] = provenance_counts.get("(none/legacy)", 0) + 1
        else:
            provenance_counts[prov] = provenance_counts.get(prov, 0) + 1

        split = it.get("split")
        if split:
            split_counts[split] = split_counts.get(split, 0) + 1

    # Always-KEEP baseline accuracy for skeptic
    total_skeptic = node_counts["skeptic"]
    always_keep_acc = (skeptic_classes.get("KEEP", 0) / total_skeptic) if total_skeptic > 0 else 0.0

    pct_positive_published = (positive_published / positive_cases * 100.0) if positive_cases > 0 else 0.0

    return {
        "name": dataset_name,
        "n_total": n_total,
        "nodes": node_counts,
        "classes": {
            "skeptic": skeptic_classes,
            "verifier": verifier_classes,
            "analyst": analyst_classes
        },
        "provenance": provenance_counts,
        "splits": split_counts,
        "legacy_count": legacy_count,
        "always_keep_accuracy": always_keep_acc,
        "pct_positive_published": pct_positive_published,
        "positive_cases": positive_cases,
        "positive_published": positive_published
    }


def print_stats(stats: Dict[str, Any]):
    print("=" * 65)
    print(f"DATASET ANALYSIS: {stats['name']} (Total Cases: {stats['n_total']})")
    print("=" * 65)

    print("\n1. Node Coverage:")
    for node, count in stats["nodes"].items():
        print(f"  - {node:<12}: {count}")

    print("\n2. Decision/Class Distribution:")
    print(f"  Skeptic:  {stats['classes']['skeptic']}")
    print(f"  Verifier: {stats['classes']['verifier']}")
    print(f"  Analyst:  {stats['classes']['analyst']}")

    print("\n3. Provenance:")
    for prov, count in stats["provenance"].items():
        print(f"  - {prov:<25}: {count}")

    if stats["splits"]:
        print("\n4. Split Composition:")
        for sp, count in stats["splits"].items():
            print(f"  - {sp:<10}: {count} ({count / stats['n_total'] * 100:.1f}%)")

    print("\n5. Baseline Metrics:")
    print(f"  - Always-KEEP baseline accuracy: {stats['always_keep_accuracy'] * 100:.1f}%")

    if stats["legacy_count"] > 0:
        print(f"\n[FLAG] Legacy cases with no provenance detected: {stats['legacy_count']}/{stats['n_total']}")

    if stats["pct_positive_published"] > 40.0:
        print(f"\n[WARNING] Selection bias risk: {stats['pct_positive_published']:.1f}% of positive cases have provenance 'pipeline_published' (threshold: 40%).")


def main():
    if not GOLDEN_PATH.exists():
        print(f"Error: {GOLDEN_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
        v1_items = json.load(f)
    stats_v1 = analyze_dataset(v1_items, "golden_dataset.json (v1)")
    print_stats(stats_v1)

    if GOLDEN_V2_PATH.exists():
        print("\n")
        with open(GOLDEN_V2_PATH, "r", encoding="utf-8") as f:
            v2_items = json.load(f)
        stats_v2 = analyze_dataset(v2_items, "golden_dataset_v2.json (v2)")
        print_stats(stats_v2)


if __name__ == "__main__":
    main()
