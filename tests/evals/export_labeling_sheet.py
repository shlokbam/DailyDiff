#!/usr/bin/env python3
"""
Export blind labeling sheets for Skeptic and Faithfulness evaluation.
Python 3.12, standard library only.
"""

import argparse
import csv
import json
import random
import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "tests" / "evals" / ".cache"
MAX_EVIDENCE_CHARS = 3000


def normalize_url(url: str) -> str:
    if not url:
        return ""
    u = url.strip().lower()
    if u.endswith("/"):
        u = u[:-1]
    return u


def get_previously_published_urls(history_path: Path, before_date: str) -> Set[str]:
    """Returns set of normalized URLs published in history before `before_date`."""
    if not history_path.exists():
        return set()
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return set()

    published = set()
    for entry in history:
        entry_date = entry.get("date", "")
        if entry_date and entry_date < before_date:
            for b in entry.get("briefs", []):
                u = normalize_url(b.get("source_url", ""))
                if u:
                    published.add(u)
    return published


def export_skeptic_sheet(
    runs_dir: Path,
    history_path: Path,
    n: int,
    stratify: bool,
    seed: int,
    include_degraded: bool,
    exclude_ids: Set[str],
    out_path: Path
) -> Tuple[int, Path]:
    run_files = sorted(runs_dir.glob("*.json"))
    items_by_url: Dict[str, Dict[str, Any]] = {}

    for rf in run_files:
        if not include_degraded and ".degraded." in rf.name:
            continue
        try:
            with open(rf, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except Exception:
            continue

        run_date = snapshot.get("date", rf.stem.split(".")[0])
        prior_published = get_previously_published_urls(history_path, run_date)

        skeptic_kept_set = {normalize_url(u) for u in snapshot.get("skeptic_kept", [])}
        decisions_list = snapshot.get("decisions", {}).get("skeptic", [])
        decisions_map = {normalize_url(d.get("url", "")): d.get("outcome") for d in decisions_list}

        for s in snapshot.get("raw_signals", []):
            url = s.get("url", "").strip()
            norm_url = normalize_url(url)
            if not norm_url:
                continue

            # Exclude if mechanically deduplicated by history
            if norm_url in prior_published:
                continue

            if norm_url not in items_by_url:
                pipeline_outcome = decisions_map.get(norm_url)
                if not pipeline_outcome:
                    pipeline_outcome = "KEEP" if norm_url in skeptic_kept_set else "REJECT"

                # Generate deterministic item ID
                raw_id_str = f"skep_{run_date}_{norm_url}"
                item_id = f"skep_{hashlib.sha256(raw_id_str.encode('utf-8')).hexdigest()[:12]}"

                if item_id in exclude_ids:
                    continue

                items_by_url[norm_url] = {
                    "item_id": item_id,
                    "title": s.get("title", ""),
                    "url": url,
                    "source": s.get("source", "Unknown"),
                    "description": s.get("description", ""),
                    "run_date": run_date,
                    "pipeline_decision": pipeline_outcome
                }

    candidate_items = list(items_by_url.values())

    # Sampling
    rng = random.Random(seed)
    if stratify and candidate_items:
        by_source: Dict[str, List[Dict[str, Any]]] = {}
        for it in candidate_items:
            by_source.setdefault(it["source"], []).append(it)
        for s in by_source:
            rng.shuffle(by_source[s])

        selected = []
        sources = sorted(by_source.keys())
        idx = 0
        while len(selected) < n and any(by_source.values()):
            src = sources[idx % len(sources)]
            if by_source[src]:
                selected.append(by_source[src].pop(0))
            idx += 1
        rng.shuffle(selected)
    else:
        rng.shuffle(candidate_items)
        selected = candidate_items[:n]

    # Write blind CSV (pipeline_decision must NOT appear in CSV)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "title", "url", "source", "description", "human_label", "notes"])
        for it in selected:
            writer.writerow([it["item_id"], it["title"], it["url"], it["source"], it["description"], "", ""])

    # Write labeling key mapping
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    key_path = CACHE_DIR / f"labeling_key_skeptic_{ts}.json"
    key_mapping = {
        it["item_id"]: {
            "title": it["title"],
            "url": it["url"],
            "source": it["source"],
            "description": it["description"],
            "run_date": it["run_date"],
            "pipeline_decision": it["pipeline_decision"]
        }
        for it in selected
    }
    with open(key_path, "w", encoding="utf-8") as f:
        json.dump(key_mapping, f, indent=2)

    return len(selected), key_path


def export_faithfulness_sheet(
    runs_dir: Path,
    n: int,
    seed: int,
    include_degraded: bool,
    exclude_ids: Set[str],
    out_path: Path
) -> Tuple[int, Path]:
    run_files = sorted(runs_dir.glob("*.json"))
    items_by_title: Dict[str, Dict[str, Any]] = {}

    for rf in run_files:
        if not include_degraded and ".degraded." in rf.name:
            continue
        try:
            with open(rf, "r", encoding="utf-8") as f:
                snapshot = json.load(f)
        except Exception:
            continue

        run_date = snapshot.get("date", rf.stem.split(".")[0])
        candidates = snapshot.get("candidates", [])
        evidence_by_url = {
            normalize_url(c.get("url", "")): (c.get("evidence") or "")[:MAX_EVIDENCE_CHARS]
            for c in candidates if c.get("url")
        }

        for b in snapshot.get("final_briefs", []):
            url = b.get("source_url", "")
            title = b.get("title", "")
            norm_url = normalize_url(url)
            evidence = evidence_by_url.get(norm_url, "")

            brief_text = f"{b.get('description', '')}\n\nWhy It Matters: {b.get('why_it_matters', '')}".strip()
            raw_id_str = f"faith_{run_date}_{title}_{url}"
            item_id = f"faith_{hashlib.sha256(raw_id_str.encode('utf-8')).hexdigest()[:12]}"

            if item_id in exclude_ids:
                continue

            if title not in items_by_title:
                items_by_title[title] = {
                    "item_id": item_id,
                    "brief_title": title,
                    "brief_text": brief_text,
                    "evidence": evidence,
                    "source_url": url,
                    "run_date": run_date
                }

    candidate_items = list(items_by_title.values())
    rng = random.Random(seed)
    rng.shuffle(candidate_items)
    selected = candidate_items[:n]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "brief_title", "brief_text", "evidence", "human_label", "notes"])
        for it in selected:
            writer.writerow([it["item_id"], it["brief_title"], it["brief_text"], it["evidence"], "", ""])

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    key_path = CACHE_DIR / f"labeling_key_faithfulness_{ts}.json"
    key_mapping = {
        it["item_id"]: {
            "brief_title": it["brief_title"],
            "brief_text": it["brief_text"],
            "evidence": it["evidence"],
            "source_url": it["source_url"],
            "run_date": it["run_date"]
        }
        for it in selected
    }
    with open(key_path, "w", encoding="utf-8") as f:
        json.dump(key_mapping, f, indent=2)

    return len(selected), key_path


