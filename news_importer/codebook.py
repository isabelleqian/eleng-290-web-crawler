"""Load sheet 1012_codebook and match article text to its measures.

Only that sheet is read. A category row groups measures. A measure row is
matched on its name, on phrases in quotation marks, and on the example list
in its definition. An article that contains none of those phrases stays
unlabeled.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from news_importer.errors import ImporterError

SHEET_NAME = "1012_codebook"
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_CODE = re.compile(r"^([A-F])(\d+)?\.\s+(.+)$")
_QUOTED = re.compile(r"[\"“]([^\"”]+)[\"”]")
_EXAMPLES = re.compile(r"(?:Examples include|This includes)\s+(.+)", re.IGNORECASE)
_HYPHEN = re.compile(r"[-‐‑–—/]+")
_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Category:
    code: str
    name: str
    definition: str


@dataclass(frozen=True)
class Measure:
    code: str
    category_code: str
    name: str
    definition: str
    phrases: tuple[str, ...]


@dataclass(frozen=True)
class Codebook:
    categories: tuple[Category, ...]
    measures: tuple[Measure, ...]

    def category(self, code: str) -> Category | None:
        for item in self.categories:
            if item.code == code:
                return item
        return None


def default_codebook_path() -> Path:
    return Path(__file__).resolve().parents[2] / "Codebook for routing app measures.xlsx"


def load_codebook(path: Path | None = None) -> Codebook:
    """Read categories and measures from sheet 1012_codebook."""
    workbook = default_codebook_path() if path is None else path
    if not workbook.is_file():
        raise ImporterError(f"codebook workbook not found: {workbook}")
    rows = _read_sheet_rows(workbook, SHEET_NAME)
    return parse_codebook_rows(rows)


def parse_codebook_rows(rows: list[tuple[str, str]]) -> Codebook:
    """Build the codebook from (name, definition) rows. The header row is skipped."""
    categories: list[Category] = []
    measures: list[Measure] = []
    for name, definition in rows:
        parsed = _parse_label(name)
        if parsed is None:
            continue
        letter, number, label = parsed
        text = " ".join(definition.split())
        if number is None:
            categories.append(Category(code=letter, name=label, definition=text))
            continue
        measures.append(
            Measure(
                code=f"{letter}{number}",
                category_code=letter,
                name=label,
                definition=text,
                phrases=tuple(match_phrases(label, text)),
            )
        )
    if not measures:
        raise ImporterError(f"sheet {SHEET_NAME} has no measures")
    return Codebook(categories=tuple(categories), measures=tuple(measures))


_SUCH_AS = re.compile(r"(?:such as|including)\s+([^.]*)", re.IGNORECASE)


def search_phrases(name: str, definition: str) -> list[str]:
    """Phrases to send to Nexis: the measure name, quoted terms, and example lists.

    A whole definition sentence is not quoted as one search. News copy rarely
    repeats a codebook sentence. List items inside the definition are searched.
    """
    found: list[str] = []
    seen: set[str] = set()

    def add(phrase: str, *, allow_single: bool, keep_name: bool = False) -> None:
        cleaned = phrase.replace("“", " ").replace("”", " ").replace('"', " ")
        cleaned = cleaned.replace("–", "-").replace("—", "-")
        cleaned = " ".join(cleaned.split()).strip(" .;")
        cleaned = re.sub(r"^(and|or)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            return
        key = normalize_phrase(cleaned)
        words = key.split()
        if not words or key in seen:
            return
        if not keep_name:
            if len(words) > 8 or key.startswith("the "):
                return
            if words[-1] in {"based", "specific", "dependent", "related"}:
                return
            if re.search(r"\b(and|or)\b", key) and len(words) > 4:
                return
            if len(words) == 1 and (not allow_single or len(words[0]) < 6):
                return
        seen.add(key)
        found.append(cleaned)

    add(name, allow_single=False, keep_name=True)
    for quoted in _QUOTED.findall(definition):
        add(quoted, allow_single=False)
    example_match = _EXAMPLES.search(definition)
    body = definition[: example_match.start()] if example_match else definition
    list_text = ""
    if example_match:
        list_text = example_match.group(1)
    for such in _SUCH_AS.findall(body):
        list_text = f"{list_text}, {such}"
    if list_text:
        plain = list_text.replace("“", " ").replace("”", " ").replace('"', " ")
        for part in re.split(r",|\band\b|\bor\b", plain):
            add(part, allow_single=True)
    return found


def match_phrases(name: str, definition: str) -> list[str]:
    """Phrases from the measure name, quoted terms, and the example list."""
    found: list[str] = []
    seen: set[str] = set()

    def add(phrase: str) -> None:
        cleaned = " ".join(phrase.split()).strip(" .;")
        if not _is_match_phrase(cleaned):
            return
        key = normalize_phrase(cleaned)
        words = key.split()
        if len(words) < 2 or key in seen:
            return
        seen.add(key)
        found.append(cleaned)

    add(name)
    for quoted in _QUOTED.findall(definition):
        add(quoted)
    example_match = _EXAMPLES.search(definition)
    if example_match:
        for part in example_match.group(1).split(","):
            part = re.sub(r"^(and|or)\s+", "", part.strip(), flags=re.IGNORECASE)
            add(part.rstrip("."))
    return found


def _is_match_phrase(phrase: str) -> bool:
    """Keep real phrases and distinctive hyphenated terms. Drop bare modifiers such as location-based."""
    if " " in phrase:
        return True
    if "-" not in phrase:
        return False
    folded = phrase.casefold()
    return not folded.endswith(("-based", "-specific", "-dependent", "-related"))


def normalize_phrase(text: str) -> str:
    """Fold case and treat a hyphen as a space so phrase matching stays exact."""
    folded = text.casefold().replace("’", "'")
    folded = _HYPHEN.sub(" ", folded)
    folded = _PUNCT.sub(" ", folded)
    return _SPACE.sub(" ", folded).strip()


def compiled_phrases(
    codebook: Codebook,
) -> tuple[tuple[str, tuple[re.Pattern[str], ...]], ...]:
    """Compile each measure's phrases once before scanning a large archive."""
    compiled: list[tuple[str, tuple[re.Pattern[str], ...]]] = []
    for measure in codebook.measures:
        patterns = tuple(
            re.compile(rf"(?<!\w){re.escape(normalize_phrase(phrase))}(?!\w)")
            for phrase in measure.phrases
            if normalize_phrase(phrase)
        )
        compiled.append((measure.code, patterns))
    return tuple(compiled)


