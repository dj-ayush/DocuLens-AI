import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from api.schemas import AnswerResponse, ConversationTurn, SourceCitation
from core.llm_chain_factory import get_llm


STOP_WORDS = {
  "about", "after", "again", "also", "because", "could", "does", "from",
  "have", "into", "just", "like", "more", "only", "that", "their", "there",
  "these", "they", "this", "what", "when", "where", "which", "with", "would",
  "your", "the", "and", "for", "are", "was", "were", "will", "can", "how",
}


def is_simple_explanation_request(question: str) -> bool:
  normalized = question.casefold()
  return "explain this simply" in normalized or "explain in simple words" in normalized


def contextualize_question(question: str, history: list[ConversationTurn]) -> str:
  normalized = question.casefold().strip()
  follow_up = normalized.startswith(("what about", "how about", "and ", "what if"))
  if follow_up and history:
    return f"{history[-1].question} {question}"
  return question


def _evidence_text(retrieval: dict[str, Any]) -> str:
  return "\n".join(chunk["page_content"] for chunk in retrieval.get("retrieved_chunks", []))


def _answer_text(response: Any) -> str:
  content = getattr(response, "content", response)
  if isinstance(content, list):
    content = " ".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
  return str(content).strip()


def validate_grounding(answer: str, evidence: str) -> bool:
  if not answer or not evidence:
    return False
  answer_lower = answer.casefold()
  if "couldn't find" in answer_lower or "i don't know" in answer_lower:
    return False
  evidence_lower = evidence.casefold()
  for value in re.findall(r"\b\d+(?:[./-]\d+)*\b", answer_lower):
    if value not in evidence_lower:
      return False
  answer_terms = {
    term for term in re.findall(r"[\w]+", answer_lower)
    if len(term) > 2 and term not in STOP_WORDS
  }
  evidence_terms = set(re.findall(r"[\w]+", evidence_lower))
  if not answer_terms:
    return False
  return len(answer_terms & evidence_terms) / len(answer_terms) >= 0.2


def _sources(retrieval: dict[str, Any]) -> list[SourceCitation]:
  return [SourceCitation(
    document_id=chunk["metadata"].get("document_id"),
    document_name=chunk["metadata"].get("document_name"),
    page_number=chunk["metadata"].get("page_number"),
    page_start=chunk["metadata"].get("page_start"),
    page_end=chunk["metadata"].get("page_end"),
    chunk_id=chunk["metadata"].get("chunk_id"),
    score=chunk["score"],
    retrieval_method=chunk["retrieval_method"],
  ) for chunk in retrieval.get("retrieved_chunks", [])]


def generate_grounded_answer(
  provider: str,
  model: str,
  question: str,
  retrieval: dict[str, Any],
  history: list[ConversationTurn] | None = None,
) -> AnswerResponse:
  sources = _sources(retrieval)
  if not retrieval.get("grounded") or not sources:
    return AnswerResponse(
      answer="I couldn't find this information in the uploaded document.",
      grounded=False,
      confidence="low",
      sources=[],
      retrieval=retrieval,
    )

  history = history or []
  simple_instruction = (
    "Explain in simple words using short paragraphs or bullets when useful. "
    "Preserve the original meaning and all important conditions."
    if is_simple_explanation_request(question)
    else "Use simple natural language and answer the question directly."
  )
  conversation = "\n".join(
    f"Previous question: {turn.question}\nPrevious answer: {turn.answer}"
    for turn in history[-3:]
  ) or "No previous conversation."
  evidence = "\n\n".join(
    f"Source: {source.document_name} | Page {source.page_start or source.page_number}"
    f"- {source.page_end or source.page_number}\n"
    f"{chunk['page_content']}"
    for source, chunk in zip(sources, retrieval["retrieved_chunks"])
  )
  prompt = [
    SystemMessage(content=(
      "Answer only from the supplied document evidence. Do not use outside knowledge, "
      "invent facts, or make unsupported assumptions. Preserve names, numbers, dates, "
      "and conditions exactly. If the evidence does not answer the question, say that "
      "you could not find the information in the uploaded document. " + simple_instruction
    )),
    HumanMessage(content=(
      f"Conversation context:\n{conversation}\n\n"
      f"Question:\n{question}\n\n"
      f"Retrieved document evidence:\n{evidence}"
    )),
  ]
  answer = _answer_text(get_llm(provider, model).invoke(prompt))
  grounded = validate_grounding(answer, _evidence_text(retrieval))
  if not grounded:
    return AnswerResponse(
      answer="I couldn't find this information in the uploaded document.",
      grounded=False,
      confidence="low",
      sources=[],
      retrieval=retrieval,
    )
  strongest_score = max(source.score for source in sources)
  confidence = "high" if strongest_score >= 0.75 else "medium"
  return AnswerResponse(
    answer=answer,
    grounded=True,
    confidence=confidence,
    sources=sources,
    retrieval=retrieval,
  )