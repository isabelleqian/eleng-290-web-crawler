"""Search Nexis with a keyword list and store each hit in its own folder.

This uses the LexisNexis Web Services API (the Nexis news API available
through a library subscription). Credentials are read from the environment.
Tests pass a search function and do not call the network.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from news_importer.analysis import ANALYSIS_EXPORT_COLUMNS, publication_year
from news_importer.errors import ImporterError
from news_importer.nexis_query import (
    NexisQuery,
    build_nexis_query,
    build_raw_nexis_query,
    location_phrase_map,
    read_keyword_lines,
    read_raw_query,
)
from news_importer.study_areas import Catalog, load_catalog

TOKEN_URL = "https://auth-api.lexisnexis.com/oauth/v2/token"
SEARCH_URL = "https://services-api.lexisnexis.com/v1/News"
TOKEN_SCOPE = "http://oauth.lexisnexis.com/all"
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class NexisHit:
    document_id: str
    title: str
    publisher: str
    publication_date: str
    location: str
    url: str
    body: str
    raw: dict


@dataclass
class NexisOptions:
    keyword_path: Path | None = None
    query_expression: str | None = None
    query_path: Path | None = None
    output_dir: Path = Path("data/nexis")
    report_path: Path = Path("data/exports/nexis_report.csv")
    limit: int = 50
    dry_run: bool = False
    timeout: float = 60.0
    catalog: Catalog | None = None
    search: Callable[[str, int], list[NexisHit]] | None = None


@dataclass
class NexisSummary:
    dry_run: bool
    queries: list[NexisQuery] = field(default_factory=list)
    stored: int = 0
    report_path: str | None = None
    output_dir: str | None = None


class NexisClient:
    """OAuth client for the LexisNexis Web Services news search."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        token_url: str = TOKEN_URL,
        search_url: str = SEARCH_URL,
        scope: str = TOKEN_SCOPE,
        timeout: float = 60.0,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.search_url = search_url
        self.scope = scope
        self.timeout = timeout
        self._token: str | None = None

    def search(self, expression: str, limit: int) -> list[NexisHit]:
        hits: list[NexisHit] = []
        skip = 0
        while len(hits) < limit:
            top = min(50, limit - len(hits))
            params = urlencode(
                {
                    "$search": expression,
                    "$expand": "Document",
                    "$top": str(top),
                    "$skip": str(skip),
                }
            )
            payload = self._get_json(f"{self.search_url}?{params}")
            batch = parse_hits(payload)
            if not batch:
                break
            hits.extend(batch)
            skip += len(batch)
            if len(batch) < top:
                break
        return hits[:limit]

    def _access_token(self) -> str:
        if self._token:
            return self._token
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "scope": self.scope,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode("utf-8")
        request = Request(
            self.token_url,
            data=body,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        payload = _read_json(request, self.timeout, "Nexis token request failed")
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise ImporterError("Nexis token response did not include access_token")
        self._token = token
        return token

    def _get_json(self, url: str) -> dict:
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._access_token()}",
            },
            method="GET",
        )
        return _read_json(request, self.timeout, "Nexis search failed")


def run_nexis(options: NexisOptions) -> NexisSummary:
    if options.limit < 1:
        raise ImporterError("limit must be a positive integer")
    catalog = options.catalog or load_catalog()
    phrase_map = location_phrase_map(catalog)
    if options.query_expression:
        queries = [build_raw_nexis_query(options.query_expression)]
    elif options.query_path:
        queries = [build_raw_nexis_query(read_raw_query(options.query_path))]
    elif options.keyword_path:
        keywords = read_keyword_lines(options.keyword_path)
        queries = [build_nexis_query(line, phrase_map) for line in keywords]
    else:
        raise ImporterError("No keyword list or query expression provided.")
    summary = NexisSummary(dry_run=options.dry_run, queries=queries)
    if options.dry_run:
        return summary

    search = options.search or _client_from_environment(options.timeout).search
    rows: list[dict[str, str]] = []
    for query in queries:
        hits = search(query.expression, options.limit)
        for hit in hits:
            folder = _store_hit(options.output_dir, query, hit)
            rows.append(_report_row(query, hit, folder, catalog))
    _write_report(options.report_path, rows)
    summary.stored = len(rows)
    summary.report_path = str(options.report_path)
    summary.output_dir = str(options.output_dir)
    return summary


def parse_hits(payload: dict) -> list[NexisHit]:
    """Read a Nexis JSON search body into hits. Unknown shapes yield no hits."""
    values = payload.get("value")
    if values is None and isinstance(payload.get("results"), list):
        values = payload["results"]
    if not isinstance(values, list):
        return []
    hits: list[NexisHit] = []
    for item in values:
        if isinstance(item, dict):
            hits.append(_hit_from_record(item))
    return hits


