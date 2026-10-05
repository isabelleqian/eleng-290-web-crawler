"""Data passed between reading, validation, storage, and the command line."""

from __future__ import annotations

from dataclasses import dataclass, field


def dump_compact(value: object) -> str:
    """Serialize metadata for a database column."""
    import json

    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class ImportDefaults:
    """Values used only when the corresponding input cell is blank."""

    study_area: str | None = None
    discovery_method: str | None = None
    query: str | None = None
    searched_at: str | None = None

    def as_json(self) -> dict[str, str | None]:
        return {
            "study_area": self.study_area,
            "discovery_method": self.discovery_method,
            "query": self.query,
            "searched_at": self.searched_at,
        }


@dataclass(frozen=True)
class InputRecord:
    """One CSV row or one nonblank text line, before validation."""

    record_number: int
    known: dict[str, str | None]
    extra: dict[str, str | None]
    original_record: dict[str, str | None]


@dataclass(frozen=True)
class Issue:
    """A rejection reason or a review warning."""

    code: str
    message: str
    field: str | None = None

    def as_dict(self) -> dict[str, str]:
        payload = {"code": self.code, "message": self.message}
        if self.field is not None:
            payload["field"] = self.field
        return payload


@dataclass
class PreparedRow:
    """A validated input record. Rejected rows are not inserted."""

    record_number: int
    original_record: dict[str, str | None]
    extra: dict[str, str | None]
    rejections: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    original_url: str | None = None
    normalized_url: str | None = None
    hostname: str | None = None
    title: str | None = None
    query: str | None = None
    study_area: str | None = None
    study_area_raw: str | None = None
    discovery_method: str | None = None
    discovery_method_raw: str | None = None
    searched_at: str | None = None
    result_rank: int | None = None
    snippet: str | None = None
    search_language: str | None = None
    search_location: str | None = None
    notes: str | None = None

    @property
    def accepted(self) -> bool:
        return not self.rejections


@dataclass(frozen=True)
class RejectionView:
    record_number: int
    reasons: list[Issue]
    original_record: dict[str, str | None]


@dataclass(frozen=True)
class WarningView:
    record_number: int
    discovery_id: str | None
    normalized_url: str
    warnings: list[Issue]


@dataclass
class ImportSummary:
    """Counts and detail printed by the import command and stored in the report."""

    dry_run: bool
    source_filename: str
    source_format: str
    batch_id: str | None
    imported_at: str | None
    database_path: str
    report_path: str | None
    defaults: ImportDefaults
    accepted: int
    rejected: int
    repeated_urls: int
    warnings: int
    records_with_warnings: int
    repeated_normalized_urls: list[str]
    rejections: list[RejectionView]
    warning_rows: list[WarningView]
