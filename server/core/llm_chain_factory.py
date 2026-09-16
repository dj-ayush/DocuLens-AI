from server.config.settings import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from server.utils.logger import logger


_llm_cache: dict[tuple[str, str], object] = {}


def _api_key_for_provider(model_provider: str) -> str | None:
  if model_provider == "groq":
    return settings.groq_api_key
  if model_provider == "gemini":
    return settings.google_api_key
  return None


def get_llm(model_provider: str, model: str):
  api_key = _api_key_for_provider(model_provider)
  if model_provider not in {"groq", "gemini"}:
    logger.error(f"Unsupported LLM Provider: {model_provider}")
    raise ValueError(f"Unsupported LLM Provider: {model_provider}")
  if not api_key:
    raise ValueError(f"API key is not configured for provider: {model_provider}")

  cache_key = (model_provider, model)
  if cache_key in _llm_cache:
    return _llm_cache[cache_key]

  logger.debug(f"Initializing LLM for {model_provider} - {model}")
  providers = {
    "groq": lambda: ChatGroq(model=model, api_key=api_key),
    "gemini": lambda: ChatGoogleGenerativeAI(model=model, api_key=api_key),
  }

  llm = providers[model_provider]()
  _llm_cache[cache_key] = llm
  return llm
