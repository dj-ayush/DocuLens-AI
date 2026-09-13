from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SearchQueryRequest(BaseModel):
    model_provider: str = Field(min_length=1)
    query: str = Field(min_length=1, max_length=4000)

class ChatRequest(BaseModel):
    model_provider: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)
    history: list["ConversationTurn"] = Field(default_factory=list, max_length=10)

    @field_validator("model_provider", "model_name")
    @classmethod
    def strip_values(cls, value: str) -> str:
        return value.strip()

class StandardAPIResponse(BaseModel):
    status: Literal["success", "error"]
    data: Any = None
    message: str | None = None


class ConversationTurn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    answer: str = Field(min_length=1, max_length=8000)


class SourceCitation(BaseModel):
    document_id: str | None = None
    document_name: str | None = None
    page_number: int | None = None
    page_start: int | None = None
    page_end: int | None = None
    chunk_id: str | None = None
    score: float
    retrieval_method: str


class AnswerResponse(BaseModel):
    answer: str
    grounded: bool
    confidence: Literal["high", "medium", "low"]
    sources: list[SourceCitation] = Field(default_factory=list)
    retrieval: dict[str, Any] | None = None


class IngestionResult(BaseModel):
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    status: Literal["processed"]
    warnings: list[str] = Field(default_factory=list)
