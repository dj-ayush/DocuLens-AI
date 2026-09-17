import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile
from langchain_core.documents import Document
from pypdf import PdfReader

from server.config.settings import settings
from server.utils.logger import logger


def _clean_page_text(text: str | None) -> str:
  if not text:
    return ""
  text = text.replace("\u00ad", "")
  return re.sub(r"\s+", " ", text).strip()


def validate_pdf(file: UploadFile) -> dict[str, Any]:
  filename = file.filename or ""
  if not filename.lower().endswith(".pdf"):
    raise ValueError("Please upload a valid PDF.")

  content_type = (file.content_type or "").lower()
  allowed_types = {
    settings.allowed_file_type.lower(),
    "application/octet-stream",
    "binary/octet-stream",
  }
  if content_type and content_type not in allowed_types:
    raise ValueError("Please upload a valid PDF.")

  file.file.seek(0, os.SEEK_END)
  file_size_bytes = file.file.tell()
  file.file.seek(0)
  max_size_bytes = settings.max_pdf_size_mb * 1024 * 1024
  if file_size_bytes > max_size_bytes:
    raise ValueError("This document is larger than the configured limit.")

  try:
    reader = PdfReader(file.file, strict=False)
    page_count = len(reader.pages)
  except Exception as exc:
    raise ValueError("Please upload a valid PDF.") from exc
  finally:
    file.file.seek(0)

  if page_count > settings.max_pdf_pages:
    raise ValueError("This document is larger than the configured limit.")
  if page_count == 0:
    raise ValueError("Please upload a PDF with at least one page.")

  logger.info(f"Validated PDF {filename}: {page_count} pages")
  return {"page_count": page_count, "file_size_bytes": file_size_bytes}


async def save_uploaded_file(files: list[UploadFile]) -> dict[str, Any]:
  if len(files) != 1:
    raise ValueError("Upload exactly one PDF document.")

  file = files[0]
  validation = validate_pdf(file)
  document_id = str(uuid4())
  filename = Path(file.filename or "document.pdf").name
  os.makedirs(settings.upload_directory, exist_ok=True)
  file_path = settings.upload_directory / f"{document_id}_{filename}"

  file.file.seek(0)
  content = await file.read()
  with open(file_path, "wb") as output_file:
    output_file.write(content)

  return {
    "document_id": document_id,
    "document_name": filename,
    "file_path": str(file_path),
    "page_count": validation["page_count"],
  }


def load_documents_from_paths(
  file_paths: list[str],
  document_id: str,
  document_name: str,
) -> tuple[list[Document], list[str]]:
  documents: list[Document] = []
  warnings: list[str] = []
  reader = PdfReader(file_paths[0], strict=False)

  for page_index, page in enumerate(reader.pages, start=1):
    try:
      text = _clean_page_text(page.extract_text())
    except Exception as exc:
      logger.warning(f"Could not extract page {page_index}: {exc}")
      warnings.append(f"Page {page_index} could not be read and was skipped.")
      continue
    if not text:
      warnings.append(f"Page {page_index} contains no extractable text.")
      continue
    documents.append(Document(
      page_content=text,
      metadata={
        "document_id": document_id,
        "document_name": document_name,
        "page_number": page_index,
        "page_start": page_index,
        "page_end": page_index,
      },
    ))

  return documents, warnings


def split_documents_to_chunks(
  docs: list[Document],
  document_id: str,
  document_name: str,
) -> list[Document]:
  from langchain_text_splitters import TokenTextSplitter

  text_splitter = TokenTextSplitter(chunk_size=500, chunk_overlap=50)
  chunks = text_splitter.split_documents(docs)
  for index, chunk in enumerate(chunks, start=1):
    page_start = chunk.metadata.get("page_start", chunk.metadata.get("page_number", 1))
    page_end = chunk.metadata.get("page_end", page_start)
    chunk.metadata.update({
      "document_id": document_id,
      "document_name": document_name,
      "chunk_id": f"{document_id}:{index}",
      "page_number": page_start,
      "page_start": page_start,
      "page_end": page_end,
    })
  logger.info(f"Split document {document_id} into {len(chunks)} chunks")
  return chunks