def _load_env_file(path: Path) -> None:
    """Fill missing Nexis variables from a local .env file. Existing variables win."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        if not key.startswith("NEXIS_") or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def _client_from_environment(timeout: float) -> NexisClient:
    _load_env_file(Path(__file__).resolve().parents[1] / ".env")
    client_id = os.environ.get("NEXIS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NEXIS_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ImporterError(
            "Nexis credentials are missing. Set NEXIS_CLIENT_ID and NEXIS_CLIENT_SECRET "
            "from the library Web Services API approval."
        )
    return NexisClient(
        client_id,
        client_secret,
        token_url=os.environ.get("NEXIS_TOKEN_URL", TOKEN_URL),
        search_url=os.environ.get("NEXIS_SEARCH_URL", SEARCH_URL),
        scope=os.environ.get("NEXIS_SCOPE", TOKEN_SCOPE),
        timeout=timeout,
    )


def _hit_from_record(item: dict) -> NexisHit:
    document = item.get("Document") if isinstance(item.get("Document"), dict) else {}
    source = item.get("Source") if isinstance(item.get("Source"), dict) else {}
    title = _text(item, "Title", "Headline", "DocumentTitle") or _text(document, "Title", "Headline")
    publisher = (
        _text(item, "Publisher", "Publication", "SourceName")
        or _text(source, "Name", "SourceName")
        or _text(document, "SourceName", "Publication")
    )
    published = (
        _text(item, "Date", "Published", "PublishedDate", "PublicationDate")
        or _text(document, "Date", "PublishedDate", "PublicationDate")
    )
    location = _location(item) or _location(document)
    url = _text(item, "Link", "Url", "WebUrl", "DocumentLink") or _text(document, "Link", "Url")
    body = _text(item, "Content", "Body", "Text") or _text(document, "Content", "Body", "Text")
    document_id = (
        _text(item, "ResultId", "Id", "DocumentId", "id")
        or hashlib.sha256(f"{title}|{published}|{publisher}".encode("utf-8")).hexdigest()[:20]
    )
    return NexisHit(
        document_id=document_id,
        title=title,
        publisher=publisher,
        publication_date=published,
        location=location,
        url=url,
        body=body,
        raw=item,
    )


def _location(record: dict) -> str:
    for key in ("Geography", "GeographicLocation", "SubjectLocation", "Location"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list):
            parts = [str(item).strip() for item in value if str(item).strip()]
            if parts:
                return "; ".join(parts)
        if isinstance(value, dict):
            name = _text(value, "Name", "Value")
            if name:
                return name
    return ""


def _text(record: dict, *keys: str) -> str:
    folded = {str(key).casefold(): value for key, value in record.items()}
    for key in keys:
        value = folded.get(key.casefold())
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _store_hit(output_dir: Path, query: NexisQuery, hit: NexisHit) -> Path:
    folder = output_dir / _slug(query.keywords) / _slug(hit.document_id)
    folder.mkdir(parents=True, exist_ok=True)
    if hit.body:
        (folder / "content.txt").write_text(hit.body if hit.body.endswith("\n") else hit.body + "\n", encoding="utf-8")
    metadata = {
        "document_id": hit.document_id,
        "keywords": query.keywords,
        "nexis_expression": query.expression,
        "title": hit.title,
        "publisher": hit.publisher,
        "publication_date": hit.publication_date,
        "publication_year": publication_year(hit.publication_date),
        "location": _subject_location(query, hit),
        "url": hit.url,
        "raw": hit.raw,
    }
    (folder / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return folder


def _report_row(query: NexisQuery, hit: NexisHit, folder: Path, catalog: Catalog) -> dict[str, str]:
    location = _subject_location(query, hit)
    location_type = _location_type(location, catalog)
    row = {column: "" for column in ANALYSIS_EXPORT_COLUMNS}
    row.update(
        {
            "source_id": f"nexis_{hit.document_id}",
            "archive_attempt_id": hit.document_id,
            "title": hit.title,
            "publisher": hit.publisher,
            "publication_date": hit.publication_date,
            "publication_year": publication_year(hit.publication_date),
            "actual_jurisdiction": location,
            "target_location_type": location_type,
            "target_location": location,
            "location": location,
            "requested_url": hit.url,
            "archive_dir": str(folder),
        }
    )
    return row


def _subject_location(query: NexisQuery, hit: NexisHit) -> str:
    if hit.location:
        return hit.location
    if query.phrases:
        return "; ".join(query.phrases)
    return ""


def _location_type(location: str, catalog: Catalog) -> str:
    area = catalog.resolve(location)
    if area is None:
        return ""
    if area.kind == "state":
        return "State"
    if area.kind == "city":
        return "City"
    return ""


def _write_report(path: Path, rows: list[dict[str, str]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ANALYSIS_EXPORT_COLUMNS
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})


def _slug(value: str) -> str:
    text = _SAFE.sub("-", value.strip()).strip("-._")
    if text in {"", ".", ".."}:
        return "unknown"
    return text[:80]


def _read_json(request: Request, timeout: float, label: str) -> dict:
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise ImporterError(f"{label}: HTTP {exc.code} {detail}") from exc
    except URLError as exc:
        raise ImporterError(f"{label}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ImporterError(f"{label}: timed out") from exc
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ImporterError(f"{label}: response was not JSON") from exc
    if not isinstance(parsed, dict):
        raise ImporterError(f"{label}: response was not a JSON object")
    return parsed
