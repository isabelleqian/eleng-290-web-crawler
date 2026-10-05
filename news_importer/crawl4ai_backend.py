"""Crawl4AI adapter for rendering one HTML page.

Written against Crawl4AI 0.9.4. The crawler is not imported until a real
render starts, so the importer and the tests run without Crawl4AI installed.
Deep crawling, stealth, and overlay removal stay off.
"""

from __future__ import annotations

from pathlib import Path

from news_importer.retrieve import USER_AGENT, RenderResult

SETUP_HINT = (
    "Install Crawl4AI for this Python with "
    "python3 -m pip install 'crawl4ai==0.9.4' pypdf. "
    "If the browser is missing, run python3 -m playwright install chromium "
    "and then crawl4ai-doctor."
)


def build_run_config(*, timeout: float, save_page_pdf: bool):
    from crawl4ai import CacheMode, CrawlerRunConfig

    return CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=max(1, int(timeout * 1000)),
        pdf=save_page_pdf,
        check_robots_txt=True,
        word_count_threshold=1,
        verbose=False,
        deep_crawl_strategy=None,
        magic=False,
        simulate_user=False,
        override_navigator=False,
        remove_overlay_elements=False,
        max_retries=0,
    )


class Crawl4AIRenderer:
    def __init__(self) -> None:
        self._crawler = None
        self.version: str | None = None

    async def start(self) -> None:
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig
            from crawl4ai.__version__ import __version__ as crawl4ai_version
        except ImportError as exc:
            raise RuntimeError(
                "Crawl4AI is not installed for this Python. " + SETUP_HINT
            ) from exc
        self.version = crawl4ai_version if isinstance(crawl4ai_version, str) else None
        self._crawler = AsyncWebCrawler(
            config=BrowserConfig(
                headless=True,
                verbose=False,
                user_agent=USER_AGENT,
            )
        )
        try:
            await self._crawler.start()
        except Exception as exc:
            self._crawler = None
            raise RuntimeError(
                f"Crawl4AI {self.version or ''} could not start the browser. {SETUP_HINT} "
                f"Detail: {exc}"
            ) from exc

    async def close(self) -> None:
        crawler = self._crawler
        self._crawler = None
        if crawler is not None:
            await crawler.close()

    async def render(
        self,
        url: str,
        *,
        timeout: float,
        save_page_pdf: bool,
    ) -> RenderResult:
        if self._crawler is None:
            return RenderResult(error="Crawl4AI browser is not started", version=self.version)
        config = build_run_config(timeout=timeout, save_page_pdf=save_page_pdf)
        try:
            result = await self._crawler.arun(url=url, config=config)
        except Exception as exc:
            return RenderResult(error=f"Crawl4AI error: {exc}", version=self.version)
        markdown = _markdown_text(result)
        html = getattr(result, "html", None) or getattr(result, "cleaned_html", None)
        error = None
        if not getattr(result, "success", False):
            error = getattr(result, "error_message", None) or "Crawl4AI reported failure"
        page_pdf = _pdf_bytes(getattr(result, "pdf", None)) if save_page_pdf else None
        page_pdf_error = None
        if save_page_pdf and not page_pdf:
            page_pdf_error = "Crawl4AI did not return a webpage PDF snapshot"
        final_url = getattr(result, "redirected_url", None) or getattr(result, "url", None)
        return RenderResult(
            html=html if isinstance(html, str) else None,
            markdown=markdown,
            page_pdf=page_pdf,
            page_pdf_error=page_pdf_error,
            error=error,
            final_url=final_url if isinstance(final_url, str) else None,
            version=self.version,
        )


def _markdown_text(result: object) -> str | None:
    markdown = getattr(result, "markdown", None)
    if markdown is None:
        return None
    raw = getattr(markdown, "raw_markdown", None)
    text = raw if isinstance(raw, str) else str(markdown)
    if not text or text == "None":
        return None
    stripped = text.strip()
    return stripped or None


def _pdf_bytes(value: object) -> bytes | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value or None
    if isinstance(value, bytearray):
        return bytes(value) or None
    if isinstance(value, str) and value:
        path = Path(value)
        if path.is_file():
            data = path.read_bytes()
            return data or None
    return None
