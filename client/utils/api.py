import requests
from io import BytesIO

from utils.config import API_URL


def handle_response(response):
  try:
    json_data = response.json()
    if response.status_code >= 400:
      raise Exception(json_data.get("message") or json_data.get("detail") or "Request failed.")
    if json_data["status"] == "success":
      return json_data.get("data")
    else:
      raise Exception(json_data.get("message", "Unknown error occurred."))
  except Exception as e:
    raise Exception(f"API Error: {str(e)}")

def get_supported_llm() -> list[str]:
  response = requests.get(f"{API_URL}/llm")
  return handle_response(response)

def get_supported_models(model_provider) -> list[str]:
  response = requests.get(f"{API_URL}/llm/{model_provider}")
  return handle_response(response)

def upload_and_process_pdf(model_provider, uploaded_files) -> dict:
  files = []
  for file in uploaded_files:
    if hasattr(file, "data"):
      files.append(("file", (file.name, BytesIO(file.data), file.type)))
    else:
      files.append(("file", (file.name, file.read(), file.type)))

  data = {
    "model_provider": model_provider
  }

  # Send one PDF to the backend.
  response = requests.post(f"{API_URL}/upload_and_process_pdfs", files=files, data=data)
  return handle_response(response)

def chat(model_provider, model_name, user_input, history=None) -> dict:
  payload = {
    "model_provider": model_provider,
    "model_name": model_name,
    "message": user_input,
    "history": history or [],
  }

  response = requests.post(f"{API_URL}/chat", json=payload)
  return handle_response(response)
