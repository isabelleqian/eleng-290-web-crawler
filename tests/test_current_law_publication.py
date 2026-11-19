"""Protect the current-law allowlist and the separation of unverified research."""
import csv
import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'research_audit/current-law-review'


class CurrentLawPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'docs/data/current_law_database.json').read_text())
        cls.records = cls.data['records']
        with (AUDIT / 'record_disposition_audit.csv').open(encoding='utf-8-sig', newline='') as stream:
            cls.audit = list(csv.DictReader(stream))

    def test_public_entries_are_effective_and_classified(self):
        ids = [r['id'] for r in self.records]
        self.assertEqual(len(ids), len(set(ids)))
        for r in self.records:
            with self.subTest(id=r['id']):
                self.assertIn(r['tier'], (1, 2, 3))
                self.assertEqual(r['category_name'], self.data['codebook'][r['category_code']])
                self.assertEqual(r['current_status'], 'In force in the official current text reviewed')
                self.assertNotIn('Bill', r['instrument_type'])
                self.assertTrue(r['classification_rationale'])
                self.assertTrue(r['operative_evidence'])
                self.assertTrue(r['source_ids'])

    def test_all_public_counts_reconcile(self):
        counts = self.data['counts']
        self.assertEqual(counts['total'], len(self.records))
        self.assertEqual(counts['by_tier'], dict(Counter(str(r['tier']) for r in self.records)))
        for field, key in [('jurisdiction', 'by_jurisdiction'), ('instrument_type', 'by_instrument_type'), ('category_code', 'by_category')]:
            self.assertEqual(counts[key], dict(Counter(r[field] for r in self.records)))
        self.assertEqual(sum(counts['by_tier'].values()), counts['total'])

    def test_original_source_accounting_and_current_aliases(self):
        self.assertEqual(len(self.audit), 3455 + 189)
        audit = {r['audit_key']: r for r in self.audit}
        self.assertEqual(len(audit), len(self.audit))
        self.assertEqual(sum(r['source_collection'] != 'legacy' for r in self.audit), 3455)
        for r in self.records:
            for source in r['source_ids']:
                self.assertIn(source, audit)
                self.assertEqual(audit[source]['public_instrument_id'], r['id'])
                self.assertEqual(audit[source]['disposition'], 'Consolidated into verified current instrument')
        self.assertNotIn('CA-AB2015', {r['id'] for r in self.records})
        self.assertEqual(audit['legacy:CA-AB2015']['disposition'], 'Removed—not yet effective')
        self.assertNotIn('FP-0109', {s for r in self.records for s in r['source_ids']})

    def test_current_entries_have_traceable_official_text(self):
        evidence = json.loads((AUDIT / 'reviewed_official_texts.json').read_text())
        norm = lambda s: ' '.join(s.split()).casefold()
        for r in self.records:
            capture = evidence[r['id']]
            self.assertEqual(capture['official_url'], r['official_url'])
            self.assertEqual(hashlib.sha256(capture['text'].encode()).hexdigest(), r['evidence_sha256'])
            self.assertIn(norm(r['operative_evidence']), norm(capture['text']))
            self.assertNotIn('Request Access', capture['text'][:2000])

    def test_crosswalk_content_and_functionality_are_preserved(self):
        # User requested that the pre-review crosswalk remain unchanged except colors.
        self.assertEqual(hashlib.sha256((ROOT / 'docs/crosswalk.html').read_bytes()).hexdigest(),
                         '85f0550c1afa49545c3ccc8e588a52e3e3d21c6077ee86dda1a0befac745aa7d')
        html = (ROOT / 'docs/law_database.html').read_text()
        self.assertNotIn('const LEGISLATION =', html)
        self.assertNotIn('const CROSSWALK =', html)
        self.assertNotIn('cohort_3455_analysis.json', html)
        self.assertEqual(len(self.data['codebook']), 35)
        self.assertEqual(Counter(code[0] for code in self.data['codebook']),
                         {'A': 5, 'B': 6, 'C': 5, 'D': 6, 'E': 6, 'F': 7})
        self.assertIn('id="full-codebook"', html)
        with (AUDIT / 'jurisdiction_tracker.csv').open(encoding='utf-8-sig', newline='') as stream:
            tracker = list(csv.DictReader(stream))
        self.assertEqual(len(tracker), 52)
        self.assertTrue(all(r['review_status'] != 'Complete' for r in tracker))


if __name__ == '__main__':
    unittest.main()
