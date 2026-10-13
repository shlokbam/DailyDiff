#!/usr/bin/env python3
"""
Import human labels and update evaluation datasets.
Python 3.12, standard library only.
"""

import argparse
import csv
import json
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "tests" / "evals" / ".cache"
DEFAULT_V2_DATASET = BASE_DIR / "tests" / "evals" / "golden_dataset_v2.json"
DEFAULT_HISTORY_FILE = BASE_DIR / "data" / "history.json"
DEFAULT_FAITHFULNESS_OUT = BASE_DIR / "tests" / "evals" / "human_labels_faithfulness.csv"


def normalize_url(url: str) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    if u.endswith("/"):
        u = u[:-1]
    return u


def get_all_published_urls(history_path: Path) -> Set[str]:
    """Returns set of all normalized URLs present in history.json."""
    if not history_path.exists():
        return set()
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return set()

    published = set()
    for entry in history:
        for b in entry.get("briefs", []):
            u = normalize_url(b.get("source_url", ""))
            if u:
                published.add(u)
    return published


def find_latest_labeling_key(task: str, custom_key_file: Optional[str] = None) -> Dict[str, Any]:
    if custom_key_file:
        kp = Path(custom_key_file)
        if not kp.exists():
            raise FileNotFoundError(f"Labeling key file not found: {kp}")
        with open(kp, "r", encoding="utf-8") as f:
            return json.load(f)

    if not CACHE_DIR.exists():
        raise FileNotFoundError(f"Cache dir {CACHE_DIR} does not exist to look for labeling keys.")

    key_files = sorted(CACHE_DIR.glob(f"labeling_key_{task}_*.json"))
    if not key_files:
        # Fallback to any labeling_key
        key_files = sorted(CACHE_DIR.glob("labeling_key_*.json"))
    if not key_files:
        raise FileNotFoundError(f"No labeling key found in {CACHE_DIR} for task '{task}'.")

    latest_key_file = key_files[-1]
    with open(latest_key_file, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_split(item_id: str) -> str:
    val = int(hashlib.sha256(item_id.encode("utf-8")).hexdigest(), 16) % 10
    return "dev" if val < 7 else "test"


def import_skeptic_labels(
    csv_path: Path,
    labeler: str,
    allow_blank: bool,
    key_file: Optional[str],
    v2_dataset_path: Path,
    history_path: Path
) -> int:
    labeling_key = find_latest_labeling_key("skeptic", key_file)
    published_urls = get_all_published_urls(history_path)

    v2_cases: List[Dict[str, Any]] = []
    if v2_dataset_path.exists():
        try:
            with open(v2_dataset_path, "r", encoding="utf-8") as f:
                v2_cases = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to read existing v2 dataset at {v2_dataset_path}: {e}")

    existing_ids = {c["id"] for c in v2_cases}
    allowed_labels = {"KEEP", "REJECT"}

    new_cases_count = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row.get("item_id", "").strip()
            label = row.get("human_label", "").strip().upper()
            notes = row.get("notes", "").strip()

            if not label:
                if allow_blank:
                    continue
                else:
                    raise ValueError(f"Blank label for item_id '{item_id}' without --allow-blank")

            if label not in allowed_labels:
                raise ValueError(f"Invalid label '{label}' for item_id '{item_id}'. Must be one of {allowed_labels}")

            if item_id in existing_ids:
                # Never modify old cases
                continue

            key_info = labeling_key.get(item_id)
            if not key_info:
                # Fallback to row info
                url = row.get("url", "").strip()
                title = row.get("title", "").strip()
                source = row.get("source", "Unknown")
                desc = row.get("description", "")
            else:
                url = key_info.get("url", row.get("url", "")).strip()
                title = key_info.get("title", row.get("title", "")).strip()
                source = key_info.get("source", row.get("source", "Unknown"))
                desc = key_info.get("description", row.get("description", ""))

            norm_url = normalize_url(url)
            provenance = "pipeline_published" if norm_url in published_urls else "pipeline_not_selected"
            split = calculate_split(item_id)

            case = {
                "id": item_id,
                "input_signal": {
                    "title": title,
                    "url": url,
                    "source": source,
                    "raw_description": desc
                },
                "ground_truth": {
                    "skeptic": {
                        "expected_decision": label,
                        "notes": notes
                    }
                },
                "provenance": provenance,
                "label_source": "human_blind",
                "labeler": labeler,
                "split": split,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            v2_cases.append(case)
            existing_ids.add(item_id)
            new_cases_count += 1

    v2_dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with open(v2_dataset_path, "w", encoding="utf-8") as f:
        json.dump(v2_cases, f, indent=2)

    return new_cases_count


def import_faithfulness_labels(
    csv_path: Path,
    labeler: str,
    allow_blank: bool,
    out_csv: Path
) -> int:
    allowed_labels = {"PASS", "FAIL"}
    rows_to_write = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row.get("item_id", "").strip()
            label = row.get("human_label", "").strip().upper()
            title = row.get("brief_title", "").strip()
            notes = row.get("notes", "").strip()

            if not label:
                if allow_blank:
                    continue
                else:
                    raise ValueError(f"Blank label for item_id '{item_id}' without --allow-blank")

            if label not in allowed_labels:
                raise ValueError(f"Invalid label '{label}' for item_id '{item_id}'. Must be one of {allowed_labels}")

            split = calculate_split(item_id)
            rows_to_write.append({
                "item_id": item_id,
                "brief_title": title,
                "human_label": label,
                "labeler": labeler,
                "split": split,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "notes": notes
            })

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    file_exists = out_csv.exists()

    with open(out_csv, "a" if file_exists else "w", newline="", encoding="utf-8") as f:
        fieldnames = ["item_id", "brief_title", "human_label", "labeler", "split", "created_at", "notes"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in rows_to_write:
            writer.writerow(r)

    return len(rows_to_write)


def main():
    parser = argparse.ArgumentParser(description="Import human labels.")
    parser.add_argument("--csv", type=str, required=True, help="Path to labeled CSV file")
    parser.add_argument("--task", choices=["skeptic", "faithfulness"], required=True, help="Evaluation task")
    parser.add_argument("--labeler", type=str, required=True, help="Name of labeler")
    parser.add_argument("--allow-blank", action="store_true", help="Allow blank labels (skip rows)")
    parser.add_argument("--key-file", type=str, help="Specific labeling key JSON file to use")
    parser.add_argument("--v2-dataset", type=str, default=str(DEFAULT_V2_DATASET), help="Path to golden_dataset_v2.json")
    parser.add_argument("--history-file", type=str, default=str(DEFAULT_HISTORY_FILE), help="Path to data/history.json")
    parser.add_argument("--out-faithfulness", type=str, default=str(DEFAULT_FAITHFULNESS_OUT), help="Output CSV for faithfulness")

    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.task == "skeptic":
            count = import_skeptic_labels(
                csv_path=csv_path,
                labeler=args.labeler,
                allow_blank=args.allow_blank,
                key_file=args.key_file,
                v2_dataset_path=Path(args.v2_dataset),
                history_path=Path(args.history_file)
            )
            print(f"Successfully imported {count} new cases to {args.v2_dataset}")
        else:
            count = import_faithfulness_labels(
                csv_path=csv_path,
                labeler=args.labeler,
                allow_blank=args.allow_blank,
                out_csv=Path(args.out_faithfulness)
            )
            print(f"Successfully imported {count} labels to {args.out_faithfulness}")
    except Exception as e:
        print(f"Import failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
