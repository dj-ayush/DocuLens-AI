import io
import json
import logging
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, PropertyMock, patch

from pypdf import PdfWriter
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

from server.api.routes import router  # noqa: E402
from server.core.document_processor import (  # noqa: E402
  load_documents_from_paths,
  split_documents_to_chunks,
  validate_pdf,
)
from server.core import vector_database  # noqa: E402
from fastapi import FastAPI, UploadFile  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from server.main import app  # noqa: E402
from server.core.retrieval import DocumentKeywordIndex, HybridRetriever  # noqa: E402
from server.core.answer_generation import (  # noqa: E402
  contextualize_question,
  generate_grounded_answer,
)
from server.api.schemas import AnswerResponse, ConversationTurn  # noqa: E402
from server.core import llm_chain_factory  # noqa: E402
from server.utils.logger import JsonFormatter  # noqa: E402


def pdf_bytes(page_count: int) -> bytes:
  writer = PdfWriter()
  for _ in range(page_count):
    writer.add_blank_page(width=72, height=72)
  output = io.BytesIO()
  writer.write(output)
  return output.getvalue()


def upload(data: bytes, filename: str = "document.pdf") -> UploadFile:
  return UploadFile(
    file=io.BytesIO(data),
    filename=filename,
    headers={"content-type": "application/pdf"},
  )


class PdfValidationTests(unittest.TestCase):
  def test_valid_one_page_pdf(self):
    result = validate_pdf(upload(pdf_bytes(1)))
    self.assertEqual(result["page_count"], 1)

  def test_valid_300_page_pdf(self):
    result = validate_pdf(upload(pdf_bytes(300)))
    self.assertEqual(result["page_count"], 300)

  def test_valid_10_page_pdf(self):
    result = validate_pdf(upload(pdf_bytes(10)))
    self.assertEqual(result["page_count"], 10)

  def test_301_page_pdf_is_accepted(self):
    result = validate_pdf(upload(pdf_bytes(301)))
    self.assertEqual(result["page_count"], 301)

  def test_larger_document_within_configured_limit_is_accepted(self):
    with patch("server.core.document_processor.settings.max_pdf_pages", 600):
      result = validate_pdf(upload(pdf_bytes(500)))
    self.assertEqual(result["page_count"], 500)

  def test_document_above_configured_page_limit_is_rejected(self):
    with patch("server.core.document_processor.settings.max_pdf_pages", 301):
      with self.assertRaisesRegex(ValueError, "larger than the configured limit"):
        validate_pdf(upload(pdf_bytes(302)))

  def test_invalid_pdf_is_rejected(self):
    with self.assertRaisesRegex(ValueError, "Please upload a valid PDF"):
      validate_pdf(upload(b"not a PDF"))

  def test_oversized_pdf_is_rejected(self):
    with patch("server.core.document_processor.settings.max_pdf_size_mb", 1):
      with self.assertRaisesRegex(ValueError, "larger than the configured limit"):
        validate_pdf(upload(b"x" * (1024 * 1024 + 1)))


