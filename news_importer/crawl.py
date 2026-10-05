"""Read the discovery queue and archive one capture per source URL."""

from __future__ import annotations

import asyncio
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from news_importer.archive import next_attempt_number, source_id_for, write_attempt
from news_importer.crawl4ai_backend import Crawl4AIRenderer
from news_importer.db import connect, ensure_schema
from news_importer.errors import ImporterError
from news_importer.importer import new_id, utc_now
from news_importer.retrieve import (
    FetchResult,
    HostGate,
    RobotsCache,
    crawl_status_for,
    fetch_url,
)

REUSABLE_OUTCOMES = {"retrieved", "partial", "paywall", "empty"}
RETRY_STATUSES = ("failed", "blocked", "not_found")
QUEUE_STATUSES = ("pending", "processing", "fetched", "blocked", "not_found", "failed")


@dataclass
class CrawlOptions:
    db_path: Path
    output_dir: Path = Path("data/archive")
    limit: int = 5
    batch_id: str | None = None
    study_area: str | None = None
    timeout: float = 30.0
    dry_run: bool = False
    save_page_pdf: bool = False
    refresh: bool = False
    retry: bool = False
    concurrency: int = 2
    host_delay: float = 1.0
    retries: int = 2
    retry_backoff: float = 0.5
    http_only: bool = False
    renderer: object | None = None
    pdf_text_extractor: object | None = None


@dataclass
class CrawlItem:
    normalized_url: str
    requested_url: str
    action: str
    source_id: str
    discovery_ids: list[str]
    outcome: str | None = None
    crawl_status: str | None = None
    attempt_id: str | None = None
    archive_dir: str | None = None
    http_status: int | None = None
    error: str | None = None


@dataclass
class CrawlSummary:
    dry_run: bool
    recovered_processing: int
    selected: int
    results: list[CrawlItem] = field(default_factory=list)
    renderer_warning: str | None = None


@dataclass
class _Job:
    normalized_url: str
    requested_url: str
    hostname: str
    source_id: str
    rows: list[sqlite3.Row]
    action: str
    reuse_attempt_id: str | None = None
    reuse_outcome: str | None = None
    reuse_archive: str | None = None
    attempt_id: str | None = None
    attempt_number: int | None = None
    archive_dir: Path | None = None


def run_crawl(options: CrawlOptions) -> CrawlSummary:
    if options.limit < 1:
        raise ImporterError("limit must be a positive integer")
    if options.concurrency < 1:
        raise ImporterError("concurrency must be a positive integer")
    if options.retries < 0:
        raise ImporterError("retries must be zero or greater")
    if options.timeout <= 0:
        raise ImporterError("timeout must be a positive number")
    if options.host_delay < 0:
        raise ImporterError("host delay must be zero or greater")
    return asyncio.run(_run(options))


async def _run(options: CrawlOptions) -> CrawlSummary:
    database = options.db_path.expanduser()
    if not database.exists():
        raise ImporterError(
            f"database not found: {database}. Import a file first."
        )
    if options.dry_run:
        connection = _open_readonly(database)
        try:
            jobs = _select_jobs(connection, options)
        finally:
            connection.close()
        return CrawlSummary(
            dry_run=True,
            recovered_processing=0,
            selected=len(jobs),
            results=[_preview(job) for job in jobs],
        )

    connection = connect(database)
    renderer: object | None = options.renderer
    started_renderer = False
    warning: str | None = None
    try:
        ensure_schema(connection)
        recovered = _recover_processing(connection)
        jobs = _select_jobs(connection, options)
        fetch_jobs = [job for job in jobs if job.action == "fetch"]
        if fetch_jobs and renderer is None and not options.http_only:
            renderer = Crawl4AIRenderer()
            try:
                await renderer.start()
                started_renderer = True
            except RuntimeError as exc:
                warning = str(exc)
                renderer = None
        for job in fetch_jobs:
            _assign_attempt(connection, job, options.output_dir)
            _claim(connection, job)
        results = await _fetch_all(options, jobs, renderer, warning)
        return CrawlSummary(
            dry_run=False,
            recovered_processing=recovered,
            selected=len(results),
            results=results,
            renderer_warning=warning,
        )
    finally:
        connection.close()
        if started_renderer and isinstance(renderer, Crawl4AIRenderer):
            await renderer.close()


