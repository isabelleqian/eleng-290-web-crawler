"""Turn input records into accepted discoveries or rejection reasons."""

from __future__ import annotations

import re

from news_importer.models import ImportDefaults, InputRecord, Issue, PreparedRow
from news_importer.study_areas import Catalog
from news_importer.urls import check_url, searched_at_error

ALLOWED_DISCOVERY_METHODS = (
    "google_first_page",
    "gemini",
    "grok_bot",
    "publisher_search",
    "other",
    "unknown",
)
_ALLOWED_METHOD_SET = set(ALLOWED_DISCOVERY_METHODS)
_POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*")


def prepare_record(
    record: InputRecord,
    defaults: ImportDefaults,
    catalog: Catalog,
) -> PreparedRow:
    """Validate one record. Blank cells inherit command-line defaults.

    A nonblank cell wins over a default. Invalid supplied values reject the
    record rather than falling back to the default. Missing optional metadata
    stays null.
    """
    rejections: list[Issue] = []
    url = check_url(record.known.get("url"))
    if not url.ok:
        rejections.append(Issue(url.code or "malformed_url", url.message or "invalid url", "url"))

    title = _cell(record, "title")
    query, _query_raw = _pick(record, "query", defaults.query)
    snippet = _cell(record, "snippet")
    search_language = _cell(record, "search_language")
    search_location = _cell(record, "search_location")
    notes = _cell(record, "notes")

    study_input, study_raw = _pick(record, "study_area", defaults.study_area)
    study_area, study_warning = _resolve_study_area(study_input, catalog)

    method_input, method_raw = _pick(record, "discovery_method", defaults.discovery_method)
    discovery_method, method_warning = _resolve_method(method_input)

    searched_at, searched_rejection = _resolve_searched_at(record, defaults)
    if searched_rejection is not None:
        rejections.append(searched_rejection)

    result_rank, rank_rejection, rank_missing = _resolve_rank(record)
    if rank_rejection is not None:
        rejections.append(rank_rejection)

    prepared = PreparedRow(
        record_number=record.record_number,
        original_record=dict(record.original_record),
        extra=dict(record.extra),
        rejections=rejections,
        original_url=record.known.get("url") if url.ok else record.known.get("url"),
        normalized_url=url.normalized if url.ok else None,
        hostname=url.hostname if url.ok else None,
        title=title,
        query=query,
        study_area=study_area,
        study_area_raw=study_raw,
        discovery_method=discovery_method,
        discovery_method_raw=method_raw,
        searched_at=searched_at,
        result_rank=result_rank,
        snippet=snippet,
        search_language=search_language,
        search_location=search_location,
        notes=notes,
    )
    if prepared.accepted:
        if study_warning is not None:
            prepared.warnings.append(study_warning)
        if method_warning is not None:
            prepared.warnings.append(method_warning)
        if discovery_method == "google_first_page":
            prepared.warnings.extend(
                _google_warnings(query, searched_at, rank_missing)
            )
    return prepared


def _cell(record: InputRecord, name: str) -> str | None:
    return _nonblank(record.known.get(name))


def _pick(
    record: InputRecord,
    name: str,
    default: str | None,
) -> tuple[str | None, str | None]:
    """Return (effective value, raw row value).

    The raw row value is null when the cell is blank and a default is used.
    """
    row_value = _nonblank(record.known.get(name))
    if row_value is not None:
        return row_value, row_value
    fallback = _nonblank(default)
    if fallback is not None:
        return fallback, None
    return None, None


def _nonblank(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text if text else None


def _resolve_study_area(
    value: str | None,
    catalog: Catalog,
) -> tuple[str | None, Issue | None]:
    if value is None:
        return None, Issue(
            "missing_study_area",
            "study_area is missing and was left null. "
            "The importer does not infer jurisdiction.",
            "study_area",
        )
    match = catalog.resolve(value)
    if match is None:
        return value, Issue(
            "unrecognized_study_area",
            f"study_area '{value}' is not in the study-area configuration. "
            "It was preserved for review and does not assign jurisdiction.",
            "study_area",
        )
    return match.id, None


def _resolve_method(value: str | None) -> tuple[str, Issue | None]:
    if value is None:
        return "unknown", None
    lowered = value.casefold()
    if lowered in _ALLOWED_METHOD_SET:
        return lowered, None
    return value, Issue(
        "unrecognized_discovery_method",
        f"discovery_method '{value}' is not one of: "
        f"{', '.join(ALLOWED_DISCOVERY_METHODS)}. It was preserved for review.",
        "discovery_method",
    )


def _resolve_searched_at(
    record: InputRecord,
    defaults: ImportDefaults,
) -> tuple[str | None, Issue | None]:
    row_value = record.known.get("searched_at")
    if row_value is not None and row_value.strip() != "":
        text = row_value.strip()
        message = searched_at_error(text)
        if message is not None:
            return None, Issue("invalid_searched_at", message, "searched_at")
        return text, None
    fallback = _nonblank(defaults.searched_at)
    if fallback is None:
        return None, None
    message = searched_at_error(fallback)
    if message is not None:
        return None, Issue("invalid_searched_at", message, "searched_at")
    return fallback, None


def _resolve_rank(record: InputRecord) -> tuple[int | None, Issue | None, bool]:
    raw = record.known.get("result_rank")
    if raw is None or raw.strip() == "":
        return None, None, True
    text = raw.strip()
    if _POSITIVE_INTEGER.fullmatch(text) is None:
        return None, Issue(
            "invalid_result_rank",
            "result_rank must be a positive integer",
            "result_rank",
        ), False
    return int(text), None, False


def _google_warnings(
    query: str | None,
    searched_at: str | None,
    rank_missing: bool,
) -> list[Issue]:
    warnings: list[Issue] = []
    missing = []
    if query is None:
        missing.append("query")
    if searched_at is None:
        missing.append("searched_at")
    if rank_missing:
        missing.append("result_rank")
    for field_name in missing:
        warnings.append(
            Issue(
                "missing_google_provenance",
                f"google_first_page record is missing {field_name}. "
                "The row was imported. This does not verify that the URL "
                "came from Google's first page.",
                field_name,
            )
        )
    return warnings
