"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_document

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# Giải thích lựa chọn tham số trong báo cáo nhóm.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini").strip().lower()

COLLECTION_NAME = "rag_documents"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with Gemini using one stable dimension for index and query."""
    if not texts:
        return []
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("All texts must be non-empty strings")
    if EMBEDDING_PROVIDER != "gemini":
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER!r}")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=api_key)
    max_attempts = max(1, int(os.getenv("EMBEDDING_MAX_ATTEMPTS", "4")))
    retry_delay = max(
        0.0, float(os.getenv("EMBEDDING_RETRY_DELAY_SECONDS", "5"))
    )
    for attempt in range(max_attempts):
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=EMBEDDING_DIM,
                    task_type="SEMANTIC_SIMILARITY",
                ),
            )
            break
        except errors.APIError as exc:
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if not retryable or attempt == max_attempts - 1:
                raise
            time.sleep(retry_delay * (2 ** attempt))
    vectors = [list(embedding.values) for embedding in (response.embeddings or [])]
    if len(vectors) != len(texts):
        raise RuntimeError("Gemini returned an unexpected number of embeddings")
    if any(len(vector) != EMBEDDING_DIM for vector in vectors):
        raise RuntimeError("Gemini returned an unexpected embedding dimension")
    return vectors

def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        relative = path.relative_to(STANDARDIZED_DIR)
        doc_type = "legal" if "legal" in relative.parts else "news"
        heading = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        source = re.search(r"^\*\*Source:\*\*\s*(.+)$", content, flags=re.MULTILINE)
        source_value = source.group(1).strip() if source else path.name
        url = source_value if source_value.startswith(("http://", "https://")) else None
        document = {
            "id": relative.as_posix(),
            "content": content,
            "metadata": {
                "source": source_value,
                "title": heading.group(1).strip() if heading else path.stem,
                "doc_type": doc_type,
                "url": url,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    if CHUNK_SIZE <= 0 or not 0 <= CHUNK_OVERLAP < CHUNK_SIZE:
        raise ValueError("Chunk size/overlap configuration is invalid")

    def split_text(text: str) -> list[str]:
        """Dependency-free recursive-style splitting with bounded overlap."""
        pieces = re.split(r"(?<=\n\n)|(?<=\n)|(?<=\. )", text)
        chunks: list[str] = []
        current = ""
        for piece in pieces:
            while len(piece) > CHUNK_SIZE:
                prefix = piece[:CHUNK_SIZE]
                if current:
                    chunks.append(current.strip())
                    current = ""
                chunks.append(prefix.strip())
                piece = piece[CHUNK_SIZE - CHUNK_OVERLAP:]
            if len(current) + len(piece) <= CHUNK_SIZE:
                current += piece
            else:
                if current.strip():
                    chunks.append(current.strip())
                overlap = current[-CHUNK_OVERLAP:] if current else ""
                current = overlap + piece
                if len(current) > CHUNK_SIZE:
                    chunks.append(current[:CHUNK_SIZE].strip())
                    current = current[CHUNK_SIZE - CHUNK_OVERLAP:]
        if current.strip():
            chunks.append(current.strip())
        return [chunk for chunk in chunks if chunk]

    chunks = []
    for document in documents:
        validate_document(document)
        texts = split_text(document["content"])
        for index, text in enumerate(text for text in texts if text):
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk."""
    if not chunks:
        return []
    batch_size = max(1, int(os.getenv("EMBEDDING_BATCH_SIZE", "32")))
    batch_delay = max(
        0.0, float(os.getenv("EMBEDDING_BATCH_DELAY_SECONDS", "0"))
    )
    output = [dict(chunk) for chunk in chunks]
    for start in range(0, len(output), batch_size):
        batch = output[start:start + batch_size]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            chunk["embedding"] = vector
        if batch_delay and start + batch_size < len(output):
            time.sleep(batch_delay)
    return output


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB."""
    if not chunks:
        return
    for chunk in chunks:
        validate_document(chunk, require_chunk=True)
        if "embedding" not in chunk:
            raise ValueError(f"Chunk has no embedding: {chunk['id']}")
    collection = get_collection()
    metadatas = [
        {key: value for key, value in chunk["metadata"].items() if value is not None}
        for chunk in chunks
    ]
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        metadatas=metadatas,
    )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()
