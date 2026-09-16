# DocuLens AI — React Frontend

Light document-chat UI for the existing FastAPI backend. No RAG logic lives in this app; all retrieval and generation go through the backend API.

## Stack

- React 19 + TypeScript
- Vite 8
- Tailwind CSS 4

## Development

1. Start the FastAPI backend from the repo root:

```bash
uvicorn server.main:app --reload
```

2. Install and run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. API calls use `/api`, proxied to `http://127.0.0.1:8000` in dev (`vite.config.ts`).

Optional: copy `.env.example` to `.env` and set `VITE_API_URL` for a custom API base in production.

## Build

```bash
npm run build
npm run preview
```

## API endpoints used

- `GET /health`
- `GET /llm`, `GET /llm/{provider}`
- `POST /upload_and_process_pdfs`
- `GET /vector_store/count/{provider}`
- `POST /chat`

The Streamlit client in `client/` is unchanged and can run in parallel.
