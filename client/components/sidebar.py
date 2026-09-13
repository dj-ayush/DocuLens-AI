import streamlit as st

from types import SimpleNamespace

from utils.helpers import (
  get_model_providers,
  get_models,
  process_uploaded_pdfs
)


def render_model_selector():
  model_provider = st.selectbox(
    "🔌 Model Provider",
    options=get_model_providers(),
    index=None,
    placeholder="Select a model provider",
    key="model_provider"
  )

  model = st.selectbox(
    "🧠 Select a model",
    options=get_models(model_provider),
    index=None,
    placeholder="Select a model",
    disabled=not model_provider,
    key="model"
  )

  return model_provider or "", model or ""

def render_upload_files_button():
  uploaded_files = st.file_uploader(
    "📚 Upload PDF",
    type=["pdf"],
    accept_multiple_files=False,
    disabled=not st.session_state.get("model"),
    key=f"uploaded_files_{st.session_state.get('uploader_key')}"
  )

  uploaded_filenames = [uploaded_files.name] if uploaded_files else []
  session_filenames = [f.name for f in st.session_state.get("pdf_files", [])]
  if uploaded_files and uploaded_filenames != session_filenames:
    st.session_state.update(unsubmitted_files=True)

  submitted = st.button("➡️ Submit", disabled=not st.session_state.get("model"))

  return uploaded_files, submitted

def sidebar_file_upload(model_provider):
  uploaded_files, submitted = render_upload_files_button()

  if submitted:
    if uploaded_files:
      file_objs = [SimpleNamespace(name=uploaded_files.name, type=uploaded_files.type, data=uploaded_files.read())]

      with st.spinner("Processing document..."):
        try:
          result = process_uploaded_pdfs(model_provider, file_objs)
          st.session_state.update(chat_ready=True)
        except Exception as e:
          st.error(f"Error: {str(e)}")
          return

        st.session_state.update(
          pdf_files=file_objs,
          document_result=result,
          unsubmitted_files=False
        )
        st.toast("Document processed successfully!", icon="✅")
    else:
      st.warning("No files uploaded.")

  return uploaded_files, submitted

def sidebar_provider_change_check(model_provider, model):
  if model_provider != st.session_state.get("last_provider"):
    st.session_state.update(chat_ready=False)
    if model:
      st.session_state.update(last_provider=model_provider)
      if st.session_state.get("pdf_files"):
        with st.spinner(f"Reprocessing PDFs with {model_provider}..."):
          try:
            result = process_uploaded_pdfs(model_provider, st.session_state.get("pdf_files"))
            st.session_state.update(chat_ready=True)
            st.session_state.update(document_result=result)
          except Exception as e:
            st.error(f"Error: {str(e)}")
            return

          st.toast("Document replaced successfully!", icon="🔁")

def sidebar_utilities():
  with st.expander("🛠️ Utilities", expanded=False):
    col1, col2, col3, col4 = st.columns(4)

    if col1.button("🔄 Reset"):
      st.session_state.clear()
      st.session_state["model_provider"] = None
      st.toast("Session reset.", icon="🔄")
      st.rerun()

    if col2.button("↻ Replace"):
      st.session_state.update(chat_ready=False, document_result=None, unsubmitted_files=False)
      st.session_state.uploader_key += 1
      st.toast("Choose a replacement document.", icon="↻")
      st.rerun()

    if col3.button("🧹 Clear"):
      st.session_state.chat_history = []
      st.session_state.update(pdf_files=[], document_result=None, chat_ready=False)
      st.session_state.uploader_key += 1
      st.toast("Chat and document cleared.", icon="🧼")
      st.rerun()

    if col4.button("↩️ Undo") and st.session_state.get("chat_history"):
      st.session_state.chat_history.pop()
      st.toast("Last message removed.", icon="↩️")
      st.rerun()
