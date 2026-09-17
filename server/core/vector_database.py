import os

from typing import Any, List
from fastapi import UploadFile
from langchain_core.documents import Document

from server.config.settings import settings
from server.core.document_processor import (
    load_documents_from_paths,
    save_uploaded_file,
    split_documents_to_chunks,
)
from server.core.retrieval import DocumentKeywordIndex, HybridRetriever

from server.utils.logger import logger


class _LazyChroma:
    def _load(self):
        from langchain_chroma import Chroma as ChromaClass

        return ChromaClass

    def __call__(self, *args, **kwargs):
        return self._load()(*args, **kwargs)

    def from_documents(self, *args, **kwargs):
        return self._load().from_documents(*args, **kwargs)


Chroma = _LazyChroma()
GROQ_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
GROQ_EMBEDDING_BATCH_SIZE = 4
_keyword_indexes: dict[str, DocumentKeywordIndex] = {}
_embeddings_cache: dict[str, object] = {}
_vectorstores_cache: dict[str, Any] = {}


def vectorstore_exists(persist_path: str) -> bool:
    exists = os.path.exists(persist_path) and bool(os.listdir(persist_path))
    logger.debug(f"Vectorstore exists at {persist_path}: {exists}")
    return exists


def get_embeddings(model_provider: str):
    logger.debug(f"Getting embeddings for provider: {model_provider}")

    if model_provider in _embeddings_cache:
        logger.info(f"Using cached embeddings for provider: {model_provider}")
        return _embeddings_cache[model_provider]

    if model_provider == "groq":
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info(
            "Initializing HuggingFace embeddings "
            f"model={GROQ_EMBEDDING_MODEL} "
            f"batch_size={GROQ_EMBEDDING_BATCH_SIZE}"
        )

        embeddings = HuggingFaceEmbeddings(
            model_name=GROQ_EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"batch_size": GROQ_EMBEDDING_BATCH_SIZE},
        )

    elif model_provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        logger.info("Initializing Gemini embeddings model=gemini-embedding-001")

        embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=settings.google_api_key,
        )

    else:
        logger.error(f"Unsupported LLM Provider: {model_provider}")
        raise ValueError(f"Unsupported LLM Provider: {model_provider}")

    _embeddings_cache[model_provider] = embeddings
    logger.info(f"Embedding initialization complete for provider: {model_provider}")
    return embeddings


def invalidate_provider_cache(model_provider: str) -> None:
    _vectorstores_cache.pop(model_provider, None)
    _keyword_indexes.pop(model_provider, None)


def initialize_empty_vectorstores():
    logger.info("Initializing empty vectorstores...")

    for provider in settings.model_options:
        persist_path = settings.vectorstore_directories[provider]
        os.makedirs(persist_path, exist_ok=True)

        logger.debug(
            f"Prepared vectorstore directory for {provider} at {persist_path}"
        )

    logger.info("Vectorstore initialization complete.")


async def upsert_vectorstore_from_pdfs(
    uploaded_files: List[UploadFile],
    model_provider: str,
):
    logger.debug(f"Upserting vectorstore for {model_provider}")

    saved_document = await save_uploaded_file(uploaded_files)
    file_path = saved_document["file_path"]

    try:
        docs, warnings = load_documents_from_paths(
            [file_path],
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
                "No extractable text was found in the PDF. "
                "Scanned documents require OCR."
            )

        del docs

        logger.info(
            f"Preparing embeddings for provider={model_provider} "
            f"document_id={saved_document['document_id']} "
            f"chunks={len(chunks)}"
        )

        embedding = get_embeddings(model_provider)
        persist_path = settings.vectorstore_directories[model_provider]

        # Remove the previous active vectorstore from the in-memory cache.
        # Do not use shutil.rmtree() because Chroma/HNSW can keep
        # files open on Windows and cause WinError 32.
        old_vectorstore = _vectorstores_cache.get(model_provider)

        if old_vectorstore is not None:
            try:
                old_vectorstore.delete_collection()
                logger.debug(
                    f"Deleted previous Chroma collection for provider: "
                    f"{model_provider}"
                )
            except Exception as error:
                logger.warning(
                    f"Could not delete previous Chroma collection: {error}"
                )

        _vectorstores_cache.pop(model_provider, None)
        _keyword_indexes.pop(model_provider, None)

        os.makedirs(persist_path, exist_ok=True)

        logger.info(
            f"Creating Chroma vectorstore provider={model_provider} "
            f"document_id={saved_document['document_id']} "
            f"chunks={len(chunks)} persist_path={persist_path}"
        )

        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=str(persist_path),
        )

        logger.info(
            f"Chroma vectorstore creation complete provider={model_provider} "
            f"document_id={saved_document['document_id']} chunks={len(chunks)}"
        )

        _vectorstores_cache[model_provider] = vectorstore

        _keyword_indexes[model_provider] = DocumentKeywordIndex(
            chunks,
            saved_document["document_id"],
        )

        logger.debug(
            f"Created document vectorstore with {len(chunks)} chunks."
        )

        return {
            "document_id": saved_document["document_id"],
            "filename": saved_document["document_name"],
            "page_count": saved_document["page_count"],
            "chunk_count": len(chunks),
            "status": "processed",
            "warnings": warnings,
        }

    finally:
        try:
            os.remove(file_path)
        except OSError:
            logger.warning(
                f"Could not remove temporary upload file: {file_path}"
            )


def load_vectorstore(model_provider: str):
    if model_provider in _vectorstores_cache:
        return _vectorstores_cache[model_provider]

    persist_path = settings.vectorstore_directories[model_provider]

    logger.debug(f"Loading vectorstore from {persist_path}")

    if vectorstore_exists(persist_path):
        logger.debug(
            f"Loading existing vectorstore for provider: {model_provider}"
        )

        vectorstore = Chroma(
            persist_directory=str(persist_path),
            embedding_function=get_embeddings(model_provider),
        )

        _vectorstores_cache[model_provider] = vectorstore

        return vectorstore

    logger.debug(
        f"VectorStore not found for provider: {model_provider}"
    )

    raise ValueError(
        f"VectorStore not found for provider: {model_provider}"
    )


def get_retriever(model_provider: str) -> HybridRetriever:
    vectorstore = load_vectorstore(model_provider)

    if model_provider not in _keyword_indexes:
        stored = vectorstore.get(
            include=["documents", "metadatas"]
        )

        documents = [
            Document(
                page_content=content,
                metadata=metadata or {},
            )
            for content, metadata in zip(
                stored.get("documents", []),
                stored.get("metadatas", []),
            )
        ]

        document_id = (
            documents[0].metadata.get("document_id")
            if documents
            else ""
        )

        _keyword_indexes[model_provider] = DocumentKeywordIndex(
            documents,
            document_id,
        )

    return HybridRetriever(
        vectorstore,
        _keyword_indexes[model_provider],
    )


def get_collections_count(model_provider: str):
    logger.debug(
        f"Getting collection count for provider: {model_provider}"
    )

    vectorstore = load_vectorstore(model_provider)

    return vectorstore._collection.count()


def find_similar_chunks(model_provider: str, query: str):
    logger.debug(
        f"Searching for similar chunks for provider: {model_provider}"
    )

    return get_retriever(model_provider).retrieve(query)
