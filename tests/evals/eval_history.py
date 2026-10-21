"""Online/offline history eval: runs rule checks across published history before and after 2026-09-04."""
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "backend"))

from app.checks import has_bold_lead, no_tldr_label, categories_unique, count_at_most_5, is_generic_fallback_text


def run_history_eval(history_path: str = "data/history.json"):
    days = json.load(open(history_path, "r", encoding="utf-8"))
    checks = {
        "bold_lead": lambda bs: all(has_bold_lead(b.get("description", "")) for b in bs),
        "no_tldr": lambda bs: all(no_tldr_label(b.get("description", "")) for b in bs),
        "unique_categories": lambda bs: categories_unique(bs),
        "at_most_5": lambda bs: count_at_most_5(bs),
        "no_generic_fallback": lambda bs: not any(is_generic_fallback_text(b.get("description", "")) or is_generic_fallback_text(b.get("why_it_matters", "")) for b in bs),
    }
    before_counts = {c: 0 for c in checks}
    after_counts = {c: 0 for c in checks}
    n_before, n_after = 0, 0

    for d in days:
        date = d.get("date", "")
        bs = d.get("briefs", [])
        is_after = date >= "2026-09-04"
        if is_after:
            n_after += 1
        else:
            n_before += 1
        for name, fn in checks.items():
            if fn(bs):
                if is_after:
                    after_counts[name] += 1
                else:
                    before_counts[name] += 1

    print(f"History Rule Checks (Before 2026-09-04: {n_before} days | From 2026-09-04 on: {n_after} days):")
    for name in checks:
        print(f"  {name:22} Before: {before_counts[name]}/{n_before} | After: {after_counts[name]}/{n_after}")
    return {"before": {**before_counts, "total": n_before}, "after": {**after_counts, "total": n_after}}

if __name__ == "__main__":
    run_history_eval()