def matching_measures(
    text: str,
    codebook: Codebook | None = None,
    compiled: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] | None = None,
) -> list[str]:
    """Return measure codes whose phrases appear in text. Order follows the codebook."""
    haystack = normalize_phrase(text)
    if not haystack:
        return []
    patterns = compiled if compiled is not None else compiled_phrases(codebook or Codebook((), ()))
    matched: list[str] = []
    for code, phrase_patterns in patterns:
        if any(pattern.search(haystack) for pattern in phrase_patterns):
            matched.append(code)
    return matched


def _parse_label(name: str) -> tuple[str, str | None, str] | None:
    match = _CODE.match(" ".join(name.split()))
    if match is None:
        return None
    return match.group(1), match.group(2), match.group(3).strip()


def _read_sheet_rows(workbook: Path, sheet_name: str) -> list[tuple[str, str]]:
    try:
        archive = zipfile.ZipFile(workbook)
    except zipfile.BadZipFile as exc:
        raise ImporterError(f"codebook workbook is not an xlsx file: {workbook}") from exc
    with archive:
        sheet_path = _sheet_path(archive, sheet_name)
        strings = _shared_strings(archive)
        return _sheet_pairs(archive.read(sheet_path), strings)


def _sheet_path(archive: zipfile.ZipFile, sheet_name: str) -> str:
    root = ET.fromstring(archive.read("xl/workbook.xml"))
    wanted: str | None = None
    for sheet in root.findall(f"{_NS}sheets/{_NS}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            wanted = sheet.attrib.get(f"{_REL}id")
            break
    if not wanted:
        raise ImporterError(f"workbook has no sheet named {sheet_name}")
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for rel in rels:
        if rel.attrib.get("Id") == wanted:
            target = rel.attrib.get("Target", "")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ImporterError(f"workbook relationship for {sheet_name} is missing")


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(f"{_NS}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{_NS}t")))
    return values


def _sheet_pairs(payload: bytes, strings: list[str]) -> list[tuple[str, str]]:
    root = ET.fromstring(payload)
    cells: dict[int, dict[int, str]] = {}
    for cell in root.iter(f"{_NS}c"):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        column, row = _cell_ref(ref)
        cells.setdefault(row, {})[column] = _cell_text(cell, strings)
    pairs: list[tuple[str, str]] = []
    for row in sorted(cells):
        pairs.append((cells[row].get(1, ""), cells[row].get(2, "")))
    return pairs


def _cell_ref(ref: str) -> tuple[int, int]:
    letters = "".join(char for char in ref if char.isalpha())
    numbers = "".join(char for char in ref if char.isdigit())
    column = 0
    for char in letters:
        column = column * 26 + (ord(char.upper()) - 64)
    return column, int(numbers)


def _cell_text(cell: ET.Element, strings: list[str]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find(f"{_NS}v")
    inline = cell.find(f"{_NS}is")
    if kind == "s" and value is not None and value.text:
        index = int(value.text)
        return strings[index] if 0 <= index < len(strings) else ""
    if kind == "inlineStr" and inline is not None:
        return "".join(node.text or "" for node in inline.iter(f"{_NS}t"))
    if value is not None and value.text:
        return value.text
    return ""
