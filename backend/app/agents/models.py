import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_groq import ChatGroq
from app.config import (
    GEMINI_API_KEY,
    MISTRAL_API_KEY,
    GROQ_API_KEY,
    PRIMARY_MODEL_GROQ,
    FALLBACK_MODEL_GEMINI,
    FALLBACK_MODEL_MISTRAL,
)

logger = logging.getLogger("DailyDiff.models")

def get_llm(temperature: float = 0.2) -> BaseChatModel:
    """
    Get the language model client with an automated multi-provider fallback configuration.
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

