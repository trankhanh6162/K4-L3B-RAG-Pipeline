"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import os
import json
import re
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
LEGAL_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
CACHE_PATH = Path(__file__).parent.parent / "pageindex_doc_ids.json"
API_BASE = "https://api.pageindex.ai"


def _headers() -> dict[str, str]:
    if not PAGEINDEX_API_KEY:
        raise RuntimeError("PAGEINDEX_API_KEY is not configured")
    return {"api_key": PAGEINDEX_API_KEY}


def _load_cache() -> dict[str, str]:
    if not CACHE_PATH.exists():
        return {}
    data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("pageindex_doc_ids.json must contain an object")
    return {str(key): str(value) for key, value in data.items()}


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    cache = _load_cache()
    paths = sorted(
        path for path in LEGAL_DIR.glob("*")
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}
    )
    if not paths:
        raise ValueError(f"No supported legal documents found in {LEGAL_DIR}")
    for path in paths:
        cache_key = path.name
        if cache_key in cache:
            continue
        with path.open("rb") as file_handle:
            response = requests.post(
                f"{API_BASE}/doc/",
                headers=_headers(),
                files={"file": (path.name, file_handle)},
                timeout=(10, 120),
            )
        response.raise_for_status()
        doc_id = response.json().get("doc_id")
        if not doc_id:
            raise RuntimeError(f"PageIndex did not return doc_id for {path.name}")
        cache[cache_key] = str(doc_id)
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Uploaded: {path.name} -> {doc_id}")


def _flatten_nodes(nodes: list[dict], source: str, doc_id: str) -> list[dict]:
    flattened = []
    stack = list(reversed(nodes))
    while stack:
        node = stack.pop()
        children = node.get("nodes") or []
        if isinstance(children, list):
            stack.extend(reversed(children))
        content = str(node.get("text") or node.get("summary") or "").strip()
        if not content:
            continue
        node_id = str(node.get("node_id") or len(flattened))
        flattened.append({
            "id": f"pageindex:{doc_id}:{node_id}",
            "content": content,
            "metadata": {
                "source": source,
                "title": str(node.get("title") or source),
                "doc_type": "legal",
                "url": None,
                "chunk_index": len(flattened),
            },
        })
    return flattened


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    if top_k <= 0 or not isinstance(query, str) or not query.strip():
        return []
    cache = _load_cache()
    if not cache:
        return []
    candidates = []
    query_terms = set(re.findall(r"\w+", query.casefold(), flags=re.UNICODE))
    for source, doc_id in cache.items():
        response = requests.get(
            f"{API_BASE}/doc/{doc_id}/",
            headers=_headers(),
            params={"type": "tree", "summary": "true"},
            timeout=(10, 60),
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "completed":
            continue
        nodes = payload.get("result") or []
        for item in _flatten_nodes(nodes, source, doc_id):
            terms = set(re.findall(r"\w+", item["content"].casefold(), flags=re.UNICODE))
            overlap = len(query_terms.intersection(terms))
            if overlap:
                item["score"] = overlap / max(len(query_terms), 1)
                item["retrieval_method"] = "pageindex"
                candidates.append(item)
    candidates.sort(key=lambda item: (-item["score"], item["id"]))
    return candidates[:top_k]


if __name__ == "__main__":
    upload_documents()
