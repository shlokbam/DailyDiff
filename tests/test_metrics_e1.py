import pytest
from tests.evals.metrics import (
    confusion_matrix,
    tpr_tnr,
    precision_recall_f1,
    balanced_accuracy,
    wilson_interval,
    bootstrap_ci,
    cohens_kappa,
    jaccard,
    fmt_rate,
)

def test_wilson_interval_known_values():
    low1, high1 = wilson_interval(20, 25)
    assert pytest.approx(low1, abs=0.002) == 0.609
    assert pytest.approx(high1, abs=0.002) == 0.911

    low2, high2 = wilson_interval(163, 174)
    assert pytest.approx(low2, abs=0.002) == 0.890
    assert pytest.approx(high2, abs=0.002) == 0.964

def test_contingency_table_kappa_tpr_tnr():
    # Table [[70, 5], [10, 15]]
    # Rows: human Pass, human Fail
    # Cols: judge Pass, judge Fail
    table = [[70, 5], [10, 15]]

    kappa = cohens_kappa(table)
    assert pytest.approx(kappa, abs=0.002) == 0.571

    tpr, tnr = tpr_tnr(table)
    assert pytest.approx(tpr, abs=0.002) == 0.933
    assert pytest.approx(tnr, abs=0.002) == 0.600

def test_cohens_kappa_identical_label_lists():
    labels = ["KEEP", "REJECT", "KEEP", "KEEP", "REJECT"]
    assert cohens_kappa(labels, labels) == 1.0

def test_jaccard_known_values():
    s1 = {"a", "b", "c"}
    s2 = {"a", "b", "c"}
    s3 = {"x", "y", "z"}

    assert jaccard(s1, s2) == 1.0
    assert jaccard(s1, s3) == 0.0
    assert jaccard(set(), set()) == 1.0

def test_bootstrap_ci_reproducible():
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    stat_fn = lambda xs: sum(xs) / len(xs)

    ci1 = bootstrap_ci(values, stat_fn, n_boot=500, seed=42)
    ci2 = bootstrap_ci(values, stat_fn, n_boot=500, seed=42)
    assert ci1 == ci2
    assert ci1[0] < 5.5 < ci1[1]

def test_fmt_rate():
    res = fmt_rate(163, 174)
    assert res == "163/174 = 93.7% (95% CI 89.0-96.4%)"

def test_confusion_matrix_and_metrics():
    y_true = [1, 1, 0, 0, 1]
    y_pred = [1, 0, 0, 1, 1]
    cm = confusion_matrix(y_true, y_pred, positive=1)
    assert cm == {"tp": 2, "fp": 1, "fn": 1, "tn": 1}

    p, r, f1 = precision_recall_f1(y_true, y_pred, positive=1)
    assert pytest.approx(p, abs=0.01) == 2 / 3
    assert pytest.approx(r, abs=0.01) == 2 / 3
    assert pytest.approx(f1, abs=0.01) == 2 / 3

    b_acc = balanced_accuracy(y_true, y_pred, positive=1)
    assert pytest.approx(b_acc, abs=0.01) == (2/3 + 1/2) / 2