def main():
    parser = argparse.ArgumentParser(description="Export blind labeling sheet.")
    parser.add_argument("--task", choices=["skeptic", "faithfulness"], required=True, help="Task to label")
    parser.add_argument("--n", type=int, default=120, help="Number of items to export")
    parser.add_argument("--stratify-by-source", action="store_true", help="Stratify signals by source (skeptic)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--out", type=str, required=True, help="Output CSV path")
    parser.add_argument("--runs-dir", type=str, default=str(BASE_DIR / "data" / "runs"), help="Runs directory")
    parser.add_argument("--history-file", type=str, default=str(BASE_DIR / "data" / "history.json"), help="History JSON file")
    parser.add_argument("--include-degraded", action="store_true", help="Include degraded runs")
    parser.add_argument("--exclude-ids-file", type=str, help="File of item IDs to exclude")

    args = parser.parse_args()

    exclude_ids: Set[str] = set()
    if args.exclude_ids_file:
        p = Path(args.exclude_ids_file)
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    exclude_ids.add(line.split(",")[0].strip())

    runs_dir = Path(args.runs_dir)
    history_path = Path(args.history_file)
    out_path = Path(args.out)

    if args.task == "skeptic":
        count, key_path = export_skeptic_sheet(
            runs_dir=runs_dir,
            history_path=history_path,
            n=args.n,
            stratify=args.stratify_by_source,
            seed=args.seed,
            include_degraded=args.include_degraded,
            exclude_ids=exclude_ids,
            out_path=out_path
        )
    else:
        count, key_path = export_faithfulness_sheet(
            runs_dir=runs_dir,
            n=args.n,
            seed=args.seed,
            include_degraded=args.include_degraded,
            exclude_ids=exclude_ids,
            out_path=out_path
        )

    print(f"Exported {count} items for '{args.task}' to {out_path}")
    print(f"Saved labeling key to {key_path}")


if __name__ == "__main__":
    main()
