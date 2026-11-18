import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from news_importer.generate_infographics import generate_database_html, generate_html_infographics


LINKS = [
    ("index.html", "Overview Map"),
    ("news_database.html", "News Database"),
    ("policy_database.html", "Policy Database"),
    ("law_database.html", "U.S. Law Database"),
    ("crosswalk.html", "News ↔ Law Crosswalk"),
]
ARCHIVE = "news_database_archive.html"


class NavLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attributes = dict(attrs)
            self.links.append([attributes["href"], ""])
            if attributes.get("aria-current") == "page":
                self.current.append(attributes["href"])

    def handle_data(self, data):
        if data.strip() and self.links:
            self.links[-1][1] += data


class SiteNavigationTests(unittest.TestCase):
    def assert_navigation(self, html, page):
        nav = re.search(r"<nav\b[^>]*>.*?</nav>", html, flags=re.DOTALL)
        self.assertIsNotNone(nav)
        parser = NavLinks()
        parser.feed(nav[0])
        self.assertEqual([tuple(link) for link in parser.links], LINKS)
        self.assertEqual(parser.current, [] if page == ARCHIVE else [page])

    def test_published_pages(self):
        docs = Path(__file__).resolve().parents[1] / "docs"
        for page in [*(href for href, _ in LINKS), ARCHIVE]:
            with self.subTest(page=page):
                self.assert_navigation((docs / page).read_text(encoding="utf-8"), page)

    def test_generated_pages(self):
        data = {
            "metadata": {
                "total_sources": 0,
                "localized_sources": 0,
                "nationwide_sources": 0,
                "unique_locations": 0,
                "year_range": "",
                "gov_counts": {},
            },
            "keyword_audit": {},
        }
        self.assert_navigation(generate_html_infographics(data), "index.html")
        self.assert_navigation(generate_database_html([]), "news_database.html")
        self.assert_navigation(generate_database_html([], is_archive=True), ARCHIVE)
