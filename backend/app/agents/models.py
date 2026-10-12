import logging
from typing import Any
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
