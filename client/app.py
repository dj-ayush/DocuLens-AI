import streamlit as st

from state.session import setup_session_state, is_chat_ready
from components.chat import (
  render_chat_history,
  render_download_chat_history,
  render_uploaded_files_expander,
  render_user_input
)
from components.sidebar import (
  render_model_selector,
  sidebar_file_upload,
  sidebar_provider_change_check,
  sidebar_utilities
)


def main():
  st.set_page_config(page_title="DocuLens AI", layout="centered")
  st.title("DocuLens AI")
  st.caption("Upload one PDF, then ask questions about that document. Supports documents of varying lengths; large documents may take longer to process.")

  setup_session_state()

  with st.sidebar:
    with st.expander("⚙️ Configuration", expanded=True):
      model_provider, model = render_model_selector()
      sidebar_file_upload(model_provider)
      sidebar_provider_change_check(model_provider, model)

    sidebar_utilities()

  if not st.session_state.get(f"uploaded_files_{st.session_state.uploader_key}", []):
    st.info("📄 Upload and process one PDF to start chatting.")

  if st.session_state.get("unsubmitted_files", False):
    st.warning("📄 A replacement document is ready. Process it before chatting.")

  if st.session_state.get("chat_ready") and st.session_state.get("pdf_files", []):
    render_uploaded_files_expander()
    result = st.session_state.get("document_result") or {}
    st.success(
      f"Active document: {result.get('filename', 'PDF')} "
      f"({result.get('page_count', '?')} pages)"
    )
    for warning in result.get("warnings", []):
      st.warning(warning)

  if st.session_state.get("chat_history", []):
    render_chat_history()

  render_download_chat_history()

  if is_chat_ready():
    render_user_input(model_provider, model)

if __name__ == "__main__":
    main()