async def _fetch_all(
    options: CrawlOptions,
    jobs: list[_Job],
    renderer: object | None,
    warning: str | None,
) -> list[CrawlItem]:
    semaphore = asyncio.Semaphore(options.concurrency)
    gate = HostGate(options.host_delay)
    robots = RobotsCache()

    async def worker(job: _Job) -> CrawlItem:
        if job.action == "reuse":
            return _apply_reuse(options.db_path, job)
        async with semaphore:
            try:
                fetched = await fetch_url(
                    job.requested_url,
                    timeout=options.timeout,
                    retries=options.retries,
                    retry_backoff=options.retry_backoff,
                    save_page_pdf=options.save_page_pdf,
                    gate=gate,
                    robots=robots,
                    renderer=None if options.http_only else renderer,
                    pdf_text_extractor=options.pdf_text_extractor,
                    http_only=options.http_only or renderer is None,
                )
            except Exception as exc:
                fetched = _failed_fetch(job.requested_url, f"retrieval failed: {exc}")
            if (
                warning
                and fetched.source_kind == "html"
                and fetched.renderer != "crawl4ai"
            ):
                from news_importer.retrieve import QualityFlag

                fetched.quality_flags.append(
                    QualityFlag("crawl4ai_unavailable", warning)
                )
                if fetched.renderer == "http":
                    fetched.renderer = "http_fallback"
            return _apply_fetch(options, job, fetched)

    return list(await asyncio.gather(*[worker(job) for job in jobs]))


def _preview(job: _Job) -> CrawlItem:
    return CrawlItem(
        normalized_url=job.normalized_url,
        requested_url=job.requested_url,
        action=job.action,
        source_id=job.source_id,
        discovery_ids=[row["id"] for row in job.rows],
        outcome=job.reuse_outcome,
        crawl_status=crawl_status_for(job.reuse_outcome) if job.reuse_outcome else None,
        attempt_id=job.reuse_attempt_id,
        archive_dir=job.reuse_archive,
    )


def _select_jobs(connection: sqlite3.Connection, options: CrawlOptions) -> list[_Job]:
    if options.retry and options.refresh:
        statuses = ("pending", *RETRY_STATUSES)
    elif options.retry:
        statuses = RETRY_STATUSES
    else:
        statuses = ("pending",)
    clauses = [f"crawl_status IN ({', '.join('?' for _ in statuses)})"]
    params: list[str] = list(statuses)
    if options.batch_id:
        clauses.append("batch_id = ?")
        params.append(options.batch_id)
    if options.study_area:
        clauses.append("study_area = ?")
        params.append(options.study_area)
    rows = connection.execute(
        f"""
        SELECT * FROM discoveries
        WHERE {' AND '.join(clauses)}
        ORDER BY imported_at ASC, rowid ASC
        """,
        params,
    ).fetchall()
    groups: dict[str, list[sqlite3.Row]] = {}
    order: list[str] = []
    for row in rows:
        key = row["normalized_url"]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    has_attempts = _table_exists(connection, "fetch_attempts")
    jobs: list[_Job] = []
    for normalized in order[: options.limit]:
        grouped = groups[normalized]
        earliest = grouped[0]
        source_id = source_id_for(normalized)
        job = _Job(
            normalized_url=normalized,
            requested_url=_request_url(earliest["original_url"]),
            hostname=earliest["hostname"],
            source_id=source_id,
            rows=grouped,
            action="fetch",
        )
        if not options.refresh and not options.retry and has_attempts:
            previous = _latest_attempt(connection, source_id)
            if previous is not None and previous["outcome"] in REUSABLE_OUTCOMES:
                archive = previous["archive_dir"]
                if archive and Path(archive, "metadata.json").is_file():
                    job.action = "reuse"
                    job.reuse_attempt_id = previous["id"]
                    job.reuse_outcome = previous["outcome"]
                    job.reuse_archive = archive
        jobs.append(job)
    return jobs