class IngestionMetadataTests(unittest.TestCase):
  def test_page_metadata_is_preserved_in_chunks(self):
    docs = [Document(page_content="A useful page", metadata={"page_number": 7, "page_start": 7, "page_end": 7})]
    chunks = split_documents_to_chunks(docs, "doc-123", "example.pdf")
    self.assertEqual(chunks[0].metadata["document_id"], "doc-123")
    self.assertEqual(chunks[0].metadata["document_name"], "example.pdf")
    self.assertEqual(chunks[0].metadata["page_number"], 7)
    self.assertEqual(chunks[0].metadata["page_start"], 7)
    self.assertEqual(chunks[0].metadata["page_end"], 7)
    self.assertTrue(chunks[0].metadata["chunk_id"].startswith("doc-123:"))

  def test_empty_pages_create_warnings(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "empty.pdf"
      path.write_bytes(pdf_bytes(1))
      documents, warnings = load_documents_from_paths([str(path)], "doc-123", "empty.pdf")
      self.assertEqual(documents, [])
      self.assertIn("no extractable text", warnings[0])

  def test_document_replacement_keeps_directory_and_replaces_active_store(self):
    with tempfile.TemporaryDirectory() as directory:
      vector_path = Path(directory) / "vector"
      vector_path.mkdir()
      saved = {
        "document_id": "new-doc",
        "document_name": "new.pdf",
        "file_path": str(Path(directory) / "new.pdf"),
        "page_count": 1,
      }
      document = Document(page_content="new content", metadata={"page_number": 1})
      fake_store = object()
      with patch.object(type(vector_database.settings), "vectorstore_directories", new_callable=PropertyMock, return_value={"groq": vector_path}), \
          patch.object(vector_database, "save_uploaded_file", new=AsyncMock(return_value=saved)), \
          patch.object(vector_database, "load_documents_from_paths", return_value=([document], [])), \
          patch.object(vector_database, "split_documents_to_chunks", return_value=[document]), \
          patch.object(vector_database, "get_embeddings", return_value=object()), \
          patch.object(vector_database.Chroma, "from_documents", return_value=fake_store):
        import asyncio
        result = asyncio.run(vector_database.upsert_vectorstore_from_pdfs([upload(pdf_bytes(1))], "groq"))
      self.assertEqual(result["document_id"], "new-doc")
      self.assertEqual(result["status"], "processed")
      self.assertTrue(vector_path.exists())
      self.assertIs(vector_database._vectorstores_cache["groq"], fake_store)

  def test_active_keyword_index_is_replaced(self):
    old_documents = [Document(page_content="old policy", metadata={"chunk_id": "old", "document_id": "old-doc"})]
    new_documents = [Document(page_content="new policy", metadata={"chunk_id": "new", "document_id": "new-doc"})]
    with patch.object(vector_database, "get_embeddings", return_value=object()), \
        patch.object(vector_database.Chroma, "from_documents", return_value=object()), \
        patch.object(vector_database, "save_uploaded_file", new=AsyncMock(return_value={
          "document_id": "new-doc", "document_name": "new.pdf", "file_path": "new.pdf", "page_count": 1,
        })), \
        patch.object(vector_database, "load_documents_from_paths", return_value=(new_documents, [])), \
        patch.object(vector_database, "split_documents_to_chunks", return_value=new_documents), \
        patch.object(type(vector_database.settings), "vectorstore_directories", new_callable=PropertyMock, return_value={"groq": Path("new-vector")}), \
        patch.object(vector_database.os.path, "exists", return_value=False):
      vector_database._keyword_indexes["groq"] = DocumentKeywordIndex(old_documents, "old-doc")
      import asyncio
      asyncio.run(vector_database.upsert_vectorstore_from_pdfs([upload(pdf_bytes(1))], "groq"))
    self.assertEqual(vector_database._keyword_indexes["groq"].document_id, "new-doc")


class HybridRetrievalTests(unittest.TestCase):
  def setUp(self):
    self.documents = [
      Document(
        page_content="Cancellation requests must be submitted within thirty days.",
        metadata={"document_id": "doc-1", "document_name": "policy.pdf", "page_number": 2, "page_start": 2, "page_end": 2, "chunk_id": "doc-1:1"},
      ),
      Document(
        page_content="Eligibility requires an active account and verified identity.",
        metadata={"document_id": "doc-1", "document_name": "policy.pdf", "page_number": 9, "page_start": 9, "page_end": 9, "chunk_id": "doc-1:2"},
      ),
    ]
    self.keyword_index = DocumentKeywordIndex(self.documents, "doc-1")

  def test_keyword_retrieval(self):
    results = self.keyword_index.search("cancellation", 5)
    self.assertEqual(results[0].document.metadata["page_number"], 2)

  def test_semantic_retrieval(self):
    class SemanticStore:
      def similarity_search_with_relevance_scores(self, query, k):
        return [(self.documents[1], 0.95)]

      documents = self.documents

    retrieval = HybridRetriever(SemanticStore(), self.keyword_index).retrieve("requirements")
    self.assertEqual(retrieval["retrieved_chunks"][0]["metadata"]["page_number"], 9)
    self.assertEqual(retrieval["retrieved_chunks"][0]["retrieval_method"], "semantic")

  def test_combined_retrieval_deduplicates_and_preserves_metadata(self):
    class SemanticStore:
      def similarity_search_with_relevance_scores(self, query, k):
        return [(self.documents[0], 0.9)]

      documents = self.documents

    retrieval = HybridRetriever(SemanticStore(), self.keyword_index).retrieve("cancellation")
    self.assertEqual(len(retrieval["retrieved_chunks"]), 1)
    result = retrieval["retrieved_chunks"][0]
    self.assertEqual(result["retrieval_method"], "hybrid")
    self.assertEqual(result["metadata"]["page_number"], 2)
    self.assertIn("score", result)

  def test_different_questions_retrieve_different_pages(self):
    class SemanticStore:
      def similarity_search_with_relevance_scores(self, query, k):
        return []

    retriever = HybridRetriever(SemanticStore(), self.keyword_index)
    cancellation = retriever.retrieve("cancellation policy")
    eligibility = retriever.retrieve("eligibility requirements")
    self.assertEqual(cancellation["retrieved_chunks"][0]["metadata"]["page_number"], 2)
    self.assertEqual(eligibility["retrieved_chunks"][0]["metadata"]["page_number"], 9)

  def test_irrelevant_question_returns_insufficient_evidence(self):
    class SemanticStore:
      def similarity_search_with_relevance_scores(self, query, k):
        return []

    retrieval = HybridRetriever(SemanticStore(), self.keyword_index).retrieve("weather forecast")
    self.assertFalse(retrieval["grounded"])
    self.assertEqual(retrieval["retrieved_chunks"], [])


class ApiTests(unittest.TestCase):
  def test_successful_ingestion_response(self):
    result = {
      "document_id": "doc-1",
      "filename": "one.pdf",
      "page_count": 1,
      "chunk_count": 1,
      "status": "processed",
      "warnings": [],
    }
    with patch("server.api.routes.upsert_vectorstore_from_pdfs", new=AsyncMock(return_value=result)):
      response = TestClient(app).post(
        "/upload_and_process_pdfs",
        files={"file": ("one.pdf", pdf_bytes(1), "application/pdf")},
        data={"model_provider": "groq"},
      )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["data"], result)

  def test_failed_ingestion_response_hides_stack_trace(self):
    with patch("server.api.routes.upsert_vectorstore_from_pdfs", new=AsyncMock(side_effect=ValueError("bad PDF"))):
      response = TestClient(app).post(
        "/upload_and_process_pdfs",
        files={"file": ("one.pdf", b"bad", "application/pdf")},
        data={"model_provider": "groq"},
      )
    self.assertEqual(response.status_code, 400)
    self.assertEqual(response.json(), {"status": "error", "data": None, "message": "bad PDF"})

  def test_fastapi_application_imports(self):
    self.assertTrue(app.title)

  def test_chat_api_returns_structured_answer(self):
    retrieval = {"grounded": True, "retrieved_chunks": [], "normalized_query": "policy"}
    answer = AnswerResponse(answer="The policy applies.", grounded=True, confidence="high", sources=[], retrieval=retrieval)
    fake_retriever = SimpleNamespace(retrieve=lambda query: retrieval)
    with patch("server.api.routes.get_retriever", return_value=fake_retriever), \
        patch("server.api.routes.contextualize_question", return_value="policy"), \
        patch("server.api.routes.generate_grounded_answer", return_value=answer):
      response = TestClient(app).post(
        "/chat",
        json={"model_provider": "groq", "model_name": "openai/gpt-oss-20b", "message": "What policy applies?"},
      )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["data"]["confidence"], "high")
    self.assertIn("grounded", response.json()["data"])

  def test_chat_api_generates_grounded_answer_with_backend_citations(self):
    retrieval = {
      "grounded": True,
      "retrieved_chunks": [
        {
          "page_content": "Refund policy allows refunds within 30 days.",
          "metadata": {
            "document_id": "doc-1",
            "document_name": "Policy.pdf",
            "page_number": 3,
            "page_start": 3,
            "page_end": 3,
            "chunk_id": "doc-1:1",
          },
          "score": 0.92,
          "retrieval_method": "hybrid",
        }
      ],
      "normalized_query": "refund policy",
      "selected_context": "Refund policy allows refunds within 30 days.",
    }
    fake_retriever = SimpleNamespace(retrieve=lambda query: retrieval)
    fake_llm = SimpleNamespace(
      invoke=lambda messages: SimpleNamespace(content="Refund policy allows refunds within 30 days.")
    )
    with patch("server.api.routes.get_retriever", return_value=fake_retriever), \
        patch("server.api.routes.contextualize_question", return_value="refund policy"), \
        patch("server.core.answer_generation.get_llm", return_value=fake_llm):
      response = TestClient(app).post(
        "/chat",
        json={"model_provider": "groq", "model_name": "openai/gpt-oss-20b", "message": "What is the refund policy?"},
      )
    data = response.json()["data"]
    self.assertEqual(response.status_code, 200)
    self.assertTrue(data["grounded"])
    self.assertEqual(data["sources"][0]["document_name"], "Policy.pdf")
    self.assertEqual(data["sources"][0]["page_number"], 3)
    self.assertEqual(data["sources"][0]["chunk_id"], "doc-1:1")

  def test_chat_api_skips_llm_when_retrieval_has_insufficient_evidence(self):
    retrieval = {"grounded": False, "retrieved_chunks": [], "normalized_query": "weather forecast"}
    fake_retriever = SimpleNamespace(retrieve=lambda query: retrieval)
    with patch("server.api.routes.get_retriever", return_value=fake_retriever), \
        patch("server.api.routes.contextualize_question", return_value="weather forecast"), \
        patch("server.core.answer_generation.get_llm", side_effect=AssertionError("LLM should not be called")):
      response = TestClient(app).post(
        "/chat",
        json={"model_provider": "groq", "model_name": "openai/gpt-oss-20b", "message": "What is the weather?"},
      )
    data = response.json()["data"]
    self.assertEqual(response.status_code, 200)
    self.assertFalse(data["grounded"])
    self.assertEqual(data["sources"], [])

  def test_groq_factory_uses_backend_api_key(self):
    with patch.object(llm_chain_factory.settings, "groq_api_key", "server-key"), \
        patch.object(llm_chain_factory, "ChatGroq", return_value="groq-llm") as groq:
      result = llm_chain_factory.get_llm("groq", "openai/gpt-oss-20b")
    self.assertEqual(result, "groq-llm")
    groq.assert_called_once_with(model="openai/gpt-oss-20b", api_key="server-key")

  def test_gemini_factory_uses_google_api_key(self):
    with patch.object(llm_chain_factory.settings, "google_api_key", "google-key"), \
        patch.object(llm_chain_factory, "ChatGoogleGenerativeAI", return_value="gemini-llm") as gemini:
      result = llm_chain_factory.get_llm("gemini", "gemini-2.0-flash")
    self.assertEqual(result, "gemini-llm")
    gemini.assert_called_once_with(model="gemini-2.0-flash", api_key="google-key")

  def test_provider_factory_rejects_missing_api_key(self):
    with patch.object(llm_chain_factory.settings, "groq_api_key", None):
      with self.assertRaisesRegex(ValueError, "API key is not configured"):
        llm_chain_factory.get_llm("groq", "openai/gpt-oss-20b")


