import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from news_importer.readable_archive import extract_html, convert_attempt


class ReadableArchiveTests(unittest.TestCase):
    def test_repeated_article_body_paragraphs_are_not_truncated(self):
        first = 'First article paragraph with inline <em>emphasis</em>. ' * 8
        last = 'Final paragraph describing a different intervention. ' * 8
        html = f'<article><p itemprop="articleBody">{first}</p><p itemprop="articleBody">{last}</p></article><article class="related"><p>Different article.</p></article>'
        body, method, _ = extract_html(html)
        self.assertIn('First article paragraph with inline emphasis.', body)
        self.assertIn('Final paragraph', body)
        self.assertNotIn('Different article.', body)
        self.assertEqual(method, 'html_article_paragraphs')

    def test_article_boundary_excludes_related_content_and_navigation(self):
        html = '<nav>Site links</nav><article><div class="entry-content sidebar-right"><p>' + 'Actual source reporting. '*20 + '</p><aside>Different headline</aside><div class="related-posts">Related story</div></div></article>'
        text, _, _ = extract_html(html)
        self.assertNotIn('Related story', text)
        self.assertNotIn('Different headline', text)
        self.assertNotIn('Site links', text)

    def test_blocked_pages_are_not_converted_and_inputs_are_preserved(self):
        with TemporaryDirectory() as temp:
            p = Path(temp)/'metadata.json'
            p.write_text(json.dumps({'outcome':'blocked'}),encoding='utf-8')
            original = p.read_bytes()
            (p.parent/'content.md').write_text('Access denied. '*100,encoding='utf-8')
            result = convert_attempt(p)
            self.assertEqual(result['status'],'unavailable')
            self.assertFalse((p.parent/'readable_article.txt').exists())
            self.assertEqual(p.read_bytes(),original)

    def test_pdf_text_is_preserved_and_existing_output_not_overwritten(self):
        with TemporaryDirectory() as temp:
            p = Path(temp)/'metadata.json'
            p.write_text(json.dumps({'outcome':'retrieved','source_kind':'pdf'}),encoding='utf-8')
            body = 'Meeting packet source text and second document. '*20
            (p.parent/'content.md').write_text(body,encoding='utf-8')
            self.assertEqual(convert_attempt(p)['status'],'written')
            out = p.parent/'readable_article.txt'
            self.assertIn(body.strip(),out.read_text(encoding='utf-8'))
            out.write_text('Reviewed manually',encoding='utf-8')
            self.assertEqual(convert_attempt(p)['status'],'existing')
            self.assertEqual(out.read_text(encoding='utf-8'),'Reviewed manually')