def _latest_attempt(connection: sqlite3.Connection, source_id: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM fetch_attempts
        WHERE source_id = ?
        ORDER BY attempt_number DESC
        LIMIT 1
        """,
        (source_id,),
    ).fetchone()


def _assign_attempt(connection: sqlite3.Connection, job: _Job, output_dir: Path) -> None:
    numbers = []
    if _table_exists(connection, "fetch_attempts"):
        rows = connection.execute(
            "SELECT attempt_number FROM fetch_attempts WHERE source_id = ?",
            (job.source_id,),
        ).fetchall()
        numbers = [row["attempt_number"] for row in rows]
    number = next_attempt_number(job.source_id, output_dir, numbers)
    job.attempt_number = number
    job.attempt_id = new_id("att")
    job.archive_dir = output_dir / job.source_id / f"attempt-{number:03d}"


def _claim(connection: sqlite3.Connection, job: _Job) -> None:
    ids = [row["id"] for row in job.rows]
    marks = ", ".join("?" for _ in ids)
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            f"UPDATE discoveries SET crawl_status = 'processing' WHERE id IN ({marks})",
            ids,
        )
        connection.execute("COMMIT")
    except sqlite3.Error:
        connection.execute("ROLLBACK")
        raise


def _apply_reuse(database: Path, job: _Job) -> CrawlItem:
    status = crawl_status_for(job.reuse_outcome or "retrieved")
    connection = connect(database)
    try:
        ensure_schema(connection)
        _link_source(connection, job, utc_now())
        _update_discoveries(
            connection,
            job,
            crawl_status=status,
            outcome=job.reuse_outcome or "retrieved",
            attempt_id=job.reuse_attempt_id,
        )
    finally:
        connection.close()
    return CrawlItem(
        normalized_url=job.normalized_url,
        requested_url=job.requested_url,
        action="reuse",
        source_id=job.source_id,
        discovery_ids=[row["id"] for row in job.rows],
        outcome=job.reuse_outcome,
        crawl_status=status,
        attempt_id=job.reuse_attempt_id,
        archive_dir=job.reuse_archive,
    )


def _apply_fetch(options: CrawlOptions, job: _Job, result: FetchResult) -> CrawlItem:
    status = crawl_status_for(result.outcome)
    retrieved_at = utc_now()
    records = [_discovery_record(row) for row in job.rows]
    assert job.archive_dir is not None and job.attempt_id and job.attempt_number
    try:
        write_attempt(
            job.archive_dir,
            result,
            source_id=job.source_id,
            attempt_id=job.attempt_id,
            attempt_number=job.attempt_number,
            normalized_url=job.normalized_url,
            retrieved_at=retrieved_at,
            discovery_records=records,
            crawl_status=status,
        )
    except OSError as exc:
        message = f"could not write the archive: {exc}"
        _mark_failed(options.db_path, job, message)
        return CrawlItem(
            normalized_url=job.normalized_url,
            requested_url=job.requested_url,
            action="fetch",
            source_id=job.source_id,
            discovery_ids=[row["id"] for row in job.rows],
            outcome="network_error",
            crawl_status="failed",
            error=message,
        )

    connection = connect(options.db_path)
    try:
        ensure_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            _link_source(connection, job, retrieved_at)
            connection.execute(
                """
                INSERT INTO fetch_attempts (
                    id, source_id, attempt_number, requested_url, final_url,
                    retrieved_at, http_status, content_type, observed_title,
                    publication_date, outcome, quality_flags_json, error,
                    archive_dir, source_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.attempt_id,
                    job.source_id,
                    job.attempt_number,
                    result.requested_url,
                    result.final_url,
                    retrieved_at,
                    result.http_status,
                    result.content_type,
                    result.observed_title,
                    result.publication_date,
                    result.outcome,
                    _flags_json(result),
                    result.error_text,
                    str(job.archive_dir),
                    result.source_kind,
                ),
            )
            _update_discoveries(
                connection,
                job,
                crawl_status=status,
                outcome=result.outcome,
                attempt_id=job.attempt_id,
            )
            connection.execute("COMMIT")
        except sqlite3.Error as exc:
            connection.execute("ROLLBACK")
            raise ImporterError(f"database error ({options.db_path}): {exc}") from exc
    finally:
        connection.close()
    return CrawlItem(
        normalized_url=job.normalized_url,
        requested_url=job.requested_url,
        action="fetch",
        source_id=job.source_id,
        discovery_ids=[row["id"] for row in job.rows],
        outcome=result.outcome,
        crawl_status=status,
        attempt_id=job.attempt_id,
        archive_dir=str(job.archive_dir),
        http_status=result.http_status,
        error=result.error_text,
    )


