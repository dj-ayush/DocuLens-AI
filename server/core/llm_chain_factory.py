from config.settings import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from utils.logger import logger


def get_llm(model_provider: str, model: str):
  logger.debug(f"Initializing LLM for {model_provider} - {model}")
  providers = {
    "groq": lambda: ChatGroq(model=model, api_key=settings.groq_api_key),
    "gemini": lambda: ChatGoogleGenerativeAI(model=model, api_key=settings.google_api_key),
  }
  if model_provider not in providers:
    logger.error(f"Unsupported LLM Provider: {model_provider}")
    raise ValueError(f"Unsupported LLM Provider: {model_provider}")
  if not getattr(settings, f"{model_provider}_api_key", None):
    raise ValueError(f"API key is not configured for provider: {model_provider}")
  return providers[model_provider]()
