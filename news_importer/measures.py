"""Tag saved articles with codebook measures and rank them on a dashboard page.

Existing analysis columns are left as they are. Tags are stored beside them.
Measure names are also sent to Nexis as phrases, together with the app group
from the saved United States overview query.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from news_importer.analysis import strip_markup
from news_importer.codebook import Codebook, Measure, load_codebook, normalize_phrase, search_phrases
from news_importer.crawl_nexis_us import is_us_hit
from news_importer.errors import ImporterError
from news_importer.nexis import NexisHit, _client_from_environment, _store_hit
from news_importer.nexis_query import NexisQuery, read_raw_query

OVERVIEW_QUERY = Path(__file__).resolve().parents[1] / "queries" / "nexis_us_overview_query.txt"
MEASURE_QUERIES = Path(__file__).resolve().parents[1] / "queries" / "nexis_measure_queries.txt"
_TITLE_PUNCT = re.compile(r"[^a-z0-9]+")


@dataclass
class TaggedArticle:
    article_id: str
    title: str
    publisher: str
    publication_date: str
    location: str
    url: str
    archive_dir: str
    origin: str
    measures: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, str | list[str]]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "publisher": self.publisher,
            "publication_date": self.publication_date,
            "location": self.location,
            "url": self.url,
            "archive_dir": self.archive_dir,
            "origin": self.origin,
            "measures": list(self.measures),
        }


@dataclass
class MeasureSearchResult:
    queries: list[NexisQuery]
    stored: int = 0
    skipped_existing: int = 0
    skipped_outside_us: int = 0


def app_group_expression(overview_text: str | None = None) -> str:
    """Return the opening app-group block from the saved overview query."""
    text = overview_text if overview_text is not None else read_raw_query(OVERVIEW_QUERY)
    text = text.strip()
    if not text.startswith("("):
        raise ImporterError("the overview query does not start with the app group")
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                group = text[: index + 1].strip()
                if "Waze" not in group or '"Google Maps"' not in group:
                    raise ImporterError("the overview app group is missing the routing-app terms")
                return group
    raise ImporterError("the overview app group is not closed")


def measure_queries(codebook: Codebook, app_group: str | None = None) -> list[NexisQuery]:
    """One Nexis search per codebook phrase, combined with the app group.

    Phrases are the measure name, quoted definition terms, and items in the
    example or "such as" lists. The same phrase is searched once.
    """
    group = app_group_expression() if app_group is None else app_group
    queries: list[NexisQuery] = []
    seen: set[str] = set()
    for measure in codebook.measures:
        for phrase in search_phrases(measure.name, measure.definition):
            key = normalize_phrase(phrase)
            if key in seen:
                continue
            seen.add(key)
            queries.append(
                NexisQuery(
                    keywords=phrase,
                    expression=f'{group} AND "{phrase}"',
                    phrases=(phrase,),
                    words=(),
                )
            )
    return queries


def write_measure_queries(queries: list[NexisQuery], path: Path | None = None) -> Path:
    destination = MEASURE_QUERIES if path is None else path
    lines = [
        "# Codebook phrases from sheet 1012_codebook.",
        "# Each line is the overview app group AND one phrase.",
        "# Phrases are measure names, quoted definition terms, and example-list items.",
        "# Geography = United States is applied to the results.",
    ]
    lines.extend(query.expression for query in queries)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination


def search_measures(
    codebook: Codebook,
    *,
    output_dir: Path,
    limit: int,
    timeout: float = 60.0,
    search: Callable[[str, int], list[NexisHit]] | None = None,
    dry_run: bool = False,
    query_path: Path | None = None,
) -> MeasureSearchResult:
    """Store new United States hits for each measure-name search."""
    if limit < 1:
        raise ImporterError("limit must be a positive integer")
    queries = measure_queries(codebook)
    result = MeasureSearchResult(queries=queries)
    write_measure_queries(queries, query_path)
    if dry_run:
        return result
    client_search = search or _client_from_environment(timeout).search
    known_ids = _known_document_ids(output_dir)
    for index, query in enumerate(queries, start=1):
        if search is None:
            print(f"search {index} of {len(queries)}: {query.keywords}", file=sys.stderr)
        hits = client_search(query.expression, limit)
        for hit in hits:
            if not isinstance(hit, NexisHit):
                continue
            document_id = hit.document_id
            short_id = document_id.replace("urn:contentItem:", "")
            if document_id in known_ids or short_id in known_ids:
                result.skipped_existing += 1
                continue
            kept, location, _location_type = is_us_hit(hit)
            if not kept:
                result.skipped_outside_us += 1
                known_ids.add(document_id)
                continue
            if location and not hit.location:
                hit.location = location
            _store_hit(output_dir, query, hit)
            known_ids.add(document_id)
            known_ids.add(short_id)
            result.stored += 1
    return result


def tag_articles(
    codebook: Codebook,
    *,
    archive_dir: Path,
    nexis_dir: Path,
) -> list[TaggedArticle]:
    """Match saved archive pages and Nexis hits. Unmatched articles stay unlabeled."""
    from news_importer.codebook import compiled_phrases, matching_measures

    compiled = compiled_phrases(codebook)
    pending: list[tuple[TaggedArticle, str]] = []
    if archive_dir.is_dir():
        pending.extend(_archive_articles(archive_dir))
    if nexis_dir.is_dir():
        pending.extend(_nexis_articles(nexis_dir))
    tagged: list[TaggedArticle] = []
    for index, (article, text) in enumerate(pending, start=1):
        article.measures = matching_measures(f"{article.title}\n{text}", compiled=compiled)
        tagged.append(article)
        if index % 250 == 0:
            print(f"tagged {index} of {len(pending)} articles", file=sys.stderr)
    return _dedupe_articles(tagged)


def write_tags(articles: list[TaggedArticle], codebook: Codebook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sheet": "1012_codebook",
        "categories": [
            {"code": item.code, "name": item.name, "definition": item.definition}
            for item in codebook.categories
        ],
        "measures": [
            _measure_summary(measure, articles) for measure in codebook.measures
        ],
        "articles": [article.as_dict() for article in articles],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_path = path.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "article_id",
                "origin",
                "title",
                "publisher",
                "publication_date",
                "location",
                "url",
                "archive_dir",
                "measures",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for article in articles:
            row = article.as_dict()
            row["measures"] = "; ".join(article.measures)
            writer.writerow(row)


def render_dashboard(articles: list[TaggedArticle], codebook: Codebook) -> str:
    """A page of categories and measures, ranked by tagged article count."""
    ranked = sorted(
        codebook.measures,
        key=lambda measure: (-_count(articles, measure.code), measure.code),
    )
    payload = {
        "categories": [
            {"code": item.code, "name": item.name, "definition": item.definition}
            for item in codebook.categories
        ],
        "measures": [
            {
                **_measure_summary(measure, articles),
                "category_name": _category_name(codebook, measure.category_code),
            }
            for measure in ranked
        ],
        "articles": [
            {
                "article_id": article.article_id,
                "title": article.title or article.article_id,
                "publisher": article.publisher,
                "publication_date": article.publication_date,
                "location": article.location,
                "url": article.url,
                "origin": article.origin,
                "measures": article.measures,
            }
            for article in articles
            if article.measures
        ],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    labeled = sum(1 for article in articles if article.measures)
    unlabeled = len(articles) - labeled
    return _DASHBOARD_HTML.format(
        data=data,
        article_count=len(articles),
        labeled_count=labeled,
        unlabeled_count=unlabeled,
        measure_count=len(codebook.measures),
    )


def write_dashboard(articles: list[TaggedArticle], codebook: Codebook, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard(articles, codebook), encoding="utf-8")
    return path


def _measure_summary(measure: Measure, articles: list[TaggedArticle]) -> dict[str, object]:
    return {
        "code": measure.code,
        "category": measure.category_code,
        "name": measure.name,
        "definition": measure.definition,
        "count": _count(articles, measure.code),
    }


def _count(articles: list[TaggedArticle], code: str) -> int:
    return sum(1 for article in articles if code in article.measures)


def _category_name(codebook: Codebook, code: str) -> str:
    category = codebook.category(code)
    return category.name if category else code


def _known_document_ids(output_dir: Path) -> set[str]:
    """Document ids already stored. Folder names are enough, so this does not open each file."""
    found: set[str] = set()
    if not output_dir.is_dir():
        return found
    for folder in output_dir.glob("*/*"):
        if not folder.is_dir():
            continue
        name = folder.name
        if name.startswith("urn-contentItem-"):
            document_id = "urn:contentItem:" + name[len("urn-contentItem-") :]
        else:
            document_id = name
        found.add(document_id)
        found.add(document_id.replace("urn:contentItem:", ""))
        found.add(name)
    return found


def _archive_articles(archive_dir: Path) -> list[tuple[TaggedArticle, str]]:
    grouped: dict[str, list[Path]] = {}
    for folder in archive_dir.glob("*/*/*/attempt-*"):
        if folder.is_dir():
            grouped.setdefault(str(folder.parent), []).append(folder)
    chosen = []
    for attempts in grouped.values():
        attempts.sort(key=lambda path: path.name)
        folder = _attempt_with_text(attempts)
        if folder is not None:
            chosen.append(folder)
    return _load_parallel(chosen, _load_archive_attempt)


def _attempt_with_text(attempts: list[Path]) -> Path | None:
    for folder in reversed(attempts):
        if (folder / "content.md").is_file() or (folder / "content.txt").is_file():
            return folder
    return None


def _load_archive_attempt(folder: Path) -> tuple[TaggedArticle, str] | None:
    metadata = _read_json(folder / "metadata.json")
    text = _read_text(folder / "content.md") or _read_text(folder / "content.txt")
    if not text and not metadata:
        return None
    source_id = str(metadata.get("source_id") or folder.parent.name)
    return (
        TaggedArticle(
            article_id=source_id,
            title=str(metadata.get("observed_title") or "").strip(),
            publisher=folder.parent.parent.name,
            publication_date=str(metadata.get("publication_date") or ""),
            location="",
            url=str(metadata.get("requested_url") or metadata.get("final_url") or ""),
            archive_dir=str(folder),
            origin="archive",
        ),
        strip_markup(text),
    )


def _nexis_articles(nexis_dir: Path) -> list[tuple[TaggedArticle, str]]:
    paths = sorted(nexis_dir.glob("*/*/metadata.json"))
    loaded = _load_parallel(paths, _load_nexis_hit)
    seen: set[str] = set()
    articles: list[tuple[TaggedArticle, str]] = []
    for article, text in loaded:
        if article.article_id in seen:
            continue
        seen.add(article.article_id)
        articles.append((article, text))
    return articles


def _load_nexis_hit(meta_path: Path) -> tuple[TaggedArticle, str] | None:
    metadata = _read_json(meta_path)
    document_id = str(metadata.get("document_id") or meta_path.parent.name).strip()
    if not document_id:
        return None
    text = _read_text(meta_path.parent / "content.txt")
    return (
        TaggedArticle(
            article_id=f"nexis_{document_id}",
            title=str(metadata.get("title") or "").strip(),
            publisher=str(metadata.get("publisher") or ""),
            publication_date=str(metadata.get("publication_date") or ""),
            location=str(metadata.get("location") or ""),
            url=str(metadata.get("url") or ""),
            archive_dir=str(meta_path.parent),
            origin="nexis",
        ),
        strip_markup(text),
    )


def _load_parallel(paths: list[Path], loader) -> list[tuple[TaggedArticle, str]]:
    if not paths:
        return []
    articles: list[tuple[TaggedArticle, str]] = []
    workers = min(8, len(paths))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(loader, path) for path in paths]
        for index, future in enumerate(as_completed(futures), start=1):
            loaded = future.result()
            if loaded is not None:
                articles.append(loaded)
            if index % 250 == 0:
                print(f"read {index} of {len(paths)} saved articles", file=sys.stderr)
    return articles


def _dedupe_articles(articles: list[TaggedArticle]) -> list[TaggedArticle]:
    by_key: dict[str, TaggedArticle] = {}
    for article in articles:
        key = _title_key(article.title) or article.article_id
        current = by_key.get(key)
        if current is None:
            by_key[key] = article
            continue
        merged = list(dict.fromkeys([*current.measures, *article.measures]))
        current.measures = merged
        if not current.url and article.url:
            current.url = article.url
        if not current.location and article.location:
            current.location = article.location
        if not current.publisher and article.publisher:
            current.publisher = article.publisher
        if not current.publication_date and article.publication_date:
            current.publication_date = article.publication_date
    return list(by_key.values())


def _title_key(title: str) -> str:
    words = _TITLE_PUNCT.sub(" ", title.casefold()).split()
    return " ".join(words)[:80]


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Routing-app measures</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #1c1917;
      --muted: #57534e;
      --line: #e7e5e4;
      --paper: #fafaf9;
      --card: #ffffff;
      --accent: #9a3412;
      --bar: #c2410c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", Palatino, Georgia, serif;
      color: var(--ink);
      background: var(--paper);
    }}
    header, main {{ width: min(1080px, calc(100% - 32px)); margin: 0 auto; }}
    header {{ padding: 28px 0 12px; }}
    h1 {{ font-size: 2rem; font-weight: 600; margin: 0 0 8px; }}
    p {{ color: var(--muted); line-height: 1.45; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 18px; margin: 16px 0; }}
    .stats div {{ min-width: 120px; }}
    .stats strong {{ display: block; font-size: 1.4rem; color: var(--ink); }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 18px; }}
    button {{
      font: inherit;
      border: 1px solid var(--line);
      background: var(--card);
      color: var(--ink);
      border-radius: 999px;
      padding: 6px 12px;
      cursor: pointer;
    }}
    button[aria-pressed="true"] {{ background: var(--ink); color: white; border-color: var(--ink); }}
    .layout {{ display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 20px; padding-bottom: 40px; }}
    @media (max-width: 800px) {{ .layout {{ grid-template-columns: 1fr; }} }}
    ol {{ list-style: none; margin: 0; padding: 0; }}
    li {{
      border: 1px solid var(--line);
      background: var(--card);
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 8px;
      cursor: pointer;
    }}
    li[aria-current="true"] {{ border-color: var(--accent); }}
    .row {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; }}
    .code {{ color: var(--accent); font-variant-numeric: tabular-nums; margin-right: 6px; }}
    .category {{ color: var(--muted); font-size: 0.92rem; }}
    .bar {{ height: 6px; background: #ffedd5; border-radius: 99px; margin-top: 8px; }}
    .bar span {{ display: block; height: 100%; background: var(--bar); border-radius: 99px; }}
    article {{
      border-top: 1px solid var(--line);
      padding: 10px 0;
    }}
    article h3 {{ margin: 0 0 4px; font-size: 1.02rem; }}
    a {{ color: var(--accent); }}
    .empty {{ color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>Routing-app measures</h1>
    <p>Measures from sheet 1012_codebook, ranked by the number of related news articles. An article can match more than one measure. Articles with no matching phrase stay unlabeled.</p>
    <div class="stats">
      <div><strong>{article_count}</strong> articles read</div>
      <div><strong>{labeled_count}</strong> matched a measure</div>
      <div><strong>{unlabeled_count}</strong> unlabeled</div>
      <div><strong>{measure_count}</strong> measures</div>
    </div>
    <div class="filters" id="filters"></div>
  </header>
  <main class="layout">
    <section>
      <ol id="measures"></ol>
    </section>
    <section>
      <h2 id="detail-title">Select a measure</h2>
      <p id="detail-definition"></p>
      <div id="articles"></div>
    </section>
  </main>
  <script id="measure-data" type="application/json">{data}</script>
  <script>
    const data = JSON.parse(document.getElementById("measure-data").textContent);
    const filters = document.getElementById("filters");
    const list = document.getElementById("measures");
    const detailTitle = document.getElementById("detail-title");
    const detailDefinition = document.getElementById("detail-definition");
    const articles = document.getElementById("articles");
    let category = "all";
    let selected = data.measures[0] ? data.measures[0].code : "";
    const maxCount = Math.max(1, ...data.measures.map((item) => item.count));

    function addFilter(code, label) {{
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.dataset.code = code;
      button.setAttribute("aria-pressed", code === category ? "true" : "false");
      button.addEventListener("click", () => {{
        category = code;
        for (const item of filters.querySelectorAll("button")) {{
          item.setAttribute("aria-pressed", item.dataset.code === category ? "true" : "false");
        }}
        drawMeasures();
      }});
      filters.appendChild(button);
    }}

    addFilter("all", "All categories");
    for (const item of data.categories) addFilter(item.code, item.code + ". " + item.name);

    function drawMeasures() {{
      list.replaceChildren();
      const visible = data.measures.filter((item) => category === "all" || item.category === category);
      if (!visible.some((item) => item.code === selected) && visible[0]) selected = visible[0].code;
      visible.forEach((item, index) => {{
        const row = document.createElement("li");
        row.setAttribute("aria-current", item.code === selected ? "true" : "false");
        const width = Math.round((item.count / maxCount) * 100);
        row.innerHTML = '<div class="row"><div><span class="code">' + (index + 1) + '</span><strong></strong></div><b></b></div><div class="category"></div><div class="bar"><span></span></div>';
        row.querySelector("strong").textContent = item.code + ". " + item.name;
        row.querySelector("b").textContent = String(item.count);
        row.querySelector(".category").textContent = item.category + ". " + item.category_name;
        row.querySelector(".bar span").style.width = width + "%";
        row.addEventListener("click", () => {{
          selected = item.code;
          drawMeasures();
        }});
        list.appendChild(row);
      }});
      drawArticles();
    }}

    function drawArticles() {{
      const measure = data.measures.find((item) => item.code === selected);
      articles.replaceChildren();
      if (!measure) {{
        detailTitle.textContent = "Select a measure";
        detailDefinition.textContent = "";
        return;
      }}
      detailTitle.textContent = measure.code + ". " + measure.name;
      detailDefinition.textContent = measure.definition;
      const found = data.articles.filter((item) => item.measures.includes(measure.code));
      found.sort((a, b) => (b.publication_date || "").localeCompare(a.publication_date || ""));
      if (!found.length) {{
        const note = document.createElement("p");
        note.className = "empty";
        note.textContent = "No saved article matched this measure.";
        articles.appendChild(note);
        return;
      }}
      for (const item of found) {{
        const card = document.createElement("article");
        const heading = document.createElement("h3");
        if (item.url && item.url.startsWith("http")) {{
          const link = document.createElement("a");
          link.href = item.url;
          link.target = "_blank";
          link.rel = "noreferrer";
          link.textContent = item.title;
          heading.appendChild(link);
        }} else {{
          heading.textContent = item.title;
        }}
        const meta = document.createElement("p");
        meta.textContent = [item.publication_date, item.publisher, item.location, item.origin].filter(Boolean).join(" · ");
        card.appendChild(heading);
        card.appendChild(meta);
        articles.appendChild(card);
      }}
    }}

    drawMeasures();
  </script>
</body>
</html>
"""
