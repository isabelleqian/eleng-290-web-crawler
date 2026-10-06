"""Command-line interface for import and retrieval."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from news_importer import __version__
from news_importer.crawl import QUEUE_STATUSES, CrawlOptions, run_crawl
from news_importer.db import export_pending, export_retrievals, list_discoveries
from news_importer.errors import ImporterError
from news_importer.importer import import_path, resolve_study_area_filter
from news_importer.models import ImportDefaults, ImportSummary
from news_importer.study_areas import Catalog, load_catalog
from news_importer.validate import ALLOWED_DISCOVERY_METHODS

DEFAULT_DB = "data/news.sqlite"
DEFAULT_REPORT_DIR = "data/reports"
DEFAULT_ARCHIVE_DIR = "data/archive"
DEFAULT_RETRIEVALS = "data/exports/retrievals.csv"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "import":
            return command_import(args)
        if args.command == "list":
            return command_list(args)
        if args.command == "export":
            return command_export(args)
        if args.command == "crawl":
            return command_crawl(args)
        if args.command == "analyze":
            return command_analyze(args)
    except ImporterError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    parser.error(f"unknown command {args.command}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m news_importer",
        description=(
            "Import locally collected news URLs into SQLite, then archive the "
            "queued pages. import, list, and export do not fetch pages. "
            "crawl fetches only the queued URLs."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 -m news_importer import samples/discoveries.csv\n"
            "  python3 -m news_importer import samples/discoveries.csv --dry-run\n"
            "  python3 -m news_importer list --study-area SF\n"
            "  python3 -m news_importer export --output data/exports/pending.csv\n"
            "  python3 -m news_importer export --retrieved --output data/exports/retrievals.csv\n"
            "  python3 -m news_importer crawl --limit 5\n"
            "  python3 -m news_importer crawl --limit 5 --dry-run\n"
            "  python3 -m news_importer list --status failed\n"
            "  python3 -m news_importer crawl --retry --limit 5\n"
            "  python3 -m news_importer crawl --limit 5 --save-page-pdf\n"
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser(
        "import",
        help="import a CSV or TXT URL list",
        description=(
            "Import a CSV file or a text file with one URL per nonblank line. "
            "Valid rows are stored. Invalid rows are reported and skipped. "
            "Reimporting a file creates a new batch and keeps the old rows."
        ),
    )
    import_parser.add_argument("path", help="CSV or TXT file to import")
    _add_db(import_parser)
    import_parser.add_argument(
        "--report-dir",
        default=DEFAULT_REPORT_DIR,
        help=f"directory for the JSON batch report (default: {DEFAULT_REPORT_DIR})",
    )
    import_parser.add_argument(
        "--format",
        choices=("csv", "txt"),
        help="input format when the file extension is not .csv or .txt",
    )
    import_parser.add_argument(
        "--study-area",
        help=(
            "study area used when a row does not supply one. "
            "Aliases such as NYC, SF, and LA are accepted. "
            "A row value wins. Unknown values are kept and flagged."
        ),
    )
    import_parser.add_argument(
        "--discovery-method",
        help=(
            "discovery method used when a row does not supply one. "
            f"Known values: {', '.join(ALLOWED_DISCOVERY_METHODS)}. "
            "Missing values become unknown. Unrecognized values are kept and flagged."
        ),
    )
    import_parser.add_argument(
        "--query",
        help="search query used when a row does not supply one",
    )
    import_parser.add_argument(
        "--searched-at",
        help=(
            "ISO 8601 date (YYYY-MM-DD) or timestamp with a timezone, "
            "used when a row does not supply searched_at. "
            "The import time is never used as the search time."
        ),
    )
    import_parser.add_argument(
        "--study-areas",
        help="path to a study-area JSON file (default: the built-in configuration)",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the summary without writing the database or a report",
    )

    list_parser = subparsers.add_parser(
        "list",
        help="show recent discoveries",
        description="Show discoveries newest first. This does not change the database.",
    )
    _add_db(list_parser)
    list_parser.add_argument("--batch", help="show only this import-batch id")
    list_parser.add_argument(
        "--study-area",
        help="filter by study-area id or alias, such as SF or new_york_city",
    )
    list_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="maximum rows to display (default: 20)",
    )
    list_parser.add_argument(
        "--status",
        choices=QUEUE_STATUSES,
        help="show only discoveries in this queue status",
    )
    list_parser.add_argument(
        "--study-areas",
        help="path to a study-area JSON file (default: the built-in configuration)",
    )

    export_parser = subparsers.add_parser(
        "export",
        help="export pending discoveries to CSV",
        description=(
            "Write a CSV sheet. By default this is the pending crawl queue. "
            "Pass --retrieved to write every discovery and the paths to its "
            "latest extracted files. Exporting does not change crawl_status."
        ),
    )
    _add_db(export_parser)
    export_parser.add_argument(
        "--retrieved",
        action="store_true",
        help="include retrieval results and paths to raw.html, content.md, metadata, and PDFs",
    )
    export_parser.add_argument(
        "--output",
        help="CSV path to create. Omit to write CSV to standard output.",
    )

    crawl_parser = subparsers.add_parser(
        "crawl",
        help="archive queued URLs",
        description=(
            "Fetch pending discoveries and save each attempt under its own folder. "
            "Repeated discoveries of the same normalized URL share one source. "
            "A real run first returns any leftover processing rows to pending. "
            "Dry-run only prints the queue."
        ),
    )
    _add_db(crawl_parser)
    crawl_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=5,
        help="maximum number of unique URLs to select (default: 5)",
    )
    crawl_parser.add_argument("--batch", help="select discoveries from this import batch only")
    crawl_parser.add_argument(
        "--study-area",
        help="select discoveries for this study-area id or alias, such as SF",
    )
    crawl_parser.add_argument(
        "--study-areas",
        help="path to a study-area JSON file (default: the built-in configuration)",
    )
    crawl_parser.add_argument(
        "--output-dir",
        default=DEFAULT_ARCHIVE_DIR,
        help=f"directory for archive folders (default: {DEFAULT_ARCHIVE_DIR})",
    )
    crawl_parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=30.0,
        help="per-request timeout in seconds (default: 30)",
    )
    crawl_parser.add_argument(
        "--concurrency",
        type=_positive_int,
        default=2,
        help="maximum URLs fetched at once (default: 2)",
    )
    crawl_parser.add_argument(
        "--host-delay",
        type=_nonnegative_float,
        default=1.0,
        help="seconds to wait between requests to the same host (default: 1)",
    )
    crawl_parser.add_argument(
        "--retries",
        type=_nonnegative_int,
        default=2,
        help="extra attempts for timeouts and temporary HTTP failures (default: 2)",
    )
    crawl_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected queue without fetching or changing the database or archive",
    )
    crawl_parser.add_argument(
        "--save-page-pdf",
        action="store_true",
        help="also save a Crawl4AI PDF snapshot of each HTML page",
    )
    crawl_parser.add_argument(
        "--refresh",
        action="store_true",
        help="fetch a new attempt even when an archive already exists",
    )
    crawl_parser.add_argument(
        "--retry",
        action="store_true",
        help="select failed, blocked, and not_found sources instead of the pending queue",
    )
    crawl_parser.add_argument(
        "--http-only",
        action="store_true",
        help="archive the HTTP response without starting Crawl4AI",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="run research analysis pass, validate evidence passages, and export findings",
        description="Run qualitative and quantitative research analysis on archived sources.",
    )
    _add_db(analyze_parser)
    analyze_parser.add_argument(
        "--output-dir",
        default="data/exports",
        help="output directory for JSON and CSV exports (default: data/exports)",
    )
    return parser


def command_import(args: argparse.Namespace) -> int:
    defaults = ImportDefaults(
        study_area=_clean(args.study_area),
        discovery_method=_clean(args.discovery_method),
        query=_clean(args.query),
        searched_at=_clean(args.searched_at),
    )
    summary = import_path(
        args.path,
        db_path=args.db,
        report_dir=args.report_dir,
        defaults=defaults,
        dry_run=args.dry_run,
        input_format=args.format,
        study_areas_path=args.study_areas,
    )
    print(format_summary(summary), end="")
    return 0


def command_list(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.study_areas)
    study_area = resolve_study_area_filter(args.study_area, catalog)
    batch_id = _clean(args.batch)
    rows, total = list_discoveries(
        Path(args.db).expanduser(),
        batch_id=batch_id,
        study_area=study_area,
        status=args.status,
        limit=args.limit,
    )
    print(format_list(rows, total=total, catalog=catalog), end="")
    return 0


def command_export(args: argparse.Namespace) -> int:
    database = Path(args.db).expanduser()
    export = export_retrievals if args.retrieved else export_pending
    label = "discoveries" if args.retrieved else "pending discoveries"
    if args.output:
        destination = Path(args.output).expanduser()
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8", newline="") as handle:
                count = export(database, handle)
        except OSError as exc:
            raise ImporterError(
                f"could not write {destination}: {exc.strerror}"
            ) from exc
        print(f"exported {count} {label} to {destination}", file=sys.stderr)
        return 0

    count = export(database, sys.stdout)
    print(f"exported {count} {label}", file=sys.stderr)
    return 0


def command_crawl(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.study_areas)
    study_area = resolve_study_area_filter(args.study_area, catalog)
    summary = run_crawl(
        CrawlOptions(
            db_path=Path(args.db).expanduser(),
            output_dir=Path(args.output_dir).expanduser(),
            limit=args.limit,
            batch_id=_clean(args.batch),
            study_area=study_area,
            timeout=args.timeout,
            sheet_path=Path(args.db).expanduser().parent / "exports" / "retrievals.csv",
            dry_run=args.dry_run,
            save_page_pdf=args.save_page_pdf,
            refresh=args.refresh,
            retry=args.retry,
            concurrency=args.concurrency,
            host_delay=args.host_delay,
            retries=args.retries,
            http_only=args.http_only,
        )
    )
    if summary.renderer_warning:
        print(f"warning: {summary.renderer_warning}", file=sys.stderr)
    print(format_crawl(summary), end="")
    return 0


def command_analyze(args: argparse.Namespace) -> int:
    from news_importer.analysis import (
        build_all_analyses,
        build_pass1_analyses,
        export_analysis_csv,
        export_analysis_json,
        export_inventory_csv,
        inventory_archived_sources,
    )

    db_path = Path(args.db).expanduser().resolve()
    base_dir = db_path.parent.parent
    archive_base = db_path.parent / "archive"
    out_dir = (base_dir / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory = inventory_archived_sources(db_path, archive_base)
    inv_csv = out_dir / "archived_sources_inventory.csv"
    export_inventory_csv(inventory, inv_csv)
    print(f"inventoried: {len(inventory)} attempts -> {inv_csv}")

    p1_entries = build_pass1_analyses(db_path, base_dir)
    p1_json_path = out_dir / "research_analysis_pass1.json"
    p1_csv_path = out_dir / "research_analysis_pass1.csv"
    export_analysis_json(p1_entries, p1_json_path)
    export_analysis_csv(p1_entries, p1_csv_path)
    print(f"pass 1 analyzed: {len(p1_entries)} core sources -> {p1_json_path}")

    all_entries = build_all_analyses(db_path, base_dir)
    all_json_path = out_dir / "research_analysis_all_sources.json"
    all_csv_path = out_dir / "research_analysis_all_sources.csv"
    export_analysis_json(all_entries, all_json_path)
    export_analysis_csv(all_entries, all_csv_path)
    print(f"all sources analyzed: {len(all_entries)} retrieved sources -> {all_json_path}")
    print(f"csv export: {all_csv_path}")
    return 0



def format_summary(summary: ImportSummary) -> str:
    lines = []
    if summary.dry_run:
        lines.append("dry run: no database changes and no report written")
    lines.append(f"file: {summary.source_filename}")
    lines.append(f"format: {summary.source_format}")
    lines.append(f"accepted: {summary.accepted}")
    lines.append(f"rejected: {summary.rejected}")
    lines.append(f"repeated_urls: {summary.repeated_urls}")
    lines.append(f"warnings: {summary.warnings}")
    if summary.dry_run:
        lines.append("batch_id: not created")
    else:
        lines.append(f"batch_id: {summary.batch_id}")
        lines.append(f"database: {summary.database_path}")
        lines.append(f"report: {summary.report_path}")
    if summary.repeated_normalized_urls:
        lines.append("repeated normalized URLs:")
        shown = summary.repeated_normalized_urls[:20]
        lines.extend(f"  {url}" for url in shown)
        hidden = len(summary.repeated_normalized_urls) - len(shown)
        if hidden:
            lines.append(f"  and {hidden} more")
    if summary.rejections:
        lines.append("rejected records:")
        for item in summary.rejections:
            reasons = "; ".join(reason.message for reason in item.reasons)
            lines.append(f"  record {item.record_number}: {reasons}")
    if summary.warning_rows:
        lines.append("warnings:")
        for item in summary.warning_rows:
            messages = "; ".join(warning.message for warning in item.warnings)
            lines.append(f"  record {item.record_number}: {messages}")
    lines.append("")
    return "\n".join(lines)


def format_list(rows, *, total: int, catalog: Catalog) -> str:
    showing = len(rows)
    lines = [f"showing {showing} of {total} discoveries"]
    if showing == 0:
        lines.append("")
        return "\n".join(lines)
    for row in rows:
        lines.append("")
        lines.append(row["id"])
        lines.append(f"  original_url: {row['original_url']}")
        lines.append(f"  normalized_url: {row['normalized_url']}")
        lines.append(f"  hostname: {row['hostname']}")
        lines.append(f"  study_area: {_study_area_label(row['study_area'], catalog)}")
        lines.append(f"  study_area_raw: {_null(row['study_area_raw'])}")
        lines.append(f"  discovery_method: {row['discovery_method']}")
        lines.append(f"  crawl_status: {row['crawl_status']}")
        if "last_outcome" in row.keys():
            lines.append(f"  last_outcome: {_null(row['last_outcome'])}")
            lines.append(f"  source_id: {_null(row['source_id'])}")
        if "archive_dir" in row.keys() and row["archive_dir"]:
            lines.append(f"  archive: {row['archive_dir']}")
        lines.append(f"  searched_at: {_null(row['searched_at'])}")
        lines.append(f"  result_rank: {_null(row['result_rank'])}")
        lines.append(f"  batch_id: {row['batch_id']}")
        lines.append(f"  source: {row['source_filename']}")
        lines.append(f"  record: {row['input_record_number']}")
        lines.append(f"  imported_at: {row['imported_at']}")
        lines.append(f"  repeat: {'yes' if row['is_repeat'] else 'no'}")
        lines.append(f"  warnings: {_warning_text(row['warnings_json'])}")
    lines.append("")
    return "\n".join(lines)


def _study_area_label(stored: str | None, catalog: Catalog) -> str:
    if stored is None:
        return "null"
    area = catalog.by_id.get(stored)
    if area is None:
        return f"{stored} (not in the study-area list)"
    return f"{area.display_name} ({area.id})"


def _warning_text(warnings_json: str) -> str:
    import json

    try:
        warnings = json.loads(warnings_json)
    except json.JSONDecodeError:
        return warnings_json
    if not warnings:
        return "none"
    return "; ".join(item.get("message", "") for item in warnings)


def _null(value: object) -> str:
    if value is None:
        return "null"
    return str(value)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def format_crawl(summary) -> str:
    lines = []
    if summary.dry_run:
        lines.append("dry run: no fetches and no database or archive changes")
    else:
        lines.append(f"recovered_processing: {summary.recovered_processing}")
    lines.append(f"selected: {summary.selected}")
    if summary.sheet_path:
        lines.append(f"retrievals: {summary.sheet_path}")
    if not summary.dry_run and summary.results:
        counts = Counter(item.outcome or "unknown" for item in summary.results)
        for outcome, count in sorted(counts.items()):
            lines.append(f"{outcome}: {count}")
    for item in summary.results:
        lines.append("")
        lines.append(item.requested_url)
        lines.append(f"  action: {item.action}")
        lines.append(f"  source_id: {item.source_id}")
        lines.append(f"  discoveries: {', '.join(item.discovery_ids)}")
        if item.outcome is not None:
            lines.append(f"  outcome: {item.outcome}")
        if item.crawl_status is not None:
            lines.append(f"  crawl_status: {item.crawl_status}")
        if item.http_status is not None:
            lines.append(f"  http_status: {item.http_status}")
        if item.attempt_id is not None:
            lines.append(f"  attempt_id: {item.attempt_id}")
        if item.archive_dir is not None:
            lines.append(f"  archive: {item.archive_dir}")
        if item.error:
            lines.append(f"  error: {item.error}")
    lines.append("")
    return "\n".join(lines)


def _positive_int(value: str) -> int:
    if not value.isdecimal() or int(value) < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return int(value)


def _nonnegative_int(value: str) -> int:
    if not value.isdecimal():
        raise argparse.ArgumentTypeError("value must be a non-negative integer")
    return int(value)


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("value must be a positive number") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be a positive number")
    return number


def _nonnegative_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("value must be a non-negative number") from None
    if number < 0:
        raise argparse.ArgumentTypeError("value must be a non-negative number")
    return number


def _add_db(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help=f"SQLite database path (default: {DEFAULT_DB})",
    )
