import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

FORBIDDEN_STRINGS = [
    "FAST_EVAL",
    "falling back to benchmark ground truth",
    "seed_baseline",
]

def test_no_forbidden_simulation_patterns():
    """
    Ensures no simulation, ground-truth fallback, or baseline seeding patterns exist
    in backend, tests, or scripts.
    """
    target_dirs = [
        ROOT_DIR / "backend",
        ROOT_DIR / "tests",
        ROOT_DIR / "scripts",
    ]

    this_file = Path(__file__).resolve()

    violations = []

    for d in target_dirs:
        if not d.exists():
            continue
        for path in d.rglob("*"):
            if path.is_file() and path != this_file:
                # Skip virtual environments, git, pycache
                if any(part in path.parts for part in [".venv", "venv", "__pycache__", ".git", ".cache"]):
                    continue
                # Only inspect code / text files
                if path.suffix in [".py", ".sh", ".json", ".js", ".jsx", ".ts", ".tsx", ".md", ".yml", ".yaml"]:
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")
                        for s in FORBIDDEN_STRINGS:
                            if s in content:
                                violations.append(f"{path.relative_to(ROOT_DIR)} contains forbidden string: '{s}'")
                    except Exception as e:
                        violations.append(f"Failed to read {path}: {e}")

    assert not violations, f"Forbidden evaluation simulation patterns found:\n" + "\n".join(violations)

def test_no_fake_json_artifacts():
    """
    Ensures fake seeded eval_results.json files are not present.
    """
    forbidden_files = [
        ROOT_DIR / "tests" / "evals" / "eval_results.json",
        ROOT_DIR / "frontend" / "public" / "eval_results.json",
        ROOT_DIR / "tests" / "evals" / "seed_baseline_results.py",
    ]
    for p in forbidden_files:
        assert not p.exists(), f"Forbidden fake artifact exists: {p.relative_to(ROOT_DIR)}"
