"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
import re
import unicodedata
from pathlib import Path

from markitdown import MarkItDown
from pypdf import PdfReader


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"

LEGAL_METADATA = {
    "230515_VUNI_Quy-che-dao-tao-Tien-si.pdf": {
        "title": "Quy chế đào tạo trình độ tiến sĩ",
        "document_code": "VU_HT01.VN",
        "issued_date": "2023-05-15",
        "title_lines": {"QUY CHẾ ĐÀO TẠO TRÌNH ĐỘ TIẾN SĨ"},
    },
    "VU_HT02.VN_Quy-che-dao-tao-Trinh-do-Thac-sy_20.12.2022.pdf": {
        "title": "Quy chế đào tạo trình độ thạc sĩ",
        "document_code": "VU_HT02.VN",
        "issued_date": "2022-12-20",
        "title_lines": {"QUY CHẾ ĐÀO TẠO TRÌNH ĐỘ THẠC SĨ"},
    },
    "VU_HT03.VN_QC-dao-tao-dai-hoc-he-chinh-quy-theo-he-thong-tin-chi.pdf": {
        "title": "Quy chế đào tạo đại học hệ chính quy theo hệ thống tín chỉ",
        "document_code": "VU_HT03.VN",
        "issued_date": "2024-05-21",
        "title_lines": {
            "QUY CHẾ ĐÀO TẠO ĐẠI HỌC HỆ CHÍNH QUY",
            "THEO HỆ THỐNG TÍN CHỈ",
        },
    },
}

_PDF_WATERMARKS = {"PgeZ2MV66JlFtoYc0Gec/A=="}
_METADATA_LINE = re.compile(
    r"^(Mã số|Đơn vị phát hành|Ngày phát hành|Phạm vi áp dụng)\s*:\s*(.*)$",
    re.IGNORECASE,
)
_CHAPTER_HEADING = re.compile(r"^(?:Chương|CHƯƠNG)\s+([IVXLCDM]+|\d+)(?:\s+(.*))?$")
_ARTICLE_HEADING = re.compile(r"^Điều\s+\d+[a-zA-Z]?\s*[.:]\s*.+$", re.IGNORECASE)
_APPENDIX_HEADING = re.compile(r"^PHỤ LỤC(?:\s+[IVXLCDM\d]+)?(?:\s*[-:]\s*.*)?$")
_LIST_ITEM = re.compile(r"^(?:\d+[.)]|[a-zđ][)]|[-–•])\s+", re.IGNORECASE)


def _front_matter(**metadata: str | None) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        serialized = "null" if value is None else json.dumps(value, ensure_ascii=False)
        lines.append(f"{key}: {serialized}")
    lines.extend(["---", ""])
    return "\n".join(lines)


def _write_markdown(path: Path, content: str) -> None:
    normalized = unicodedata.normalize("NFC", content).strip()
    if len(normalized) < 200:
        raise ValueError(f"Markdown content is empty or too short: {path.name}")

    temporary_path = path.with_suffix(f"{path.suffix}.part")
    temporary_path.write_text(f"{normalized}\n", encoding="utf-8")
    temporary_path.replace(path)


def _table_cells(line: str) -> list[str]:
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|"):
        value = value[:-1]
    return [cell.strip() for cell in value.split("|")]


