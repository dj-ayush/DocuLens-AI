from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from config.settings import settings
from core.vector_database import (
    get_collections_count,
    find_similar_chunks,
    upsert_vectorstore_from_pdfs,
    get_retriever,
)
from api.schemas import SearchQueryRequest, ChatRequest, StandardAPIResponse
from core.answer_generation import contextualize_question, generate_grounded_answer
from utils.logger import logger

router = APIRouter()


@router.get("/health", response_model=StandardAPIResponse)
def health_check():
  logger.debug("Health check requested")
  return StandardAPIResponse(
    status="success",
    data="ok",
    message="Service is healthy"
  )

@router.get("/llm", response_model=StandardAPIResponse)
async def get_llm_options():
  logger.debug("Fetching LLM providers.")
  return StandardAPIResponse(
    status="success",
    data=[provider.title() for provider in settings.model_options.keys()]
  )

@router.get("/llm/{model_provider}", response_model=StandardAPIResponse)
async def get_llm_models(model_provider: str):
  model_provider = model_provider.lower()
  if model_provider not in settings.model_options:
    logger.warning(f"Invalid model provider: {model_provider}")
    raise HTTPException(status_code=400, detail="Invalid model provider.")

  logger.debug(f"Fetching models for provider: {model_provider}")
  return StandardAPIResponse(
    status="success",
    data=settings.model_options[model_provider]["models"]
  )

@router.post("/upload_and_process_pdfs", response_model=StandardAPIResponse)
async def upload_and_process_pdfs(
  files: list[UploadFile] = File(...),
  model_provider: str = Form(...)
):
  try:
    model_provider = model_provider.lower()
    if len(files) != 1:
      raise HTTPException(status_code=400, detail="Upload exactly one PDF.")
    if model_provider not in settings.model_options:
      raise HTTPException(status_code=400, detail="Invalid model provider.")
    logger.info(f"Received {len(files)} files for model provider: {model_provider}")
    result = await upsert_vectorstore_from_pdfs(files, model_provider)
    logger.info("Files processed successfully")
    return StandardAPIResponse(status="success", data=result)
  except HTTPException:
    raise
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  except Exception as e:
    logger.exception("Error while uploading and processing files")
    raise HTTPException(status_code=500, detail="Unable to process the uploaded PDF.") from e

@router.get("/vector_store/count/{model_provider}", response_model=StandardAPIResponse)
async def get_vectorstore_count(model_provider: str):
  try:
    model_provider = model_provider.lower()
    logger.info(f"Getting collection count for provider: {model_provider}")
    count = get_collections_count(model_provider)
    return StandardAPIResponse(status="success", data=count)
  except ValueError as e:
    raise HTTPException(status_code=404, detail=str(e)) from e
  except Exception as e:
    logger.exception("Error getting collection count")
    raise HTTPException(status_code=500, detail="Unable to read vector store.") from e

@router.post("/vector_store/search", response_model=StandardAPIResponse)
async def get_vectorstore_search(request: SearchQueryRequest):
  try:
    model_provider = request.model_provider.lower()
    logger.info(f"Search requested with query: {request.query} for provider: {request.model_provider}")
    results = find_similar_chunks(model_provider, request.query)
    return StandardAPIResponse(status="success", data=results)
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e)) from e
  except Exception as e:
    logger.exception("Error during similarity search")
    raise HTTPException(status_code=500, detail="Unable to search the document.") from e

@router.post("/chat", response_model=StandardAPIResponse)
async def chat(request: ChatRequest):
  try:
    message = request.message
    model_name = request.model_name
    model_provider = request.model_provider.lower()
    logger.debug(f"Chat request for model: {request.model_name} (provider: {request.model_provider})")

    if model_provider not in settings.model_options:
      logger.warning("Invalid model provider.")
      raise HTTPException(status_code=400, detail="Invalid model provider.")
    if model_name not in settings.model_options[model_provider]["models"]:
      logger.warning("Invalid model name.")
      raise HTTPException(status_code=400, detail="Invalid model name.")

    retriever = get_retriever(model_provider)
    retrieval_query = contextualize_question(message, request.history)
    retrieval = retriever.retrieve(retrieval_query)
    response = generate_grounded_answer(
      provider=model_provider,
      model=model_name,
      question=message,
      retrieval=retrieval,
      history=request.history,
    )
    logger.debug("Chat response generated successfully")
    return StandardAPIResponse(status="success", data=response.model_dump())
  except HTTPException:
    raise
  except Exception as e:
    logger.exception("Chat endpoint encountered an error")
    raise HTTPException(status_code=500, detail="Unable to generate a response.") from e
