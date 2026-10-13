"""
Standard library evaluation metrics for DailyDiff pipeline and harness.
Pure Python 3.12, no third-party dependencies.
"""

import math
import random
from typing import Sequence, Any, Callable, Dict, Tuple, List, Set, Union


def confusion_matrix(
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    positive: Any = True
) -> Dict[str, int]:
    """
    Computes confusion matrix counts for binary classification.
    Returns {"tp": tp, "fp": fp, "fn": fn, "tn": tn}.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: len(y_true)={len(y_true)} vs len(y_pred)={len(y_pred)}")

    tp = fp = fn = tn = 0
    for yt, yp in zip(y_true, y_pred):
        is_true = (yt == positive)
        is_pred = (yp == positive)
        if is_true and is_pred:
            tp += 1
        elif not is_true and is_pred:
            fp += 1
        elif is_true and not is_pred:
            fn += 1
        else:
            tn += 1

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def tpr_tnr(
    y_true_or_cm: Union[Sequence[Any], Dict[str, int], List[List[int]]],
    y_pred: Sequence[Any] = None,
    positive: Any = True
) -> Tuple[float, float]:
    """
    Computes True Positive Rate (Sensitivity/Recall) and True Negative Rate (Specificity).
    Can accept:
      - (y_true, y_pred, positive=...)
      - a confusion matrix dict {"tp": ..., "fp": ..., "fn": ..., "tn": ...}
      - a 2x2 contingency table [[tp, fn], [fp, tn]] or [[pass_pass, pass_fail], [fail_pass, fail_fail]]
    """
    if isinstance(y_true_or_cm, dict):
        tp = y_true_or_cm.get("tp", 0)
        fp = y_true_or_cm.get("fp", 0)
        fn = y_true_or_cm.get("fn", 0)
        tn = y_true_or_cm.get("tn", 0)
    elif isinstance(y_true_or_cm, (list, tuple)) and len(y_true_or_cm) == 2 and isinstance(y_true_or_cm[0], (list, tuple)):
        # Table format: rows are true classes [pos, neg], cols are pred classes [pos, neg]
        # row 0: [tp, fn], row 1: [fp, tn]
        tp = y_true_or_cm[0][0]
        fn = y_true_or_cm[0][1]
        fp = y_true_or_cm[1][0]
        tn = y_true_or_cm[1][1]
    else:
        cm = confusion_matrix(y_true_or_cm, y_pred, positive=positive)
        tp, fp, fn, tn = cm["tp"], cm["fp"], cm["fn"], cm["tn"]

    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    return tpr, tnr


def precision_recall_f1(
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    positive: Any = True
) -> Tuple[float, float, float]:
    """
    Computes Precision, Recall (TPR), and F1 Score.
    """
    cm = confusion_matrix(y_true, y_pred, positive=positive)
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def balanced_accuracy(
    y_true: Sequence[Any],
    y_pred: Sequence[Any],
    positive: Any = True
) -> float:
    """
    Computes balanced accuracy: (TPR + TNR) / 2.
    """
    tpr, tnr = tpr_tnr(y_true, y_pred, positive=positive)
    return (tpr + tnr) / 2.0


def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """
    Computes the Wilson score confidence interval for a binomial proportion k / n.
    Returns (low, high) as fractions in [0.0, 1.0].
    """
    if n <= 0:
        return 0.0, 0.0

    p = k / n
    z2 = z * z
    denominator = 1.0 + (z2 / n)
    center = p + (z2 / (2.0 * n))
    spread = z * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))

    low = (center - spread) / denominator
    high = (center + spread) / denominator

    low = max(0.0, min(1.0, low))
    high = max(0.0, min(1.0, high))
    return low, high


def bootstrap_ci(
    values: Sequence[Any],
    stat_fn: Callable[[List[Any]], float],
    n_boot: int = 2000,
    seed: int = 0
) -> Tuple[float, float]:
    """
    Computes 95% bootstrap confidence interval using standard percentiles.
    Deterministic when seed is provided.
    """
    if not values:
        return 0.0, 0.0

    n = len(values)
    rng = random.Random(seed)
    boot_stats = []

    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        boot_stats.append(stat_fn(sample))

    boot_stats.sort()
    low_idx = int(math.floor(0.025 * (n_boot - 1)))
    high_idx = int(math.ceil(0.975 * (n_boot - 1)))

    return boot_stats[low_idx], boot_stats[high_idx]


def cohens_kappa(
    y_true_or_table: Union[Sequence[Any], List[List[int]]],
    y_pred: Sequence[Any] = None
) -> float:
    """
    Computes Cohen's kappa coefficient of inter-rater agreement.
    Can accept two label sequences (y_true, y_pred) or a 2x2 contingency table [[n00, n01], [n10, n11]].
    """
    if y_pred is None and isinstance(y_true_or_table, (list, tuple)) and len(y_true_or_table) == 2:
        # 2x2 table format
        table = y_true_or_table
        n00, n01 = table[0][0], table[0][1]
        n10, n11 = table[1][0], table[1][1]
        total = n00 + n01 + n10 + n11
        if total == 0:
            return 1.0

        p_o = (n00 + n11) / total
        r0 = (n00 + n01) / total
        r1 = (n10 + n11) / total
        c0 = (n00 + n10) / total
        c1 = (n01 + n11) / total
        p_e = (r0 * c0) + (r1 * c1)

        if math.isclose(1.0 - p_e, 0.0):
            return 1.0
        return (p_o - p_e) / (1.0 - p_e)

    # Sequence format
    y_true = y_true_or_table
    if len(y_true) != len(y_pred):
        raise ValueError(f"Length mismatch: {len(y_true)} vs {len(y_pred)}")
    n = len(y_true)
    if n == 0:
        return 1.0

    categories = list(dict.fromkeys(list(y_true) + list(y_pred)))
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    num_cats = len(categories)

    # Build confusion matrix
    cm = [[0] * num_cats for _ in range(num_cats)]
    for yt, yp in zip(y_true, y_pred):
        cm[cat_to_idx[yt]][cat_to_idx[yp]] += 1

    p_o = sum(cm[i][i] for i in range(num_cats)) / n

    p_e = 0.0
    for i in range(num_cats):
        row_sum = sum(cm[i][j] for j in range(num_cats))
        col_sum = sum(cm[j][i] for j in range(num_cats))
        p_e += (row_sum / n) * (col_sum / n)

    if math.isclose(1.0 - p_e, 0.0):
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


def jaccard(a: Union[Set[Any], Sequence[Any]], b: Union[Set[Any], Sequence[Any]]) -> float:
    """
    Computes Jaccard similarity coefficient |a & b| / |a | b|.
    If both are empty, returns 1.0.
    """
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 1.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def fmt_rate(k: int, n: int, z: float = 1.96) -> str:
    """
    Formats a count, total, and percentage with 95% Wilson confidence interval.
    Example: '163/174 = 93.7% (95% CI 89.0-96.4%)'
    """
    if n == 0:
        return "0/0 = 0.0% (95% CI 0.0-0.0%)"

    pct = (k / n) * 100.0
    low, high = wilson_interval(k, n, z=z)
    low_pct = low * 100.0
    high_pct = high * 100.0
    return f"{k}/{n} = {pct:.1f}% (95% CI {low_pct:.1f}-{high_pct:.1f}%)"
