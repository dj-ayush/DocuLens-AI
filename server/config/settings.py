from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "DocuLens AI"
    environment: str = "development"
    log_level: str = "INFO"
    llm_provider: str = "groq"

    groq_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "RAG_GROQ_API_KEY",
            "GROQ_API_KEY",
        ),
    )

    google_api_key: str | None = None

    max_pdf_size_mb: int = Field(default=200, ge=1)
    max_pdf_pages: int = Field(default=2000, ge=1)
    allowed_file_type: str = "application/pdf"

    upload_directory: Path = Path("./temp/uploaded_files")
    vectorstore_root_directory: Path = Path("./data")

    semantic_top_k: int = Field(default=8, ge=1)
    keyword_top_k: int = Field(default=8, ge=1)
    final_top_k: int = Field(default=5, ge=1)
    minimum_relevance_score: float = Field(
        default=0.15,
        ge=0,
        le=1,
    )

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="RAG_",
        extra="ignore",
    )

    @property
    def model_options(self) -> dict[str, dict[str, object]]:
        return {
            "groq": {
                "playground": "https://console.groq.com",
                "models": [
                    "openai/gpt-oss-20b",
                ],
            },
            "gemini": {
                "playground": "https://ai.google.dev",
                "models": [
                    "gemini-3.6-flash",
                ],
            },
        }

    @property
    def vectorstore_directories(self) -> dict[str, Path]:
        return {
            provider: self.vectorstore_root_directory / f"{provider}_vector_store"
            for provider in self.model_options
        }


settings = Settings()