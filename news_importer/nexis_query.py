"""Turn a keyword list into a Nexis search where every term must hit.

A multi-word place name is sent as one phrase. "Los Angeles Waze" requires
the words Los Angeles next to each other, and also requires Waze. It does
not match an article that only has Los in one sentence and Angeles in another.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from news_importer.errors import ImporterError
from news_importer.study_areas import Catalog, alias_key, load_catalog

# Places that are more than one word and are not already a study-area name.
# Longer names in the catalog are matched first, so "New York City" stays intact.
_EXTRA_LOCATION_PHRASES = ("New York",)

_QUOTE = re.compile(r'"([^"]+)"')
REMEMBERED_KEYWORDS = Path(__file__).resolve().parents[1] / "queries" / "nexis_keywords.txt"


@dataclass(frozen=True)
class NexisQuery:
    keywords: str
    expression: str
    phrases: tuple[str, ...]
    words: tuple[str, ...]

    @property
    def location_phrases(self) -> tuple[str, ...]:
        return self.phrases


def location_phrase_map(catalog: Catalog | None = None) -> dict[str, str]:
    """Map a folded place name to the spelling sent to Nexis."""
    catalog = load_catalog() if catalog is None else catalog
    phrases: dict[str, str] = {}
    for area in catalog.areas:
        if " " in area.name.strip():
            phrases[alias_key(area.name)] = area.name
        for alias in area.aliases:
            text = alias.strip()
            if " " not in text or "(" in text:
                continue
            phrases.setdefault(alias_key(text), _title_phrase(text))
    for extra in _EXTRA_LOCATION_PHRASES:
        phrases.setdefault(alias_key(extra), extra)
    return phrases


def build_nexis_query(keywords: str, phrases: dict[str, str] | None = None) -> NexisQuery:
    """Require every keyword. Quote each multi-word location as a phrase."""
    text = keywords.strip()
    if not text:
        raise ImporterError("a keyword line is empty")
    phrase_map = location_phrase_map() if phrases is None else phrases
    quoted, remainder = _quoted_phrases(text)
    tokens = [token for token in remainder.split() if token]
    _reject_boolean_or(tokens)
    terms = _match_locations(
        [token for token in tokens if token.casefold() != "and"],
        phrase_map,
    )
    phrases_out = list(quoted)
    words: list[str] = []
    for kind, value in terms:
        if kind == "phrase":
            phrases_out.append(value)
        else:
            words.append(value)
    if not phrases_out and not words:
        raise ImporterError(f"keyword line has no search terms: {keywords}")
    parts = [f'"{phrase}"' for phrase in phrases_out] + words
    return NexisQuery(
        keywords=text,
        expression=" AND ".join(parts),
        phrases=tuple(phrases_out),
        words=tuple(words),
    )


def build_raw_nexis_query(expression: str) -> NexisQuery:
    """Wrap a raw Nexis Boolean/proximity search expression."""
    text = expression.strip()
    if not text:
        raise ImporterError("raw query expression is empty")
    return NexisQuery(
        keywords=text,
        expression=text,
        phrases=(),
        words=(),
    )


def read_raw_query(path: Path) -> str:
    """Read a raw query expression from a text file, ignoring comment lines."""
    if not path.is_file():
        raise ImporterError(f"query file not found: {path}")
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ImporterError(f"query file is not valid UTF-8 ({path}): {exc.reason}") from exc
    lines = [
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    query = " ".join(" ".join(lines).split())
    if not query:
        raise ImporterError(f"query file has no search expression: {path}")
    return query


def save_keyword_list(source: Path, destination: Path | None = None) -> list[str]:
    """Store a keyword text list and keep that exact list for later searches."""
    stored = REMEMBERED_KEYWORDS if destination is None else destination
    lines = read_keyword_lines(source)
    phrase_map = location_phrase_map()
    for line in lines:
        build_nexis_query(line, phrase_map)
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def load_keyword_list(path: Path | None = None) -> list[str]:
    """Return the keyword list saved earlier."""
    stored = REMEMBERED_KEYWORDS if path is None else path
    if not stored.is_file():
        raise ImporterError(
            "No keyword list is saved yet. "
            "Save a text file with: python3 -m news_importer keywords save your-list.txt"
        )
    try:
        return read_keyword_lines(stored)
    except ImporterError as exc:
        if "no searches" in str(exc):
            raise ImporterError(
                "No keyword list is saved yet. "
                "Save a text file with: python3 -m news_importer keywords save your-list.txt"
            ) from exc
        raise


def read_keyword_lines(path: Path) -> list[str]:
    """Read one required-keyword search per record.

    A text file has one search per line. A JSON file is a list of strings.
    A CSV file must have a `keywords` column. The archived Google query file,
    which uses a `query` column and OR, is not accepted here.
    """
    if not path.is_file():
        raise ImporterError(f"keyword file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _read_json_keywords(path)
    if suffix == ".csv":
        return _read_csv_keywords(path)
    return _read_text_keywords(path)


def _quoted_phrases(text: str) -> tuple[list[str], str]:
    found: list[str] = []

    def replace(match: re.Match[str]) -> str:
        phrase = " ".join(match.group(1).split())
        if phrase:
            found.append(phrase)
        return " "

    return found, _QUOTE.sub(replace, text)


def _reject_boolean_or(tokens: list[str]) -> None:
    for token in tokens:
        if token.casefold() in {"or", "not"}:
            raise ImporterError(
                "Nexis keyword searches require every word. "
                "OR and NOT belong to the archived Google search queries. "
                f"Remove '{token}' and list only the words that must all appear."
            )


def _match_locations(
    tokens: list[str],
    phrases: dict[str, str],
) -> list[tuple[str, str]]:
    lengths = sorted({len(key.split()) for key in phrases}, reverse=True)
    index = 0
    matched: list[tuple[str, str]] = []
    while index < len(tokens):
        found = False
        for length in lengths:
            window = tokens[index : index + length]
            if len(window) < length:
                continue
            key = alias_key(" ".join(window))
            if key in phrases:
                matched.append(("phrase", phrases[key]))
                index += length
                found = True
                break
        if not found:
            matched.append(("word", tokens[index]))
            index += 1
    return matched


def _title_phrase(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:] if part else part for part in value.split())


def _read_text_keywords(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ImporterError(f"keyword file is not valid UTF-8 ({path}): {exc.reason}") from exc
    keywords = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]
    if not keywords:
        raise ImporterError(f"keyword file has no searches: {path}")
    return keywords


def _read_json_keywords(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ImporterError(f"keyword file is not valid JSON ({path}): {exc.msg}") from exc
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ImporterError(f"keyword JSON must be a list of strings: {path}")
    keywords = [item.strip() for item in payload if item.strip()]
    if not keywords:
        raise ImporterError(f"keyword file has no searches: {path}")
    return keywords


def _read_csv_keywords(path: Path) -> list[str]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ImporterError(f"keyword CSV has no header: {path}")
            fields = {name.strip().casefold(): name for name in reader.fieldnames}
            if "keywords" not in fields:
                raise ImporterError(
                    f"{path} has no keywords column. "
                    "Google search files that use a query column are archived. "
                    "Put one required-keyword search in each keywords cell."
                )
            column = fields["keywords"]
            keywords = [
                (row.get(column) or "").strip()
                for row in reader
                if (row.get(column) or "").strip()
            ]
    except UnicodeDecodeError as exc:
        raise ImporterError(f"keyword file is not valid UTF-8 ({path}): {exc.reason}") from exc
    if not keywords:
        raise ImporterError(f"keyword file has no searches: {path}")
    return keywords
