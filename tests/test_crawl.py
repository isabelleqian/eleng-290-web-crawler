"""Retrieval tests against a local HTTP server. No live news sites."""

from __future__ import annotations

import csv
import importlib.util
import json
import sqlite3
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_importer.archive import source_id_for  # noqa: E402
from news_importer.cli import build_parser  # noqa: E402
from news_importer.crawl import CrawlOptions, run_crawl  # noqa: E402
from news_importer.db import connect, ensure_schema  # noqa: E402
from news_importer.importer import import_path  # noqa: E402
from news_importer.retrieve import PdfText, RenderResult, html_to_text  # noqa: E402

PARAGRAPHS = [
    "The transportation department described a pilot that limits cut-through trips on a residential street near the waterfront.",
    "Residents had reported queues of app-routed drivers on weekday mornings, and the board asked staff to watch the next month.",
    "The notice explains the hours, the exceptions for local access, and the date the board will review the results.",
    "It quotes the staff recommendation and a neighborhood letter without adding a summary from this archive.",
    "The bakery on the corner opens at seven.",
    "A separate sentence about the library clock is kept even though it is outside the research topic.",
]


def article_html(
    *,
    title: str = "Boston street pilot",
    date: str | None = "2024-06-15T13:00:00Z",
    extra: str = "",
    link: bool = True,
) -> str:
    body = "\n".join(f"<p>{paragraph}</p>" for paragraph in PARAGRAPHS)
    date_meta = ""
    if date:
        date_meta = f'<meta property="article:published_time" content="{date}">'
    pdf_link = ""
    if link:
        pdf_link = '<p><a href="/files/staff-report.pdf">Staff report</a></p>'
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{title}</title>{date_meta}</head><body><article>"
        f"<h1>{title}</h1>{body}{extra}{pdf_link}"
        "</article></body></html>"
    )


LONG_HTML = article_html()
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        self.server.hits.append(path)
        route = self.server.routes.get(path)
        if route is None:
            self.send_error(404)
            return
        if callable(route):
            route = route()
        status, headers, body = route
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            try:
                self.wfile.write(body)
            except BrokenPipeError:
                return

    def log_message(self, format: str, *args: object) -> None:
        return


class _Server(ThreadingHTTPServer):
    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.routes: dict = {}
        self.hits: list[str] = []


class CrawlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = _Server()
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.httpd.server_address
        cls.base = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self) -> None:
        self.httpd.routes = {}
        self.httpd.hits = []
        self.temporary = TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = self.root / "news.sqlite"
        self.archive = self.root / "archive"
        self.files = 0

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_html_archive_keeps_general_text_and_imported_fields(self) -> None:
        self.route("/story", 200, "text/html; charset=utf-8", LONG_HTML.encode())
        self.import_rows(
            [
                {
                    "url": f"{self.base}/story",
                    "title": "Search headline",
                    "snippet": "Search snippet about the pilot",
                    "study_area": "boston",
                }
            ]
        )
        summary = self.crawl()
        self.assertEqual(summary.results[0].outcome, "retrieved")
        self.assertEqual(summary.results[0].crawl_status, "fetched")
        metadata, folder = self.only_attempt()
        relative = folder.relative_to(self.archive).parts
        self.assertEqual(relative[0], "boston")
        self.assertEqual(relative[1], "127.0.0.1")
        self.assertTrue(relative[2].startswith("story--src_"))
        self.assertEqual(relative[3], "attempt-001")
        self.assertEqual(metadata["observed_title"], "Boston street pilot")
        self.assertEqual(metadata["publication_date"], "2024-06-15T13:00:00Z")
        self.assertEqual(metadata["source_kind"], "html")
        self.assertIsNone(metadata["artifacts"]["original_pdf"])
        self.assertIsNone(metadata["artifacts"]["page_pdf"])
        text = (folder / "content.md").read_text(encoding="utf-8")
        self.assertIn("The bakery on the corner opens at seven.", text)
        self.assertIn("library clock", text)
        self.assertGreaterEqual(len(html_to_text(LONG_HTML)), 400)
        self.assertEqual(
            metadata["pdf_link_candidates"],
            [f"{self.base}/files/staff-report.pdf"],
        )
        self.assertEqual(self.hit_count("/files/staff-report.pdf"), 0)
        self.assertEqual(metadata["discovery_records"][0]["imported_title"], "Search headline")
        self.assertEqual(
            metadata["discovery_records"][0]["imported_snippet"],
            "Search snippet about the pilot",
        )
        row = self.one_discovery()
        self.assertEqual(row["title"], "Search headline")
        self.assertEqual(row["snippet"], "Search snippet about the pilot")
        self.assertEqual(row["last_outcome"], "retrieved")
        self.assertTrue((folder / "raw.html").is_file())
        self.assertTrue((folder / "metadata.json").is_file())

    def test_duplicate_discoveries_share_one_source_and_reuse_it(self) -> None:
        self.route("/story", 200, "text/html; charset=utf-8", LONG_HTML.encode())
        url = f"{self.base}/story"
        self.import_rows(
            [
                {"url": url, "title": "First headline", "study_area": "boston"},
                {"url": url, "title": "Second headline", "study_area": "boston"},
            ]
        )
        first = self.crawl()
        self.assertEqual(len(first.results), 1)
        self.assertEqual(len(first.results[0].discovery_ids), 2)
        self.assertEqual(self.hit_count("/story"), 1)
        connection = connect(self.db)
        try:
            sources = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            links = connection.execute("SELECT COUNT(*) FROM source_discoveries").fetchone()[0]
            distinct = connection.execute(
                "SELECT COUNT(DISTINCT source_id) FROM discoveries"
            ).fetchone()[0]
            attempts = connection.execute("SELECT COUNT(*) FROM fetch_attempts").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(sources, 1)
        self.assertEqual(links, 2)
        self.assertEqual(distinct, 1)
        self.assertEqual(attempts, 1)

        self.import_rows([{"url": url, "title": "Third headline", "study_area": "boston"}])
        second = self.crawl()
        self.assertEqual(second.results[0].action, "reuse")
        self.assertEqual(self.hit_count("/story"), 1)
        self.assertEqual(len(list(self.archive.glob("**/attempt-*"))), 1)
        connection = connect(self.db)
        try:
            rows = connection.execute(
                "SELECT source_id, last_attempt_id, title FROM discoveries ORDER BY rowid"
            ).fetchall()
        finally:
            connection.close()
        self.assertEqual(len({row["source_id"] for row in rows}), 1)
        self.assertEqual(len({row["last_attempt_id"] for row in rows}), 1)
        self.assertEqual([row["title"] for row in rows], [
            "First headline",
            "Second headline",
            "Third headline",
        ])

    def test_refresh_keeps_the_earlier_attempt(self) -> None:
        self.route("/story", 200, "text/html; charset=utf-8", LONG_HTML.encode())
        url = f"{self.base}/story"
        self.import_rows([{"url": url, "title": "Headline", "study_area": "boston"}])
        self.crawl()
        first_meta = self.only_attempt()[0]
        self.import_rows([{"url": url, "title": "Again", "study_area": "boston"}])
        summary = self.crawl(refresh=True)
        self.assertEqual(summary.results[0].action, "fetch")
        folders = sorted(self.archive.glob("**/attempt-*"))
        self.assertEqual([path.name for path in folders], ["attempt-001", "attempt-002"])
        kept = json.loads((folders[0] / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(kept["attempt_id"], first_meta["attempt_id"])
        self.assertEqual(self.hit_count("/story"), 2)

    def test_redirect_records_the_final_url(self) -> None:
        self.route("/article", 200, "text/html; charset=utf-8", LONG_HTML.encode())
        self.httpd.routes["/old"] = (
            302,
            {"Location": f"{self.base}/article"},
            b"",
        )
        self.import_rows([{"url": f"{self.base}/old", "title": "Old headline"}])
        summary = self.crawl()
        self.assertEqual(summary.results[0].outcome, "retrieved")
        metadata, folder = self.only_attempt()
        self.assertEqual(metadata["requested_url"], f"{self.base}/old")
        self.assertEqual(metadata["final_url"], f"{self.base}/article")
        self.assertEqual(folder.relative_to(self.archive).parts[0], "unassigned")
        self.assertEqual(metadata["observed_title"], "Boston street pilot")

    def test_original_pdf_is_preserved_without_relying_on_the_suffix(self) -> None:
        self.route("/ordinance", 200, "application/octet-stream", PDF_BYTES)
        self.import_rows(
            [{"url": f"{self.base}/ordinance", "title": "Search title for the PDF"}]
        )
        summary = self.crawl(pdf_text_extractor=self.extract_pdf)
        self.assertEqual(summary.results[0].outcome, "retrieved")
        metadata, folder = self.only_attempt()
        self.assertEqual(metadata["source_kind"], "original_pdf")
        self.assertEqual((folder / "original.pdf").read_bytes(), PDF_BYTES)
        self.assertFalse((folder / "page.pdf").exists())
        self.assertFalse((folder / "raw.html").exists())
        self.assertIn("Ordinance text", (folder / "content.md").read_text(encoding="utf-8"))
        self.assertEqual(metadata["observed_title"], "Canyon road rules")
        self.assertEqual(metadata["discovery_records"][0]["imported_title"], "Search title for the PDF")
        self.assertIn(
            "original.pdf is the publisher file",
            metadata["notes"],
        )

    def test_html_with_a_pdf_suffix_is_not_stored_as_an_original_pdf(self) -> None:
        self.route("/notes.pdf", 200, "text/html; charset=utf-8", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/notes.pdf", "title": "Notes"}])
        self.crawl()
        metadata, folder = self.only_attempt()
        self.assertEqual(metadata["source_kind"], "html")
        self.assertFalse((folder / "original.pdf").exists())
        self.assertTrue((folder / "raw.html").is_file())

    def test_pdf_without_text_is_kept_and_flagged(self) -> None:
        self.route("/scan", 200, "application/pdf", PDF_BYTES)
        self.import_rows([{"url": f"{self.base}/scan", "title": "Scanned notice"}])
        summary = self.crawl(pdf_text_extractor=lambda _data: PdfText(None, None))
        self.assertEqual(summary.results[0].outcome, "empty")
        metadata, folder = self.only_attempt()
        self.assertEqual((folder / "original.pdf").read_bytes(), PDF_BYTES)
        self.assertFalse((folder / "content.md").exists())
        codes = {flag["code"] for flag in metadata["quality_flags"]}
        self.assertIn("needs_ocr", codes)
        self.assertIn("needs_review", codes)

    def test_http_errors_timeouts_empty_and_partial_content(self) -> None:
        self.route(
            "/missing",
            404,
            "text/html",
            b"<html><title>Missing notice</title><body>The notice is gone.</body></html>",
        )
        self.route("/short", 200, "text/html", b"<html><title>Note</title><body><p>Short notice.</p></body></html>")
        self.route("/blank", 200, "text/html", b"<html><head><title></title></head><body></body></html>")
        self.route("/denied", 403, "text/html", b"<html><title>No entry</title><body>No entry.</body></html>")
        paywall = article_html(extra='<div class="paywall">Subscribe to continue</div>')
        self.route("/metered", 200, "text/html", paywall.encode())
        blocked = article_html(extra="<p>Please verify you are human before reading on.</p>")
        self.route("/challenge", 200, "text/html", blocked.encode())
        self.httpd.routes["/slow"] = lambda: (
            time.sleep(0.8) or (200, {"Content-Type": "text/html"}, LONG_HTML.encode())
        )
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            if calls["count"] == 1:
                return (503, {"Content-Type": "text/html"}, b"<html><title>Busy</title><body>Busy</body></html>")
            return (200, {"Content-Type": "text/html"}, LONG_HTML.encode())

        self.httpd.routes["/flaky"] = flaky
        self.route("/limited", 429, "text/plain", b"slow down", extra_headers={"Retry-After": "120"})
        self.import_rows(
            [
                {"url": f"{self.base}/missing", "title": "Missing headline"},
                {"url": f"{self.base}/short", "title": "Short headline"},
                {"url": f"{self.base}/blank", "title": "Blank headline"},
                {"url": f"{self.base}/denied", "title": "Denied headline"},
                {"url": f"{self.base}/metered", "title": "Metered headline"},
                {"url": f"{self.base}/challenge", "title": "Challenge headline"},
                {"url": f"{self.base}/slow", "title": "Slow headline"},
                {"url": f"{self.base}/flaky", "title": "Flaky headline"},
                {"url": f"{self.base}/limited", "title": "Limited headline"},
                {"url": "http://127.0.0.1:1/refused", "title": "Refused headline"},
            ]
        )
        started = time.monotonic()
        summary = self.crawl(limit=9, timeout=0.2, retries=1)
        self.assertLess(time.monotonic() - started, 8)
        by_url = {item.requested_url: item for item in summary.results}
        self.assertEqual(by_url[f"{self.base}/missing"].outcome, "not_found")
        self.assertEqual(by_url[f"{self.base}/short"].outcome, "partial")
        self.assertEqual(by_url[f"{self.base}/blank"].outcome, "empty")
        self.assertEqual(by_url[f"{self.base}/denied"].outcome, "blocked")
        self.assertEqual(by_url[f"{self.base}/metered"].outcome, "paywall")
        self.assertEqual(by_url[f"{self.base}/challenge"].outcome, "blocked")
        self.assertEqual(by_url[f"{self.base}/slow"].outcome, "timeout")
        self.assertEqual(by_url[f"{self.base}/flaky"].outcome, "retrieved")
        self.assertEqual(by_url[f"{self.base}/limited"].outcome, "blocked")
        self.assertEqual(self.hit_count("/limited"), 1)
        self.assertGreaterEqual(self.hit_count("/slow"), 2)
        self.assertEqual(calls["count"], 2)

        refused = self.crawl(limit=1, retries=0, timeout=1)
        self.assertEqual(refused.results[0].outcome, "network_error")
        self.assertEqual(refused.results[0].crawl_status, "failed")

        missing = self.metadata_for("/missing")
        self.assertEqual(missing["observed_title"], "Missing notice")
        self.assertEqual(missing["discovery_records"][0]["imported_title"], "Missing headline")
        self.assertTrue(missing["errors"])
        metered = self.metadata_for("/metered")
        metered_text = (self.attempt_dir("/metered") / "content.md").read_text(encoding="utf-8")
        self.assertIn("The bakery on the corner opens at seven.", metered_text)
        self.assertIn("paywall_phrase", {flag["code"] for flag in metered["quality_flags"]})
        limited = self.metadata_for("/limited")
        self.assertIn("retry_after_too_long", {flag["code"] for flag in limited["quality_flags"]})
        blank = self.metadata_for("/blank")
        self.assertIsNone(blank["observed_title"])
        self.assertIsNone(blank["publication_date"])

    def test_publication_date_is_not_guessed(self) -> None:
        prose = article_html(date=None, title="Board meeting")
        prose = prose.replace(
            "The bakery on the corner opens at seven.",
            "The board met on June 15, 2024, and the bakery on the corner opens at seven.",
        )
        self.route("/prose", 200, "text/html", prose.encode())
        conflict = article_html(
            extra='<meta name="citation_publication_date" content="2020-01-02">'
        )
        self.route("/conflict", 200, "text/html", conflict.encode())
        self.import_rows(
            [
                {"url": f"{self.base}/prose", "title": "Prose headline"},
                {"url": f"{self.base}/conflict", "title": "Conflict headline"},
            ]
        )
        self.crawl(limit=2)
        prose_meta = self.metadata_for("/prose")
        self.assertIsNone(prose_meta["publication_date"])
        self.assertEqual(prose_meta["observed_title"], "Board meeting")
        conflict_meta = self.metadata_for("/conflict")
        self.assertIsNone(conflict_meta["publication_date"])
        self.assertIn(
            "ambiguous_publication_date",
            {flag["code"] for flag in conflict_meta["quality_flags"]},
        )

    def test_robots_disallow_is_recorded_and_not_bypassed(self) -> None:
        self.route(
            "/robots.txt",
            200,
            "text/plain",
            b"User-agent: *\nDisallow: /\n",
        )
        self.route("/story", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/story", "title": "Headline"}])
        summary = self.crawl()
        self.assertEqual(summary.results[0].outcome, "blocked")
        self.assertEqual(self.hit_count("/story"), 0)
        self.assertGreaterEqual(self.hit_count("/robots.txt"), 1)
        metadata, _folder = self.only_attempt()
        self.assertIn("robots_disallow", {flag["code"] for flag in metadata["quality_flags"]})
        signal = next(
            flag["signal"]
            for flag in metadata["quality_flags"]
            if flag["code"] == "robots_disallow"
        )
        self.assertIn(f"{self.base}/story", signal)

    def test_each_robots_block_names_its_own_url(self) -> None:
        self.route("/robots.txt", 200, "text/plain", b"User-agent: *\nDisallow: /\n")
        self.route("/chicago", 200, "text/html", LONG_HTML.encode())
        self.route("/seattle", 200, "text/html", LONG_HTML.encode())
        self.import_rows(
            [
                {"url": f"{self.base}/chicago", "title": "Chicago"},
                {"url": f"{self.base}/seattle", "title": "Seattle"},
            ]
        )
        summary = self.crawl(limit=2, concurrency=2)
        self.assertEqual({item.outcome for item in summary.results}, {"blocked"})
        self.assertEqual(self.hit_count("/chicago"), 0)
        self.assertEqual(self.hit_count("/seattle"), 0)
        chicago = self.metadata_for("/chicago")
        seattle = self.metadata_for("/seattle")
        chicago_signal = next(
            flag["signal"] for flag in chicago["quality_flags"] if flag["code"] == "robots_disallow"
        )
        seattle_signal = next(
            flag["signal"] for flag in seattle["quality_flags"] if flag["code"] == "robots_disallow"
        )
        self.assertIn(f"{self.base}/chicago", chicago_signal)
        self.assertNotIn("/seattle", chicago_signal)
        self.assertIn(f"{self.base}/seattle", seattle_signal)
        self.assertNotIn("/chicago", seattle_signal)

    def test_unreachable_robots_txt_blocks_the_page_without_fetching_it(self) -> None:
        self.route("/robots.txt", 403, "text/plain", b"forbidden")
        self.route("/story", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/story", "title": "Headline"}])
        summary = self.crawl()
        self.assertEqual(summary.results[0].outcome, "blocked")
        self.assertEqual(self.hit_count("/story"), 0)
        metadata, _folder = self.only_attempt()
        self.assertIn("robots_unreachable", {flag["code"] for flag in metadata["quality_flags"]})
        self.assertIn(f"{self.base}/story", metadata["quality_flags"][0]["signal"])
        self.assertIn("not requested", metadata["errors"][0])

    def test_robots_txt_timeout_is_treated_as_a_disallow(self) -> None:
        self.httpd.routes["/robots.txt"] = lambda: (
            time.sleep(0.8) or (200, {"Content-Type": "text/plain"}, b"User-agent: *\nAllow: /\n")
        )
        self.route("/story", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/story", "title": "Headline"}])
        summary = self.crawl(timeout=0.2, retries=1)
        self.assertEqual(summary.results[0].outcome, "blocked")
        self.assertEqual(self.hit_count("/story"), 0)
        metadata, _folder = self.only_attempt()
        self.assertIn("robots_unreachable", {flag["code"] for flag in metadata["quality_flags"]})

    def test_cloudflare_script_and_subscriber_prompt_do_not_hide_a_full_article(self) -> None:
        scripted = article_html(
            extra='<script src="/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/v1"></script>'
        )
        prompted = article_html(extra="<p>Already a subscriber? Log in</p>")
        self.route("/scripted", 200, "text/html", scripted.encode())
        self.route("/prompted", 200, "text/html", prompted.encode())
        self.import_rows(
            [
                {"url": f"{self.base}/scripted", "title": "Scripted"},
                {"url": f"{self.base}/prompted", "title": "Prompted"},
            ]
        )
        summary = self.crawl(limit=2)
        by_url = {item.requested_url: item for item in summary.results}
        self.assertEqual(by_url[f"{self.base}/scripted"].outcome, "retrieved")
        self.assertEqual(by_url[f"{self.base}/prompted"].outcome, "retrieved")

    def test_permission_wall_is_blocked_even_when_the_chrome_is_long(self) -> None:
        wall = article_html(
            extra="<p>You don't have permission to access this content</p>"
        )
        self.route("/wall", 200, "text/html", wall.encode())
        self.import_rows([{"url": f"{self.base}/wall", "title": "Wall"}])
        summary = self.crawl()
        self.assertEqual(summary.results[0].outcome, "blocked")
        metadata, _folder = self.only_attempt()
        self.assertIn("block_phrase", {flag["code"] for flag in metadata["quality_flags"]})

    def test_resume_retries_failures_without_recrawling_successes(self) -> None:
        self.route("/gone", 404, "text/html", b"<html><title>Gone</title><body>Gone</body></html>")
        self.route("/kept", 200, "text/html", LONG_HTML.encode())
        self.import_rows(
            [
                {"url": f"{self.base}/gone", "title": "Gone headline"},
                {"url": f"{self.base}/kept", "title": "Kept headline"},
            ]
        )
        self.crawl(limit=2)
        self.route("/gone", 200, "text/html", LONG_HTML.encode())
        kept_hits = self.hit_count("/kept")
        skipped = self.crawl(limit=5)
        self.assertEqual(skipped.selected, 0)
        self.assertEqual(self.hit_count("/kept"), kept_hits)
        connection = connect(self.db)
        try:
            gone = connection.execute(
                "SELECT crawl_status FROM discoveries WHERE original_url LIKE '%/gone'"
            ).fetchone()
        finally:
            connection.close()
        self.assertEqual(gone["crawl_status"], "not_found")

        retried = self.crawl(retry=True, limit=5)
        self.assertEqual(len(retried.results), 1)
        self.assertEqual(retried.results[0].outcome, "retrieved")
        self.assertTrue(retried.results[0].requested_url.endswith("/gone"))
        self.assertEqual(self.hit_count("/kept"), kept_hits)
        source = source_id_for(f"{self.base}/gone")
        source_dir = self.source_folder(source)
        names = sorted(path.name for path in source_dir.glob("attempt-*"))
        self.assertEqual(names, ["attempt-001", "attempt-002"])
        self.assertTrue((source_dir / "attempt-001" / "metadata.json").is_file())

    def test_processing_rows_are_recovered_and_dry_run_changes_nothing(self) -> None:
        self.route("/story", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/story", "title": "Headline"}])
        connection = connect(self.db)
        try:
            connection.execute("UPDATE discoveries SET crawl_status = 'processing'")
        finally:
            connection.close()
        preview = self.crawl(dry_run=True)
        self.assertEqual(preview.selected, 0)
        self.assertEqual(preview.recovered_processing, 0)
        connection = connect(self.db)
        try:
            status = connection.execute("SELECT crawl_status FROM discoveries").fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(status, "processing")
        self.assertFalse(self.archive.exists())

        summary = self.crawl()
        self.assertEqual(summary.recovered_processing, 1)
        self.assertEqual(summary.results[0].outcome, "retrieved")
        connection = connect(self.db)
        try:
            statuses = {
                row[0]
                for row in connection.execute("SELECT crawl_status FROM discoveries")
            }
        finally:
            connection.close()
        self.assertEqual(statuses, {"fetched"})

    def test_dry_run_of_the_pending_queue_writes_nothing(self) -> None:
        self.route("/story", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/story", "title": "Headline", "study_area": "boston"}])
        before = self.snapshot()
        summary = self.crawl(dry_run=True, limit=5)
        self.assertTrue(summary.dry_run)
        self.assertEqual(summary.results[0].action, "fetch")
        self.assertEqual(summary.results[0].source_id, source_id_for(f"{self.base}/story"))
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.hit_count("/story"), 0)
        self.assertFalse(self.archive.exists())

    def test_filters_limit_and_page_pdf_failure(self) -> None:
        self.route("/boston", 200, "text/html", LONG_HTML.encode())
        self.route("/seattle", 200, "text/html", LONG_HTML.encode())
        self.route("/chicago", 200, "text/html", LONG_HTML.encode())
        first = self.import_rows(
            [
                {"url": f"{self.base}/boston", "title": "Boston", "study_area": "boston"},
                {"url": f"{self.base}/seattle", "title": "Seattle", "study_area": "seattle"},
            ]
        )
        self.import_rows(
            [{"url": f"{self.base}/chicago", "title": "Chicago", "study_area": "chicago"}]
        )
        limited = self.crawl(limit=1)
        self.assertEqual(len(limited.results), 1)
        self.assertTrue(limited.results[0].requested_url.endswith("/boston"))
        area = self.crawl(limit=5, study_area="seattle")
        self.assertEqual(len(area.results), 1)
        self.assertTrue(area.results[0].requested_url.endswith("/seattle"))
        batched = self.crawl(limit=5, batch_id=first.batch_id)
        self.assertEqual(batched.selected, 0)
        self.crawl(limit=5, study_area="chicago")

        self.route("/render", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/render", "title": "Render"}])

        class BrokenSnapshot:
            async def render(self, url: str, *, timeout: float, save_page_pdf: bool):
                del url, timeout, save_page_pdf
                return RenderResult(
                    html=LONG_HTML,
                    markdown=html_to_text(LONG_HTML),
                    page_pdf=None,
                    page_pdf_error="snapshot failed",
                )

        rendered = self.crawl(limit=1, http_only=False, save_page_pdf=True, renderer=BrokenSnapshot())
        self.assertEqual(rendered.results[0].outcome, "retrieved")
        metadata, folder = self.metadata_and_folder("/render")
        self.assertIn("page_pdf_failed", {flag["code"] for flag in metadata["quality_flags"]})
        self.assertFalse((folder / "page.pdf").exists())
        self.assertIn("bakery", (folder / "content.md").read_text(encoding="utf-8"))
        self.assertIn("snapshot of the rendered HTML", metadata["notes"])

        class Snapshot:
            async def render(self, url: str, *, timeout: float, save_page_pdf: bool):
                del url, timeout
                self.requested = save_page_pdf
                return RenderResult(
                    html=LONG_HTML,
                    markdown=html_to_text(LONG_HTML),
                    page_pdf=b"%PDF-1.4\nsnapshot\n",
                )

        renderer = Snapshot()
        self.import_rows([{"url": f"{self.base}/render", "title": "Render again"}])
        saved = self.crawl(
            limit=1,
            refresh=True,
            http_only=False,
            save_page_pdf=True,
            renderer=renderer,
        )
        self.assertTrue(renderer.requested)
        self.assertEqual(saved.results[0].outcome, "retrieved")
        folders = sorted(self.source_folder(source_id_for(f"{self.base}/render")).glob("attempt-*"))
        self.assertEqual((folders[-1] / "page.pdf").read_bytes(), b"%PDF-1.4\nsnapshot\n")
        self.assertFalse((folders[-1] / "original.pdf").exists())

        self.route("/plain", 200, "text/html", LONG_HTML.encode())
        self.import_rows([{"url": f"{self.base}/plain", "title": "Plain page"}])
        warned = self.crawl(limit=1, save_page_pdf=True, http_only=True)
        self.assertEqual(warned.results[0].outcome, "retrieved")
        flags = {
            flag["code"]
            for flag in self.metadata_for("/plain")["quality_flags"]
        }
        self.assertIn("page_pdf_failed", flags)
        self.assertFalse((self.attempt_dir("/plain") / "page.pdf").exists())

    def test_migration_preserves_existing_rows(self) -> None:
        legacy = self.root / "legacy.sqlite"
        connection = sqlite3.connect(legacy)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE discoveries (
                id TEXT PRIMARY KEY,
                batch_id TEXT,
                original_url TEXT NOT NULL,
                normalized_url TEXT,
                study_area TEXT,
                crawl_status TEXT NOT NULL DEFAULT 'pending',
                imported_at TEXT,
                original_record_json TEXT
            )
            """
        )
        connection.execute(
            "INSERT INTO discoveries (id, crawl_status, original_url) VALUES ('disc_keep', 'pending', 'http://127.0.0.1/keep')"
        )
        connection.commit()
        ensure_schema(connection)
        row = connection.execute(
            "SELECT id, crawl_status, original_url, source_id, last_outcome FROM discoveries"
        ).fetchone()
        self.assertEqual(row["id"], "disc_keep")
        self.assertEqual(row["crawl_status"], "pending")
        self.assertEqual(row["original_url"], "http://127.0.0.1/keep")
        self.assertIsNone(row["source_id"])
        self.assertIsNone(row["last_outcome"])
        self.assertIsNotNone(
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sources'"
            ).fetchone()
        )
        connection.close()

    def test_cli_defaults_and_dry_run(self) -> None:
        args = build_parser().parse_args(["crawl"])
        self.assertEqual(args.limit, 5)
        self.assertEqual(args.timeout, 30.0)
        self.assertEqual(args.concurrency, 2)
        self.assertEqual(args.host_delay, 1.0)
        self.assertEqual(args.retries, 2)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.save_page_pdf)
        self.assertFalse(args.retry)
        self.assertFalse(args.refresh)

        url = "http://127.0.0.1:9/local-research-notice"
        csv_path = self.root / "urls.csv"
        csv_path.write_text(f"url,title\n{url},Local notice\n", encoding="utf-8")
        imported = subprocess.run(
            [
                sys.executable,
                "-m",
                "news_importer",
                "import",
                str(csv_path),
                "--db",
                str(self.db),
                "--report-dir",
                str(self.root / "reports"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(imported.returncode, 0, imported.stderr)
        before = self.db.read_bytes()
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "news_importer",
                "crawl",
                "--dry-run",
                "--db",
                str(self.db),
                "--limit",
                "5",
                "--output-dir",
                str(self.archive),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("dry run: no fetches", completed.stdout)
        self.assertIn(url, completed.stdout)
        self.assertEqual(self.db.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    @unittest.skipUnless(
        importlib.util.find_spec("crawl4ai") is not None,
        "Crawl4AI is not installed for this Python",
    )
    def test_crawl4ai_config_does_not_recurse_or_hide_barriers(self) -> None:
        from news_importer.crawl4ai_backend import build_run_config

        config = build_run_config(timeout=12, save_page_pdf=True)
        self.assertTrue(config.pdf)
        self.assertIsNone(config.deep_crawl_strategy)
        self.assertFalse(config.magic)
        self.assertFalse(config.simulate_user)
        self.assertFalse(config.override_navigator)
        self.assertFalse(config.remove_overlay_elements)
        self.assertEqual(config.word_count_threshold, 1)
        self.assertEqual(config.max_retries, 0)
        self.assertTrue(config.check_robots_txt)

    def route(
        self,
        path: str,
        status: int,
        content_type: str,
        body: bytes,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        headers = {"Content-Type": content_type}
        if extra_headers:
            headers.update(extra_headers)
        self.httpd.routes[path] = (status, headers, body)

    def import_rows(self, rows: list[dict[str, str]]):
        self.files += 1
        path = self.root / f"urls-{self.files}.csv"
        headers: list[str] = []
        for row in rows:
            for key in row:
                if key not in headers:
                    headers.append(key)
        lines = [",".join(headers)]
        for row in rows:
            lines.append(",".join(row.get(header, "") for header in headers))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return import_path(
            path,
            db_path=self.db,
            report_dir=self.root / "reports",
        )

    def test_retrieval_sheet_lists_extracted_file_paths(self) -> None:
        self.route("/story", 200, "text/html; charset=utf-8", LONG_HTML.encode())
        self.import_rows(
            [{"url": f"{self.base}/story", "title": "Imported", "study_area": "Boston"}]
        )
        sheet = self.root / "retrievals.csv"
        summary = self.crawl(sheet_path=sheet)
        self.assertEqual(summary.sheet_path, str(sheet))
        with sheet.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["imported_title"], "Imported")
        self.assertEqual(rows[0]["outcome"], "retrieved")
        raw_html = Path(rows[0]["raw_html"])
        markdown = Path(rows[0]["markdown"])
        metadata = Path(rows[0]["metadata_json"])
        self.assertTrue(raw_html.is_file())
        self.assertTrue(markdown.is_file())
        self.assertTrue(metadata.is_file())
        self.assertEqual(rows[0]["original_pdf"], "")
        self.assertEqual(rows[0]["page_pdf"], "")
        self.assertEqual(rows[0]["archive_dir"], str(raw_html.parent))

    def crawl(self, **kwargs):
        values = {
            "db_path": self.db,
            "output_dir": self.archive,
            "limit": 5,
            "timeout": 2,
            "concurrency": 1,
            "host_delay": 0,
            "retries": 1,
            "retry_backoff": 0,
            "http_only": True,
        }
        values.update(kwargs)
        return run_crawl(CrawlOptions(**values))

    def hit_count(self, path: str) -> int:
        return sum(1 for hit in self.httpd.hits if hit == path)

    def test_legacy_hash_folder_moves_under_the_study_area(self) -> None:
        url = f"{self.base}/story"
        self.import_rows([{"url": url, "title": "Headline", "study_area": "boston"}])
        source = source_id_for(url)
        legacy = self.archive / source / "attempt-001"
        legacy.mkdir(parents=True)
        (legacy / "metadata.json").write_text("{}\n", encoding="utf-8")
        connection = connect(self.db)
        try:
            ensure_schema(connection)
            connection.execute(
                """
                INSERT INTO sources (
                    id, normalized_url, requested_url, hostname, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (source, url, url, "127.0.0.1", "2026-01-01T00:00:00Z"),
            )
            connection.execute(
                "UPDATE discoveries SET source_id = ? WHERE normalized_url = ?",
                (source, url),
            )
            connection.execute(
                """
                INSERT INTO fetch_attempts (
                    id, source_id, attempt_number, requested_url, final_url,
                    retrieved_at, http_status, content_type, observed_title,
                    publication_date, outcome, quality_flags_json, error,
                    archive_dir, source_kind
                ) VALUES (?, ?, 1, ?, ?, ?, 200, 'text/html', 'Headline', NULL,
                          'retrieved', '[]', NULL, ?, 'html')
                """,
                (
                    "att_legacy",
                    source,
                    url,
                    url,
                    "2026-01-01T00:00:00Z",
                    str(legacy),
                ),
            )
            from news_importer.crawl import _relocate_legacy_archives

            moved = _relocate_legacy_archives(self.archive, connection)
            stored = connection.execute(
                "SELECT archive_dir FROM fetch_attempts WHERE id = 'att_legacy'"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertEqual(moved, 1)
        destination = self.source_folder(source) / "attempt-001"
        self.assertEqual(destination.relative_to(self.archive).parts[0], "boston")
        self.assertTrue((destination / "metadata.json").is_file())
        self.assertFalse((self.archive / source).exists())
        self.assertEqual(Path(stored), destination)

    def source_folder(self, source_id: str) -> Path:
        matches = [
            path
            for path in self.archive.rglob("*")
            if path.is_dir() and (path.name == source_id or path.name.endswith(f"--{source_id}"))
        ]
        self.assertEqual(len(matches), 1, matches)
        return matches[0]

    def only_attempt(self) -> tuple[dict, Path]:
        folders = list(self.archive.glob("**/attempt-*"))
        self.assertEqual(len(folders), 1, folders)
        metadata = json.loads((folders[0] / "metadata.json").read_text(encoding="utf-8"))
        return metadata, folders[0]

    def attempt_dir(self, suffix: str) -> Path:
        matches = [
            path
            for path in self.archive.glob("**/attempt-*")
            if suffix in json.loads((path / "metadata.json").read_text(encoding="utf-8"))["requested_url"]
        ]
        self.assertEqual(len(matches), 1, matches)
        return matches[0]

    def metadata_for(self, suffix: str) -> dict:
        return json.loads((self.attempt_dir(suffix) / "metadata.json").read_text(encoding="utf-8"))

    def metadata_and_folder(self, suffix: str) -> tuple[dict, Path]:
        folder = self.attempt_dir(suffix)
        return json.loads((folder / "metadata.json").read_text(encoding="utf-8")), folder

    def one_discovery(self) -> sqlite3.Row:
        connection = connect(self.db)
        try:
            return connection.execute("SELECT * FROM discoveries").fetchone()
        finally:
            connection.close()

    def snapshot(self):
        connection = sqlite3.connect(self.db)
        try:
            discoveries = connection.execute(
                """
                SELECT id, crawl_status, source_id, last_outcome, last_attempt_id, title, snippet
                FROM discoveries ORDER BY rowid
                """
            ).fetchall()
            sources = connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            attempts = connection.execute("SELECT COUNT(*) FROM fetch_attempts").fetchone()[0]
        finally:
            connection.close()
        files = []
        if self.archive.exists():
            files = sorted(
                str(path.relative_to(self.archive))
                for path in self.archive.rglob("*")
                if path.is_file()
            )
        return discoveries, sources, attempts, files

    @staticmethod
    def extract_pdf(_data: bytes) -> PdfText:
        return PdfText(text="Ordinance text " * 30, title="Canyon road rules")


if __name__ == "__main__":
    unittest.main()
