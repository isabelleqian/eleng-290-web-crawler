import json
import re
import tempfile
import unittest
from pathlib import Path

from news_importer.review_summaries import apply_reviewed_summaries, refresh_page


class ReviewSummaryTests(unittest.TestCase):
    def test_exact_join_preserves_filtering_metadata_and_unmatched_records(self):
        original = {"database": [
            {"source_id": "known", "summary": "old", "is_relevant": 0,
             "title": "Original title", "date": "2020", "url": "https://example.org"},
            {"source_id": "unknown", "summary": "Keep me", "is_relevant": 1},
        ]}
        updated = apply_reviewed_summaries(original, {"known": "Full reviewed summary"})
        self.assertEqual(updated["database"][0], {
            **original["database"][0], "summary": "Full reviewed summary"})
        self.assertEqual(updated["database"][1], original["database"][1])
        self.assertEqual(original["database"][0]["summary"], "old")

    def test_saved_page_keeps_full_summary_and_escapes_script_content(self):
        summary = "A full summary. " * 40 + "</script>"
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "page.html"
            page.write_text('<script>const ROWS = [{"id":"known","summary":"old"}];'
                            '</script><p class="leading-relaxed line-clamp-2">', encoding="utf-8")
            refresh_page(page, "ROWS", {"known": summary})
            text = page.read_text(encoding="utf-8")
            match = re.search(r"const ROWS = ", text)
            rows, _ = json.JSONDecoder().raw_decode(text[match.end():])
            self.assertEqual(rows[0]["summary"], summary)
            self.assertNotIn("line-clamp-2", text)
            self.assertEqual(text.count("</script>"), 1)


if __name__ == "__main__":
    unittest.main()
