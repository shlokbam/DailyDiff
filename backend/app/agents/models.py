import logging
import json
from typing import Any, Optional, Callable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from app.config import (
    GEMINI_API_KEY,
    MISTRAL_API_KEY,
    GROQ_API_KEY,
    PRIMARY_MODEL_GROQ,
    FALLBACK_MODEL_GEMINI,
    FALLBACK_MODEL_MISTRAL,
)
from app.run_health import health

logger = logging.getLogger("DailyDiff.models")

class BudgetExceeded(Exception):
    """Raised when pipeline total runtime exceeds LLM_TIME_BUDGET_SECONDS."""
    pass

def get_llm(temperature: float = 0.2) -> BaseChatModel:
    """
    Get the language model client with an automated multi-provider fallback configuration.
    Configures strict 30s timeouts and max 1 retry to fail fast on outages.
    Priority order:
    1. Groq (ultra-fast sub-second inference, high rate limits)
    2. Google Gemini (gemini-3.8-flash)
    3. Mistral AI
    """
    available_llms = []

    # 1. Groq
    if GROQ_API_KEY:
        try:
            groq_llm = ChatGroq(
                model=PRIMARY_MODEL_GROQ,
                groq_api_key=GROQ_API_KEY,
                temperature=temperature,
                request_timeout=30.0,
                max_retries=1,
            )
            available_llms.append(groq_llm)
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGroq: {e}")

    # 2. Gemini
    if GEMINI_API_KEY:
        try:
            gemini_llm = ChatGoogleGenerativeAI(
                model=FALLBACK_MODEL_GEMINI,
                google_api_key=GEMINI_API_KEY,
                temperature=temperature,
                timeout=30.0,
                max_retries=1,
            )
            available_llms.append(gemini_llm)
        except Exception as e:
            logger.warning(f"Failed to initialize ChatGoogleGenerativeAI: {e}")

    # 3. Mistral AI
    if MISTRAL_API_KEY:
        try:
            mistral_llm = ChatMistralAI(
                model=FALLBACK_MODEL_MISTRAL,
                mistral_api_key=MISTRAL_API_KEY,
                temperature=temperature,
                timeout=30.0,
                max_retries=1,
            )
            available_llms.append(mistral_llm)
        except Exception as e:
            logger.warning(f"Failed to initialize ChatMistralAI: {e}")

    if not available_llms:
        raise ValueError(
            "No valid LLM API key (GROQ_API_KEY, GEMINI_API_KEY, or MISTRAL_API_KEY) found in environment."
        )

    primary_llm = available_llms[0]
    fallback_llms = available_llms[1:]

    if fallback_llms:
        return primary_llm.with_fallbacks(fallback_llms)
    return primary_llm

def invoke_llm(node: str, llm: BaseChatModel, prompt: Any) -> Any:
    """
    Standardized LLM invocation wrapper for all agent nodes.
    Checks time budget, tracks execution timings, and records call counts/errors in health.
    """
    if health.over_budget():
        health.add_warning(f"LLM time budget exceeded before executing node: {node}")
        raise BudgetExceeded(f"Execution time exceeded LLM_TIME_BUDGET_SECONDS budget before node '{node}'")

    health.start_timer(node)
    try:
        response = llm.invoke(prompt)
        health.record_llm_call(node, response=response)
        return response
    except Exception as e:
        health.record_llm_call(node, error=e)
        raise e
    finally:
        health.stop_timer(node)

def escape_untrusted(text: Any) -> str:
    """
    Escapes XML special characters in untrusted external text.
    Prevents closing tag breakout in prompt document wrappers.
    """
    if text is None:
        return ""
    return str(text).replace("<", "&lt;").replace(">", "&gt;")

def _strip_markdown_fences(content: str) -> str:
    """Strip markdown code block fences (e.g. ```json ... ```) from LLM output."""
    s = content.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s

def invoke_json(
    node: str,
    llm: BaseChatModel,
    prompt: Any,
    validate_fn: Optional[Callable[[Any], bool]] = None,
) -> Any:
    """
    Invokes LLM and parses JSON output.
    On JSON parse or validation failure, retries ONCE with a reminder.
    Only after the retry fails does it call health.mark_fallback.
    Both attempts are recorded in health.
    """
    last_err: Optional[Exception] = None

    # First attempt
    try:
        resp = invoke_llm(node, llm, prompt)
        text = _strip_markdown_fences(resp.content if hasattr(resp, "content") else str(resp))
        parsed = json.loads(text)
        if validate_fn is not None and not validate_fn(parsed):
            raise ValueError(f"Schema validation failed for {node} response")
        return parsed
    except BudgetExceeded:
        raise
    except Exception as e:
        last_err = e
        logger.warning(f"First attempt of {node} produced invalid JSON/schema ({e}). Retrying once...")

    # Build retry prompt with reminder
    retry_prompt = prompt
    reminder = (
        "\n\nIMPORTANT: Your previous response was not valid JSON or failed schema validation. "
        "Please return ONLY a valid JSON structure matching the requested format with no markdown formatting, "
        "no code fences, and no surrounding text."
    )
    if isinstance(retry_prompt, str):
        retry_prompt = retry_prompt + reminder

    # Retry attempt
    try:
        retry_resp = invoke_llm(node, llm, retry_prompt)
        text = _strip_markdown_fences(retry_resp.content if hasattr(retry_resp, "content") else str(retry_resp))
        parsed = json.loads(text)
        if validate_fn is not None and not validate_fn(parsed):
            raise ValueError(f"Schema validation failed on retry for {node} response")
        return parsed
    except BudgetExceeded:
        raise
    except Exception as retry_err:
        last_err = retry_err
        logger.error(f"{node} JSON parsing/validation failed after retry: {retry_err}")
        health.mark_fallback(node, f"Malformed JSON output after retry: {last_err}")
        raise last_err

