"""Read CSV and one-URL-per-line text files."""

from __future__ import annotations

import csv
from pathlib import Path

from news_importer.errors import ImporterError
from news_importer.models import InputRecord

KNOWN_FIELDS = {
    "url",
    "title",
    "query",
    "study_area",
    "discovery_method",
    "searched_at",
    "result_rank",
    "snippet",
    "search_language",
    "search_location",
    "notes",
}


def read_records(path: Path, input_format: str | None) -> tuple[str, list[InputRecord]]:
    fmt = detect_format(path, input_format)
    if fmt == "csv":
        return fmt, read_csv(path)
    return fmt, read_txt(path)


def detect_format(path: Path, input_format: str | None) -> str:
    if input_format is not None:
        lowered = input_format.strip().lower()
        if lowered not in {"csv", "txt"}:
            raise ImporterError("format must be csv or txt")
        return lowered
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".txt", ".text"}:
        return "txt"
    raise ImporterError(
        f"cannot tell whether {path.name} is CSV or TXT. "
        "Pass --format csv or --format txt."
    )


def read_csv(path: Path) -> list[InputRecord]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            try:
                header = next(reader)
            except StopIteration:
                raise ImporterError(
                    f"{path}: CSV file is empty; expected a header row with a url column"
                ) from None
            specs = _header_specs(header, path)
            records: list[InputRecord] = []
            for row in reader:
                if len(row) == 0:
                    continue
                if len(row) > len(specs):
                    number = len(records) + 1
                    raise ImporterError(
                        f"{path}: CSV record {number} has more columns than the header"
                    )
                padded: list[str | None] = list(row) + [None] * (len(specs) - len(row))
                records.append(_record_from_cells(len(records) + 1, specs, padded))
            return records
    except UnicodeDecodeError as exc:
        raise ImporterError(f"{path}: file is not valid UTF-8 ({exc.reason})") from exc
    except csv.Error as exc:
        raise ImporterError(f"{path}: malformed CSV ({exc})") from exc


def read_txt(path: Path) -> list[InputRecord]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImporterError(f"{path}: file is not valid UTF-8 ({exc.reason})") from exc
    records: list[InputRecord] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            continue
        records.append(
            InputRecord(
                record_number=line_number,
                known={"url": line},
                extra={},
                original_record={"url": line},
            )
        )
    return records


def _header_specs(header: list[str], path: Path) -> list[tuple[str, str, str]]:
    """Return (kind, lookup key, original header label) for each column."""
    if len(header) == 0 or all(cell.strip() == "" for cell in header):
        raise ImporterError(
            f"{path}: CSV file is empty; expected a header row with a url column"
        )
    specs: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for cell in header:
        stripped = cell.strip()
        if stripped == "":
            raise ImporterError(f"{path}: CSV header contains an empty column name")
        folded = stripped.casefold()
        if folded in seen:
            raise ImporterError(f"{path}: CSV header contains duplicate column names")
        seen.add(folded)
        if folded in KNOWN_FIELDS:
            specs.append(("known", folded, stripped))
        else:
            specs.append(("extra", stripped, stripped))
    if "url" not in seen:
        raise ImporterError(f"{path}: CSV file is missing the required 'url' column")
    return specs


def _record_from_cells(
    record_number: int,
    specs: list[tuple[str, str, str]],
    cells: list[str | None],
) -> InputRecord:
    known: dict[str, str | None] = {}
    extra: dict[str, str | None] = {}
    original: dict[str, str | None] = {}
    for (kind, key, label), value in zip(specs, cells, strict=True):
        original[label] = value
        if kind == "known":
            known[key] = value
        else:
            extra[key] = value
    return InputRecord(
        record_number=record_number,
        known=known,
        extra=extra,
        original_record=original,
    )
