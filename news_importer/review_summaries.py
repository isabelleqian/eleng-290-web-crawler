"""Connect separate reviewed summaries to published pages without re-filtering."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWS = ROOT / "outputs/article_review_pilot/reviewed_results.csv"


def load_reviewed_summaries(path: Path = REVIEWS) -> dict[str, str]:
    """Use exact original identifiers; never infer matches from titles."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        summaries = {}
        for row in csv.DictReader(stream):
            source_id = row["source_id"]
            if source_id in summaries:
                raise ValueError(f"Duplicate reviewed source_id: {source_id}")
            summary = row["factual_summary"].strip()
            if summary:
                summaries[source_id] = summary
    return summaries


def apply_reviewed_summaries(payload, summaries: dict[str, str]):
    """Return a copy changing only existing summary fields on matched records."""
    if isinstance(payload, list):
        return [apply_reviewed_summaries(item, summaries) for item in payload]
    if isinstance(payload, dict):
        result = {key: apply_reviewed_summaries(value, summaries)
                  for key, value in payload.items()}
        source_id = payload.get("source_id") or payload.get("id")
        if "summary" in payload and source_id in summaries:
            result["summary"] = summaries[source_id]
        return result
    return payload


def refresh_page(path: Path, variable: str, summaries: dict[str, str]) -> None:
    """Refresh a saved page's JSON only, retaining its existing corpus and UI."""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"\b(?:let|const) {variable}\s*=\s*", text)
    if not match:
        raise ValueError(f"Missing {variable} payload in {path}")
    payload, length = json.JSONDecoder().raw_decode(text[match.end():])
    updated = apply_reviewed_summaries(payload, summaries)
    encoded = json.dumps(updated, ensure_ascii=False).replace("<", "\\u003c")
    text = text[:match.end()] + encoded + text[match.end() + length:]
    # Full reviewed summaries should remain visible in article rows.
    text = text.replace("leading-relaxed line-clamp-2", "leading-relaxed")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    summaries = load_reviewed_summaries()
    for page, variable in [("index.html", "DATA"), ("news_database.html", "ROWS")]:
        refresh_page(ROOT / "docs" / page, variable, summaries)
        print(f"Updated reviewed summaries in docs/{page}")


if __name__ == "__main__":
    main()
