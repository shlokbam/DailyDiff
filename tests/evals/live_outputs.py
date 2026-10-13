import os
import json
import hashlib
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.agents.skeptic import deduplicate_and_filter_node
from app.agents.verifier import verifier_node
from app.agents.analyst import analyst_node
from app.agents.editor import editor_node
from app.run_health import health
from tests.evals.run_meta import get_git_sha

logger = logging.getLogger("DailyDiff.eval.live_outputs")
CACHE_DIR = BASE_DIR / "tests" / "evals" / ".cache"

def get_dataset_hash(dataset_path: Path) -> str:
    with open(dataset_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_agents_and_checks_hash() -> str:
    h = hashlib.sha256()
    agents_dir = BASE_DIR / "backend" / "app" / "agents"
    files = sorted(agents_dir.glob("*.py"))
    checks_file = BASE_DIR / "backend" / "app" / "checks.py"
    if checks_file.exists():
        files.append(checks_file)
    for p in files:
        if p.is_file():
            h.update(p.name.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()

def get_configured_models() -> List[str]:
    try:
        from app.config import PRIMARY_MODEL_GROQ, FALLBACK_MODEL_GEMINI, FALLBACK_MODEL_MISTRAL
        models = [PRIMARY_MODEL_GROQ, FALLBACK_MODEL_GEMINI, FALLBACK_MODEL_MISTRAL]
    except Exception:
        models = ["llama-3.3-70b-versatile", "gemini-3.8-flash", "open-mixtral-8x22b"]
    if os.getenv("SMOKE_MODE") == "1" or "--smoke" in sys.argv:
        models.insert(0, "fake-smoke-model")
    return sorted(list(set(models)))

def get_cache_metadata(dataset_path: Path) -> Dict[str, Any]:
    return {
        "dataset_sha256": get_dataset_hash(dataset_path),
        "git_sha": get_git_sha(),
        "code_hash": get_agents_and_checks_hash(),
        "models": get_configured_models(),
    }

def get_cache_file_path(node_name: str, meta: Dict[str, Any]) -> Path:
    models_hash = hashlib.sha256("_".join(meta["models"]).encode("utf-8")).hexdigest()[:8]
    cache_key = f"{meta['dataset_sha256'][:12]}_{meta['git_sha'][:8]}_{meta['code_hash'][:12]}_{models_hash}_{node_name}.json"
    return CACHE_DIR / cache_key

def get_or_generate_live_outputs(node_name: str, dataset_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Executes real pipeline nodes against golden_dataset.json and caches real outputs.
    Subsequent calls load from cache only if metadata matches.
    Never caches outputs if any test case has status ERROR.
    """
    ds_path = Path(dataset_path) if dataset_path else BASE_DIR / "tests" / "evals" / "golden_dataset.json"
    meta = get_cache_metadata(ds_path)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = get_cache_file_path(node_name, meta)

    force_refresh = os.getenv("EVAL_REFRESH") == "1"

    if not force_refresh and cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                cached = json.load(f)
            if isinstance(cached, dict) and cached.get("metadata") == meta:
                outputs = cached.get("outputs", [])
                if not any(o.get("status") == "ERROR" for o in outputs):
                    logger.info(f"Loading cached live outputs for {node_name} from {cache_file}")
                    return outputs
            logger.warning(f"Cache metadata mismatch or corrupted for {node_name}; re-generating.")
        except Exception as err:
            logger.warning(f"Failed to read cache file {cache_file}: {err}; re-generating.")

    with open(ds_path, "r") as f:
        dataset = json.load(f)

    logger.info(f"Generating live outputs for node: {node_name} (dataset hash: {meta['dataset_sha256'][:8]})...")

    outputs: List[Dict[str, Any]] = []

    if node_name == "skeptic":
        test_cases = [item for item in dataset if item.get("ground_truth", {}).get("skeptic")]
        raw_signals = []
        for c in test_cases:
            sig = c["input_signal"].copy()
            sig["description"] = sig.get("raw_description", sig.get("description", ""))
            sig["eval_id"] = c["id"]
            if c.get("archetype") != "negative_duplicate_release":
                orig_url = sig.get("url", "")
                sig["url"] = f"{orig_url}?eval_bench=1" if orig_url else ""
            raw_signals.append(sig)

        passed_ids = set()
        error_cases: Dict[str, str] = {}
        chunk_size = 8

        for i in range(0, len(raw_signals), chunk_size):
            chunk = raw_signals[i:i + chunk_size]
            prev_fallbacks_len = len(health.fallbacks)
            try:
                result = deduplicate_and_filter_node({"raw_signals": chunk})
                if len(health.fallbacks) > prev_fallbacks_len:
                    recent = health.fallbacks[prev_fallbacks_len:]
                    reason = recent[-1].get("reason", "Internal fallback used")
                    logger.warning(f"Skeptic chunk used internal fallback: {reason}")
                    for c in chunk:
                        error_cases[c["eval_id"]] = f"ERROR (fallback_used): {reason}"
                    continue

                for cand in result.get("candidates", []):
                    eid = cand.get("eval_id")
                    if eid:
                        passed_ids.add(eid)
                    else:
                        for tc in test_cases:
                            if tc["input_signal"]["title"] == cand.get("title"):
                                passed_ids.add(tc["id"])
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Skeptic chunk execution error: {err_msg}")
                for c in chunk:
                    error_cases[c["eval_id"]] = err_msg

        for c in test_cases:
            cid = c["id"]
            if cid in error_cases:
                outputs.append({
                    "id": cid,
                    "title": c["input_signal"]["title"],
                    "status": "ERROR",
                    "error": error_cases[cid],
                    "actual_decision": None,
                    "raw_output": None
                })
            else:
                is_kept = cid in passed_ids
                outputs.append({
                    "id": cid,
                    "title": c["input_signal"]["title"],
                    "status": "EVALUATED",
                    "actual_decision": "KEEP" if is_kept else "REJECT",
                    "raw_output": f"Decision: {'KEEP' if is_kept else 'REJECT'}"
                })

    elif node_name == "verifier":
        test_cases = [item for item in dataset if item.get("ground_truth", {}).get("verifier")]
        candidates = []
        for c in test_cases:
            candidates.append({
                "eval_id": c["id"],
                "title": c["input_signal"]["title"],
                "description": c["input_signal"].get("raw_description", ""),
                "detailed_content": c["input_signal"].get("scraped_docs", ""),
                "source": c["input_signal"].get("source", ""),
                "url": c["input_signal"].get("url", "")
            })

        vetted_ids = set()
        error_cases: Dict[str, str] = {}
        chunk_size = 5

        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]
            prev_fallbacks_len = len(health.fallbacks)
            try:
                result = verifier_node({"researched_candidates": chunk})
                if len(health.fallbacks) > prev_fallbacks_len:
                    recent = health.fallbacks[prev_fallbacks_len:]
                    reason = recent[-1].get("reason", "Internal fallback used")
                    logger.warning(f"Verifier chunk used internal fallback: {reason}")
                    for c in chunk:
                        error_cases[c["eval_id"]] = f"ERROR (fallback_used): {reason}"
                    continue

                for v in result.get("vetted_candidates", []):
                    eid = v.get("eval_id")
                    if eid:
                        vetted_ids.add(eid)
                    else:
                        for tc in test_cases:
                            if tc["input_signal"]["title"] == v.get("title"):
                                vetted_ids.add(tc["id"])
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Verifier chunk execution error: {err_msg}")
                for c in chunk:
                    error_cases[c["eval_id"]] = err_msg

        for c in test_cases:
            cid = c["id"]
            if cid in error_cases:
                outputs.append({
                    "id": cid,
                    "title": c["input_signal"]["title"],
                    "status": "ERROR",
                    "error": error_cases[cid],
                    "actual_status": None,
                    "raw_output": None
                })
            else:
                is_valid = cid in vetted_ids
                status = "VALID" if is_valid else "INVALID"
                outputs.append({
                    "id": cid,
                    "title": c["input_signal"]["title"],
                    "status": "EVALUATED",
                    "actual_status": status,
                    "raw_output": f"Verification Status: {status}"
                })

    elif node_name == "analyst":
        test_cases = [item for item in dataset if item.get("ground_truth", {}).get("analyst")]
        candidates = []
        for c in test_cases:
            candidates.append({
                "eval_id": c["id"],
                "title": c["input_signal"]["title"],
                "description": c["input_signal"].get("raw_description", ""),
                "detailed_content": c["input_signal"].get("scraped_docs", ""),
                "source": c["input_signal"].get("source", ""),
                "url": c["input_signal"].get("url", "")
            })

        analyzed = []
        error_cases: Dict[str, str] = {}
        chunk_size = 6

        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]
            prev_fallbacks_len = len(health.fallbacks)
            try:
                result = analyst_node({"vetted_candidates": chunk})
                if len(health.fallbacks) > prev_fallbacks_len:
                    recent = health.fallbacks[prev_fallbacks_len:]
                    reason = recent[-1].get("reason", "Internal fallback used")
                    logger.warning(f"Analyst chunk used internal fallback: {reason}")
                    for c in chunk:
                        error_cases[c["eval_id"]] = f"ERROR (fallback_used): {reason}"
                    continue

                analyzed.extend(result.get("vetted_candidates", []))
            except Exception as e:
                err_msg = str(e)
                logger.error(f"Analyst chunk execution error: {err_msg}")
                for c in chunk:
                    error_cases[c["eval_id"]] = err_msg

        analyzed_map = {}
        for a in analyzed:
            eid = a.get("eval_id")
            if eid:
                analyzed_map[eid] = a
            else:
                for tc in test_cases:
                    if tc["input_signal"]["title"] == a.get("title"):
                        analyzed_map[tc["id"]] = a

        for c in test_cases:
            cid = c["id"]
            if cid in error_cases:
                outputs.append({
                    "id": cid,
                    "title": c["input_signal"]["title"],
                    "status": "ERROR",
                    "error": error_cases[cid],
                    "raw_output": None
                })
            else:
                item = analyzed_map.get(cid)
                if item:
                    verdict = item.get("verdict", "")
                    why = item.get("why_it_matters", "")
                    who = item.get("who_cares", "")
                    raw = f"Verdict: {verdict}\nWhy It Matters: {why}\nWho Cares: {who}"
                    outputs.append({
                        "id": cid,
                        "title": c["input_signal"]["title"],
                        "status": "EVALUATED",
                        "raw_output": raw
                    })
                else:
                    outputs.append({
                        "id": cid,
                        "title": c["input_signal"]["title"],
                        "status": "ERROR",
                        "error": "Item dropped or missing from analyst response",
                        "raw_output": None
                    })

    elif node_name == "editor":
        test_cases = [item for item in dataset if item.get("ground_truth", {}).get("editor")]
        candidates = []
        for c in test_cases:
            candidates.append({
                "eval_id": c["id"],
                "title": c["input_signal"]["title"],
                "description": c["input_signal"].get("raw_description", ""),
                "why_it_matters": c["ground_truth"]["analyst"]["practical_takeaway_rubric"] if c.get("ground_truth", {}).get("analyst") else "Notable developer update.",
                "who_cares": ", ".join(c["ground_truth"]["analyst"]["expected_audience_keywords"]) if c.get("ground_truth", {}).get("analyst") else "Developers",
                "verdict": c["ground_truth"]["analyst"]["expected_verdict"] if c.get("ground_truth", {}).get("analyst") else "WATCH",
                "confidence": 90,
                "source": c["input_signal"].get("source", "GitHub"),
                "url": c["input_signal"].get("url", "")
            })

        final_briefs = []
        error_msg = None
        prev_fallbacks_len = len(health.fallbacks)

        try:
            result = editor_node({"vetted_candidates": candidates})
            if len(health.fallbacks) > prev_fallbacks_len:
                recent = health.fallbacks[prev_fallbacks_len:]
                reason = recent[-1].get("reason", "Internal fallback used")
                error_msg = f"ERROR (fallback_used): {reason}"
                logger.warning(f"Editor used internal fallback: {reason}")
            else:
                final_briefs = result.get("final_briefs", [])
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Editor execution error: {error_msg}")

        if error_msg:
            for idx, c in enumerate(candidates):
                outputs.append({
                    "id": f"brief_{idx+1}",
                    "title": c.get("title", ""),
                    "category": None,
                    "status": "ERROR",
                    "error": error_msg,
                    "raw_output": None
                })
        else:
            for idx, b in enumerate(final_briefs):
                raw = (
                    f"**{b.get('title', '')}**\n\n"
                    f"{b.get('description', '')}\n\n"
                    f"Category: {b.get('category', '')}\n"
                    f"Why it matters: {b.get('why_it_matters', '')}"
                )
                outputs.append({
                    "id": f"brief_{idx+1}",
                    "title": b.get("title", ""),
                    "category": b.get("category", ""),
                    "status": "EVALUATED",
                    "raw_output": raw
                })
    else:
        raise ValueError(f"Unknown node_name: {node_name}")

    has_errors = any(o.get("status") == "ERROR" for o in outputs)
    if not has_errors:
        with open(cache_file, "w") as f:
            json.dump({"metadata": meta, "outputs": outputs}, f, indent=2)
        logger.info(f"Cached {len(outputs)} live outputs to {cache_file}")
    else:
        n_err = sum(1 for o in outputs if o.get("status") == "ERROR")
        logger.warning(f"Refusing to write cache file {cache_file} because {n_err} ERROR cases exist.")

    return outputs
