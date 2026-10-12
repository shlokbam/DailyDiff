import os
import time
from typing import Dict, Any, List, Optional

class RunHealth:
    """
    Singleton runtime health tracker for DailyDiff pipeline executions.
    Tracks fallback events, LLM calls/errors, candidate stage counts,
    evidence sources, timings, and time budget compliance.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.fallbacks: List[Dict[str, str]] = []
        self.llm_calls_count = 0
        self.llm_errors_count = 0
        self.models_used: Dict[str, int] = {}
        self.node_llm_calls: Dict[str, int] = {}
        self.node_llm_errors: Dict[str, int] = {}
        self.counts: Dict[str, int] = {
            "raw_signals": 0,
            "after_dedup": 0,
            "skeptic_passed": 0,
            "researched": 0,
            "verified": 0,
            "analyzed": 0,
            "final": 0,
        }
        self.source_counts: Dict[str, int] = {}
        self.source_yield: Dict[str, float] = {}
        self.content_sources: Dict[str, str] = {}
        self.warnings: List[str] = []
        self._timers: Dict[str, float] = {}
        self.durations: Dict[str, float] = {}
        self.start_time: float = time.time()

    def mark_fallback(self, node: str, reason: str):
        self.fallbacks.append({"node": node, "reason": reason})

    @property
    def has_fallbacks(self) -> bool:
        return len(self.fallbacks) > 0

    def record_llm_call(self, node: str, response: Any = None, error: Any = None):
        self.llm_calls_count += 1
        self.node_llm_calls[node] = self.node_llm_calls.get(node, 0) + 1

        if error is not None:
            self.llm_errors_count += 1
            self.node_llm_errors[node] = self.node_llm_errors.get(node, 0) + 1

        model_name = "unknown-model"
        if response is not None:
            meta = getattr(response, "response_metadata", {}) or {}
            model_name = (
                meta.get("model_name")
                or meta.get("model")
                or getattr(response, "model_name", None)
                or getattr(response, "model", None)
                or "live-model"
            )
        self.models_used[str(model_name)] = self.models_used.get(str(model_name), 0) + 1

    def set_count(self, stage: str, n: int):
        self.counts[stage] = int(n)

    def set_source_count(self, source: str, n: int):
        self.source_counts[source] = int(n)

    def set_source_yield(self, source: str, pct: float):
        self.source_yield[source] = round(float(pct), 2)

    def set_content_source(self, candidate_url: str, kind: str):
        valid_kinds = {"readme", "api_fallback", "web_page", "description_only", "empty"}
        if kind not in valid_kinds:
            kind = "empty"
        self.content_sources[candidate_url] = kind

    def add_warning(self, text: str):
        self.warnings.append(text)

    def start_timer(self, node: str):
        self._timers[node] = time.time()

    def stop_timer(self, node: str):
        start = self._timers.pop(node, None)
        if start is not None:
            elapsed = time.time() - start
            self.durations[node] = round(self.durations.get(node, 0.0) + elapsed, 3)

    def over_budget(self) -> bool:
        budget = float(os.getenv("LLM_TIME_BUDGET_SECONDS", "600"))
        elapsed = time.time() - self.start_time
        return elapsed > budget

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counts": self.counts.copy(),
            "source_counts": self.source_counts.copy(),
            "source_yield": self.source_yield.copy(),
            "content_sources": self.content_sources.copy(),
            "models_used": self.models_used.copy(),
            "n_llm_calls": self.llm_calls_count,
            "n_llm_errors": self.llm_errors_count,
            "node_llm_calls": self.node_llm_calls.copy(),
            "node_llm_errors": self.node_llm_errors.copy(),
            "durations": self.durations.copy(),
            "total_elapsed_seconds": round(time.time() - self.start_time, 3),
            "warnings": list(self.warnings),
            "fallbacks": list(self.fallbacks),
            "has_fallbacks": self.has_fallbacks,
        }

# Global module singleton
health = RunHealth()
