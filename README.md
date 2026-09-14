# DocuLens AI

DocuLens AI is a document question-answering application built with Streamlit and FastAPI. A user uploads one PDF, asks questions about it, and receives a grounded answer with page-level citations.

## Problem Statement

Long documents are difficult to search manually. DocuLens AI extracts a PDF's text, preserves page metadata, retrieves only relevant evidence for each question, and uses an LLM to produce a simple answer without sending the complete document to the model.

## Key Features

- One active PDF document at a time
- Configurable file-size and page-count limits
- Page-aware PDF extraction and chunking
- HuggingFace embeddings with ChromaDB
- Hybrid semantic and keyword retrieval
- Configurable retrieval limits and relevance threshold
- Groq as the default LLM provider
- Optional Gemini provider
- Grounded answers with backend-owned page citations
- Lightweight follow-up question context
- Replacement isolation for the active document
- Simple user-facing errors without API keys or stack traces

## System Architecture

```text
                         DocuLens AI
                              |
                +-------------+-------------+
                |                           |
                v                           v
        Streamlit Client             FastAPI Backend
                                            |
                                            v
                                      PDF Validation
                                            |
                                            v
                                  PDF Text Extraction
                                            |
                                            v
                                  Page-aware Chunking
                                            |
                                            v
                                   HuggingFace Embeddings
                                            |
                                            v
                                         ChromaDB
                                            |
                         +------------------+------------------+
                         |                                     |
                         v                                     v
                  Semantic Search                       Keyword Search
                         |                                     |
                         +------------------+------------------+
                                            |
                                            v
                                   Hybrid Retrieval
                                            |
                                            v
                                  Relevant Chunks Only
                                            |
                                            v
                                  Groq / Gemini LLM
                                            |
                                            v
                              Grounded Answer + Citations
                                            |
                                            v
                                    Streamlit Client
```

## RAG Pipeline

1. The user uploads one PDF.
2. The backend validates the file type, size, PDF structure, and configured page limit.
3. Text is extracted page by page while preserving page metadata.
4. The extracted text is split into chunks with document, page, and chunk metadata.
5. Chunks are converted into embeddings using the configured embedding model.
6. Embeddings are stored in ChromaDB.
7. A lightweight keyword index is maintained for the active document.
8. A user question is processed using both semantic and keyword retrieval.
9. Retrieved results are combined, deduplicated, ranked, and filtered.
10. Only the final relevant chunks are provided to the selected LLM.
11. The backend generates a grounded answer and attaches the source page metadata.
12. The Streamlit client displays the answer and page citations.

## Hybrid Retrieval

Semantic retrieval uses ChromaDB similarity search.

Keyword retrieval uses a lightweight in-memory BM25-style index scoped to the active document.

The application combines both retrieval results, removes duplicate chunks, ranks the evidence, and selects the configured number of final chunks.

The normal UI does not expose raw retrieval debug information.

## PDF Processing

The processor validates:

- `application/pdf` content type
- `.pdf` filename
- Maximum file size
- PDF structure
- Actual page count
- At least one page

The page limit is configurable and defaults to 2,000 pages.

Documents below or above 300 pages are supported, subject to the configured limit and available system resources.

Pages without extractable text are reported as warnings. OCR is not included.

## Embeddings and ChromaDB

DocuLens AI uses the local HuggingFace embedding model:

```text
sentence-transformers/all-MiniLM-L12-v2
```

The generated embeddings are stored in ChromaDB together with document and page metadata.

The active document is isolated from previous uploads. When a new PDF replaces the current document, the previous active vector data is removed before the new document is indexed.

## LLM Providers

Groq is the default LLM provider and uses the official `langchain-groq` integration with:

```text
openai/gpt-oss-20b
```

Gemini remains available as an optional provider through `langchain-google-genai`.

The LLM provider is responsible for answer generation. Embeddings and LLM inference are separate parts of the pipeline.

API keys are read by the FastAPI backend only. The Streamlit frontend never receives or stores provider API keys.

## Citations and Follow-ups

Citations are created by the backend from retrieved chunk metadata rather than being generated by the LLM.