def _mark_failed(database: Path, job: _Job, message: str) -> None:
    connection = connect(database)
    try:
        _update_discoveries(
            connection,
            job,
            crawl_status="failed",
            outcome="network_error",
            attempt_id=None,
        )
    finally:
        connection.close()
    del message


def _link_source(connection: sqlite3.Connection, job: _Job, linked_at: str) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO sources (
            id, normalized_url, requested_url, hostname, created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (job.source_id, job.normalized_url, job.requested_url, job.hostname, linked_at),
    )
    connection.executemany(
        """
        INSERT OR IGNORE INTO source_discoveries (source_id, discovery_id, linked_at)
        VALUES (?, ?, ?)
        """,
        [(job.source_id, row["id"], linked_at) for row in job.rows],
    )


def _update_discoveries(
    connection: sqlite3.Connection,
    job: _Job,
    *,
    crawl_status: str,
    outcome: str,
    attempt_id: str | None,
) -> None:
    ids = [row["id"] for row in job.rows]
    marks = ", ".join("?" for _ in ids)
    connection.execute(
        f"""
        UPDATE discoveries
        SET crawl_status = ?, source_id = ?, last_outcome = ?, last_attempt_id = ?
        WHERE id IN ({marks})
        """,
        [crawl_status, job.source_id, outcome, attempt_id, *ids],
    )


def _recover_processing(connection: sqlite3.Connection) -> int:
    cursor = connection.execute(
        """
        UPDATE discoveries
        SET crawl_status = 'pending'
        WHERE crawl_status = 'processing'
        """
    )
    return cursor.rowcount if cursor.rowcount is not None else 0


def _discovery_record(row: sqlite3.Row) -> dict[str, str | None]:
    return {
        "discovery_id": row["id"],
        "original_url": row["original_url"],
        "imported_title": row["title"],
        "imported_snippet": row["snippet"],
    }


def _flags_json(result: FetchResult) -> str:
    import json

    return json.dumps([flag.as_dict() for flag in result.quality_flags], ensure_ascii=False)


def _failed_fetch(url: str, message: str) -> FetchResult:
    from news_importer.retrieve import QualityFlag

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
        source_kind="other",
        quality_flags=[QualityFlag("needs_review", message)],
        errors=[message],
        renderer="none",
    )


def _request_url(original: str) -> str:
    stripped = original.strip()
    parts = urlsplit(stripped)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return row is not None


def _open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ImporterError(f"database not found: {path}. Import a file first.")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    connection.row_factory = sqlite3.Row
    found = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'discoveries'
        """
    ).fetchone()
    if found is None:
        connection.close()
        raise ImporterError(
            f"database {path} has no discoveries table. Import a file first."
        )
    return connection
