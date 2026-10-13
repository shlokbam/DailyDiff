# DailyDiff Evaluation Layer

This directory contains the offline evaluation infrastructure, labeling workflows, dataset tooling, and baseline verifiers for the DailyDiff multi-agent intelligence pipeline. All evaluation metrics and harness tools in this directory run offline without live LLM API calls and rely solely on real datasets and blind human annotations.

---

## Directory Overview

- **`metrics.py`**  
  Standard-library-only statistical evaluation routines:
  - Binary confusion matrix, TPR/TNR, precision, recall, and balanced accuracy.
  - Wilson score confidence intervals for binomial proportions.
  - Empirical bootstrap confidence intervals with deterministic RNG seeds.
  - Cohen's kappa coefficient for inter-annotator agreement.
  - Jaccard set similarity and formatted rate reporting (`fmt_rate`).

- **`golden_dataset.json`**  
  The v1 baseline benchmark dataset across pipeline nodes (Skeptic, Verifier, Analyst, Editor). Kept strictly immutable.

- **`golden_dataset_v2.json`**  
  Dataset v2 expanding benchmark coverage. Each entry specifies `id`, `input_signal`, `ground_truth`, `provenance`, `label_source`, `labeler`, `split`, and `created_at`.

- **`dataset_stats.py`**  
  CLI diagnostic tool inspecting dataset composition:
  - Node coverage and class balance across nodes.
  - Provenance distribution (`pipeline_published`, `pipeline_not_selected`, `synthetic_perturbation`, `injection`, `legacy`).
  - Baseline rate checks and alerts if published positives exceed policy thresholds.

- **`export_labeling_sheet.py`**  
  Generates blind annotation sheets (`.csv`) for human review from raw run snapshots.
  - Completely scrubs pipeline decisions and decision text.
  - Deduplicates items against historical publications prior to run dates.
  - Saves the unblinded mapping key securely to `tests/evals/.cache/labeling_key_*.json` (gitignored).

- **`import_labels.py`**  
  Ingests reviewed labeling sheets:
  - Validates labels against allowed task schemas (`KEEP`/`REJECT` for Skeptic, `PASS`/`FAIL` for Faithfulness).
  - Matches candidate URLs against `data/history.json` to assign provenance.
  - Assigns deterministic splits via item ID hashing and appends new cases without modifying existing entries.

- **`relabel_check.py`**  
  Compares two independent annotation passes on identical item IDs to report percent agreement, Cohen's kappa, and contingency tables.

- **`make_adversarial.py`**  
  Deterministic generator producing synthetic perturbations and prompt injection benchmarks (`adversarial_cases.json`) from verified-good cases.
  - *Note:* Synthetic perturbations are easier to detect than real errors, serving as foundational regression guards.

- **`eval_published_history.py`**  
  Offline checks runner evaluating historical publication history (`data/history.json`) against production quality checks across distinct temporal windows. Outputs `tests/evals/baselines/history_checks.json`.

---

## Blind Human Labeling Flow

To prevent confirmation bias, labelers must never see the pipeline's decisions during annotation.

```
data/runs/*.json
       │
       ▼
[export_labeling_sheet.py]
       │
       ├──► tests/evals/.cache/labeling_key_*.json (private unblinded mapping)
       └──► labeling_sheet.csv (blind: item details only, blank human_label)
                   │
                   ▼
           [Human Annotation] (KEEP / REJECT)
                   │
                   ├──► [relabel_check.py] ◄── [Second Annotator CSV]
                   │    (Agreement & Cohen's Kappa)
                   ▼
           [import_labels.py]
                   │
                   ▼
        golden_dataset_v2.json
```

1. **Export Blind Sheet**
   ```bash
   python tests/evals/export_labeling_sheet.py --task skeptic --n 120 --stratify-by-source --out labeling_sheet.csv
   ```
2. **Annotate Blindly**
   Open `labeling_sheet.csv` and fill the `human_label` column (`KEEP` or `REJECT`) without viewing model verdicts.
3. **Check Inter-Rater Reliability (Optional)**
   ```bash
   python tests/evals/relabel_check.py --first annotator_a.csv --second annotator_b.csv
   ```
4. **Import Verified Annotations**
   ```bash
   python tests/evals/import_labels.py --csv labeling_sheet.csv --task skeptic --labeler <name>
   ```

---

## Split Partitioning

Dataset splits (`dev` vs `test`) are assigned deterministically using a SHA-256 hash of each `item_id`:

- The hexadecimal SHA-256 digest of `item_id` is converted to an integer and evaluated modulo 10:
  - If `(hash % 10) < 7`: Assigned to `dev`.
  - If `(hash % 10) >= 7`: Assigned to `test`.
- This ensures:
  1. Complete reproducibility across all machines and environments.
  2. Stability: Adding or removing other cases never shifts existing item split assignments.
  3. No data leakage between development tuning and benchmark testing.