Source metadata includes information such as:

- Document name
- Page number or page range
- Chunk ID
- Retrieval score
- Retrieval method

The frontend presents the relevant document and page information with the answer.

A small amount of previous conversation history can be included with a chat request so that simple follow-up questions can be understood in context.

## Configuration

Copy `.env.example` to `.env` and configure the required provider key:

```env
RAG_ENVIRONMENT=development
RAG_LOG_LEVEL=INFO
RAG_LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
RAG_GOOGLE_API_KEY=your_google_api_key_here
RAG_MAX_PDF_SIZE_MB=200
RAG_MAX_PDF_PAGES=2000
RAG_ALLOWED_FILE_TYPE=application/pdf
RAG_SEMANTIC_TOP_K=8
RAG_KEYWORD_TOP_K=8
RAG_FINAL_TOP_K=5
RAG_MINIMUM_RELEVANCE_SCORE=0.15
```

`GROQ_API_KEY` is required when Groq is selected.

`RAG_GOOGLE_API_KEY` is required only when Gemini is selected.

## Project Structure

```text
client/
├── app.py
├── components/
│   ├── chat.py
│   └── sidebar.py
├── state/
│   └── session.py
└── utils/
    ├── api.py
    ├── config.py
    └── helpers.py

server/
├── main.py
├── api/
│   ├── routes.py
│   └── schemas.py
├── config/
│   └── settings.py
├── core/
│   ├── document_processor.py
│   ├── vector_database.py
│   ├── retrieval.py
│   ├── answer_generation.py
│   └── llm_chain_factory.py
└── utils/
    └── logger.py

tests/
└── test_foundation.py
```

## Installation

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install -r server/requirements.txt
python -m pip install -r client/requirements.txt
```

Create `.env` from `.env.example` and add your provider key.

## Running the Backend

From the repository root:

```powershell
.venv\Scripts\Activate.ps1
cd server
uvicorn main:app --reload
```

The FastAPI backend runs at:

```text
http://127.0.0.1:8000
```

## Running the Frontend

Open a second terminal:

```powershell
.venv\Scripts\Activate.ps1
cd client
streamlit run app.py
```

The Streamlit application will display its local URL.

## Testing

Run from the repository root:

```powershell
.venv\Scripts\Activate.ps1
python -m compileall -q server client tests
python -m unittest discover -s tests -v
```

The tests use mocked LLM responses where applicable and do not require a real provider request.

## Example Usage

1. Start the FastAPI backend.
2. Start the Streamlit frontend.
3. Upload a PDF.
4. Wait for document processing to complete.
5. Ask a question about the document.
6. Receive a grounded answer with the relevant page citation.
7. Ask a follow-up question if required.

Example:

```text
Question:
What is the main purpose of this document?

Answer:
The document explains the main concepts and components of the subject.

Source:
Document.pdf - Page 3
```

## Error Handling

The API returns simple user-facing errors for invalid PDFs, documents above configured limits, missing documents, insufficient evidence, and provider failures.

Detailed exceptions are logged by the backend.

Internal paths, stack traces, and API keys are not returned to the frontend.

## Security

- Provider API keys are loaded only by the backend.
- `.env` is ignored by source control.
- `.env.example` contains placeholders only.
- Uploaded files and generated vector data are ignored by source control.
- File type, PDF structure, file size, and page count are validated.
- User questions are treated as text and are not executed as code.

## Current Limitations

- OCR is not included for scanned PDFs.
- The keyword index is maintained in memory for the active document.
- The application currently supports one active document rather than multi-document search.
- Grounding validation is lightweight and heuristic.
- Authentication and production deployment configuration are outside the current project scope.

## Future Improvements

Possible future improvements include stronger evidence verification, optional OCR, persistent session isolation, retrieval evaluation, and production deployment configuration.

## Technology Stack

- Python
- FastAPI
- Streamlit
- LangChain
- Groq via `langchain-groq`
- Gemini via `langchain-google-genai`
- ChromaDB
- HuggingFace Sentence Transformers
- PyPDF
- Pydantic Settings
