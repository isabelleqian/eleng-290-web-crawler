"""Codebook measure matching and the ranked measures page. No live API calls."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_importer.codebook import (  # noqa: E402
    default_codebook_path,
    load_codebook,
    matching_measures,
    parse_codebook_rows,
)
from news_importer.measures import (  # noqa: E402
    app_group_expression,
    measure_queries,
    render_dashboard,
    search_measures,
    tag_articles,
)
from news_importer.nexis import NexisHit  # noqa: E402

A2 = (
    "A2. Through-traffic restrictions",
    'Measures prohibiting through trips. Examples include "local traffic only" and "no through traffic" rules.',
)
B2 = (
    "B2. Vertical traffic calming",
    "Raised roadway treatments. Examples include speed humps, speed tables, and raised crosswalks.",
)
D1 = (
    "D1. Area and cordon congestion charging",
    "Charges imposed for entering a designated congested area.",
)


def sample_codebook():
    return parse_codebook_rows(
        [
            ("Categories and subcategories", "Definition"),
            ("A. Access and circulation regulation", "Access measures."),
            A2,
            ("B. Physical and spatial traffic interventions", "Physical measures."),
            B2,
            ("D. Pricing and economic measures", "Charges."),
            D1,
        ]
    )


class CodebookParseTests(unittest.TestCase):
    def test_categories_group_measures_and_examples_become_phrases(self) -> None:
        codebook = sample_codebook()
        self.assertEqual([item.code for item in codebook.categories], ["A", "B", "D"])
        by_code = {item.code: item for item in codebook.measures}
        self.assertEqual(by_code["A2"].category_code, "A")
        self.assertIn("no through traffic", [phrase.casefold() for phrase in by_code["A2"].phrases])
        self.assertIn("local traffic only", [phrase.casefold() for phrase in by_code["A2"].phrases])
        self.assertIn("speed humps", [phrase.casefold() for phrase in by_code["B2"].phrases])

    def test_real_sheet_has_the_measure_list(self) -> None:
        path = default_codebook_path()
        if not path.is_file():
            self.skipTest(f"workbook is not available: {path}")
        codebook = load_codebook(path)
        self.assertEqual(len(codebook.categories), 6)
        self.assertEqual(len(codebook.measures), 35)
        self.assertEqual(codebook.measures[0].code, "A1")
        self.assertEqual(codebook.measures[-1].code, "F7")

    def test_an_article_can_match_more_than_one_measure_and_can_stay_unlabeled(self) -> None:
        codebook = sample_codebook()
        both = matching_measures(
            "The city added speed humps and posted no through traffic signs.",
            codebook,
        )
        self.assertEqual(both, ["A2", "B2"])
        self.assertEqual(matching_measures("The council met on Tuesday.", codebook), [])
        hyphen = matching_measures("Residents asked for a no-through-traffic rule.", codebook)
        self.assertEqual(hyphen, ["A2"])

    def test_a_generic_modifier_is_not_a_measure_phrase(self) -> None:
        codebook = parse_codebook_rows(
            [
                (
                    "D6. Parking pricing",
                    "This includes fixed, location-based, time-based, and dynamic parking prices.",
                )
            ]
        )
        phrases = [phrase.casefold() for phrase in codebook.measures[0].phrases]
        self.assertIn("dynamic parking prices", phrases)
        self.assertNotIn("location-based", phrases)
        self.assertEqual(
            matching_measures("The app offers location-based services.", codebook),
            [],
        )
        self.assertEqual(
            matching_measures("The city adopted dynamic parking prices downtown.", codebook),
            ["D6"],
        )


class MeasureSearchTests(unittest.TestCase):
    def test_measure_names_are_phrases_inside_the_app_group(self) -> None:
        queries = measure_queries(sample_codebook(), app_group_expression())
        by_name = {query.keywords: query.expression for query in queries}
        expression = by_name["Through-traffic restrictions"]
        self.assertIn('( Waze OR "Google Maps"', expression)
        self.assertIn('AND "Through-traffic restrictions"', expression)
        self.assertNotIn(" OR ", expression.split("AND", 1)[1])
        keywords = {query.keywords.casefold() for query in queries}
        self.assertIn("speed humps", keywords)
        self.assertIn("local traffic only", keywords)
        self.assertNotIn("location-based", keywords)

    def test_search_stores_a_new_us_hit_and_skips_a_repeat(self) -> None:
        hit = NexisHit(
            document_id="urn:contentItem:measure1",
            title="Town posts no through traffic signs after Waze shortcuts",
            publisher="Local Paper",
            publication_date="2024-05-01",
            location="United States",
            url="https://example.test/through",
            body="Drivers using Waze were told no through traffic.",
            raw={"Geography": "United States"},
        )
        calls: list[str] = []

        def search(expression: str, limit: int) -> list[NexisHit]:
            calls.append(expression)
            self.assertEqual(limit, 2)
            if "Through-traffic restrictions" in expression:
                return [hit, hit]
            return []

        codebook = sample_codebook()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = search_measures(
                codebook,
                output_dir=root,
                limit=2,
                search=search,
                query_path=root / "measure_queries.txt",
            )
            self.assertEqual(first.stored, 1)
            self.assertEqual(first.skipped_existing, 1)
            second = search_measures(
                codebook,
                output_dir=root,
                limit=2,
                search=search,
                query_path=root / "measure_queries.txt",
            )
            self.assertEqual(second.stored, 0)
            self.assertGreaterEqual(second.skipped_existing, 1)
            articles = tag_articles(codebook, archive_dir=root / "missing", nexis_dir=root)
            matched = [article for article in articles if "A2" in article.measures]
            self.assertEqual(len(matched), 1)
            page = render_dashboard(articles, codebook)
            start = page.index('type="application/json">') + len('type="application/json">')
            payload = json.loads(page[start : page.index("</script>", start)])
            self.assertEqual(payload["measures"][0]["code"], "A2")
            self.assertGreater(payload["measures"][0]["count"], payload["measures"][1]["count"])
        self.assertTrue(calls)

    def test_archive_and_nexis_copies_of_one_headline_count_once(self) -> None:
        codebook = sample_codebook()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempt = root / "archive" / "city" / "news.example" / "story--src_abc" / "attempt-001"
            attempt.mkdir(parents=True)
            (attempt / "content.md").write_text("The street now has speed humps.\n", encoding="utf-8")
            (attempt / "metadata.json").write_text(
                json.dumps(
                    {
                        "source_id": "src_abc",
                        "observed_title": "Speed humps go in on Oak Street",
                        "publication_date": "2020-01-02",
                        "requested_url": "https://news.example/oak",
                    }
                ),
                encoding="utf-8",
            )
            nexis = root / "nexis" / "speed-humps" / "doc1"
            nexis.mkdir(parents=True)
            (nexis / "content.txt").write_text("Neighbors wanted speed humps.\n", encoding="utf-8")
            (nexis / "metadata.json").write_text(
                json.dumps(
                    {
                        "document_id": "doc1",
                        "title": "Speed humps go in on Oak Street",
                        "publisher": "News Example",
                        "publication_date": "2020-01-02",
                        "location": "Oakland",
                        "url": "https://news.example/oak",
                    }
                ),
                encoding="utf-8",
            )
            articles = tag_articles(codebook, archive_dir=root / "archive", nexis_dir=root / "nexis")
            self.assertEqual(len(articles), 1)
            self.assertEqual(articles[0].measures, ["B2"])
            self.assertEqual(articles[0].location, "Oakland")
