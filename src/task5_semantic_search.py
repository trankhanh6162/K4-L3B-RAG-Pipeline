"""
Task 5 — Semantic search.

Embed query bằng chính hàm của Task 4, query ChromaDB và đổi cosine distance
thành similarity. Output phải theo SearchResult, sort giảm dần và không quá top_k.
"""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về dense SearchResult theo score giảm dần."""
    if top_k <= 0:
        return []
    if not isinstance(query, str) or not query.strip():
        return []
    query_vector = embed_texts([query.strip()])[0]
    collection = get_collection()
    count = collection.count() if hasattr(collection, "count") else top_k
    if count == 0:
        return []
    response = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        normalized_metadata = dict(metadata)
        normalized_metadata.setdefault("url", None)
        results.append({
            "id": item_id,
            "content": content,
            "score": float(1.0 - distance),
            "metadata": normalized_metadata,
            "retrieval_method": "dense",
        })
    return sorted(results, key=lambda item: (-item["score"], item["id"]))[:top_k]


if __name__ == "__main__":
    for result in semantic_search("test query", top_k=3):
        print(result)
