"""
LLM provider setup and invocation.
Priority: Groq -> Mistral (30s timeouts).
Never retries API errors. Retries once for malformed JSON only.
"""

import os
import sys
import time
import json
import re
import logging
from typing import Any, Optional, Callable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI

from app.config import (
    GROQ_API_KEY, MISTRAL_API_KEY,
    PRIMARY_MODEL_GROQ, GROQ_FALLBACK_MODELS, FALLBACK_MODEL_MISTRAL,
)
from app.run_health import health

logger = logging.getLogger("DailyDiff.models")

def rate_limit_pause(node: str, seconds: int = 30):
    """Paces execution between LLM nodes to stay strictly beneath free-tier 8,000 TPM quotas.
    Automatically skipped during unit tests (pytest) or if SKIP_PIPELINE_PAUSE=1."""
    if os.getenv("SKIP_PIPELINE_PAUSE") == "1" or "pytest" in sys.modules:
        return
    logger.info(f"Rate-limit pacing: sleeping {seconds}s before '{node}' node to reset 60s rolling TPM window...")
    time.sleep(seconds)

def get_llm(temperature: float = 0.2) -> BaseChatModel:
    """Build resilient provider fallback chain across active Groq models -> Mistral (30s timeouts)."""
    providers = []
    if GROQ_API_KEY:
        groq_models = [PRIMARY_MODEL_GROQ] + GROQ_FALLBACK_MODELS
        seen = set()
        for model_name in groq_models:
            if model_name and model_name not in seen:
                seen.add(model_name)
                try:
                    providers.append(
                        ChatGroq(
                            model=model_name,
                            groq_api_key=GROQ_API_KEY,
                            temperature=temperature,
                            request_timeout=30.0,
                            max_retries=0
                        )
                    )
                except Exception as e:
                    logger.warning(f"Could not init Groq model {model_name}: {e}")

    if MISTRAL_API_KEY:
        try:
            providers.append(ChatMistralAI(model=FALLBACK_MODEL_MISTRAL, mistral_api_key=MISTRAL_API_KEY, temperature=temperature, timeout=30.0, max_retries=0))
        except Exception as e:
            logger.warning(f"Could not init Mistral: {e}")

    if not providers:
        raise ValueError("No valid LLM API key (GROQ or MISTRAL) found.")
    return providers[0].with_fallbacks(providers[1:]) if len(providers) > 1 else providers[0]

def invoke_llm(node: str, llm: BaseChatModel, prompt: Any) -> Any:
    """Invokes LLM once without retry; tracks timings and errors."""
    health.start_timer(node)
    try:
        resp = llm.invoke(prompt)
        health.record_llm_call(node, response=resp)
        return resp
    except Exception as e:
        health.record_llm_call(node, error=e)
        raise e
    finally:
        health.stop_timer(node)

def escape_untrusted(text: Any) -> str:
    """Removes HTML comments (invisible on the page but readable by the model), then escapes < and >."""
    s = re.sub(r"<!--.*?-->", "", str(text or ""), flags=re.DOTALL)
    s = re.sub(r"<!--.*", "", s, flags=re.DOTALL)  # an unclosed comment: drop everything after it
    return s.replace("<", "&lt;").replace(">", "&gt;")

def _clean_json_str(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        s = "\n".join(lines[1:-1] if lines[-1].strip().startswith("```") else lines[1:]).strip()
    return s

def invoke_json(node: str, llm: BaseChatModel, prompt: Any, validate_fn: Optional[Callable[[Any], bool]] = None) -> Any:
    """Calls the LLM and parses JSON.
    - An API error (429, timeout, network) is raised immediately. It is NOT retried.
    - Malformed JSON or a failed schema check is retried ONCE.
    The calling node records the failure (one hard fallback per failed node)."""
    for attempt in range(2):
        p = prompt if attempt == 0 else f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON, no surrounding text or markdown."
        resp = invoke_llm(node, llm, p)  # API errors propagate from here, outside the try block
        try:
            data = json.loads(_clean_json_str(getattr(resp, "content", str(resp))))
            if validate_fn and not validate_fn(data):
                raise ValueError(f"Schema check failed on {node} output")
            return data
        except ValueError as e:  # json.JSONDecodeError is a ValueError
            if attempt == 0:
                logger.warning(f"{node} returned bad JSON ({e}). Retrying once...")
                continue
            raise ValueError(f"{node}: invalid JSON after one retry: {e}") from e
