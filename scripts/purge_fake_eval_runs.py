#!/usr/bin/env python3
"""
scripts/purge_fake_eval_runs.py

Purges unverified / fake evaluation runs from the eval_runs database table.
Refuses to run without the explicit --confirm flag.
Exports all current eval_runs rows to a timestamped backup before deleting
any row whose raw_report_json lacks meta.mode == "live".

Usage:
    python scripts/purge_fake_eval_runs.py --confirm
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path so app modules can be loaded
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.database import get_db_connection, DATABASE_URL, DB_PATH, init_db

def main():
    if "--confirm" not in sys.argv:
        print("=" * 60)
        print("ERROR: Refusing to run without --confirm flag.")
        print("This script purges all evaluation runs that lack meta.mode == 'live'.")
        print("To proceed, execute:")
        print("    python scripts/purge_fake_eval_runs.py --confirm")
        print("=" * 60)
        sys.exit(1)

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Print database target
    target = f"Postgres ({DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'configured'})" if DATABASE_URL else f"SQLite ({DB_PATH})"
    print(f"Target Database: {target}")

    # 2. Get current row count
    cursor.execute("SELECT COUNT(*) FROM eval_runs")
    total_count = cursor.fetchone()[0]
    print(f"Current eval_runs row count: {total_count}")

    if total_count == 0:
        print("eval_runs table is already empty. Nothing to purge.")
        conn.close()
        return

    # 3. Export all rows to a timestamped JSON backup
    cursor.execute("""
        SELECT id, run_type, composite_score, total_cases, pass_rate, summary_json, raw_report_json, created_at
        FROM eval_runs
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()

    backup_data = []
    ids_to_purge = []

    for r in rows:
        row_id = r[0]
        raw_json_str = r[6]
        report = {}
        try:
            report = json.loads(raw_json_str) if raw_json_str else {}
        except Exception:
            report = {}

        mode = report.get("meta", {}).get("mode")
        if mode != "live":
            ids_to_purge.append(row_id)

        backup_data.append({
            "id": r[0],
            "run_type": r[1],
            "composite_score": r[2],
            "total_cases": r[3],
            "pass_rate": r[4],
            "summary_json": r[5],
            "raw_report_json": r[6],
            "created_at": str(r[7]),
            "detected_mode": mode
        })

    backup_dir = REPO_ROOT / "scripts" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"eval_runs_backup_{ts}.json"

    with open(backup_file, "w") as f:
        json.dump(backup_data, f, indent=2)

    print(f"Exported {len(backup_data)} rows to backup: {backup_file}")

    # 4. Delete every row whose stored report lacks meta.mode == 'live'
    print(f"Rows lacking meta.mode == 'live': {len(ids_to_purge)} out of {total_count}")

    if ids_to_purge:
        if DATABASE_URL:
            cursor.execute("DELETE FROM eval_runs WHERE id = ANY(%s)", (ids_to_purge,))
        else:
            placeholders = ",".join("?" for _ in ids_to_purge)
            cursor.execute(f"DELETE FROM eval_runs WHERE id IN ({placeholders})", ids_to_purge)

        conn.commit()
        print(f"Successfully deleted {len(ids_to_purge)} rows from eval_runs.")
    else:
        print("No rows needed purging; all rows have meta.mode == 'live'.")

    cursor.execute("SELECT COUNT(*) FROM eval_runs")
    remaining_count = cursor.fetchone()[0]
    print(f"Remaining live rows in eval_runs: {remaining_count}")

    conn.close()

if __name__ == "__main__":
    main()
