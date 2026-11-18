import json
import unittest
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_policy_preview import build_preview


class PolicyPreviewTests(unittest.TestCase):
    @unittest.skipUnless(
        (Path(__file__).resolve().parents[2] / "policy-search/data/source_verification_round3.json").is_file(),
        "local Policy Commons inputs are unavailable",
    )
    def test_snapshot_and_output(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as directory:
            output = Path(directory)
            build_preview(root.parent / "policy-search", output)
            rows = json.loads((output / "data/policy_screening.json").read_text(encoding="utf-8"))
            candidates = [row for row in rows if row["candidate"]]
            self.assertEqual(len({row["id"] for row in rows}), 1290)
            self.assertEqual(len(candidates), 73)
            self.assertEqual(len({row["group"] for row in candidates}), 71)
            self.assertEqual(Counter(row["model"] for row in rows), {
                "INCLUDE": 66, "UNCERTAIN": 546, "EXCLUDE": 678,
            })
            by_id = {row["id"]: row for row in rows}
            self.assertEqual(by_id["11736563"]["human"], "EXCLUDE")
            self.assertEqual(by_id["10548199"]["human"], "")
            self.assertEqual(sum(bool(row["trials"]) for row in rows), 5)
            trials = [trial for row in rows for trial in row["trials"]]
            self.assertEqual(len({trial["id"] for trial in trials}), 10)
            self.assertEqual(len(trials), 11)
            self.assertEqual(sum(trial["id"] == "PILOT_MI_002" for trial in trials), 2)
            self.assertTrue(all((output / row["pdf"]).is_file() for row in rows if row["pdf"]))
            self.assertTrue((output / "policy_database_archive.html").is_file())
            review = json.loads((output / "data/policy_measure_review.json").read_text(encoding="utf-8"))
            instances = {item["id"]: item for item in review["instances"]}
            self.assertEqual(len(instances), 10)
            self.assertEqual({item["id"] for item in instances["PILOT_MI_002"]["sources"]},
                             {"10548199", "10846413"})
            self.assertEqual(sum("E4" in item["codes"] for item in instances.values()), 3)
            self.assertTrue(all(item["reviewStatus"] == "pending" for item in instances.values()))
            self.assertTrue((output / "policy_measure_review.html").is_file())
            overview = (output / "index.html").read_text(encoding="utf-8")
            overview_data = json.loads(overview.split('<script type="application/json" id="policy-overview-data">', 1)[1]
                                       .split("</script>", 1)[0])
            self.assertEqual(overview_data["counts"]["E4"], 3)
            self.assertEqual(overview_data["counts"]["A1"], 2)
            self.assertEqual([place["id"] for place in overview_data["places"]], ["PILOT_MI_002"])
            self.assertEqual((output / "news_database.html").read_bytes(),
                             (root / "docs/news_database.html").read_bytes())
