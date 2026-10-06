"""Tests for the research analysis module."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from news_importer.analysis import (
    ALLOWED_CATEGORIES,
    ALLOWED_GOVERNING_LEVELS,
    ALLOWED_MEASURE_STATUSES,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_TARGET_LOCATION_TYPES,
    DiscoveryReference,
    MeasureItem,
    ResearchAnalysisEntry,
    SupportingPassage,
    build_pass1_analyses,
    export_analysis_csv,
    export_analysis_json,
    export_inventory_csv,
    inventory_archived_sources,
    normalize_whitespace,
    strip_markdown,
    verify_passage,
)


class AnalysisUnitTests(unittest.TestCase):
    def test_codebook_allowed_values(self):
        self.assertIn("news reporting", ALLOWED_SOURCE_TYPES)
        self.assertIn("government material", ALLOWED_SOURCE_TYPES)
        self.assertIn("company statement", ALLOWED_SOURCE_TYPES)
        self.assertIn("community testimony", ALLOWED_SOURCE_TYPES)
        self.assertIn("other", ALLOWED_SOURCE_TYPES)

        self.assertIn("proposed", ALLOWED_MEASURE_STATUSES)
        self.assertIn("piloted", ALLOWED_MEASURE_STATUSES)
        self.assertIn("implemented", ALLOWED_MEASURE_STATUSES)
        self.assertIn("withdrawn", ALLOWED_MEASURE_STATUSES)
        self.assertIn("unclear", ALLOWED_MEASURE_STATUSES)

        self.assertIn("Experimented Measures", ALLOWED_CATEGORIES)
        self.assertIn("Community Feedback", ALLOWED_CATEGORIES)
        self.assertIn("Both", ALLOWED_CATEGORIES)
        self.assertIn("Out of Scope", ALLOWED_CATEGORIES)

        self.assertIn("Government: Federal", ALLOWED_GOVERNING_LEVELS)
        self.assertIn("Government: State", ALLOWED_GOVERNING_LEVELS)
        self.assertIn("Government: County", ALLOWED_GOVERNING_LEVELS)
        self.assertIn("Government: City", ALLOWED_GOVERNING_LEVELS)
        self.assertIn("Company", ALLOWED_GOVERNING_LEVELS)
        self.assertIn("Non-Government Organization", ALLOWED_GOVERNING_LEVELS)

        self.assertIn("City", ALLOWED_TARGET_LOCATION_TYPES)
        self.assertIn("County", ALLOWED_TARGET_LOCATION_TYPES)
        self.assertIn("State", ALLOWED_TARGET_LOCATION_TYPES)
        self.assertIn("Country", ALLOWED_TARGET_LOCATION_TYPES)

    def test_strip_markdown(self):
        text = "Check out [Boston](https://example.com/boston) and ![logo](https://example.com/img.png) today."
        stripped = strip_markdown(text)
        self.assertEqual(stripped, "Check out Boston and  today.")

    def test_verify_passage_exact_and_normalized(self):
        content = (
            "# Heading\n\n"
            "This is a paragraph with [a link](https://example.com) and multiple   spaces.\n"
            "Another line of text."
        )
        # Exact
        matched, note = verify_passage("Another line of text.", content)
        self.assertTrue(matched)
        self.assertEqual(note, "Exact verbatim match")

        # Normalized whitespace
        matched, note = verify_passage("paragraph with [a link](https://example.com) and multiple spaces.", content)
        self.assertTrue(matched)
        self.assertEqual(note, "Normalized whitespace match")

        # Stripped markdown link
        matched, note = verify_passage("paragraph with a link and multiple spaces.", content)
        self.assertTrue(matched)
        self.assertEqual(note, "Plaintext normalized match")

        # Not found
        matched, note = verify_passage("nonexistent passage", content)
        self.assertFalse(matched)

    def test_export_json_and_csv(self):
        entry = ResearchAnalysisEntry(
            source_id="src_test",
            archive_attempt_id="att_test",
            requested_url="https://example.com/test",
            final_url="https://example.com/test",
            title="Test Title",
            publisher="Test Publisher",
            publication_date="2026-01-01",
            actual_jurisdiction="City of Test",
            governing_level="Government: City",
            authority_names="Test City Council",
            target_location_type="City",
            target_location="Test City",
            source_type="news reporting",
            factual_summary="Test summary",
            measures=[
                MeasureItem(
                    actor="Test City",
                    mechanism="Test barrier",
                    purpose="Prevent cut-through",
                    status="piloted",
                    governing_level="Government: City",
                    authority_names="Test City Council",
                    target_location_type="City",
                    target_location="Test City",
                    implementation_dates="2026-01-01",
                    reported_effects="Reduced traffic",
                    demonstrated_causal_effects="None",
                )
            ],
            community_feedback=[],
            category="Experimented Measures",
            supporting_passages=[
                SupportingPassage(claim_topic="test", verbatim_text="Test snippet", verified=True, verification_note="Exact")
            ],
            quality_flags=[],
            unresolved_questions=["None"],
            discovery_records=[
                DiscoveryReference("disc_1", "batch_1", "SF", "other", "https://example.com/test")
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            json_file = tmppath / "out.json"
            csv_file = tmppath / "out.csv"

            export_analysis_json([entry], json_file)
            self.assertTrue(json_file.is_file())
            data = json.loads(json_file.read_text())
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["source_id"], "src_test")
            self.assertEqual(data[0]["governing_level"], "Government: City")
            self.assertEqual(data[0]["authority_names"], "Test City Council")
            self.assertEqual(data[0]["target_location_type"], "City")
            self.assertEqual(data[0]["target_location"], "Test City")

            export_analysis_csv([entry], csv_file)
            self.assertTrue(csv_file.is_file())
            csv_text = csv_file.read_text()
            self.assertIn("src_test", csv_text)
            self.assertIn("Test Title", csv_text)
            self.assertIn("Government: City", csv_text)
            self.assertIn("Test City Council", csv_text)
            self.assertIn("target_location_type", csv_text)
            self.assertIn("Test City", csv_text)

    def test_build_all_analyses(self):
        from news_importer.analysis import build_all_analyses
        db_path = Path("data/news.sqlite")
        archive_root = Path(".")
        entries = build_all_analyses(db_path, archive_root)
        self.assertEqual(len(entries), 43)

        for e in entries:
            self.assertIn(e.governing_level, ALLOWED_GOVERNING_LEVELS)
            self.assertIn(e.target_location_type, ALLOWED_TARGET_LOCATION_TYPES)
            self.assertIn(e.category, ALLOWED_CATEGORIES)
            self.assertIn(e.source_type, ALLOWED_SOURCE_TYPES)
            self.assertTrue(len(e.authority_names) > 0)
            self.assertTrue(len(e.target_location) > 0)
            for p in e.supporting_passages:
                self.assertTrue(p.verified, f"Passage '{p.claim_topic}' in {e.source_id} failed verification")


if __name__ == "__main__":
    unittest.main()

