"""Checks for extracting Nexis article text without indexing metadata."""

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from news_importer.readable_nexis import readable_article, convert_directory


class ReadableNexisTests(unittest.TestCase):
    def test_namespaces_inline_text_entities_and_metadata(self):
        metadata = {"title": "Example", "raw": {"Document": {"Content": '''
            <entry xmlns="urn:atom"><author><name>LexisNexis</name></author>
            <article xmlns:n="urn:nitf"><n:body.content><bodyText>
            <p>One <em>bold</em> word &amp; another.<br/>Next line.</p>
            <p/><p>Second paragraph.</p></bodyText></n:body.content>
            <metadata><publicationName>Original News</publicationName>
            <p>Indexing noise</p></metadata></article></entry>'''}}}
        result = readable_article(metadata)
        self.assertIn("Original publication: Original News", result)
        self.assertIn("One bold word & another. Next line.\n\nSecond paragraph.", result)
        self.assertNotIn("Indexing noise", result)
        self.assertNotIn("Author: LexisNexis", result)

    def test_batch_recurses_skips_and_continues_after_failure(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            good = root / "keyword" / "article"
            bad = root / "keyword" / "broken"
            good.mkdir(parents=True)
            bad.mkdir(parents=True)
            data = {"raw": {"Document": {"Content":
                    "<article><body.content><p>Article text.</p></body.content></article>"}}}
            (good / "metadata.json").write_text(json.dumps(data), encoding="utf-8")
            (bad / "metadata.json").write_text("{}", encoding="utf-8")
            self.assertEqual(convert_directory(root), (1, 0, 1))
            output = good / "readable_article.txt"
            self.assertIn("Article text.", output.read_text(encoding="utf-8"))
            output.write_text("Keep existing", encoding="utf-8")
            self.assertEqual(convert_directory(root), (0, 1, 1))
            self.assertEqual(output.read_text(encoding="utf-8"), "Keep existing")
            self.assertEqual(convert_directory(root, overwrite=True), (1, 0, 1))
            self.assertIn("Article text.", output.read_text(encoding="utf-8"))

    def test_missing_article_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "raw.Document.Content"):
            readable_article({"title": "Metadata only"})

    def test_dtd_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "DTD"):
            readable_article({"raw": {"Document": {"Content": '<!DOCTYPE x><x/>'}}})


if __name__ == "__main__":
    unittest.main()
