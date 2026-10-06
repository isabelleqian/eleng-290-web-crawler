"""Fetch one queued URL and describe what came back.

HTTP status, redirects, content type, and PDF bytes come from a direct
request. Crawl4AI is only asked to render HTML. This module does not follow
links, solve challenges, or fill in missing article text.
"""

from __future__ import annotations

import asyncio
import io
import re
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

USER_AGENT = "ELENG290-NewsArchive/0.2 (local research crawler)"
MAX_BYTES = 40 * 1024 * 1024
MAX_RETRY_AFTER = 60.0
SHORT_TEXT = 400
RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

_DATE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?$"
)
_BLOCK_PHRASES = (
    "verify you are human",
    "please verify you are a human",
    "checking your browser",
    "enable javascript and cookies",
    "are you a robot",
    "bot detection",
    "unusual traffic from your computer",
    "pardon our interruption",
    "access to this page has been denied",
    "you don't have permission to access this content",
    "you do not have permission to access this content",
)
_PAYWALL_PHRASES = (
    "subscribe to continue",
    "subscribe to read",
    "subscription required",
    "subscribers only",
    "sign in to continue",
    "sign in to read the full",
    "this content is reserved for subscribers",
)
_PAYWALL_MARKUP = (
    'data-paywall',
    'class="paywall"',
    "class='paywall'",
    'id="paywall"',
    "id='paywall'",
)
_DATE_ATTRIBUTES = {
    "article:published_time",
    "og:published_time",
    "citation_publication_date",
    "parsely-pub-date",
    "datepublished",
}


@dataclass
class QualityFlag:
    code: str
    signal: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "signal": self.signal}


@dataclass
class PdfText:
    text: str | None
    title: str | None
    error: str | None = None


@dataclass
class RenderResult:
    html: str | None = None
    markdown: str | None = None
    page_pdf: bytes | None = None
    page_pdf_error: str | None = None
    error: str | None = None
    final_url: str | None = None
    version: str | None = None


@dataclass
class FetchResult:
    requested_url: str
    final_url: str | None
    http_status: int | None
    content_type: str | None
    outcome: str
    observed_title: str | None
    publication_date: str | None
    html: str | None
    markdown: str | None
    original_pdf: bytes | None
    page_pdf: bytes | None
    body: bytes | None
    source_kind: str
    quality_flags: list[QualityFlag] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pdf_link_candidates: list[str] = field(default_factory=list)
    renderer: str = "http"
    renderer_version: str | None = None
    renderer_final_url: str | None = None
    retries_used: int = 0

    @property
    def error_text(self) -> str | None:
        if not self.errors:
            return None
        return "\n".join(self.errors)


@dataclass
class _HttpResult:
    requested_url: str
    final_url: str | None
    status: int | None
    content_type: str | None
    headers: dict[str, str]
    body: bytes
    error: str | None = None
    hint: str | None = None
    truncated: bool = False


class HostGate:
    """Keep a modest gap between requests to the same host and port."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self._locks: dict[str, asyncio.Lock] = {}
        self._next_at: dict[str, float] = {}
        self._guard = asyncio.Lock()

    async def wait(self, key: str) -> None:
        async with self._guard:
            lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            ready = self._next_at.get(key, now)
            if ready > now:
                await asyncio.sleep(ready - now)
            self._next_at[key] = time.monotonic() + self.delay


@dataclass
class _RobotsRecord:
    parser: object | None = None
    failure: str | None = None
    failure_kind: str | None = None


class RobotsCache:
    """Remember one robots.txt per origin, then decide each URL on its own."""

    def __init__(self) -> None:
        self._records: dict[str, _RobotsRecord] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def check(
        self,
        url: str,
        *,
        timeout: float,
        gate: HostGate,
    ) -> tuple[bool, QualityFlag | None]:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        async with self._guard:
            lock = self._locks.setdefault(origin, asyncio.Lock())
        async with lock:
            record = self._records.get(origin)
            if record is None:
                robots_url = f"{origin}/robots.txt"
                await gate.wait(parts.netloc.lower())
                response = await asyncio.to_thread(
                    _request,
                    robots_url,
                    min(timeout, 10.0),
                )
                record = _robots_record(response)
                self._records[origin] = record
        return _robots_decision(record, url)


def extract_pdf_text(data: bytes) -> PdfText:
    """Read text from PDF bytes with pypdf. Missing text is left empty."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return PdfText(
            text=None,
            title=None,
            error="pypdf is not installed, so the PDF text was not extracted",
        )
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        return PdfText(text=None, title=None, error=f"PDF text extraction failed: {exc}")
    title = None
    metadata = reader.metadata
    if metadata is not None and getattr(metadata, "title", None):
        title = str(metadata.title).strip() or None
    parts: list[str] = []
    try:
        for page in reader.pages:
            parts.append(page.extract_text() or "")
    except Exception as exc:
        return PdfText(
            text=None,
            title=title,
            error=f"PDF text extraction failed: {exc}",
        )
    text = "\n".join(parts).strip()
    return PdfText(text=text or None, title=title, error=None)