def _is_table_separator(line: str) -> bool:
    cells = _table_cells(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _clean_pdf_page(text: str, page_number: int, title_lines: set[str]) -> list[str]:
    lines = [unicodedata.normalize("NFC", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line not in _PDF_WATERMARKS]

    nonempty_positions = [index for index, line in enumerate(lines) if line]
    edge_positions = set(nonempty_positions[:4] + nonempty_positions[-4:])
    lines = [
        line
        for index, line in enumerate(lines)
        if not (index in edge_positions and line == str(page_number))
    ]
    if page_number == 1:
        lines = [line for line in lines if line not in title_lines]
    return lines


def _legal_heading(lines: list[str], index: int) -> tuple[str | None, int]:
    line = lines[index]
    chapter_match = _CHAPTER_HEADING.match(line)
    if chapter_match:
        number, heading_text = chapter_match.groups()
        if heading_text and len(heading_text.split()) < 2:
            return None, 1
        consumed = 1
        if not heading_text:
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index]:
                next_index += 1
            if next_index < len(lines):
                candidate = lines[next_index]
                if candidate == candidate.upper() and 1 < len(candidate.split()) <= 16:
                    heading_text = candidate
                    consumed = next_index - index + 1
        heading = f"## Chương {number}"
        if heading_text:
            heading += f": {heading_text}"
        return heading, consumed

    if _ARTICLE_HEADING.match(line):
        return f"### {line}", 1
    if _APPENDIX_HEADING.match(line):
        return f"## {line.title()}", 1
    if (
        line == line.upper()
        and not re.search(r"\d", line)
        and len(line) >= 8
        and 1 < len(line.split()) <= 12
        and len(line) <= 100
    ):
        return f"## {line}", 1
    return None, 1


def _format_legal_content(lines: list[str], title: str) -> str:
    output = [f"# {title}", ""]
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.extend([" ".join(paragraph), ""])
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = re.sub(r"[ \t]+", " ", lines[index]).strip()
        if not line:
            flush_paragraph()
            index += 1
            continue

        metadata_match = _METADATA_LINE.match(line)
        if metadata_match:
            flush_paragraph()
            label, value = metadata_match.groups()
            output.extend([f"- **{label}:** {value}", ""])
            index += 1
            continue

        if line.startswith("|"):
            flush_paragraph()
            if not _is_table_separator(line):
                cells = [cell for cell in _table_cells(line) if cell]
                if cells:
                    if cells[0] in {
                        "Mã số",
                        "Đơn vị phát hành",
                        "Ngày phát hành",
                        "Phạm vi áp dụng",
                    } and len(cells) >= 2:
                        value = cells[1].removeprefix(":").strip()
                        output.extend([f"- **{cells[0]}:** {value}", ""])
                    else:
                        output.extend(["- " + " | ".join(cells), ""])
            index += 1
            continue

        heading, consumed = _legal_heading(lines, index)
        if heading:
            flush_paragraph()
            output.extend([heading, ""])
            index += consumed
            continue

        if _LIST_ITEM.match(line):
            flush_paragraph()
            paragraph.append(line)
            index += 1
            continue

        paragraph.append(line)
        index += 1

    flush_paragraph()
    return "\n".join(output).strip()


def _extract_pdf(source_path: Path, metadata: dict) -> str:
    reader = PdfReader(source_path)
    lines: list[str] = []
    for page_number, page in enumerate(reader.pages, 1):
        page_lines = _clean_pdf_page(
            page.extract_text(extraction_mode="plain") or "",
            page_number,
            metadata["title_lines"],
        )
        nonempty = [line for line in page_lines if line]
        is_contents_page = page_number <= 3 and any(
            line in {"MỤC LỤC", "NỘI DUNG"} for line in nonempty[:5]
        )
        if not is_contents_page:
            lines.extend(page_lines)
    return _format_legal_content(lines, metadata["title"])


def _sequential_page_markers(lines: list[str], page_count: int) -> dict[int, int]:
    markers: dict[int, int] = {}
    search_start = 0
    for page_number in range(1, page_count + 1):
        for index in range(search_start, len(lines)):
            if lines[index].strip() == str(page_number):
                markers[page_number] = index
                search_start = index + 1
                break
    return markers if len(markers) == page_count else {}


def _clean_linear_legal(
    text: str,
    metadata: dict,
    page_count: int,
) -> str:
    lines = [unicodedata.normalize("NFC", line).strip() for line in text.splitlines()]
    page_markers = _sequential_page_markers(lines, page_count)
    remove_indices = set(page_markers.values())

    contents_index = next(
        (index for index, line in enumerate(lines) if line in {"MỤC LỤC", "NỘI DUNG"}),
        None,
    )
    contents_end = None
    if contents_index is not None:
        later_markers = [index for index in remove_indices if index > contents_index]
        contents_end = min(later_markers) if later_markers else None

    cleaned_lines = []
    for index, line in enumerate(lines):
        if index in remove_indices or line in metadata["title_lines"]:
            continue
        if contents_index is not None and contents_end is not None:
            if contents_index <= index <= contents_end:
                continue
        cleaned_lines.append(line)
    return _format_legal_content(cleaned_lines, metadata["title"])


def _merge_bold_fragments(line: str) -> str:
    pattern = re.compile(r"(\w+)\*\*\*\*(\w+)")

    def merge(match: re.Match) -> str:
        left, right = match.groups()
        separator = "" if min(len(left), len(right)) == 1 else " "
        return f"{left}{separator}{right}"

    return pattern.sub(merge, line).replace("****", " ")


def _clean_news_content(markdown: str, title: str) -> str:
    lines = unicodedata.normalize("NFC", markdown).replace("\r\n", "\n").splitlines()
    first_heading = next(
        (index for index, line in enumerate(lines) if line.lstrip().startswith("#")),
        len(lines),
    )
    lines = lines[first_heading + 1 :]
    output = [f"# {title}", ""]
    blank_pending = False
    table_headers: list[str] | None = None

    for raw_line in lines:
        line = _merge_bold_fragments(raw_line.rstrip()).strip()
        if not line or line == "Notifications":
            blank_pending = bool(output and output[-1])
            continue

        if _is_table_separator(line) or line == "|":
            continue

        heading_match = re.match(r"^(#{1,6})\s*(.+)$", line)
        if heading_match:
            table_headers = None
            marker, heading_text = heading_match.groups()
            heading_text = heading_text.replace("**", "").strip()
            line = f"{marker} {heading_text}"
        elif line.startswith("|"):
            cells = _table_cells(line)
            if not any(cells):
                continue
            if all(cell.startswith("**") and cell.endswith("**") for cell in cells if cell):
                table_headers = [cell.strip("*_ ") for cell in cells]
                continue
            if table_headers:
                record_name = table_headers[0].strip("# ") or "Record"
                output.extend(["", f"#### {record_name}: {cells[0]}"])
                for header, value in zip(table_headers[1:], cells[1:]):
                    if value:
                        output.append(f"- **{header}:** {value}")
                blank_pending = False
                continue
            line = "- " + " | ".join(cells)
        else:
            line = re.sub(r"^\s*(?:[*+-]\s+)+", "- ", line)

        if blank_pending and output[-1]:
            output.append("")
        output.append(line)
        blank_pending = False

    return "\n".join(output).strip()


def convert_legal_docs() -> None:
    """Convert legal PDF/DOCX files to normalized Markdown."""
    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    output_dir.mkdir(parents=True, exist_ok=True)
    converter = MarkItDown(enable_plugins=False)

    source_paths = sorted(
        path
        for path in legal_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".pdf", ".doc", ".docx"}
    )
    for source_path in source_paths:
        metadata = LEGAL_METADATA.get(source_path.name)
        if metadata is None:
            title = " ".join(source_path.stem.replace("_", " ").replace("-", " ").split())
            metadata = {
                "title": title,
                "document_code": None,
                "issued_date": None,
                "title_lines": set(),
            }

        if source_path.name == "VU_HT02.VN_Quy-che-dao-tao-Trinh-do-Thac-sy_20.12.2022.pdf":
            extracted_content = _extract_pdf(source_path, metadata)
        else:
            result = converter.convert(source_path)
            extracted_content = _clean_linear_legal(
                str(result.text_content or ""),
                metadata,
                len(PdfReader(source_path).pages) if source_path.suffix.lower() == ".pdf" else 0,
            )

        content = _front_matter(
            title=metadata["title"],
            source=source_path.name,
            doc_type="legal",
            url=None,
            document_code=metadata["document_code"],
            issued_date=metadata["issued_date"],
        ) + extracted_content
        output_path = output_dir / f"{source_path.stem}.md"
        _write_markdown(output_path, content)
        print(f"Converted: {source_path.name} -> {output_path.name}")


def convert_news_articles() -> None:
    """Convert crawled article JSON files to normalized Markdown."""
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)
    required_fields = {"url", "title", "date_crawled", "content_markdown"}

    for source_path in sorted(news_dir.glob("*.json")):
        data = json.loads(source_path.read_text(encoding="utf-8"))
        missing_fields = required_fields - data.keys()
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"{source_path.name} is missing fields: {missing}")
        if any(not str(data[field]).strip() for field in required_fields):
            raise ValueError(f"{source_path.name} contains empty required fields")

        title = re.sub(r"\s*-\s*VinUni Policy\s*$", "", str(data["title"])).strip()
        quality_status = (
            "needs_source_review"
            if source_path.name in {"article_01.json", "article_03.json"}
            else "cleaned"
        )
        content = _front_matter(
            title=title,
            source=source_path.name,
            doc_type="news",
            url=str(data["url"]).strip(),
            date_crawled=str(data["date_crawled"]).strip(),
            content_kind="policy",
            quality_status=quality_status,
        )
        content += _clean_news_content(str(data["content_markdown"]), title)
        output_path = output_dir / f"{source_path.stem}.md"
        _write_markdown(output_path, content)
        print(f"Converted: {source_path.name} -> {output_path.name}")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()