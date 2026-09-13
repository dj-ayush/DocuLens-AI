# DocuLens AI - Server

This is the FastAPI backend for DocuLens AI. It validates one PDF per upload, preserves page metadata, stores only the current document, retrieves relevant chunks, and sends grounded context to the configured LLM provider.

---

## Features

- ✅ Upload and process one active PDF within the configurable resource limit
- 🧠 Chat with LLM using vectorstore retrieval
- 🔎 Retrieve relevant document evidence for each question
- 🌐 Uses Groq by default, with Gemini available as an optional provider

---

## Project Structure

```
server/
├── api/                        # FastAPI routes and schemas
├── config/                     # Environment and constants
├── core/                       # LLM logic, vectorstore, processing
├── utils/                      # Logger and helpers
├── main.py                     # App entry point
```

---

## 📦 Installation

1. **Clone the repo**

```bash
git clone https://github.com/dj-ayush/DocuLens-AI.git
cd rag-bot-fastapi
```

2. **Create a virtual environment (optional)**

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
cd server

pip3 install -r requirements.txt
```

---

## Configuration

Copy the repository `.env.example` to `.env` and set environment variables:

- **Groq**: [console.groq.com](https://console.groq.com/)
- **Gemini**: [ai.google.dev](https://ai.google.dev)

```env
RAG_LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
RAG_MAX_PDF_SIZE_MB=200
RAG_MAX_PDF_PAGES=2000
RAG_SEMANTIC_TOP_K=8
RAG_KEYWORD_TOP_K=8
RAG_FINAL_TOP_K=5
RAG_MINIMUM_RELEVANCE_SCORE=0.15
```

Additional provider keys and all configurable limits are documented in `.env.example`.

---

## ▶️ Usage

Run the app:

```bash
cd DocuLens-AI/server

uvicorn main:app --reload
```

---

## API Endpoints

- `/upload_and_process_pdfs`
- `/chat`
- `/vector_store/count/{provider}`
- `/vector_store/search`
- `/llm`
- `/llm/{provider}`
- `/health`

## Logging

Logs are printed to the console and controlled via `utils/logger.py`.

## Tests

From the repository root:

```bash
python -m compileall -q server client tests
python -m unittest discover -s tests -v
```
