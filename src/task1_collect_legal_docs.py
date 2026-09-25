"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import json
import os
from pathlib import Path

import requests


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"

DOCUMENT_SOURCES = {
    "230515_VUNI_Quy-che-dao-tao-Tien-si.pdf": (
        "https://policy.vinuni.edu.vn/wp-content/uploads/2023/05/"
        "230515_VUNI_Quy-che-dao-tao-Tien-si.pdf"
    ),
    "VU_HT02.VN_Quy-che-dao-tao-Trinh-do-Thac-sy_20.12.2022.pdf": (
        "https://policy.vinuni.edu.vn/wp-content/uploads/2023/05/"
        "VU_HT02.VN_Quy-che-dao-tao-Trinh-do-Thac-sy_20.12.2022.pdf"
    ),
    "VU_HT03.EN_Academic-Regulations-For-Full-Time-Undergraduate-Programs_30102024.pdf": (
        "https://policy.vinuni.edu.vn/wp-content/uploads/2023/05/"
        "VU_HT03.EN_Academic-Regulations-For-Full-Time-Undergraduate-Programs_30102024.pdf"
    ),
}


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tải ít nhất 3 PDF/DOCX từ nguồn công khai."""
    setup_directory()
    existing_documents = [
        path
        for path in DATA_DIR.iterdir()
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}
        and path.stat().st_size > 1024
    ]
    if len(existing_documents) >= 3:
        print("Skipped download: at least 3 valid documents already exist")
        return

    headers = {"User-Agent": "VinUni-RAG-Lab/1.0"}

    for filename, url in DOCUMENT_SOURCES.items():
        output = DATA_DIR / filename
        if output.exists() and output.stat().st_size > 1024:
            print(f"Skipped existing file: {output}")
            continue

        temporary_output = output.with_suffix(f"{output.suffix}.part")
        try:
            with requests.get(url, headers=headers, timeout=60, stream=True) as response:
                response.raise_for_status()
                with temporary_output.open("wb") as file:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            file.write(chunk)

            if temporary_output.stat().st_size <= 1024:
                raise ValueError("Downloaded document is too small")
            with temporary_output.open("rb") as file:
                if file.read(5) != b"%PDF-":
                    raise ValueError("Downloaded content is not a PDF")

            temporary_output.replace(output)
            print(f"Downloaded: {output}")
        except Exception:
            temporary_output.unlink(missing_ok=True)
            raise


if __name__ == "__main__":
    setup_directory()
    download_documents()