"""SQLite storage for import batches and discoveries.

Normalized URLs are indexed for repeat reports. They are not unique: every
accepted input record stays its own discovery, including exact duplicates and
later reimports of the same file.
"""

from __future__ import annotations

import json
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
    """
    CREATE TABLE IF NOT EXISTS crawled_documents (
        id TEXT PRIMARY KEY,
        origin TEXT NOT NULL,
        title TEXT NOT NULL,
        publisher TEXT NOT NULL,
        publication_date TEXT NOT NULL,
        location TEXT NOT NULL,
        url TEXT NOT NULL,
        archive_dir TEXT NOT NULL,
        measure_codes TEXT NOT NULL,
        governing_level TEXT NOT NULL,
        category TEXT NOT NULL,
        target_location_type TEXT NOT NULL,
        factual_summary TEXT NOT NULL,
        in_research_set INTEGER NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_crawled_documents_origin ON crawled_documents(origin)",
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


_US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut",
    "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa",
    "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire",
    "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio",
    "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "District of Columbia",
}
_NATIONWIDE = {"united states", "usa", "u.s.", "u.s.a.", "us", "international", "global"}


def sync_crawled_documents(db_path: Path, tags_path: Path, analysis_path: Path) -> int:
    """Store every tagged archive page and Nexis hit in the project database.

    The research-analysis file is a coded subset. Rows from that file keep their
    coded fields. Every other crawled article is stored too.
    """
    articles = []
    if tags_path.is_file():
        payload = json.loads(tags_path.read_text(encoding="utf-8"))
        articles = payload.get("articles") or []
    coded: dict[str, dict] = {}
    if analysis_path.is_file():
        for item in json.loads(analysis_path.read_text(encoding="utf-8")):
            source_id = str(item.get("source_id") or "")
            if source_id:
                coded[source_id] = item
    if not articles:
        articles = [
            {
                "article_id": source_id,
                "origin": "nexis" if source_id.startswith("nexis_") else "archive",
                "title": item.get("title") or "",
                "publisher": item.get("publisher") or "",
                "publication_date": item.get("publication_date") or "",
                "location": item.get("target_location") or item.get("location") or "",
                "url": item.get("requested_url") or "",
                "archive_dir": item.get("archive_dir") or "",
                "measures": [],
            }
            for source_id, item in coded.items()
        ]
    else:
        seen = {str(article.get("article_id") or "") for article in articles}
        title_index: dict[str, dict] = {}
        for article in articles:
            title = str(article.get("title") or "").casefold().strip()
            if title and title not in title_index:
                title_index[title] = article
        aliases: dict[str, dict] = {}
        for source_id, item in coded.items():
            if source_id in seen:
                continue
            title = str(item.get("title") or "").casefold().strip()
            match = title_index.get(title)
            if match is None and len(title) >= 40:
                for other, candidate in title_index.items():
                    short, long = (title, other) if len(title) <= len(other) else (other, title)
                    if len(short) >= 40 and long.startswith(short):
                        match = candidate
                        break
            if match is not None:
                match_id = str(match.get("article_id") or "")
                if match_id and match_id not in coded and match_id not in aliases:
                    aliases[match_id] = item
                continue
            articles.append({
                "article_id": source_id,
                "origin": "nexis" if source_id.startswith("nexis_") else "archive",
                "title": item.get("title") or "",
                "publisher": item.get("publisher") or "",
                "publication_date": item.get("publication_date") or "",
                "location": item.get("target_location") or "",
                "url": item.get("requested_url") or "",
                "archive_dir": item.get("archive_dir") or "",
                "measures": [],
            })
        coded.update(aliases)
    rows = [_document_row(article, coded.get(str(article.get("article_id") or ""))) for article in articles]
    unique: dict[str, tuple] = {}
    for row in rows:
        if row[0]:
            unique[row[0]] = row
    rows = list(unique.values())
    connection = connect(db_path)
    try:
        ensure_schema(connection)
        connection.execute("BEGIN")
        connection.execute("DELETE FROM crawled_documents")
        connection.executemany(
            """
            INSERT INTO crawled_documents (
                id, origin, title, publisher, publication_date, location, url,
                archive_dir, measure_codes, governing_level, category,
                target_location_type, factual_summary, in_research_set
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.execute("COMMIT")
    except sqlite3.Error as exc:
        connection.execute("ROLLBACK")
        raise ImporterError(f"database error ({db_path}): {exc}") from exc
    finally:
        connection.close()
    return len(rows)


def load_crawled_documents(db_path: Path) -> list[dict[str, str]]:
    """Return dashboard rows for every document in the unified table."""
    if not db_path.is_file():
        return []
    connection = connect(db_path)
    try:
        ensure_schema(connection)
        found = connection.execute(
            """
            SELECT id, origin, title, publisher, publication_date, location, url,
                   archive_dir, governing_level, category, target_location_type,
                   factual_summary
            FROM crawled_documents
            ORDER BY publication_date DESC, title
            """
        ).fetchall()
    finally:
        connection.close()
    rows = []
    for item in found:
        location = item["location"] or "United States"
        location_type = item["target_location_type"] or "Country"
        rows.append({
            "source_id": item["id"],
            "origin": item["origin"] or "",
            "title": item["title"],
            "publisher": item["publisher"],
            "publication_date": item["publication_date"],
            "target_location": location,
            "target_location_type": location_type,
            "governing_level": item["governing_level"] or "Not coded",
            "category": item["category"] or "Unlabeled",
            "factual_summary": item["factual_summary"] or "",
            "authority_names": item["publisher"],
            "supporting_passage": "",
            "url": item["url"] or "",
            "archive_dir": item["archive_dir"] or "",
        })
    return rows


def load_database_rows(db_path: Path) -> list[dict[str, str]]:
    """Return every column of crawled_documents for the database page."""
    if not db_path.is_file():
        return []
    connection = connect(db_path)
    try:
        ensure_schema(connection)
        found = connection.execute(
            """
            SELECT id, origin, title, publisher, publication_date, location, url,
                   archive_dir, measure_codes, governing_level, category,
                   target_location_type, factual_summary, in_research_set
            FROM crawled_documents
            ORDER BY publication_date DESC, title
            """
        ).fetchall()
    finally:
        connection.close()
    return [{key: item[key] if item[key] is not None else "" for key in item.keys()} for item in found]


def _document_row(article: dict, coded: dict | None) -> tuple:
    source_id = str(article.get("article_id") or "")
    location = (article.get("location") or "").strip()
    publication_date = str(article.get("publication_date") or "")
    location_type = ""
    governing = ""
    category = ""
    summary = ""
    if coded:
        coded_location = str(coded.get("target_location") or "").strip()
        if coded_location:
            location = coded_location
        coded_date = str(coded.get("publication_date") or "").strip()
        if coded_date:
            publication_date = coded_date
        location_type = str(coded.get("target_location_type") or "")
        governing = str(coded.get("governing_level") or "")
        category = str(coded.get("category") or "")
        summary = str(coded.get("factual_summary") or "")
    if not location:
        location = "United States"
        location_type = location_type or "Country"
    elif location.casefold() in _NATIONWIDE:
        location_type = location_type or "Country"
    elif not location_type:
        location_type = "State" if location in _US_STATES else "City"
    measures = article.get("measures") or []
    if not category:
        category = "Unlabeled"
    if not governing:
        governing = "Not coded"
    return (
        source_id,
        str(article.get("origin") or ""),
        str(article.get("title") or source_id),
        str(article.get("publisher") or ""),
        publication_date,
        location,
        str(article.get("url") or ""),
        str(article.get("archive_dir") or ""),
        "; ".join(str(code) for code in measures),
        governing,
        category,
        location_type,
        summary,
        1 if coded else 0,
    )
