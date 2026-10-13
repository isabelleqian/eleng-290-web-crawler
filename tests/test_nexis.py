"""Nexis keyword searches. No live API calls."""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_importer.analysis import ANALYSIS_EXPORT_COLUMNS, classify_governing_level_from_text  # noqa: E402
from news_importer.errors import ImporterError  # noqa: E402
from news_importer.nexis import NexisHit, NexisOptions, _load_env_file, parse_hits, run_nexis  # noqa: E402
from news_importer.nexis_query import (  # noqa: E402
    build_nexis_query,
    build_raw_nexis_query,
    load_keyword_list,
    read_keyword_lines,
    read_raw_query,
    save_keyword_list,
)


class NexisQueryTests(unittest.TestCase):
    def test_multiword_location_is_one_phrase_and_every_word_is_required(self) -> None:
        query = build_nexis_query("Los Angeles Waze")
        self.assertEqual(query.expression, '"Los Angeles" AND Waze')
        self.assertEqual(query.phrases, ("Los Angeles",))
        self.assertEqual(query.words, ("Waze",))
        self.assertNotIn("Angeles", query.words)
        self.assertNotIn("Los", query.words)

    def test_longer_place_name_wins_over_a_shorter_one(self) -> None:
        query = build_nexis_query("New York City Waze")
        self.assertEqual(query.expression, '"New York City" AND Waze')

    def test_split_place_words_are_not_treated_as_the_place(self) -> None:
        query = build_nexis_query("Angeles Los Waze")
        self.assertEqual(query.expression, "Angeles AND Los AND Waze")

    def test_quoted_phrase_stays_intact(self) -> None:
        query = build_nexis_query('Boston "traffic nightmare"')
        self.assertEqual(query.expression, '"traffic nightmare" AND Boston')

    def test_or_is_rejected_as_the_archived_google_style(self) -> None:
        with self.assertRaises(ImporterError):
            build_nexis_query("Los Angeles OR Waze")


