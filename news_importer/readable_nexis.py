"""Convert Nexis metadata.json files into readable UTF-8 articles.

Run from the project root:
    python -m news_importer.readable_nexis path/to/metadata.json -o article.txt
    python -m news_importer.readable_nexis data/nexis

Uses only the Python standard library. Input files are never modified.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET


def local_name(element: ET.Element) -> str:
    """Ignore XML namespace prefixes when matching tags."""
    return element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""


def text_content(element: ET.Element) -> str:
    """Keep inline text and represent explicit line breaks as whitespace."""
    parts = [element.text or ""]
    for child in element:
        parts.append(" " if local_name(child) == "br" else text_content(child))
        parts.append(child.tail or "")
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def readable_article(metadata: dict) -> str:
    """Extract article paragraphs and selected provenance from Nexis XML."""
    raw = metadata.get("raw") or {}
    xml = (raw.get("Document") or {}).get("Content")
    if not isinstance(xml, str) or not xml.strip():
        raise ValueError("No article body found at raw.Document.Content.")
    # Do not allow custom entities or DTDs in externally supplied XML.
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", xml, re.IGNORECASE):
        raise ValueError("XML containing a DTD or entity declaration is unsupported.")
    root = ET.fromstring(xml)

    def first_text(tag: str) -> str:
        return next((text_content(e) for e in root.iter()
                     if local_name(e) == tag and text_content(e)), "")

    body = next((e for e in root.iter() if local_name(e) == "body.content"), None)
    if body is None:
        raise ValueError("No article body found: XML has no body.content element.")
    paragraphs = [text_content(e) for e in body.iter() if local_name(e) == "p"]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        raise ValueError("The article body contains no readable paragraphs.")

    fields = [
        ("Title", metadata.get("title") or raw.get("Title") or first_text("hl1")),
        ("Publication date", metadata.get("publication_date") or raw.get("Date")),
        ("Original publication", first_text("publicationName")),
        # Atom author/name often identifies LexisNexis, not the journalist.
        ("Author", raw.get("Byline") or first_text("byline")),
        ("Document ID", metadata.get("document_id") or raw.get("ResultId")),
        ("Database", (raw.get("Source") or {}).get("Name") or metadata.get("publisher")),
        ("Article URL", metadata.get("url") or raw.get("WebNewsUrl")),
        ("Search keywords", metadata.get("keywords")),
        ("Search query", metadata.get("nexis_expression")),
    ]
    header = [f"{label}: {value}" for label, value in fields if value]
    return "\n".join(header) + "\n\nARTICLE BODY\n\n" + "\n\n".join(paragraphs) + "\n"


def convert_file(metadata_path: Path, output: Path, overwrite: bool = False) -> None:
    """Write a readable article without modifying its input."""
    if output.resolve() == metadata_path.resolve():
        raise ValueError("Output must differ from the input metadata file.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a JSON object.")
    article = readable_article(metadata)
    with output.open("w" if overwrite else "x", encoding="utf-8") as stream:
        stream.write(article)


def convert_directory(root: Path, overwrite: bool = False) -> tuple[int, int, int]:
    """Find metadata recursively, skipping existing outputs and reporting failures."""
    if not root.is_dir():
        raise ValueError(f"Directory does not exist: {root}")
    paths = sorted(root.rglob("metadata.json"))
    if not paths:
        raise ValueError(f"No metadata.json files found under {root}")
    written = skipped = failed = 0
    for path in paths:
        output = path.with_name("readable_article.txt")
        if output.exists() and not overwrite:
            skipped += 1
            continue
        try:
            convert_file(path, output, overwrite)
        except (OSError, ValueError, ET.ParseError) as exc:
            failed += 1
            print(f"FAILED {path}: {exc}")
        else:
            written += 1
    print(f"Finished: {written} written, {skipped} skipped, {failed} failed.")
    return written, skipped, failed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path, nargs="?", default=Path("data/nexis"),
                        help="Metadata file or directory to search recursively (default: data/nexis)")
    parser.add_argument("-o", "--output", type=Path,
                        help="Output path for single-file mode only")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing outputs")
    args = parser.parse_args()
    try:
        if args.metadata.is_dir():
            if args.output:
                raise ValueError("--output is only supported for a single metadata file.")
            _, _, failed = convert_directory(args.metadata, args.overwrite)
            if failed:
                parser.exit(1)
        else:
            if not args.metadata.exists():
                raise ValueError(f"Input does not exist: {args.metadata}")
            output = args.output or args.metadata.with_name("readable_article.txt")
            convert_file(args.metadata, output, args.overwrite)
            print(f"Wrote {output.resolve()}")
    except (OSError, ValueError, ET.ParseError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