async def fetch_url(
    url: str,
    *,
    timeout: float,
    retries: int,
    retry_backoff: float,
    save_page_pdf: bool,
    gate: HostGate,
    robots: RobotsCache,
    renderer: object | None,
    pdf_text_extractor: Callable[[bytes], PdfText | str | None] | None,
    http_only: bool,
) -> FetchResult:
    allowed, robots_flag = await robots.check(url, timeout=timeout, gate=gate)
    if not allowed:
        flags = [robots_flag] if robots_flag is not None else []
        if robots_flag is not None and robots_flag.code == "robots_network_error":
            return FetchResult(
                requested_url=url,
                final_url=None,
                http_status=None,
                content_type=None,
                outcome="network_error",
                observed_title=None,
                publication_date=None,
                html=None,
                markdown=None,
                original_pdf=None,
                page_pdf=None,
                body=None,
                source_kind="html",
                quality_flags=flags,
                errors=[robots_flag.signal],
                renderer="none",
            )
        if robots_flag is not None and robots_flag.code == "robots_unreachable":
            robots_error = "robots.txt could not be read, so this URL was not requested"
        else:
            robots_error = "robots.txt disallows this URL for this crawler"
        return FetchResult(
            requested_url=url,
            final_url=None,
            http_status=None,
            content_type=None,
            outcome="blocked",
            observed_title=None,
            publication_date=None,
            html=None,
            markdown=None,
            original_pdf=None,
            page_pdf=None,
            body=None,
            source_kind="html",
            quality_flags=flags,
            errors=[robots_error],
            renderer="none",
        )

    response: _HttpResult | None = None
    retries_used = 0
    stopped_for_retry_after = False
    parts = urlsplit(url)
    host_key = parts.netloc.lower()
    for attempt in range(retries + 1):
        await gate.wait(host_key)
        response = await asyncio.to_thread(_request, url, timeout)
        retryable = response.hint in {"timeout", "network_error"} or (
            response.status in RETRYABLE_STATUSES
        )
        if not retryable or attempt >= retries:
            break
        wait = _retry_after_seconds(response.headers.get("retry-after"))
        if wait is not None and wait > MAX_RETRY_AFTER:
            stopped_for_retry_after = True
            break
        retries_used += 1
        if wait is not None and wait > 0:
            await asyncio.sleep(wait)
        elif retry_backoff > 0:
            await asyncio.sleep(retry_backoff * (2**attempt))

    assert response is not None
    return await _interpret(
        response,
        retries_used=retries_used,
        stopped_for_retry_after=stopped_for_retry_after,
        save_page_pdf=save_page_pdf,
        renderer=renderer,
        pdf_text_extractor=pdf_text_extractor,
        http_only=http_only,
        timeout=timeout,
        robots_flag=robots_flag,
    )


def crawl_status_for(outcome: str) -> str:
    if outcome in {"retrieved", "partial", "paywall", "empty"}:
        return "fetched"
    if outcome == "blocked":
        return "blocked"
    if outcome == "not_found":
        return "not_found"
    return "failed"


