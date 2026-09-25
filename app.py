import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.task10_generation import generate_with_citation, reorder_for_llm


st.set_page_config(
    page_title="RAG Chatbot",
    page_icon="💬",
    layout="wide",
)


def render_sources(sources: list[dict]) -> None:
    """Hiển thị sources theo đúng thứ tự [Source N] trong prompt."""
    if not sources:
        st.info("Không có nguồn tài liệu phù hợp.")
        return

    for index, source in enumerate(sources, 1):
        metadata = source["metadata"]
        title = metadata.get("title") or metadata.get("source") or source["id"]
        chunk_index = metadata.get("chunk_index")
        chunk_label = f" · chunk {chunk_index}" if chunk_index is not None else ""
        with st.expander(f"[Source {index}] {title}{chunk_label}"):
            st.caption(
                f"{metadata.get('source', 'N/A')} · "
                f"{source['retrieval_method']} · score={source['score']:.4f}"
            )
            if metadata.get("url"):
                st.link_button("Mở nguồn", metadata["url"])
            st.write(source["content"])


if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("RAG Chatbot")
    st.caption("Trợ lý hỏi đáp dựa trên bộ tài liệu đã được lập chỉ mục")
    top_k = st.slider("Số chunks", 3, 10, 5)
    if st.button("Xóa hội thoại", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("RAG Chatbot")
st.caption("Câu trả lời chỉ sử dụng thông tin từ các nguồn được hiển thị.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            st.caption(
                f"Retrieval source: {message.get('retrieval_source', 'none')}"
            )
            render_sources(message.get("sources", []))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm tài liệu và tạo câu trả lời..."):
            try:
                result = generate_with_citation(query, top_k=top_k)
            except Exception as exc:
                st.error(f"Không thể xử lý câu hỏi: {exc}")
                st.stop()

        # Task 10 đánh số citation theo thứ tự sau khi reorder.
        display_sources = reorder_for_llm(result["sources"])
        st.markdown(result["answer"])
        st.caption(f"Retrieval source: {result['retrieval_source']}")
        render_sources(display_sources)

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": display_sources,
        "retrieval_source": result["retrieval_source"],
    })