class NexisStoreTests(unittest.TestCase):
    def test_hits_are_stored_and_the_report_keeps_measure_columns(self) -> None:
        payload = {
            "value": [
                {
                    "ResultId": "urn:contentItem:abc",
                    "Title": "Waze fills Baxter Street",
                    "Date": "2018-04-17T00:00:00Z",
                    "Source": {"Name": "Los Angeles Times"},
                    "Geography": "Los Angeles",
                    "Document": {"Content": "Drivers using Waze filled Los Angeles side streets."},
                    "Link": "https://example.test/baxter",
                }
            ]
        }
        hits = parse_hits(payload)
        self.assertEqual(hits[0].location, "Los Angeles")
        self.assertEqual(hits[0].publication_date, "2018-04-17T00:00:00Z")

        def search(expression: str, limit: int) -> list[NexisHit]:
            self.assertEqual(expression, '"Los Angeles" AND Waze')
            self.assertEqual(limit, 5)
            return hits

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            keywords = root / "keywords.txt"
            keywords.write_text("Los Angeles Waze\n", encoding="utf-8")
            summary = run_nexis(
                NexisOptions(
                    keyword_path=keywords,
                    output_dir=root / "nexis",
                    report_path=root / "nexis_report.csv",
                    limit=5,
                    search=search,
                )
            )
            self.assertEqual(summary.stored, 1)
            stored = list((root / "nexis").rglob("metadata.json"))
            self.assertEqual(len(stored), 1)
            metadata = json.loads(stored[0].read_text(encoding="utf-8"))
            self.assertEqual(metadata["publication_year"], "2018")
            self.assertEqual(metadata["location"], "Los Angeles")
            self.assertIn("Los Angeles", (stored[0].parent / "content.txt").read_text(encoding="utf-8"))
            with (root / "nexis_report.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0].keys())[: len(ANALYSIS_EXPORT_COLUMNS)], ANALYSIS_EXPORT_COLUMNS)
            self.assertEqual(rows[0]["publication_year"], "2018")
            self.assertEqual(rows[0]["location"], "Los Angeles")
            self.assertEqual(rows[0]["publisher"], "Los Angeles Times")
            self.assertEqual(rows[0]["measure_actors"], "")
            self.assertEqual(rows[0]["measure_mechanisms"], "")
            self.assertEqual(rows[0]["measure_statuses"], "")
            self.assertIn("measure_actors", rows[0])

    def test_dry_run_writes_nothing(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            keywords = root / "keywords.txt"
            keywords.write_text("Salt Lake City Waze\n", encoding="utf-8")

            def search(expression: str, limit: int) -> list[NexisHit]:
                raise AssertionError("dry run called Nexis")

            summary = run_nexis(
                NexisOptions(
                    keyword_path=keywords,
                    output_dir=root / "nexis",
                    report_path=root / "report.csv",
                    dry_run=True,
                    search=search,
                )
            )
            self.assertEqual(summary.queries[0].expression, '"Salt Lake City" AND Waze')
            self.assertFalse((root / "nexis").exists())
            self.assertFalse((root / "report.csv").exists())

    def test_env_file_supplies_a_missing_credential(self) -> None:
        import os

        with TemporaryDirectory() as temporary:
            path = Path(temporary) / ".env"
            path.write_text('NEXIS_CLIENT_ID="library-id"\n', encoding="utf-8")
            os.environ.pop("NEXIS_CLIENT_ID", None)
            _load_env_file(path)
            self.assertEqual(os.environ["NEXIS_CLIENT_ID"], "library-id")
            os.environ.pop("NEXIS_CLIENT_ID", None)

    def test_a_text_list_is_saved_and_loaded_unchanged(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "given.txt"
            source.write_text("Los Angeles Waze\n\n# note\nBoston Waze\n", encoding="utf-8")
            stored = root / "remembered.txt"
            saved = save_keyword_list(source, stored)
            self.assertEqual(saved, ["Los Angeles Waze", "Boston Waze"])
            self.assertEqual(load_keyword_list(stored), ["Los Angeles Waze", "Boston Waze"])
            self.assertEqual(
                stored.read_text(encoding="utf-8"),
                "Los Angeles Waze\nBoston Waze\n",
            )

    def test_google_query_csv_is_not_a_keyword_file(self) -> None:
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "queries.csv"
            path.write_text("query\nLos Angeles OR Waze\n", encoding="utf-8")
            with self.assertRaises(ImporterError):
                read_keyword_lines(path)

    def test_raw_query_expression_and_file(self) -> None:
        raw_expr = '( Waze OR "Google Maps" ) AND ( "road closure" OR "turn restriction" )'
        q = build_raw_nexis_query(raw_expr)
        self.assertEqual(q.expression, raw_expr)
        self.assertEqual(q.keywords, raw_expr)

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            q_file = root / "raw_query.txt"
            q_file.write_text(f"# Comment\n{raw_expr}\n", encoding="utf-8")
            loaded = read_raw_query(q_file)
            self.assertEqual(loaded, raw_expr)

            summary = run_nexis(
                NexisOptions(
                    query_path=q_file,
                    output_dir=root / "nexis",
                    report_path=root / "report.csv",
                    dry_run=True,
                )
            )
            self.assertEqual(summary.queries[0].expression, raw_expr)

    def test_governing_level_classification_keywords(self) -> None:
        fed_text = "The U.S. Department of Transportation announced new safety guidance."
        self.assertIn("Government: Federal", classify_governing_level_from_text(fed_text))

        city_text = "The Los Angeles City Council passed a traffic diverter ordinance."
        self.assertIn("Government: City", classify_governing_level_from_text(city_text))

        company_text = "Google updated its routing algorithm to avoid narrow streets."
        self.assertIn("Company", classify_governing_level_from_text(company_text))


class NexisAnalysisUnitTests(unittest.TestCase):
    def test_build_nexis_analyses_validates_all_passages_and_schema(self) -> None:
        from news_importer.nexis_analysis import build_nexis_analyses
        nexis_root = ROOT / "data" / "nexis"
        if not nexis_root.is_dir():
            self.skipTest("data/nexis not found")
        entries = build_nexis_analyses(nexis_root)
        self.assertEqual(len(entries), 8)
        for e in entries:
            self.assertTrue(e.source_id.startswith("nexis_urn:contentItem:"))
            self.assertTrue(len(e.supporting_passages) >= 3)
            for p in e.supporting_passages:
                self.assertTrue(p.verified, f"Passage '{p.claim_topic}' in {e.source_id} failed verification")
            self.assertTrue(len(e.authority_names) > 0)
            self.assertTrue(len(e.target_location) > 0)

    def test_nexis_report_and_all_sources_columns_match(self) -> None:
        from news_importer.analysis import ANALYSIS_EXPORT_COLUMNS
        from news_importer.nexis_analysis import update_nexis_report
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            report_csv = root / "nexis_report.csv"
            entries = update_nexis_report(ROOT / "data" / "nexis", report_csv)
            self.assertEqual(len(entries), 8)
            self.assertTrue(report_csv.is_file())
            with report_csv.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(list(rows[0].keys()), ANALYSIS_EXPORT_COLUMNS)
            self.assertEqual(len(rows), 8)
            self.assertTrue(rows[0]["measure_actors"])
            self.assertTrue(rows[0]["governing_level"])


if __name__ == "__main__":
    unittest.main()


