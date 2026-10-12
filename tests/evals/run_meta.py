import os
import sys
import json
import time
import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

# Call tracking state
class CallTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.n_llm_calls = 0
        self.n_llm_errors = 0
        self.models_used = {}

    def record_call(self, model_name: str):
        self.n_llm_calls += 1
        name = model_name or "unknown-model"
        self.models_used[name] = self.models_used.get(name, 0) + 1

    def record_error(self):
        self.n_llm_errors += 1

TRACKER = CallTracker()

def get_git_sha() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(BASE_DIR), capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

def get_dataset_metadata(dataset_path: Optional[str] = None) -> tuple[str, int]:
    path = Path(dataset_path) if dataset_path else BASE_DIR / "tests" / "evals" / "golden_dataset.json"
    try:
        with open(path, "rb") as f:
            content = f.read()
            sha = hashlib.sha256(content).hexdigest()
        data = json.loads(content.decode("utf-8"))
        count = len(data) if isinstance(data, list) else 0
        return sha, count
    except Exception:
        return "unknown", 0

def get_deepeval_version() -> str:
    try:
        import deepeval
        return getattr(deepeval, "__version__", "4.2.8")
    except Exception:
        return "4.2.8"

def ensure_api_keys(mode: str):
    """Fails immediately before doing any work if live mode is requested without API keys."""
    if mode == "live":
        groq = os.getenv("GROQ_API_KEY", "").strip()
        gemini = os.getenv("GEMINI_API_KEY", "").strip()
        mistral = os.getenv("MISTRAL_API_KEY", "").strip()
        if not (groq or gemini or mistral):
            raise RuntimeError(
                "Cannot execute live evaluation: No LLM API keys found in environment.\n"
                "Please configure at least one of GROQ_API_KEY, GEMINI_API_KEY, or MISTRAL_API_KEY in .env, "
                "or run in smoke mode using --smoke."
            )

def build_run_meta(
    mode: str,
    started_at: str,
    finished_at: str,
    wall_seconds: float,
    dataset_path: Optional[str] = None
) -> Dict[str, Any]:
    dataset_sha, dataset_n = get_dataset_metadata(dataset_path)

    meta = {
        "mode": mode,
        "started_at": started_at,
        "finished_at": finished_at,
        "wall_seconds": round(wall_seconds, 3),
        "git_sha": get_git_sha(),
        "dataset_sha256": dataset_sha,
        "dataset_n": dataset_n,
        "models_used": TRACKER.models_used.copy(),
        "n_llm_calls": TRACKER.n_llm_calls,
        "n_llm_errors": TRACKER.n_llm_errors,
        "deepeval_version": get_deepeval_version(),
        "python_version": sys.version.split()[0]
    }
    return meta

def verify_live_guards(meta: Dict[str, Any]):
    """Strict guard: in live mode, if n_llm_calls == 0 raise RuntimeError."""
    if meta.get("mode") == "live":
        if meta.get("n_llm_calls", 0) == 0:
            raise RuntimeError("Live evaluation failed guard check: no LLM calls were made.")

def enable_model_tracking(mode: str):
    """
    Configures model invocation:
    - In smoke mode: replaces get_llm across all agent modules with SmokeChatModel
    - In live mode: wraps get_llm to intercept responses and record response_metadata
    """
    TRACKER.reset()
    import app.agents.models
    import app.agents.skeptic
    import app.agents.verifier
    import app.agents.analyst
    import app.agents.editor

    orig_get_llm = app.agents.models.get_llm

    target_modules = [
        app.agents.models,
        app.agents.skeptic,
        app.agents.verifier,
        app.agents.analyst,
        app.agents.editor
    ]

    if mode == "smoke":
        from tests.evals.smoke_model import SmokeChatModel
        def smoke_get_llm(temperature: float = 0.2):
            return SmokeChatModel()

        for mod in target_modules:
            setattr(mod, "get_llm", smoke_get_llm)
    else:
        class TrackingWrapper:
            def __init__(self, inner):
                self._inner = inner

            def invoke(self, *args, **kwargs):
                try:
                    resp = self._inner.invoke(*args, **kwargs)
                    meta = getattr(resp, "response_metadata", {}) or {}
                    model_name = (
                        meta.get("model_name")
                        or meta.get("model")
                        or getattr(self._inner, "model_name", None)
                        or getattr(self._inner, "model", None)
                        or "live-model"
                    )
                    TRACKER.record_call(str(model_name))
                    return resp
                except Exception as e:
                    TRACKER.record_error()
                    raise e

            def __getattr__(self, name):
                return getattr(self._inner, name)

        def live_get_llm(temperature: float = 0.2):
            inner = orig_get_llm(temperature=temperature)
            return TrackingWrapper(inner)

        for mod in target_modules:
            setattr(mod, "get_llm", live_get_llm)