class LoggingTests(unittest.TestCase):
  def test_json_exception_logs_include_traceback(self):
    formatter = JsonFormatter()
    try:
      raise RuntimeError("boom")
    except RuntimeError:
      record = logging.getLogger("test").makeRecord(
        "test", logging.ERROR, __file__, 1, "failure", (), sys.exc_info()
      )
    payload = json.loads(formatter.format(record))
    self.assertIn("RuntimeError: boom", payload["exception"])


class AnswerGenerationTests(unittest.TestCase):
  def setUp(self):
    self.retrieval = {
      "normalized_query": "what is the refund policy",
      "grounded": True,
      "selected_context": "Customers may request a refund within 30 days of purchase.",
      "retrieved_chunks": [
        {
          "page_content": "Customers may request a refund within 30 days of purchase.",
          "metadata": {
            "document_id": "doc-1", "document_name": "Policy.pdf", "page_number": 42,
            "page_start": 42, "page_end": 42, "chunk_id": "doc-1:7",
          },
          "score": 0.91,
          "retrieval_method": "hybrid",
        },
      ],
    }

  def mocked_llm(self, content):
    llm = SimpleNamespace(invoke=lambda messages: SimpleNamespace(content=content))
    return patch("server.core.answer_generation.get_llm", return_value=llm)

  def test_correct_answer_and_citation_metadata(self):
    with self.mocked_llm("Customers can request a refund within 30 days."):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "What is the refund policy?", self.retrieval)
    self.assertTrue(result.grounded)
    self.assertEqual(result.confidence, "high")
    self.assertEqual(result.sources[0].page_number, 42)
    self.assertEqual(result.sources[0].chunk_id, "doc-1:7")
    self.assertEqual(result.sources[0].retrieval_method, "hybrid")

  def test_simple_explanation_instruction_is_sent(self):
    captured = {}
    def invoke(messages):
      captured["prompt"] = " ".join(str(message.content) for message in messages)
      return SimpleNamespace(content="Customers can ask for their money back within 30 days.")
    with patch("server.core.answer_generation.get_llm", return_value=SimpleNamespace(invoke=invoke)):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "Explain this simply.", self.retrieval)
    self.assertTrue(result.grounded)
    self.assertIn("Explain in simple words", captured["prompt"])

  def test_multiple_source_pages_are_returned(self):
    retrieval = dict(self.retrieval)
    retrieval["retrieved_chunks"] = [
      dict(self.retrieval["retrieved_chunks"][0]),
      {
        "page_content": "Refunds are returned to the original payment method.",
        "metadata": {**self.retrieval["retrieved_chunks"][0]["metadata"], "page_number": 44, "page_start": 44, "page_end": 44, "chunk_id": "doc-1:8"},
        "score": 0.8,
        "retrieval_method": "semantic",
      },
    ]
    with self.mocked_llm("Customers can request a refund within 30 days and receive it through the original payment method."):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "What is the refund policy?", retrieval)
    self.assertEqual([source.page_number for source in result.sources], [42, 44])

  def test_exact_number_and_date_are_preserved(self):
    retrieval = dict(self.retrieval)
    retrieval["selected_context"] = "Applications submitted on 2026-01-15 are reviewed within 30 days."
    retrieval["retrieved_chunks"] = [dict(self.retrieval["retrieved_chunks"][0], page_content=retrieval["selected_context"])]
    with self.mocked_llm("Applications submitted on 2026-01-15 are reviewed within 30 days."):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "When are applications reviewed?", retrieval)
    self.assertTrue(result.grounded)

  def test_unsupported_answer_is_rejected(self):
    with self.mocked_llm("The policy also includes free international shipping."):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "What is the refund policy?", self.retrieval)
    self.assertFalse(result.grounded)
    self.assertEqual(result.sources, [])

  def test_follow_up_question_uses_previous_topic(self):
    history = [ConversationTurn(question="What is the refund policy?", answer="Refunds are available within 30 days.")]
    self.assertIn("What is the refund policy?", contextualize_question("What about international customers?", history))

  def test_insufficient_retrieval_does_not_call_llm(self):
    retrieval = {"grounded": False, "retrieved_chunks": [], "normalized_query": "unknown"}
    with patch("server.core.answer_generation.get_llm", side_effect=AssertionError("LLM should not be called")):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "Unknown question", retrieval)
    self.assertFalse(result.grounded)
    self.assertEqual(result.confidence, "low")

  def test_answer_response_schema(self):
    with self.mocked_llm("Customers can request a refund within 30 days."):
      result = generate_grounded_answer("groq", "openai/gpt-oss-20b", "What is the refund policy?", self.retrieval)
    validated = AnswerResponse.model_validate(result.model_dump())
    self.assertEqual(validated.answer, result.answer)


if __name__ == "__main__":
  unittest.main()
