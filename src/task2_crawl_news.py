"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://policy.vinuni.edu.vn/academic-affairs/english-language-requirements-for-undergraduate-admissions/",
    "https://policy.vinuni.edu.vn/all-policies/english-language-proficiency-requirements-for-graduation-at-vinuniversity/",
    "https://policy.vinuni.edu.vn/all-policies/guideline-for-program-change-request/",
    "https://policy.vinuni.edu.vn/all-policies/student-grade-appeal-procedure/",
    "https://policy.vinuni.edu.vn/all-policies/procedure-for-requesting-a-leave-of-absence-withdrawal-and-return-from-a-leave-of-absence/",
]


async def crawl_article(url: str) -> dict:
    """Crawl one public VinUni policy page and return normalized content."""
    browser_config = BrowserConfig(headless=True, verbose=False)
    run_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "footer", "script", "style", "form"],
        remove_overlay_elements=True,
        page_timeout=60_000,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)

    if not result.success:
        raise RuntimeError(result.error_message or "Crawler returned an unsuccessful result")

    markdown_result = result.markdown
    content = getattr(markdown_result, "raw_markdown", markdown_result)
    content = str(content or "").strip()
    if len(content) < 200:
        raise ValueError("Crawled Markdown is empty or too short")

    metadata = result.metadata or {}
    title = str(metadata.get("title") or url.rstrip("/").rsplit("/", 1)[-1]).strip()
    return {
        "url": url,
        "title": title,
        "date_crawled": datetime.now(timezone.utc).isoformat(),
        "content_markdown": content,
    }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())