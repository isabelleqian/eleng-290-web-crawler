"""Import URL lists into SQLite, one discovery per accepted input record."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from news_importer.db import (
    connect,
    discovery_row,
    ensure_schema,
    read_existing_normalized_urls,
    write_batch,
)
from news_importer.errors import ImporterError
from news_importer.inputs import read_records
from news_importer.models import (
    ImportDefaults,
    ImportSummary,
    PreparedRow,
    RejectionView,
    WarningView,
    dump_compact,
)
from news_importer.study_areas import Catalog, load_catalog
from news_importer.urls import require_valid_searched_at
from news_importer.validate import prepare_record


def import_path(
    path: str | Path,
    *,
    db_path: str | Path = "data/news.sqlite",
    report_dir: str | Path = "data/reports",
    defaults: ImportDefaults | None = None,
    dry_run: bool = False,
    input_format: str | None = None,
    study_areas_path: str | Path | None = None,
) -> ImportSummary:
    """Import a CSV or TXT file.

    A real import always creates a new batch. Reimporting a file does not
    update or delete discoveries from the earlier batch. Dry-run validates
    the file, compares normalized URLs with the database when one already
    exists, and writes nothing.
    """
    source = Path(path)
    database = Path(db_path).expanduser()
    reports = Path(report_dir).expanduser()
    chosen = defaults or ImportDefaults()
    if not source.is_file():
        raise ImporterError(f"input file not found: {source}")
    if chosen.searched_at is not None:
        require_valid_searched_at(chosen.searched_at, "--searched-at")

    catalog = load_catalog(study_areas_path)
    source_format, records = read_records(source, input_format)
    prepared = [prepare_record(record, chosen, catalog) for record in records]
    accepted = [row for row in prepared if row.accepted]
    rejected = [row for row in prepared if not row.accepted]

    if dry_run:
        existing = read_existing_normalized_urls(database)
        repeat_flags, repeated_urls = annotate_repeats(accepted, existing)
        return _summary(
            dry_run=True,
            source=source,
            source_format=source_format,
            batch_id=None,
            imported_at=None,
            database=database,
            report_path=None,
            defaults=chosen,
            accepted=accepted,
            rejected=rejected,
            repeat_flags=repeat_flags,
            repeated_urls=repeated_urls,
            discovery_ids=[None] * len(accepted),
        )

    batch_id = new_id("batch")
    imported_at = utc_now()
    discovery_ids = [new_id("disc") for _ in accepted]
    summary = _store_batch(
        database=database,
        source=source,
        source_format=source_format,
        batch_id=batch_id,
        imported_at=imported_at,
        defaults=chosen,
        accepted=accepted,
        rejected=rejected,
        discovery_ids=discovery_ids,
    )
    report_path = reports / f"{batch_id}.json"
    _write_report(report_path, summary)
    summary.report_path = str(report_path)
    return summary


def annotate_repeats(
    accepted: list[PreparedRow],
    existing: set[str],
) -> tuple[list[bool], list[str]]:
    """Mark discoveries whose normalized URL was already seen.

    The first stored occurrence is not a repeat. A later row in this batch,
    or any row whose URL is already in the database, is a repeat and is kept.
    """
    seen = set(existing)
    flags: list[bool] = []
    repeated: list[str] = []
    reported: set[str] = set()
    for row in accepted:
        normalized = row.normalized_url or ""
        is_repeat = normalized in seen
        flags.append(is_repeat)
        if is_repeat and normalized not in reported:
            repeated.append(normalized)
            reported.add(normalized)
        seen.add(normalized)
    return flags, repeated


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _store_batch(
    *,
    database: Path,
    source: Path,
    source_format: str,
    batch_id: str,
    imported_at: str,
    defaults: ImportDefaults,
    accepted: list[PreparedRow],
    rejected: list[PreparedRow],
    discovery_ids: list[str],
) -> ImportSummary:
    """Write a batch in one transaction so a failure leaves no partial batch."""
    connection = connect(database)
    started = False
    try:
        ensure_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        started = True
        found = connection.execute("SELECT normalized_url FROM discoveries").fetchall()
        existing = {row[0] for row in found}
        repeat_flags, repeated_urls = annotate_repeats(accepted, existing)
        summary = _summary(
            dry_run=False,
            source=source,
            source_format=source_format,
            batch_id=batch_id,
            imported_at=imported_at,
            database=database,
            report_path=None,
            defaults=defaults,
            accepted=accepted,
            rejected=rejected,
            repeat_flags=repeat_flags,
            repeated_urls=repeated_urls,
            discovery_ids=discovery_ids,
        )
        write_batch(
            connection,
            batch_id=batch_id,
            source_filename=summary.source_filename,
            source_format=source_format,
            imported_at=imported_at,
            defaults_json=dump_compact(defaults.as_json()),
            accepted_count=summary.accepted,
            rejected_count=summary.rejected,
            repeated_url_count=summary.repeated_urls,
            warning_record_count=summary.records_with_warnings,
            warning_message_count=summary.warnings,
            rows=[
                discovery_row(
                    discovery_id=discovery_id,
                    batch_id=batch_id,
                    original_url=row.original_url or "",
                    normalized_url=row.normalized_url or "",
                    hostname=row.hostname or "",
                    title=row.title,
                    query=row.query,
                    study_area=row.study_area,
                    study_area_raw=row.study_area_raw,
                    discovery_method=row.discovery_method or "unknown",
                    discovery_method_raw=row.discovery_method_raw,
                    searched_at=row.searched_at,
                    result_rank=row.result_rank,
                    snippet=row.snippet,
                    search_language=row.search_language,
                    search_location=row.search_location,
                    notes=row.notes,
                    extra=row.extra,
                    source_filename=summary.source_filename,
                    input_record_number=row.record_number,
                    imported_at=imported_at,
                    warnings=[issue.as_dict() for issue in row.warnings],
                    is_repeat=is_repeat,
                    original_record=row.original_record,
                )
                for row, discovery_id, is_repeat in zip(
                    accepted, discovery_ids, repeat_flags, strict=True
                )
            ],
        )
        connection.execute("COMMIT")
        started = False
        return summary
    except sqlite3.Error as exc:
        if started:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        raise ImporterError(f"database error ({database}): {exc}") from exc
    finally:
        connection.close()


def _write_report(path: Path, summary: ImportSummary) -> None:
    payload = {
        "batch_id": summary.batch_id,
        "source_filename": summary.source_filename,
        "source_format": summary.source_format,
        "imported_at": summary.imported_at,
        "database_path": summary.database_path,
        "defaults": summary.defaults.as_json(),
        "summary": {
            "accepted": summary.accepted,
            "rejected": summary.rejected,
            "repeated_urls": summary.repeated_urls,
            "warnings": summary.warnings,
            "records_with_warnings": summary.records_with_warnings,
        },
        "repeated_normalized_urls": summary.repeated_normalized_urls,
        "rejected": [
            {
                "record_number": item.record_number,
                "reasons": [reason.as_dict() for reason in item.reasons],
                "original_record": item.original_record,
            }
            for item in summary.rejections
        ],
        "warnings": [
            {
                "record_number": item.record_number,
                "discovery_id": item.discovery_id,
                "normalized_url": item.normalized_url,
                "warnings": [warning.as_dict() for warning in item.warnings],
            }
            for item in summary.warning_rows
        ],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise ImporterError(
            f"imported batch {summary.batch_id} into {summary.database_path}, "
            f"but could not write the report {path}: {exc.strerror}"
        ) from exc


def _summary(
    *,
    dry_run: bool,
    source: Path,
    source_format: str,
    batch_id: str | None,
    imported_at: str | None,
    database: Path,
    report_path: str | None,
    defaults: ImportDefaults,
    accepted: list[PreparedRow],
    rejected: list[PreparedRow],
    repeat_flags: list[bool],
    repeated_urls: list[str],
    discovery_ids: list[str | None],
) -> ImportSummary:
    warning_rows = [
        WarningView(
            record_number=row.record_number,
            discovery_id=discovery_id,
            normalized_url=row.normalized_url or "",
            warnings=list(row.warnings),
        )
        for row, discovery_id in zip(accepted, discovery_ids, strict=True)
        if row.warnings
    ]
    return ImportSummary(
        dry_run=dry_run,
        source_filename=str(source),
        source_format=source_format,
        batch_id=batch_id,
        imported_at=imported_at,
        database_path=str(database),
        report_path=report_path,
        defaults=defaults,
        accepted=len(accepted),
        rejected=len(rejected),
        repeated_urls=sum(1 for flag in repeat_flags if flag),
        warnings=sum(len(row.warnings) for row in accepted),
        records_with_warnings=sum(1 for row in accepted if row.warnings),
        repeated_normalized_urls=repeated_urls,
        rejections=[
            RejectionView(row.record_number, list(row.rejections), dict(row.original_record))
            for row in rejected
        ],
        warning_rows=warning_rows,
    )


def resolve_study_area_filter(value: str | None, catalog: Catalog) -> str | None:
    """Map a list filter alias to the stored study-area id when it is known."""
    if value is None or value.strip() == "":
        return None
    text = value.strip()
    match = catalog.resolve(text)
    if match is None:
        return text
    return match.id
