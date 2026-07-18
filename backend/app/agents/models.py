import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from app.config import (
    GEMINI_API_KEY,
    MISTRAL_API_KEY,
    PRIMARY_MODEL_MISTRAL,
    FALLBACK_MODEL_GEMINI,
)

logger = logging.getLogger("DailyDiff.models")

def get_llm(temperature: float = 0.2) -> BaseChatModel:
    """
    Get the language model client with auto-fallback configuration.
    Uses Mistral as primary, falling back to Gemini.
    """
    fallbacks = []

    # Configure Primary LLM: Mistral
    if MISTRAL_API_KEY:
        primary_llm = ChatMistralAI(
            model=PRIMARY_MODEL_MISTRAL,
            mistral_api_key=MISTRAL_API_KEY,
            temperature=temperature,
        )
    else:
        logger.warning("MISTRAL_API_KEY not found in configuration. Trying Gemini...")
        primary_llm = None

    # Configure Fallback LLM: Gemini
    if GEMINI_API_KEY:
        gemini_llm = ChatGoogleGenerativeAI(
            model=FALLBACK_MODEL_GEMINI,
            google_api_key=GEMINI_API_KEY,
            temperature=temperature,
        )
        fallbacks.append(gemini_llm)
    else:
        logger.warning("GEMINI_API_KEY not found in configuration.")

    if not primary_llm and not fallbacks:
        raise ValueError(
            "Neither GEMINI_API_KEY nor MISTRAL_API_KEY is configured. "
            "Please provide at least one valid key in your environment."
        )

    if not primary_llm:
        # If Mistral is missing but Gemini is configured, use Gemini directly
        return fallbacks[0]

    # Combine primary with fallbacks using LangChain's native chain configuration
    if fallbacks:
        return primary_llm.with_fallbacks(fallbacks)
    else:
        return primary_llm
