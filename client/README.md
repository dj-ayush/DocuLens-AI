# DocuLens AI - Client

This is the Streamlit frontend for DocuLens AI. It supports one active PDF document per session, shows processing status and page count, and enables chat only after processing succeeds.

---

## Features

- 📄 Upload and chat with one active PDF within the configured resource limit
- 🧠 Choose between LLM providers (Groq, Gemini)
- 📚 Page citations in grounded answers
- 📥 Downloadable chat history

---

## Project Structure

```
client/
├── app.py                      # Main Streamlit entry point
├── state/
│   └── session.py              # Handles session state setup
├── components/
│   ├── chat.py                 # All chat-related UI: input, history, uploads
│   └── sidebar.py              # Model selection, upload, and document controls
├── utils/
│   ├── api.py                  # Server communication
│   ├── config.py               # API_URL etc.
│   └── helpers.py              # High-level orchestration (calls to api.py)
```

---

## 📦 Installation

1. **Clone the repo**

```bash
git clone https://github.com/Zlash65/rag-bot-fastapi.git
cd rag-bot-fastapi
```

2. **Create a virtual environment (optional)**

```bash
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**

```bash
cd client

pip3 install -r requirements.txt
```

---

## ▶️ Usage

Run the app:

```bash
cd rag-bot-fastapi/client

streamlit run app.py
```

Steps:
1. Select a model provider
2. Choose a model
3. Upload one PDF
4. Click **Submit**
5. Ask questions about the active document in the chat input

---

## Configuration

Set `API_URL` in `client/utils/config.py` to your FastAPI server:
```python
API_URL = "http://127.0.0.1:8000"
```

---

## 🧼 Tools Panel

- **🔄 Reset**: Clears session state and reruns app
- **🧹 Clear Chat**: Clears chat + PDF submission
- **↩️ Undo**: Removes last question/response

---

## 📦 Download Chat History

Chat history is saved in the session state and can be exported as a CSV with the following columns:

| Question | Answer | Model Provider | Model Name | PDF File | Timestamp |
|----------|--------|----------------|------------|---------------------|-----------|
| What is this PDF about? | This PDF explains... | Groq | llama3-70b-8192 | file1.pdf, file2.pdf | 2025-07-03 21:00:00 |

---

## ⚠️ Notes

- Ensure the backend (FastAPI) server is running before launching the client.
- Chat requires one PDF to be uploaded and processed first.
