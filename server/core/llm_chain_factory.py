from config.settings import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from utils.logger import logger


def _api_key_for_provider(model_provider: str) -> str | None:
  if model_provider == "groq":
    return settings.groq_api_key
  if model_provider == "gemini":
    return settings.google_api_key
  return None


def get_llm(model_provider: str, model: str):
  logger.debug(f"Initializing LLM for {model_provider} - {model}")
  api_key = _api_key_for_provider(model_provider)
  providers = {
    "groq": lambda: ChatGroq(model=model, api_key=api_key),
    "gemini": lambda: ChatGoogleGenerativeAI(model=model, api_key=api_key),
  }
  if model_provider not in providers:
    logger.error(f"Unsupported LLM Provider: {model_provider}")
    raise ValueError(f"Unsupported LLM Provider: {model_provider}")
  if not api_key:
    raise ValueError(f"API key is not configured for provider: {model_provider}")
  return providers[model_provider]()
