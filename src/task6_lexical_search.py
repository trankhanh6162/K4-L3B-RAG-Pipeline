"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""


import re
import math


CORPUS: list[dict] = []


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def _get_corpus() -> list[dict]:
    if CORPUS:
        return CORPUS
    from .task4_chunking_indexing import chunk_documents, load_documents

    return chunk_documents(load_documents())


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    if not corpus:
        raise ValueError("Cannot build a BM25 index from an empty corpus")

    class BM25Index:
        def __init__(self, tokenized_corpus: list[list[str]]):
            self.corpus = tokenized_corpus
            self.avgdl = sum(map(len, tokenized_corpus)) / len(tokenized_corpus)
            self.document_frequency: dict[str, int] = {}
            for document in tokenized_corpus:
                for token in set(document):
                    self.document_frequency[token] = self.document_frequency.get(token, 0) + 1

        def get_scores(self, query_tokens: list[str]) -> list[float]:
            scores = []
            total = len(self.corpus)
            k1, b = 1.5, 0.75
            for document in self.corpus:
                frequencies = {token: document.count(token) for token in set(query_tokens)}
                score = 0.0
                for token in query_tokens:
                    frequency = frequencies.get(token, 0)
                    document_frequency = self.document_frequency.get(token, 0)
                    if not frequency or not document_frequency:
                        continue
                    inverse_frequency = math.log(
                        1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
                    )
                    denominator = frequency + k1 * (
                        1 - b + b * len(document) / max(self.avgdl, 1)
                    )
                    score += inverse_frequency * frequency * (k1 + 1) / denominator
                scores.append(score)
            return scores

    return BM25Index([_tokenize(item["content"]) for item in corpus])


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    if top_k <= 0 or not isinstance(query, str) or not query.strip():
        return []
    corpus = _get_corpus()
    if not corpus:
        return []
    bm25 = build_bm25_index(corpus)
    scores = bm25.get_scores(_tokenize(query))
    indices = sorted(range(len(corpus)), key=lambda i: (-float(scores[i]), i))
    results = []
    seen = set()
    for index in indices:
        score = float(scores[index])
        item = corpus[index]
        if score <= 0 or item["id"] in seen:
            continue
        seen.add(item["id"])
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": item["metadata"],
            "retrieval_method": "bm25",
        })
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)
