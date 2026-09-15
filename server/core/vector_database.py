import os
import shutil

from typing import List
from fastapi import UploadFile
from langchain_core.documents import Document

from server.config.settings import settings
from server.core.document_processor import (
  load_documents_from_paths,
  save_uploaded_file,
  split_documents_to_chunks,
)
from server.core.retrieval import DocumentKeywordIndex, HybridRetriever

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from server.utils.logger import logger


_keyword_indexes: dict[str, DocumentKeywordIndex] = {}


def vectorstore_exists(persist_path: str) -> bool:
  exists = os.path.exists(persist_path) and bool(os.listdir(persist_path))
  logger.debug(f"Vectorstore exists at {persist_path}: {exists}")
  return exists

def get_embeddings(model_provider: str):
  logger.debug(f"Getting embeddings for provider: {model_provider}")
  if model_provider == "groq":
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L12-v2")
  elif model_provider == "gemini":
    return GoogleGenerativeAIEmbeddings(
      model="models/embedding-001",
      google_api_key=settings.google_api_key
    )
  else:
    logger.error(f"Unsupported LLM Provider: {model_provider}")
    raise ValueError(f"Unsupported LLM Provider: {model_provider}")

def initialize_empty_vectorstores():
  logger.info("Initializing empty vectorstores...")
  for provider in settings.model_options:
    persist_path = settings.vectorstore_directories[provider]
    os.makedirs(persist_path, exist_ok=True)

    logger.debug(f"Prepared vectorstore directory for {provider} at {persist_path}")

  logger.info("Vectorstore initialization complete.")

async def upsert_vectorstore_from_pdfs(uploaded_files: List[UploadFile], model_provider: str):
  logger.debug(f"Upserting vectorstore for {model_provider}")
  saved_document = await save_uploaded_file(uploaded_files)
  docs, warnings = load_documents_from_paths(
    [saved_document["file_path"]],
    saved_document["document_id"],
    saved_document["document_name"],
  )
  chunks = split_documents_to_chunks(
    docs,
    saved_document["document_id"],
    saved_document["document_name"],
  )
  if not chunks:
    raise ValueError(
      "No extractable text was found in the PDF. Scanned documents require OCR."
    )
  embedding = get_embeddings(model_provider)

  persist_path = settings.vectorstore_directories[model_provider]

  if os.path.exists(persist_path):
    shutil.rmtree(persist_path)
  vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding,
    persist_directory=str(persist_path),
  )
  _keyword_indexes[model_provider] = DocumentKeywordIndex(chunks, saved_document["document_id"])
  logger.debug(f"Created document vectorstore with {len(chunks)} chunks.")

  return {
    "document_id": saved_document["document_id"],
    "filename": saved_document["document_name"],
    "page_count": saved_document["page_count"],
    "chunk_count": len(chunks),
    "status": "processed",
    "warnings": warnings,
  }

def load_vectorstore(model_provider: str):
  persist_path = settings.vectorstore_directories[model_provider]
  logger.debug(f"Loading vectorstore from {persist_path}")

  if vectorstore_exists(persist_path):
    logger.debug(f"Loading existing vectorstore for provider: {model_provider}")
    return Chroma(
      persist_directory=str(persist_path),
      embedding_function=get_embeddings(model_provider),
    )

  logger.debug(f"VectorStore not found for provider: {model_provider}")
  raise ValueError(f"VectorStore not found for provider: {model_provider}")


def get_retriever(model_provider: str) -> HybridRetriever:
  vectorstore = load_vectorstore(model_provider)
  if model_provider not in _keyword_indexes:
    stored = vectorstore.get(include=["documents", "metadatas"])
    documents = [
      Document(page_content=content, metadata=metadata or {})
      for content, metadata in zip(stored.get("documents", []), stored.get("metadatas", []))
    ]
    document_id = documents[0].metadata.get("document_id") if documents else ""
    _keyword_indexes[model_provider] = DocumentKeywordIndex(documents, document_id)
  return HybridRetriever(vectorstore, _keyword_indexes[model_provider])

def get_collections_count(model_provider: str):
  logger.debug(f"Getting collection count for provider: {model_provider}")
  vectorstore = load_vectorstore(model_provider)
  return vectorstore._collection.count()

def find_similar_chunks(model_provider: str, query: str):
  logger.debug(f"Searching for similar chunks for provider: {model_provider}")
  return get_retriever(model_provider).retrieve(query)
