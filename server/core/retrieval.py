import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict

from server.config.settings import settings
from server.utils.logger import logger


TOKEN_PATTERN = re.compile(r"[\w]+(?:[-'][\w]+)*", re.UNICODE)


def normalize_query(query: str) -> str:
  return " ".join(query.casefold().split())


def _tokens(text: str) -> list[str]:
  return TOKEN_PATTERN.findall(normalize_query(text))


@dataclass
class RetrievalEvidence:
  document: Document
  score: float
  method: str


class DocumentKeywordIndex:
  def __init__(self, documents: list[Document], document_id: str):
    self.document_id = document_id
    self.documents = documents
    self.term_frequencies = [
      Counter(_tokens(document.page_content))
      for document in documents
    ]

    self.document_frequency = Counter()

    for frequencies in self.term_frequencies:
      self.document_frequency.update(frequencies.keys())

    self.average_length = (
      sum(
        sum(frequencies.values())
        for frequencies in self.term_frequencies
      ) / len(documents)
      if documents
      else 0
    )

  def search(
    self,
    query: str,
    limit: int,
  ) -> list[RetrievalEvidence]:

    query_terms = _tokens(query)

    if not query_terms or not self.documents:
      return []

    document_count = len(self.documents)
    scores: list[RetrievalEvidence] = []

    for index, frequencies in enumerate(self.term_frequencies):
      length = sum(frequencies.values()) or 1
      score = 0.0

      for term in query_terms:
        term_frequency = frequencies.get(term, 0)

        if not term_frequency:
          continue

        idf = math.log(
          1
          + (
            document_count
            - self.document_frequency[term]
            + 0.5
          )
          / (
            self.document_frequency[term]
            + 0.5
          )
        )

        denominator = (
          term_frequency
          + 1.5
          * (
            0.25
            + 0.75 * length / (self.average_length or 1)
          )
        )

        score += (
          idf
          * term_frequency
          * 2.5
          / denominator
        )

      if score > 0:
        scores.append(
          RetrievalEvidence(
            self.documents[index],
            score,
            "keyword",
          )
        )

    scores.sort(
      key=lambda evidence: evidence.score,
      reverse=True,
    )

    maximum = scores[0].score if scores else 0

    return [
      RetrievalEvidence(
        evidence.document,
        evidence.score / maximum,
        evidence.method,
      )
      for evidence in scores[:limit]
    ]


class HybridRetriever(BaseRetriever):
  vectorstore: Any
  keyword_index: DocumentKeywordIndex | None = None

  model_config = ConfigDict(
    arbitrary_types_allowed=True
  )

  def __init__(
    self,
    vectorstore,
    keyword_index: DocumentKeywordIndex | None = None,
    **kwargs,
  ):
    super().__init__(
      vectorstore=vectorstore,
      keyword_index=keyword_index,
      **kwargs,
    )

  def _semantic_search(
    self,
    query: str,
  ) -> list[RetrievalEvidence]:

    scores_are_distances = True

    try:
      # Use raw similarity/distance scores instead of
      # similarity_search_with_relevance_scores().
      #
      # Chroma can return distances that are outside the
      # 0..1 range expected by LangChain's relevance-score
      # wrapper. Using raw scores avoids that warning.

      results = self.vectorstore.similarity_search_with_score(
        query,
        k=settings.semantic_top_k,
      )

    except (AttributeError, ValueError):
      try:
        results = self.vectorstore.similarity_search_with_relevance_scores(
          query,
          k=settings.semantic_top_k,
        )
        scores_are_distances = False

      except (AttributeError, ValueError):
        documents = self.vectorstore.similarity_search(
          query,
          k=settings.semantic_top_k,
        )

        results = [
          (document, 0.0)
          for document in documents
        ]

    evidence: list[RetrievalEvidence] = []

    for document, distance in results:

      if self.keyword_index is not None:
        if (
          document.metadata.get("document_id")
          != self.keyword_index.document_id
        ):
          continue

      try:
        distance = float(distance)
      except (TypeError, ValueError):
        distance = 1.0

      if scores_are_distances:
        # Chroma cosine distance is normally:
        #
        #   0.0 = identical
        #   1.0 = unrelated
        #
        # Convert distance into a normalized similarity.
        similarity = 1.0 - distance
      else:
        similarity = distance

      similarity = max(
        0.0,
        min(similarity, 1.0),
      )

      evidence.append(
        RetrievalEvidence(
          document,
          similarity,
          "semantic",
        )
      )

    return evidence

  def retrieve(self, query: str) -> dict:
    normalized_query = normalize_query(query)

    semantic = (
      self._semantic_search(normalized_query)
      if self.keyword_index
      else []
    )

    keyword = (
      self.keyword_index.search(
        normalized_query,
        settings.keyword_top_k,
      )
      if self.keyword_index
      else []
    )

    combined: dict[str, RetrievalEvidence] = {}

    semantic_scores = {
      evidence.document.metadata.get("chunk_id"): evidence.score
      for evidence in semantic
    }

    keyword_scores = {
      evidence.document.metadata.get("chunk_id"): evidence.score
      for evidence in keyword
    }

    documents = {
      evidence.document.metadata.get("chunk_id"): evidence.document
      for evidence in semantic + keyword
    }

    for chunk_id, document in documents.items():

      score = (
        0.65 * semantic_scores.get(chunk_id, 0)
        + 0.35 * keyword_scores.get(chunk_id, 0)
      )

      if score >= settings.minimum_relevance_score:

        if (
          chunk_id in semantic_scores
          and chunk_id in keyword_scores
        ):
          method = "hybrid"
        elif chunk_id in semantic_scores:
          method = "semantic"
        else:
          method = "keyword"

        combined[chunk_id] = RetrievalEvidence(
          document,
          score,
          method,
        )

    selected = sorted(
      combined.values(),
      key=lambda evidence: evidence.score,
      reverse=True,
    )[:settings.final_top_k]

    results = [
      self._serialize(evidence)
      for evidence in selected
    ]

    return {
      "normalized_query": normalized_query,
      "retrieved_chunks": results,
      "selected_context": "\n\n".join(
        item["page_content"]
        for item in results
      ),
      "grounded": bool(results),
    }

  def _get_relevant_documents(
    self,
    query: str,
    *,
    run_manager,
  ) -> list[Document]:

    return [
      Document(
        item["page_content"],
        metadata=item["metadata"],
      )
      for item in self.retrieve(query)["retrieved_chunks"]
    ]

  @staticmethod
  def _serialize(
    evidence: RetrievalEvidence,
  ) -> dict:

    return {
      "page_content": evidence.document.page_content,
      "metadata": dict(evidence.document.metadata),
      "score": round(evidence.score, 6),
      "retrieval_method": evidence.method,
    }
