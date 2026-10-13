import json
import re
from typing import Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from tests.evals.run_meta import TRACKER

DESIGNATED_CATEGORIES = [
    "Tech Shift",
    "Cool Tool",
    "Career & Learning",
    "Ecosystem Update",
    "Watchlist",
]

class SmokeChatModel(BaseChatModel):
    """
    Fake chat model for offline plumbing tests (--smoke mode).
    Returns valid structural responses to test graph and serialization pipelines.
    Never calls external networks or LLM APIs.
    """
    model_name: str = "fake-smoke-model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        TRACKER.record_call("fake-smoke-model")

        # Combine message texts to inspect prompt intent
        prompt = " ".join(m.content if isinstance(m.content, str) else str(m.content) for m in messages)
        prompt_lower = prompt.lower()

        # Parse signal and document IDs
        signal_ids = [int(m) for m in re.findall(r'<signal\s+id=["\']?(\d+)', prompt, re.IGNORECASE)]
        doc_ids = [int(m) for m in re.findall(r'<document\s+id=["\']?(\d+)', prompt, re.IGNORECASE)]

        if "skeptic" in prompt_lower or "filter and deduplicate" in prompt_lower or "<signal" in prompt_lower:
            # Skeptic returns list of signal IDs
            content = json.dumps(signal_ids if signal_ids else [0, 1, 2])

        elif "verifier" in prompt_lower or "fact-check" in prompt_lower or "verification status" in prompt_lower:
            # Verifier returns list of dicts with id, status VALID, reason
            target_ids = doc_ids if doc_ids else [0, 1]
            results = [
                {
                    "id": i,
                    "status": "VALID",
                    "reason": "Verified claims match reference documentation."
                }
                for i in target_ids
            ]
            content = json.dumps(results)

        elif "analyst" in prompt_lower or "practical developer takeaway" in prompt_lower:
            # Analyst returns list of dicts with id, why_it_matters, who_cares, verdict in WATCH/INTEGRATE/READ
            target_ids = doc_ids if doc_ids else [0]
            results = [
                {
                    "id": i,
                    "why_it_matters": "Enables developers to test workflows without external dependencies.",
                    "who_cares": "CS students building portfolios, React beginners, and software engineers",
                    "verdict": "INTEGRATE"
                }
                for i in target_ids
            ]
            content = json.dumps(results)

        elif "editor" in prompt_lower or "editorial curation" in prompt_lower or "newsletter" in prompt_lower or "draft" in prompt_lower:
            # Editor returns up to 5 briefs with unique valid categories, a bold lead, a valid verdict, and a source_url taken from candidates
            candidates = []
            cand_match = re.search(r'Candidates list:\s*(\[\s*\{.*?\}\s*\])', prompt, re.DOTALL)
            if cand_match:
                try:
                    candidates = json.loads(cand_match.group(1))
                except Exception:
                    pass

            if not candidates:
                json_blocks = re.findall(r'```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```', prompt, re.DOTALL)
                for jb in json_blocks:
                    try:
                        candidates = json.loads(jb)
                        if isinstance(candidates, list) and candidates:
                            break
                    except Exception:
                        pass

            if not candidates:
                raw_match = re.search(r'(\[\s*\{.*?"url".*?\}\s*\])', prompt, re.DOTALL)
                if raw_match:
                    try:
                        candidates = json.loads(raw_match.group(1))
                    except Exception:
                        pass

            if not candidates:
                candidates = [
                    {"title": f"Dev Primitive {i+1}", "url": f"https://github.com/example/repo{i+1}"}
                    for i in range(5)
                ]

            briefs = []
            for idx, c in enumerate(candidates[:5]):
                title = c.get("title") or f"Developer Update {idx+1}"
                cat = DESIGNATED_CATEGORIES[idx % len(DESIGNATED_CATEGORIES)]
                verdict = c.get("verdict")
                if verdict not in ["WATCH", "INTEGRATE", "READ"]:
                    verdict = "INTEGRATE"
                url = c.get("url") or f"https://github.com/example/repo{idx+1}"
                lead_title = "This development update" if re.search(r'\d', title) else title
                briefs.append({
                    "title": title,
                    "description": f"**{lead_title} provides essential primitives for developers.**\n\nWhat happened: Framework primitives were structured for testing.",
                    "why_it_matters": c.get("why_it_matters") or "Enables developers to test workflows without external dependencies.",
                    "who_cares": c.get("who_cares") or "CS students and software engineers",
                    "verdict": verdict,
                    "category": cat,
                    "source_url": url
                })
            content = json.dumps(briefs)

        elif "steps" in prompt_lower:
            content = json.dumps({"steps": ["Step 1: Check relevance", "Step 2: Check clarity"]})
        elif "score" in prompt_lower:
            content = json.dumps({"score": 8.0, "reason": "Smoke test synthetic validation."})
        else:
            content = "{}"

        msg = AIMessage(content=content, response_metadata={"model_name": "fake-smoke-model", "model": "fake-smoke-model"})
        return ChatResult(generations=[ChatGeneration(message=msg)])

    @property
    def _llm_type(self) -> str:
        return "smoke_chat_model"