def _request(url: str, timeout: float) -> _HttpResult:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/pdf,application/xhtml+xml,text/plain,*/*;q=0.8",
        },
        method="GET",
    )
    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        body, truncated = _read_limited(exc)
        headers = {key.lower(): value for key, value in exc.headers.items()}
        return _HttpResult(
            requested_url=url,
            final_url=exc.geturl(),
            status=exc.code,
            content_type=headers.get("content-type"),
            headers=headers,
            body=body,
            truncated=truncated,
        )
    except TimeoutError as exc:
        return _http_failure(url, "timeout", f"timed out: {exc}")
    except URLError as exc:
        reason = exc.reason
        if isinstance(reason, (TimeoutError, socket.timeout)) or "timed out" in str(reason).lower():
            return _http_failure(url, "timeout", f"timed out: {reason}")
        return _http_failure(url, "network_error", f"network error: {reason}")
    except OSError as exc:
        return _http_failure(url, "network_error", f"network error: {exc}")
    else:
        try:
            body, truncated = _read_limited(response)
            headers = {key.lower(): value for key, value in response.headers.items()}
            return _HttpResult(
                requested_url=url,
                final_url=response.geturl(),
                status=getattr(response, "status", None) or response.getcode(),
                content_type=headers.get("content-type"),
                headers=headers,
                body=body,
                truncated=truncated,
            )
        finally:
            response.close()


def _http_failure(url: str, hint: str, error: str) -> _HttpResult:
    return _HttpResult(
        requested_url=url,
        final_url=None,
        status=None,
        content_type=None,
        headers={},
        body=b"",
        error=error,
        hint=hint,
    )


def _read_limited(response) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(64 * 1024)
        if not chunk:
            return b"".join(chunks), False
        total += len(chunk)
        if total > MAX_BYTES:
            chunks.append(chunk[: len(chunk) - (total - MAX_BYTES)])
            return b"".join(chunks), True
        chunks.append(chunk)


def _retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _robots_record(response: _HttpResult) -> _RobotsRecord:
    if response.status == 404:
        return _RobotsRecord()
    if response.hint == "network_error":
        return _RobotsRecord(
            failure=response.error or "Could not read robots.txt",
            failure_kind="network_error",
        )
    if response.hint is not None or response.status != 200:
        detail = response.error or f"HTTP {response.status}"
        return _RobotsRecord(failure=detail, failure_kind="unreachable")
    from urllib.robotparser import RobotFileParser

    parser = RobotFileParser()
    parser.parse(response.body.decode("utf-8", "replace").splitlines())
    return _RobotsRecord(parser=parser)


def _robots_decision(
    record: _RobotsRecord,
    target_url: str,
) -> tuple[bool, QualityFlag | None]:
    if record.failure_kind == "network_error":
        return False, QualityFlag(
            "robots_network_error",
            record.failure or f"Could not read robots.txt for {target_url}",
        )
    if record.failure is not None:
        return False, QualityFlag(
            "robots_unreachable",
            f"Could not read robots.txt ({record.failure}). {target_url} was not requested.",
        )
    parser = record.parser
    if parser is None or parser.can_fetch(USER_AGENT, target_url):
        return True, None
    return False, QualityFlag(
        "robots_disallow",
        f"robots.txt disallows {target_url} for {USER_AGENT}",
    )


async def _interpret(
    response: _HttpResult,
    *,
    retries_used: int,
    stopped_for_retry_after: bool,
    save_page_pdf: bool,
    renderer: object | None,
    pdf_text_extractor: Callable[[bytes], PdfText | str | None] | None,
    http_only: bool,
    timeout: float,
    robots_flag: QualityFlag | None,
) -> FetchResult:
    flags: list[QualityFlag] = []
    errors: list[str] = []
    if robots_flag is not None:
        flags.append(robots_flag)
    if response.truncated:
        flags.append(QualityFlag("response_truncated", f"Response exceeded {MAX_BYTES} bytes"))
    if stopped_for_retry_after:
        header = response.headers.get("retry-after")
        flags.append(
            QualityFlag(
                "retry_after_too_long",
                f"Retry-After was {header}, above the {MAX_RETRY_AFTER:.0f}s wait cap. "
                "No further request was sent.",
            )
        )
    if response.error:
        errors.append(response.error)

    if response.hint in {"timeout", "network_error"}:
        return _result(
            response,
            outcome=response.hint or "network_error",
            flags=flags,
            errors=errors,
            retries_used=retries_used,
            source_kind="other",
        )

    kind = _source_kind(response)
    if kind == "original_pdf":
        return _interpret_pdf(
            response,
            flags=flags,
            errors=errors,
            retries_used=retries_used,
            extractor=pdf_text_extractor,
        )

    html = None
    text = None
    if kind in {"html", "text"} and response.body:
        html = _decode_text(response.body, response.content_type) if kind == "html" else None
        decoded = _decode_text(response.body, response.content_type)
        text = html_to_text(decoded) if kind == "html" else decoded.strip()
        if kind == "text":
            html = None

    page_pdf = None
    page_pdf_error = None
    renderer_name = "http" if http_only or renderer is None else "crawl4ai"
    renderer_version = None
    renderer_final = None
    saved_html = html
    saved_text = text

    should_render = (
        renderer is not None
        and kind == "html"
        and response.status is not None
        and 200 <= response.status < 300
    )
    if should_render:
        rendered = await _call_renderer(
            renderer,
            response.final_url or response.requested_url,
            timeout=timeout,
            save_page_pdf=save_page_pdf,
        )
        renderer_version = rendered.version
        renderer_final = rendered.final_url
        if rendered.html:
            saved_html = rendered.html
        if rendered.markdown and rendered.markdown.strip():
            saved_text = rendered.markdown.strip()
            renderer_name = "crawl4ai"
        elif rendered.error:
            flags.append(QualityFlag("renderer_failed", rendered.error))
            errors.append(rendered.error)
            renderer_name = "http_fallback"
        else:
            flags.append(
                QualityFlag(
                    "renderer_empty",
                    "Crawl4AI returned no markdown. The HTTP response text was kept.",
                )
            )
            renderer_name = "http_fallback"
        if save_page_pdf:
            page_pdf = rendered.page_pdf
            if not page_pdf:
                page_pdf_error = rendered.page_pdf_error or (
                    "Crawl4AI did not return a webpage PDF snapshot"
                )
    elif save_page_pdf and kind == "html" and response.status and 200 <= response.status < 300:
        page_pdf_error = "Webpage PDF snapshots require Crawl4AI"

    if page_pdf_error:
        flags.append(QualityFlag("page_pdf_failed", page_pdf_error))

    title, publication_date, date_flags, pdf_links = _page_metadata(
        saved_html,
        response.final_url or response.requested_url,
    )
    flags.extend(date_flags)
    outcome, flags = _assess(
        html=saved_html,
        text=saved_text,
        status=response.status,
        source_kind=kind if kind != "text" else "html",
        flags=flags,
    )
    if response.status is not None and response.status >= 500:
        outcome = "network_error"
        flags.append(QualityFlag("http_5xx", f"HTTP {response.status}"))
    if stopped_for_retry_after and response.status == 429:
        outcome = "blocked"

    body = None
    original_pdf = None
    if kind == "other":
        body = response.body or None
        if body and outcome == "retrieved":
            flags.append(
                QualityFlag(
                    "unrecognized_content",
                    f"Content type {response.content_type or 'unknown'} is not HTML or PDF",
                )
            )
            flags.append(QualityFlag("needs_review", "Unrecognized content was saved for review"))

    return _result(
        response,
        outcome=outcome,
        flags=flags,
        errors=errors,
        retries_used=retries_used,
        source_kind="html" if kind == "text" else kind,
        html=saved_html,
        markdown=saved_text,
        title=title,
        publication_date=publication_date,
        original_pdf=original_pdf,
        page_pdf=page_pdf,
        body=body,
        pdf_links=pdf_links,
        renderer=renderer_name,
        renderer_version=renderer_version,
        renderer_final_url=renderer_final,
    )


def _interpret_pdf(
    response: _HttpResult,
    *,
    flags: list[QualityFlag],
    errors: list[str],
    retries_used: int,
    extractor: Callable[[bytes], PdfText | str | None] | None,
) -> FetchResult:
    if _media_type(response.content_type) not in {None, "application/pdf", "application/octet-stream"}:
        if not response.body.lstrip().startswith(b"%PDF-"):
            flags.append(
                QualityFlag(
                    "content_type_mismatch",
                    f"Content type was {response.content_type}, and the body was treated as a PDF",
                )
            )
    elif response.content_type and "pdf" not in response.content_type.lower():
        flags.append(
            QualityFlag(
                "content_type_mismatch",
                f"Body starts with %PDF but content type was {response.content_type}",
            )
        )
    extracted = _coerce_pdf(
        extract_pdf_text(response.body) if extractor is None else extractor(response.body)
    )
    if extracted.error:
        errors.append(extracted.error)
        if "not installed" in extracted.error:
            flags.append(QualityFlag("pdf_text_unavailable", extracted.error))
        else:
            flags.append(QualityFlag("needs_ocr", extracted.error))
        flags.append(QualityFlag("needs_review", "The original PDF was saved without usable text"))
    elif not extracted.text:
        flags.append(
            QualityFlag(
                "needs_ocr",
                "No text could be extracted from the PDF. The original bytes were saved.",
            )
        )
        flags.append(QualityFlag("needs_review", "The original PDF needs review or OCR"))
    outcome = "retrieved" if extracted.text else "empty"
    if response.status in {401, 403, 429}:
        outcome = "blocked"
    elif response.status in {404, 410}:
        outcome = "not_found"
    elif response.status is not None and response.status >= 500:
        outcome = "network_error"
        flags.append(QualityFlag("http_5xx", f"HTTP {response.status}"))
    title = extracted.title
    return _result(
        response,
        outcome=outcome,
        flags=flags,
        errors=errors,
        retries_used=retries_used,
        source_kind="original_pdf",
        markdown=extracted.text,
        title=title,
        original_pdf=response.body,
    )


def _result(
    response: _HttpResult,
    *,
    outcome: str,
    flags: list[QualityFlag],
    errors: list[str],
    retries_used: int,
    source_kind: str,
    html: str | None = None,
    markdown: str | None = None,
    title: str | None = None,
    publication_date: str | None = None,
    original_pdf: bytes | None = None,
    page_pdf: bytes | None = None,
    body: bytes | None = None,
    pdf_links: list[str] | None = None,
    renderer: str = "http",
    renderer_version: str | None = None,
    renderer_final_url: str | None = None,
) -> FetchResult:
    if response.status in {401, 403}:
        outcome = "blocked"
        flags.append(QualityFlag("http_status", f"HTTP {response.status}"))
    elif response.status in {404, 410}:
        outcome = "not_found"
        flags.append(QualityFlag("http_status", f"HTTP {response.status}"))
    elif response.status == 429 and outcome != "network_error":
        outcome = "blocked"
        flags.append(QualityFlag("http_status", "HTTP 429"))
    unique_errors: list[str] = []
    for item in errors:
        if item and item not in unique_errors:
            unique_errors.append(item)
    if (
        response.status is not None
        and outcome in {"not_found", "blocked", "network_error"}
    ):
        message = f"HTTP {response.status}"
        if message not in unique_errors:
            unique_errors.append(message)
    return FetchResult(
        requested_url=response.requested_url,
        final_url=response.final_url,
        http_status=response.status,
        content_type=response.content_type,
        outcome=outcome,
        observed_title=title,
        publication_date=publication_date,
        html=html,
        markdown=markdown,
        original_pdf=original_pdf,
        page_pdf=page_pdf,
        body=body,
        source_kind=source_kind,
        quality_flags=_unique_flags(flags),
        errors=unique_errors,
        pdf_link_candidates=pdf_links or [],
        renderer=renderer,
        renderer_version=renderer_version,
        renderer_final_url=renderer_final_url,
        retries_used=retries_used,
    )


def _source_kind(response: _HttpResult) -> str:
    body = response.body
    media = _media_type(response.content_type)
    if body.lstrip().startswith(b"%PDF-"):
        return "original_pdf"
    if media == "application/pdf" and not _looks_like_html(body):
        return "original_pdf"
    if media in {"text/html", "application/xhtml+xml"} or _looks_like_html(body):
        return "html"
    if media is not None and (media.startswith("text/") or media in {"application/json", "application/xml"}):
        return "text"
    return "other"


def _looks_like_html(body: bytes) -> bool:
    sample = body.lstrip()[:300].lower()
    return sample.startswith((b"<!doctype html", b"<html", b"<head", b"<body"))


def _media_type(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def _decode_text(body: bytes, content_type: str | None) -> str:
    charset = None
    if content_type and "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip(" \"'")
    if not charset:
        head = body[:2048].decode("ascii", "ignore")
        match = re.search(r"charset=['\"]?\s*([A-Za-z0-9._-]+)", head, re.IGNORECASE)
        if match:
            charset = match.group(1)
    try:
        return body.decode(charset or "utf-8")
    except (LookupError, UnicodeDecodeError):
        return body.decode("utf-8", "replace")


def html_to_text(html: str) -> str:
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    return parser.text()


def _page_metadata(
    html: str | None,
    base_url: str,
) -> tuple[str | None, str | None, list[QualityFlag], list[str]]:
    if not html:
        return None, None, [], []
    parser = _PageParser()
    parser.feed(html)
    parser.close()
    title = _clean_title(parser.title)
    if title is None:
        title = _clean_title(parser.meta_content("og:title", "property") or parser.meta_content("og:title", "name"))
    dates = parser.publication_dates()
    flags: list[QualityFlag] = []
    publication = None
    distinct = list(dict.fromkeys(item[0] for item in dates))
    if len(distinct) == 1:
        publication = dates[0][1]
    elif len(distinct) > 1:
        shown = ", ".join(distinct)
        flags.append(
            QualityFlag(
                "ambiguous_publication_date",
                f"Page metadata contained more than one publication date: {shown}",
            )
        )
    links: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        absolute = urljoin(base_url, href)
        path = urlsplit(absolute).path.lower()
        if path.endswith(".pdf") and absolute not in seen:
            seen.add(absolute)
            links.append(absolute)
    return title, publication, flags, links


def _assess(
    *,
    html: str | None,
    text: str | None,
    status: int | None,
    source_kind: str,
    flags: list[QualityFlag],
) -> tuple[str, list[QualityFlag]]:
    visible = re.sub(r"\s+", " ", text or "").strip()
    visible_haystack = visible.lower()
    block = _first_phrase(visible_haystack, _BLOCK_PHRASES)
    paywall = _first_phrase(visible_haystack, _PAYWALL_PHRASES)
    if paywall is None and html:
        paywall = _first_phrase(html.lower(), _PAYWALL_MARKUP)
    if status in {401, 403, 429}:
        outcome = "blocked"
    elif status in {404, 410}:
        outcome = "not_found"
    elif block is not None:
        outcome = "blocked"
        flags.append(QualityFlag("block_phrase", f"Matched access-barrier text: {block}"))
    elif status is not None and status >= 500:
        outcome = "network_error"
    elif source_kind == "original_pdf":
        outcome = "retrieved"
    elif paywall is not None:
        outcome = "paywall"
        flags.append(QualityFlag("paywall_phrase", f"Matched paywall text: {paywall}"))
        flags.append(QualityFlag("needs_review", "Paywall language was present in the captured page"))
    elif not visible:
        outcome = "empty"
        if html and len(html) > 200:
            flags.append(
                QualityFlag(
                    "uncertain_extraction",
                    "The HTML response had no visible text. It may be a script shell.",
                )
            )
        else:
            flags.append(QualityFlag("empty_body", "The response had no visible text"))
        flags.append(QualityFlag("needs_review", "No article text was extracted"))
    elif status == 206 or len(visible) < SHORT_TEXT:
        outcome = "partial"
        signal = (
            f"HTTP 206 and extracted text is {len(visible)} characters"
            if status == 206
            else f"Extracted text is {len(visible)} characters, below {SHORT_TEXT}"
        )
        flags.append(QualityFlag("short_text", signal))
        flags.append(QualityFlag("needs_review", "The capture may be only part of the article"))
    else:
        outcome = "retrieved"
    return outcome, flags


def _first_phrase(haystack: str, phrases: tuple[str, ...]) -> str | None:
    for phrase in phrases:
        if phrase in haystack:
            return phrase
    return None


def _clean_title(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", value).strip()
    return text or None


def _unique_flags(flags: list[QualityFlag]) -> list[QualityFlag]:
    seen: set[tuple[str, str]] = set()
    unique: list[QualityFlag] = []
    for flag in flags:
        key = (flag.code, flag.signal)
        if key not in seen:
            seen.add(key)
            unique.append(flag)
    return unique


def _coerce_pdf(value: PdfText | str | None) -> PdfText:
    if isinstance(value, PdfText):
        return value
    if isinstance(value, str):
        text = value.strip() or None
        return PdfText(text=text, title=None)
    return PdfText(text=None, title=None)


async def _call_renderer(
    renderer: object,
    url: str,
    *,
    timeout: float,
    save_page_pdf: bool,
) -> RenderResult:
    try:
        if hasattr(renderer, "render"):
            result = await renderer.render(url, timeout=timeout, save_page_pdf=save_page_pdf)
        else:
            result = await renderer(url, timeout=timeout, save_page_pdf=save_page_pdf)
    except Exception as exc:
        return RenderResult(error=f"renderer failed: {exc}")
    if isinstance(result, RenderResult):
        return result
    return RenderResult(error="renderer returned an unexpected value")


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._title: list[str] = []
        self._in_title = False
        self._skip = 0
        self._in_json = False
        self._json: list[str] = []
        self._text: list[str] = []
        self.metas: list[dict[str, str]] = []
        self.hrefs: list[str] = []
        self.json_ld: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            self.metas.append(attr)
        if tag == "a" and attr.get("href"):
            self.hrefs.append(attr["href"])
        if tag in {"p", "div", "h1", "h2", "h3", "li", "br", "tr", "section", "article"}:
            self._text.append("\n")
        if tag in {"script", "style", "noscript"}:
            if tag == "script" and "ld+json" in attr.get("type", "").lower():
                self._in_json = True
                self._json = []
            else:
                self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_json:
            self.json_ld.append("".join(self._json))
            self._in_json = False
            return
        if tag in {"script", "style", "noscript"} and self._skip:
            self._skip -= 1
        if tag in {"p", "div", "h1", "h2", "h3", "li", "tr", "section", "article"}:
            self._text.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title.append(data)
        elif self._in_json:
            self._json.append(data)
        elif self._skip == 0:
            self._text.append(data)

    @property
    def title(self) -> str:
        return "".join(self._title)

    def text(self) -> str:
        raw = "".join(self._text)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines()]
        compact = "\n".join(line for line in lines if line)
        return compact.strip()

    def meta_content(self, name: str, attribute: str) -> str | None:
        wanted = name.lower()
        for meta in self.metas:
            if meta.get(attribute, "").lower() == wanted and meta.get("content", "").strip():
                return meta["content"]
        return None

    def publication_dates(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for meta in self.metas:
            key = (meta.get("property") or meta.get("name") or meta.get("itemprop") or "").lower()
            content = meta.get("content", "").strip()
            if key in _DATE_ATTRIBUTES:
                day = _reliable_date(content)
                if day is not None:
                    found.append((day, content))
        for blob in self.json_ld:
            for content in re.findall(r'"datePublished"\s*:\s*"([^"]+)"', blob):
                day = _reliable_date(content.strip())
                if day is not None:
                    found.append((day, content.strip()))
        return found


def _reliable_date(value: str) -> str | None:
    match = _DATE.match(value.strip())
    if match is None:
        return None
    return match.group(1)
