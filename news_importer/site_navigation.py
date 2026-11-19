"""Render the shared navigation and synchronize the published HTML."""

import re
from pathlib import Path


NAV_LINKS = (
    ("index.html", "Overview Map"),
    ("news_database.html", "News Database"),
    ("policy_database.html", "Policy Database"),
    ("law_database.html", "U.S. Law Database"),
    ("crosswalk.html", "News ↔ Law Crosswalk"),
)
ARCHIVE_PAGE = "news_database_archive.html"


def render_site_navigation(page: str, indent: str = "") -> str:
    lines = [
        '<nav aria-label="Site navigation" class="site-navigation">'
    ]
    for href, label in NAV_LINKS:
        if href == page:
            style = "site-navigation-link"
            current = ' aria-current="page"'
        else:
            style = "site-navigation-link"
            current = ""
        lines.append(f'  <a href="{href}" class="{style}"{current}>{label}</a>')
    lines.append("</nav>")
    return ("\n" + indent).join(lines)


def sync_published_navigation(docs: Path) -> None:
    for page in [*(href for href, _ in NAV_LINKS), ARCHIVE_PAGE]:
        path = docs / page
        with path.open(encoding="utf-8", newline="") as stream:
            html = stream.read()
        nav = re.search(r"^([ \t]*)<nav\b[^>]*>.*?</nav>", html, flags=re.MULTILINE | re.DOTALL)
        if nav is None:
            raise ValueError(f"No site navigation found in {path}")
        indent = nav[1]
        rendered = indent + render_site_navigation(page, indent)
        if "\r\n" in html:
            rendered = rendered.replace("\n", "\r\n")
        if rendered != nav[0]:
            updated = html[:nav.start()] + rendered + html[nav.end():]
            with path.open("w", encoding="utf-8", newline="") as stream:
                stream.write(updated)


if __name__ == "__main__":
    sync_published_navigation(Path(__file__).resolve().parents[1] / "docs")
