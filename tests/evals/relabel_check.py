#!/usr/bin/env python3
"""
Evaluate inter-annotator agreement and Cohen's kappa between two labeling passes.
Python 3.12, standard library only.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from tests.evals.metrics import fmt_rate, cohens_kappa, confusion_matrix


def load_labeled_csv(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row.get("item_id", "").strip()
            label = row.get("human_label", "").strip().upper()
            if item_id and label:
                mapping[item_id] = label
    return mapping


def compare_labeling_passes(first_path: Path, second_path: Path):
    labels1_map = load_labeled_csv(first_path)
    labels2_map = load_labeled_csv(second_path)

    common_ids = sorted(set(labels1_map.keys()) & set(labels2_map.keys()))
    if not common_ids:
        print(f"Error: No overlapping item_ids between {first_path.name} and {second_path.name}.", file=sys.stderr)
        sys.exit(1)

    labels1 = [labels1_map[cid] for cid in common_ids]
    labels2 = [labels2_map[cid] for cid in common_ids]

    n_total = len(common_ids)
    n_agreed = sum(1 for l1, l2 in zip(labels1, labels2) if l1 == l2)

    agreement_str = fmt_rate(n_agreed, n_total)
    kappa = cohens_kappa(labels1, labels2)

    all_labels = sorted(set(labels1) | set(labels2))

    print("=" * 60)
    print("RELABEL CHECK / INTER-ANNOTATOR AGREEMENT REPORT")
    print("=" * 60)
    print(f"First File:   {first_path}")
    print(f"Second File:  {second_path}")
    print(f"Shared Items: {n_total}")
    print(f"Agreement:    {agreement_str}")
    print(f"Cohen's Kappa:{kappa:.3f}")
    print("\nConfusion Matrix (Rows: First File, Cols: Second File):")
    header = f"{'':<12}" + "".join(f"{lbl:>10}" for lbl in all_labels)
    print(header)

    for l1 in all_labels:
        row_counts = []
        for l2 in all_labels:
            c = sum(1 for a, b in zip(labels1, labels2) if a == l1 and b == l2)
            row_counts.append(c)
        row_str = f"{l1:<12}" + "".join(f"{cnt:>10}" for cnt in row_counts)
        print(row_str)
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Check agreement between two labeling passes.")
    parser.add_argument("--first", type=str, required=True, help="First labeled CSV")
    parser.add_argument("--second", type=str, required=True, help="Second labeled CSV")

    args = parser.parse_args()
    compare_labeling_passes(Path(args.first), Path(args.second))


if __name__ == "__main__":
    main()
