"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve
from .contracts import validate_generation_result


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        url = metadata.get("url") or "N/A"
        parts.append(
            f"[Source {index} | ID: {chunk['id']} | Title: {metadata['title']} | "
            f"Source: {metadata['source']} | URL: {url}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = LLM_PROVIDER.strip().lower()
    if not LLM_MODEL:
        raise RuntimeError("LLM_MODEL is not configured")
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.create(
            model=LLM_MODEL,
            instructions=system_prompt,
            input=user_message,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        text = response.output_text
    elif provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        text = response.text
    elif provider == "anthropic":
        from anthropic import Anthropic

        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=LLM_MODEL,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=1200,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER!r}")
    if not text or not text.strip():
        raise RuntimeError(f"{provider} returned an empty response")
    return text.strip()


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    refusal = "Tôi không thể xác minh thông tin này từ nguồn hiện có."
    if not isinstance(query, str) or not query.strip() or top_k <= 0:
        return {"answer": refusal, "sources": [], "retrieval_source": "none"}
    try:
        chunks = retrieve(query.strip(), top_k=top_k)
    except Exception:
        chunks = []
    if not chunks:
        result = {"answer": refusal, "sources": [], "retrieval_source": "none"}
        validate_generation_result(result)
        return result
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = (
        f"Context:\n{context}\n\nQuestion: {query}\n\n"
        "Cite sources using [Source N] exactly as labeled above."
    )
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        answer = refusal
    method = chunks[0]["retrieval_method"]
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"
    result = {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }
    validate_generation_result(result)
    return result


if __name__ == "__main__":
    print(generate_with_citation("test query"))
