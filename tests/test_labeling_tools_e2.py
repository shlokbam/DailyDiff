import csv
import json
import pytest
from pathlib import Path
from unittest.mock import patch

from tests.evals.export_labeling_sheet import export_skeptic_sheet, export_faithfulness_sheet
from tests.evals.import_labels import import_skeptic_labels, calculate_split
from tests.evals.relabel_check import compare_labeling_passes, load_labeled_csv
from tests.evals.metrics import cohens_kappa

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "runs"
HISTORY_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "history.json"


def test_exported_skeptic_sheet_contains_no_decision_column_or_text(tmp_path):
    out_csv = tmp_path / "skeptic_sheet.csv"
    count, key_path = export_skeptic_sheet(
        runs_dir=FIXTURES_DIR,
        history_path=HISTORY_FIXTURE,
        n=10,
        stratify=False,
        seed=42,
        include_degraded=False,
        exclude_ids=set(),
        out_path=out_csv
    )

    assert count > 0
    assert out_csv.exists()

    with open(out_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    # 1. Decision column must not exist
    assert "pipeline_decision" not in header
    assert "decision" not in header
    assert "outcome" not in header
    assert header == ["item_id", "title", "url", "source", "description", "human_label", "notes"]

    # 2. Pipeline decision text (KEEP / REJECT) must not appear in any row
    for r in rows:
        human_label = r[5]
        assert human_label == "", "human_label must start empty for blind review"
        row_text = " ".join(r)
        assert "KEEP" not in row_text
        assert "REJECT" not in row_text

    # 3. Labeling key file exists and has decisions
    assert key_path.exists()
    with open(key_path, "r", encoding="utf-8") as f:
        key_data = json.load(f)
    assert len(key_data) == count
    for k, v in key_data.items():
        assert "pipeline_decision" in v


def test_same_seed_gives_same_order(tmp_path):
    out1 = tmp_path / "out1.csv"
    out2 = tmp_path / "out2.csv"
    out3 = tmp_path / "out3.csv"

    export_skeptic_sheet(FIXTURES_DIR, HISTORY_FIXTURE, n=10, stratify=False, seed=42, include_degraded=False, exclude_ids=set(), out_path=out1)
    export_skeptic_sheet(FIXTURES_DIR, HISTORY_FIXTURE, n=10, stratify=False, seed=42, include_degraded=False, exclude_ids=set(), out_path=out2)
    export_skeptic_sheet(FIXTURES_DIR, HISTORY_FIXTURE, n=10, stratify=False, seed=999, include_degraded=False, exclude_ids=set(), out_path=out3)

    content1 = out1.read_text(encoding="utf-8")
    content2 = out2.read_text(encoding="utf-8")
    content3 = out3.read_text(encoding="utf-8")

    assert content1 == content2, "Same seed must produce identical file content and order"


def test_import_with_invalid_label_fails(tmp_path):
    csv_file = tmp_path / "invalid_labels.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "title", "url", "source", "description", "human_label", "notes"])
        writer.writerow(["skep_12345", "FastDB", "https://github.com/fast/fastdb", "GitHub", "Desc", "MAYBE", ""])

    # Key file
    key_file = tmp_path / "key.json"
    with open(key_file, "w", encoding="utf-8") as f:
        json.dump({"skep_12345": {"url": "https://github.com/fast/fastdb", "title": "FastDB"}}, f)

    v2_dataset = tmp_path / "golden_v2.json"

    with pytest.raises(ValueError) as exc:
        import_skeptic_labels(
            csv_path=csv_file,
            labeler="Tester",
            allow_blank=False,
            key_file=str(key_file),
            v2_dataset_path=v2_dataset,
            history_path=HISTORY_FIXTURE
        )
    assert "Invalid label 'MAYBE'" in str(exc.value)


def test_split_is_stable_across_runs():
    item_ids = [f"item_{i}" for i in range(25)]
    splits_run1 = [calculate_split(iid) for iid in item_ids]
    splits_run2 = [calculate_split(iid) for iid in item_ids]

    assert splits_run1 == splits_run2
    assert "dev" in splits_run1
    assert "test" in splits_run1
    # Check approximately 70% dev
    dev_ratio = splits_run1.count("dev") / len(splits_run1)
    assert 0.5 <= dev_ratio <= 0.9


def test_relabel_check_on_identical_files_gives_kappa_1(tmp_path, capsys):
    f1 = tmp_path / "pass1.csv"
    f2 = tmp_path / "pass2.csv"

    rows = [
        ["skep_1", "FastDB", "https://github.com/a", "GitHub", "", "KEEP", ""],
        ["skep_2", "Crypto", "https://github.com/b", "Reddit", "", "REJECT", ""],
        ["skep_3", "Tool", "https://github.com/c", "Hacker News", "", "KEEP", ""],
    ]

    for p in [f1, f2]:
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["item_id", "title", "url", "source", "description", "human_label", "notes"])
            writer.writerows(rows)

    compare_labeling_passes(f1, f2)
    captured = capsys.readouterr().out

    assert "Cohen's Kappa:1.000" in captured
    assert "Agreement:    3/3 = 100.0%" in captured
