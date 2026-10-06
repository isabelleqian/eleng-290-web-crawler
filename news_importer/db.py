"""SQLite storage for import batches and discoveries.

Normalized URLs are indexed for repeat reports. They are not unique: every
accepted input record stays its own discovery, including exact duplicates and
later reimports of the same file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from news_importer.errors import ImporterError
from news_importer.models import dump_compact

EXPORT_COLUMNS = [
    "discovery_id",
    "batch_id",
    "crawl_status",
    "is_repeat",
    "original_url",
    "normalized_url",
    "hostname",
    "title",
    "query",
    "study_area",
    "study_area_raw",
    "discovery_method",
    "discovery_method_raw",
    "searched_at",
    "result_rank",
    "snippet",
    "search_language",
    "search_location",
    "notes",
    "extra_metadata_json",
    "warnings_json",
    "source_filename",
    "input_record_number",
    "imported_at",
    "original_record_json",
]

RETRIEVAL_COLUMNS = [
    "discovery_id",
    "batch_id",
    "study_area",
    "original_url",
    "normalized_url",
    "hostname",
    "imported_title",
    "imported_snippet",
    "discovery_method",
    "crawl_status",
    "outcome",
    "source_id",
    "attempt_id",
    "attempt_number",
    "requested_url",
    "final_url",
    "retrieved_at",
    "http_status",
    "content_type",
    "observed_title",
    "publication_date",
    "source_kind",
    "archive_dir",
    "raw_html",
    "markdown",
    "metadata_json",
    "original_pdf",
    "page_pdf",
    "body_file",
    "error",
]

_ARTIFACT_FILES = {
    "raw_html": "raw.html",
    "markdown": "content.md",
    "metadata_json": "metadata.json",
    "original_pdf": "original.pdf",
    "page_pdf": "page.pdf",
    "body_file": "body.bin",
}

_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS import_batches (
        id TEXT PRIMARY KEY,
        source_filename TEXT NOT NULL,
        source_format TEXT NOT NULL,
        imported_at TEXT NOT NULL,
        defaults_json TEXT NOT NULL,
        accepted_count INTEGER NOT NULL,
        rejected_count INTEGER NOT NULL,
        repeated_url_count INTEGER NOT NULL,
        warning_record_count INTEGER NOT NULL,
        warning_message_count INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS discoveries (
        id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL REFERENCES import_batches(id),
        original_url TEXT NOT NULL,
        normalized_url TEXT NOT NULL,
        hostname TEXT NOT NULL,
        title TEXT,
        query TEXT,
        study_area TEXT,
        study_area_raw TEXT,
        discovery_method TEXT NOT NULL,
        discovery_method_raw TEXT,
        searched_at TEXT,
        result_rank INTEGER,
        snippet TEXT,
        search_language TEXT,
        search_location TEXT,
        notes TEXT,
        extra_metadata_json TEXT NOT NULL,
        source_filename TEXT NOT NULL,
        input_record_number INTEGER NOT NULL,
        imported_at TEXT NOT NULL,
        warnings_json TEXT NOT NULL,
        crawl_status TEXT NOT NULL DEFAULT 'pending',
        is_repeat INTEGER NOT NULL CHECK (is_repeat IN (0, 1)),
        original_record_json TEXT NOT NULL,
        source_id TEXT,
        last_outcome TEXT,
        last_attempt_id TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_discoveries_normalized_url ON discoveries(normalized_url)",
    "CREATE INDEX IF NOT EXISTS idx_discoveries_batch_id ON discoveries(batch_id)",
    "CREATE INDEX IF NOT EXISTS idx_discoveries_study_area ON discoveries(study_area)",
    "CREATE INDEX IF NOT EXISTS idx_discoveries_crawl_status ON discoveries(crawl_status)",
    "CREATE INDEX IF NOT EXISTS idx_discoveries_imported_at ON discoveries(imported_at)",
    """
    CREATE TABLE IF NOT EXISTS sources (
        id TEXT PRIMARY KEY,
        normalized_url TEXT NOT NULL UNIQUE,
        requested_url TEXT NOT NULL,
        hostname TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS source_discoveries (
        source_id TEXT NOT NULL,
        discovery_id TEXT NOT NULL,
        linked_at TEXT NOT NULL,
        PRIMARY KEY (source_id, discovery_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fetch_attempts (
        id TEXT PRIMARY KEY,
        source_id TEXT NOT NULL,
        attempt_number INTEGER NOT NULL,
        requested_url TEXT NOT NULL,
        final_url TEXT,
        retrieved_at TEXT NOT NULL,
        http_status INTEGER,
        content_type TEXT,
        observed_title TEXT,
        publication_date TEXT,
        outcome TEXT NOT NULL,
        quality_flags_json TEXT NOT NULL,
        error TEXT,
        archive_dir TEXT NOT NULL,
        source_kind TEXT NOT NULL,
        UNIQUE (source_id, attempt_number)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_fetch_attempts_source_id ON fetch_attempts(source_id)",
)

_DISCOVERY_COLUMNS = {
    "source_id": "TEXT",
    "last_outcome": "TEXT",
    "last_attempt_id": "TEXT",
}


def connect(path: Path) -> sqlite3.Connection:
    """Open a database and create its parent directory when needed."""
    if path.exists() and not path.is_file():
        raise ImporterError(f"database path is not a file: {path}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ImporterError(
            f"could not create the database directory for {path}: {exc.strerror}"
        ) from exc
    try:
        connection = sqlite3.connect(path, isolation_level=None, timeout=5)
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    for statement in _SCHEMA:
        connection.execute(statement)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(discoveries)")}
    for name, declaration in _DISCOVERY_COLUMNS.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE discoveries ADD COLUMN {name} {declaration}")


def read_existing_normalized_urls(path: Path) -> set[str]:
    """Read normalized URLs without creating or modifying the database."""
    if not path.exists():
        return set()
    if not path.is_file():
        raise ImporterError(f"database path is not a file: {path}")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    try:
        row = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'discoveries'
            """
        ).fetchone()
        if row is None:
            return set()
        found = connection.execute("SELECT normalized_url FROM discoveries").fetchall()
        return {item[0] for item in found}
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    finally:
        connection.close()


def write_batch(
    connection: sqlite3.Connection,
    *,
    batch_id: str,
    source_filename: str,
    source_format: str,
    imported_at: str,
    defaults_json: str,
    accepted_count: int,
    rejected_count: int,
    repeated_url_count: int,
    warning_record_count: int,
    warning_message_count: int,
    rows: Iterable[tuple],
) -> None:
    """Insert one batch and its discoveries. The caller owns the transaction."""
    connection.execute(
        """
        INSERT INTO import_batches (
            id, source_filename, source_format, imported_at, defaults_json,
            accepted_count, rejected_count, repeated_url_count,
            warning_record_count, warning_message_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch_id,
            source_filename,
            source_format,
            imported_at,
            defaults_json,
            accepted_count,
            rejected_count,
            repeated_url_count,
            warning_record_count,
            warning_message_count,
        ),
    )
    connection.executemany(
        """
        INSERT INTO discoveries (
            id, batch_id, original_url, normalized_url, hostname,
            title, query, study_area, study_area_raw,
            discovery_method, discovery_method_raw,
            searched_at, result_rank, snippet, search_language, search_location,
            notes, extra_metadata_json, source_filename, input_record_number,
            imported_at, warnings_json, crawl_status, is_repeat, original_record_json
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, 'pending', ?, ?
        )
        """,
        rows,
    )


def discovery_row(
    *,
    discovery_id: str,
    batch_id: str,
    original_url: str,
    normalized_url: str,
    hostname: str,
    title: str | None,
    query: str | None,
    study_area: str | None,
    study_area_raw: str | None,
    discovery_method: str,
    discovery_method_raw: str | None,
    searched_at: str | None,
    result_rank: int | None,
    snippet: str | None,
    search_language: str | None,
    search_location: str | None,
    notes: str | None,
    extra: dict,
    source_filename: str,
    input_record_number: int,
    imported_at: str,
    warnings: list[dict],
    is_repeat: bool,
    original_record: dict,
) -> tuple:
    return (
        discovery_id,
        batch_id,
        original_url,
        normalized_url,
        hostname,
        title,
        query,
        study_area,
        study_area_raw,
        discovery_method,
        discovery_method_raw,
        searched_at,
        result_rank,
        snippet,
        search_language,
        search_location,
        notes,
        dump_compact(extra),
        source_filename,
        input_record_number,
        imported_at,
        dump_compact(warnings),
        1 if is_repeat else 0,
        dump_compact(original_record),
    )


def list_discoveries(
    path: Path,
    *,
    batch_id: str | None,
    study_area: str | None,
    status: str | None = None,
    limit: int,
) -> tuple[list[sqlite3.Row], int]:
    connection = _open_readonly(path)
    try:
        clause, params = _filters(batch_id, study_area, status)
        total = connection.execute(
            f"SELECT COUNT(*) FROM discoveries {clause}",
            params,
        ).fetchone()[0]
        rows = connection.execute(
            f"""
            {_list_select(connection)}
            {clause}
            ORDER BY imported_at DESC, rowid DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return list(rows), int(total)
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    finally:
        connection.close()


def export_pending(path: Path, output) -> int:
    """Write pending discoveries as CSV. Exporting does not change crawl_status."""
    import csv

    connection = _open_readonly(path)
    try:
        rows = connection.execute(
            """
            SELECT
                id AS discovery_id,
                batch_id,
                crawl_status,
                is_repeat,
                original_url,
                normalized_url,
                hostname,
                title,
                query,
                study_area,
                study_area_raw,
                discovery_method,
                discovery_method_raw,
                searched_at,
                result_rank,
                snippet,
                search_language,
                search_location,
                notes,
                extra_metadata_json,
                warnings_json,
                source_filename,
                input_record_number,
                imported_at,
                original_record_json
            FROM discoveries
            WHERE crawl_status = 'pending'
            ORDER BY imported_at ASC, rowid ASC
            """
        ).fetchall()
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    finally:
        connection.close()

    writer = csv.DictWriter(
        output,
        fieldnames=EXPORT_COLUMNS,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({column: _csv_cell(row[column]) for column in EXPORT_COLUMNS})
    return len(rows)


def export_retrievals(path: Path, output) -> int:
    """Write one row per discovery, including paths to its latest extracted files."""
    import csv

    connection = _open_readonly(path)
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(discoveries)")}
        has_attempts = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'fetch_attempts'
            """
        ).fetchone()
        if "last_attempt_id" in columns and has_attempts is not None:
            rows = connection.execute(
                """
                SELECT
                    discoveries.id AS discovery_id,
                    discoveries.batch_id,
                    discoveries.study_area,
                    discoveries.original_url,
                    discoveries.normalized_url,
                    discoveries.hostname,
                    discoveries.title AS imported_title,
                    discoveries.snippet AS imported_snippet,
                    discoveries.discovery_method,
                    discoveries.crawl_status,
                    discoveries.source_id,
                    fetch_attempts.id AS attempt_id,
                    fetch_attempts.attempt_number,
                    fetch_attempts.requested_url,
                    fetch_attempts.final_url,
                    fetch_attempts.retrieved_at,
                    fetch_attempts.http_status,
                    fetch_attempts.content_type,
                    fetch_attempts.observed_title,
                    fetch_attempts.publication_date,
                    fetch_attempts.outcome,
                    fetch_attempts.source_kind,
                    fetch_attempts.archive_dir,
                    fetch_attempts.error
                FROM discoveries
                LEFT JOIN fetch_attempts
                    ON fetch_attempts.id = discoveries.last_attempt_id
                ORDER BY discoveries.imported_at ASC, discoveries.rowid ASC
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    id AS discovery_id,
                    batch_id,
                    study_area,
                    original_url,
                    normalized_url,
                    hostname,
                    title AS imported_title,
                    snippet AS imported_snippet,
                    discovery_method,
                    crawl_status,
                    NULL AS source_id,
                    NULL AS attempt_id,
                    NULL AS attempt_number,
                    NULL AS requested_url,
                    NULL AS final_url,
                    NULL AS retrieved_at,
                    NULL AS http_status,
                    NULL AS content_type,
                    NULL AS observed_title,
                    NULL AS publication_date,
                    NULL AS outcome,
                    NULL AS source_kind,
                    NULL AS archive_dir,
                    NULL AS error
                FROM discoveries
                ORDER BY imported_at ASC, rowid ASC
                """
            ).fetchall()
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    finally:
        connection.close()

    writer = csv.DictWriter(
        output,
        fieldnames=RETRIEVAL_COLUMNS,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in rows:
        record = {column: _csv_cell(row[column]) for column in RETRIEVAL_COLUMNS if column in row.keys()}
        record.update(_artifact_paths(row["archive_dir"]))
        writer.writerow(record)
    return len(rows)


def _artifact_paths(archive_dir: str | None) -> dict[str, str]:
    paths = {column: "" for column in _ARTIFACT_FILES}
    if not archive_dir:
        return paths
    folder = Path(archive_dir)
    for column, filename in _ARTIFACT_FILES.items():
        candidate = folder / filename
        if candidate.is_file():
            paths[column] = str(candidate)
    return paths


def _open_readonly(path: Path) -> sqlite3.Connection:
    """Open an existing database without creating tables or changing rows."""
    if not path.exists():
        raise ImporterError(f"database not found: {path}. Import a file first.")
    if not path.is_file():
        raise ImporterError(f"database path is not a file: {path}")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True, timeout=5)
    except sqlite3.Error as exc:
        raise ImporterError(f"database error ({path}): {exc}") from exc
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        found = connection.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'discoveries'
            """
        ).fetchone()
    except sqlite3.Error as exc:
        connection.close()
        raise ImporterError(f"database error ({path}): {exc}") from exc
    if found is None:
        connection.close()
        raise ImporterError(
            f"database {path} has no discoveries table. Import a file first."
        )
    return connection


def _list_select(connection: sqlite3.Connection) -> str:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(discoveries)")}
    has_attempts = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'fetch_attempts'
        """
    ).fetchone()
    if "last_attempt_id" in columns and has_attempts is not None:
        return """
            SELECT discoveries.*, (
                SELECT archive_dir FROM fetch_attempts
                WHERE fetch_attempts.id = discoveries.last_attempt_id
            ) AS archive_dir
            FROM discoveries
        """
    return "SELECT * FROM discoveries"


def _filters(
    batch_id: str | None,
    study_area: str | None,
    status: str | None = None,
) -> tuple[str, list[str]]:
    clauses: list[str] = []
    params: list[str] = []
    if batch_id:
        clauses.append("batch_id = ?")
        params.append(batch_id)
    if study_area:
        clauses.append("study_area = ?")
        params.append(study_area)
    if status:
        clauses.append("crawl_status = ?")
        params.append(status)
    if not clauses:
        return "", params
    return "WHERE " + " AND ".join(clauses), params


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    return str(value)
