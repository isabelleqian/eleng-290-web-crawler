"""Write one retrieval attempt to its own folder."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from news_importer.retrieve import FetchResult

_ATTEMPT_DIR = re.compile(r"attempt-(\d+)$")
_SAFE_PART = re.compile(r"[^A-Za-z0-9._-]+")


def source_id_for(normalized_url: str) -> str:
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()[:20]
    return f"src_{digest}"


def folder_study_area(study_areas: list[str | None]) -> str:
    """Pick one folder label from the study areas linked to a source."""
    unique: list[str] = []
    for area in study_areas:
        if area and area not in unique:
            unique.append(area)
    if len(unique) == 1:
        return _path_part(unique[0])
    if len(unique) > 1:
        return "mixed"
    return "unassigned"


def source_directory(
    output_dir: Path,
    *,
    source_id: str,
    hostname: str,
    normalized_url: str,
    study_areas: list[str | None],
) -> Path:
    """Build a browsable folder for one source.

    The path is study area, hostname, then a page name. The source id stays
    on the last folder so the directory still matches the database.
    """
    area = folder_study_area(study_areas)
    host = _path_part(hostname or "unknown-host")
    slug = _slug_from_url(normalized_url)
    return output_dir / area / host / f"{slug}--{source_id}"


def find_source_directory(output_dir: Path, source_id: str) -> Path | None:
    """Return the folder that already holds this source, including older hash folders."""
    if not output_dir.is_dir():
        return None
    direct = output_dir / source_id
    if direct.is_dir():
        return direct
    matches = [
        path
        for path in output_dir.rglob("*")
        if path.is_dir() and path.name.endswith(f"--{source_id}")
    ]
    if not matches:
        return None
    return sorted(matches)[0]


def next_attempt_number(source_dir: Path, existing_numbers: list[int]) -> int:
    disk_max = 0
    if source_dir.is_dir():
        for child in source_dir.iterdir():
            match = _ATTEMPT_DIR.fullmatch(child.name)
            if match:
                disk_max = max(disk_max, int(match.group(1)))
    return max([0, disk_max, *existing_numbers]) + 1


def _path_part(value: str) -> str:
    text = _SAFE_PART.sub("-", value.strip()).strip("-._")
    if text in {"", ".", ".."}:
        return "unknown"
    return text[:80]


def _slug_from_url(url: str) -> str:
    parts = urlsplit(url)
    segments = [segment for segment in parts.path.split("/") if segment]
    if not segments:
        leaf = "home"
    elif (
        len(segments) >= 2
        and segments[-1].isdigit()
        and not segments[-2].isdigit()
    ):
        leaf = f"{segments[-2]}-{segments[-1]}"
    else:
        leaf = segments[-1]
    if parts.query:
        leaf = f"{leaf}-{parts.query}"
    return _path_part(leaf).lower()


def write_attempt(
    directory: Path,
    result: FetchResult,
    *,
    source_id: str,
    attempt_id: str,
    attempt_number: int,
    normalized_url: str,
    retrieved_at: str,
    discovery_records: list[dict[str, str | None]],
    crawl_status: str,
) -> dict:
    """Save artifacts first and write metadata.json last.

    The directory is created only for this call. An existing attempt folder
    is left untouched.
    """
    artifacts = {
        "raw_html": "raw.html" if result.html is not None else None,
        "markdown": "content.md" if result.markdown else None,
        "metadata": "metadata.json",
        "original_pdf": "original.pdf" if result.original_pdf is not None else None,
        "page_pdf": "page.pdf" if result.page_pdf else None,
        "body": "body.bin" if result.body else None,
    }
    metadata = {
        "source_id": source_id,
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "requested_url": result.requested_url,
        "final_url": result.final_url,
        "renderer_final_url": result.renderer_final_url,
        "normalized_url": normalized_url,
        "retrieved_at": retrieved_at,
        "http_status": result.http_status,
        "content_type": result.content_type,
        "observed_title": result.observed_title,
        "publication_date": result.publication_date,
        "outcome": result.outcome,
        "crawl_status": crawl_status,
        "source_kind": result.source_kind,
        "quality_flags": [flag.as_dict() for flag in result.quality_flags],
        "errors": result.errors or None,
        "pdf_link_candidates": result.pdf_link_candidates,
        "discovery_records": discovery_records,
        "artifacts": artifacts,
        "renderer": result.renderer,
        "renderer_version": result.renderer_version,
        "retries_used": result.retries_used,
        "notes": _kind_note(result.source_kind),
    }
    directory.mkdir(parents=True, exist_ok=False)
    if result.html is not None:
        (directory / "raw.html").write_text(result.html, encoding="utf-8")
    if result.markdown:
        (directory / "content.md").write_text(result.markdown + "\n", encoding="utf-8")
    if result.original_pdf is not None:
        (directory / "original.pdf").write_bytes(result.original_pdf)
    if result.page_pdf:
        (directory / "page.pdf").write_bytes(result.page_pdf)
    if result.body:
        (directory / "body.bin").write_bytes(result.body)
    (directory / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return metadata


def _kind_note(source_kind: str) -> str:
    if source_kind == "original_pdf":
        return "original.pdf is the publisher file from the queued URL."
    if source_kind == "html":
        return (
            "page.pdf, when present, is a snapshot of the rendered HTML page. "
            "It is not an original PDF document."
        )
    return "body.bin is the response body. It was not treated as HTML or an original PDF."
