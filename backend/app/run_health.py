"""
Tracks runtime pipeline metrics, model calls, node timings, and failure states.
Kept simple and minimal for gate checks, snapshot recording, and evals.
"""

import time
from typing import Dict, Any, List

class RunHealth:
    def __init__(self):
        self.reset()

    def reset(self):
        self.fallbacks: List[Dict[str, str]] = []  # Hard failures
        self.warnings: List[str] = []               # Soft issues (e.g. dropped items)
        self.counts: Dict[str, int] = {}            # Stage counts
        self.models_used: Dict[str, int] = {}       # Model names and call counts
        self.durations: Dict[str, float] = {}       # Seconds elapsed per node
        self.llm_calls_count = 0
        self.llm_errors_count = 0
        self._timers: Dict[str, float] = {}

    def mark_fallback(self, node: str, reason: str):
        """Record a hard node failure that blocks publication."""
        self.fallbacks.append({"node": node, "reason": str(reason)})

    @property
    def has_fallbacks(self) -> bool:
        return len(self.fallbacks) > 0

    def add_warning(self, text: str):
        """Record a non-fatal soft issue."""
        self.warnings.append(str(text))

    def record_llm_call(self, node: str, response: Any = None, error: Any = None):
        """Track LLM invocation count, model name, and error status."""
        self.llm_calls_count += 1
        if error is not None:
            self.llm_errors_count += 1
            return
        model = "live-model"
        if response is not None:
            meta = getattr(response, "response_metadata", {}) or {}
            model = meta.get("model_name") or meta.get("model") or getattr(response, "model_name", None) or "live-model"
        self.models_used[str(model)] = self.models_used.get(str(model), 0) + 1

    def set_count(self, stage: str, n: int):
        self.counts[stage] = int(n)

    def start_timer(self, node: str):
        self._timers[node] = time.time()

    def stop_timer(self, node: str):
        start = self._timers.pop(node, None)
        if start is not None:
            self.durations[node] = round(self.durations.get(node, 0.0) + (time.time() - start), 2)

health = RunHealth()
