"""Create readable text from existing non-Nexis archives without fetching pages.

    python -m news_importer.readable_archive data/archive

Original artifacts and metadata are never modified. Existing readable files are
preserved unless --overwrite is passed. The report records gaps and extraction
limitations; a readable file is not a verification of metadata or completeness.
"""
from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.parent = None


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        node.parent = self.stack[-1]
        self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def walk(node):
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from walk(child)


NOISE = re.compile(r'(?:^|[-_\s])(?:related|recommended|recommendations|recirculation|recirc|newsletter|share|sharing|social|advertisement|comment|comments|promo)(?:$|[-_\s])', re.I)
BLOCKS = {'p','div','section','article','main','li','h1','h2','h3','h4','blockquote','tr','pre'}


def node_text(node):
    if node.tag in {'script','style','nav','aside','footer','form','button','iframe','noscript','svg'}:
        return ''
    label = node.attrs.get('class','') + ' ' + node.attrs.get('id','')
    if NOISE.search(label) or 'hidden' in node.attrs or node.attrs.get('aria-hidden') == 'true':
        return ''
    parts = [node_text(c) if isinstance(c, Node) else c for c in node.children]
    text = ''.join(parts)
    if node.tag == 'br':
        return '\n'
    return '\n\n' + text + '\n\n' if node.tag in BLOCKS else text


def clean_text(text):
    lines = [re.sub(r'[ \t\r\f\v]+', ' ', line).strip() for line in text.splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def structured_bodies(value):
    if isinstance(value, dict):
        kind = value.get('@type', [])
        kinds = [kind] if isinstance(kind, str) else kind
        if any(str(k).endswith(('Article','Posting')) for k in kinds) and isinstance(value.get('articleBody'), str):
            yield value['articleBody']
        for child in value.values():
            yield from structured_bodies(child)
    elif isinstance(value, list):
        for child in value:
            yield from structured_bodies(child)


def extract_html(html):
    """Prefer explicit article bodies; main content is a flagged fallback."""
    doc = Document(html)
    nodes = list(walk(doc.root))
    structured = []
    for node in nodes:
        if node.tag == 'script' and node.attrs.get('type','').lower() == 'application/ld+json':
            try:
                value = json.loads(''.join(c for c in node.children if isinstance(c,str)))
                structured.extend(structured_bodies(value))
            except (ValueError, TypeError):
                pass
    # Multiple article objects may include related articles. Use the longest body
    # and flag ambiguity rather than concatenate unrelated stories.
    structured = [clean_text(x) for x in structured if len(clean_text(x)) >= 200]
    if structured:
        return max(structured,key=len), 'structured_article_body', (['multiple_article_bodies'] if len(set(structured)) > 1 else [])
    # Some publishers mark every paragraph as articleBody. Preserve the whole
    # group in its enclosing article instead of choosing the longest paragraph.
    paragraph_groups = {}
    for node in nodes:
        if node.tag == 'p' and node.attrs.get('itemprop') == 'articleBody':
            parent = node.parent
            while parent is not None and parent.tag != 'article':
                parent = parent.parent
            paragraph_groups.setdefault(parent, []).append(clean_text(node_text(node)))
    if paragraph_groups:
        text = max(('\n\n'.join(p for p in parts if p) for parts in paragraph_groups.values()), key=len)
        if len(text) >= 200:
            return text, 'html_article_paragraphs', (['multiple_article_bodies'] if len(paragraph_groups)>1 else [])
    candidates = []
    for node in nodes:
        label = node.attrs.get('class','') + ' ' + node.attrs.get('id','')
        score = 0
        if node.tag == 'p':
            continue
        if node.attrs.get('itemprop') == 'articleBody':
            score = 4
        elif re.search(r'article[-_]?body|story[-_]?body|post[-_]?content|article[-_]?content|entry[-_]?content|body-copy|cooked',label,re.I):
            score = 3
        elif node.tag == 'article':
            score = 2
        elif node.tag == 'main' or node.attrs.get('role') == 'main':
            score = 1
        if score:
            text = clean_text(node_text(node))
            if len(text) >= 200:
                candidates.append((score,len(text),text))
    if not candidates:
        raise ValueError('No identifiable article/main body in saved HTML')
    score, _, text = max(candidates, key=lambda c:(c[0],c[1]))
    flags = ['review_for_boilerplate']
    if score == 1:
        flags.append('main_content_fallback')
    if sum(c[0] == score for c in candidates) > 1:
        flags.append('multiple_content_containers')
    return text, 'html_article' if score > 1 else 'html_main', flags


def markdown_text(text):
    text = re.sub(r'!\[[^\]]*\]\([^\n]*?\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\n]*?\)', r'\1', text)
    text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.M)
    return clean_text(text)


def convert_attempt(path, overwrite=False):
    meta = json.loads(path.read_text(encoding='utf-8-sig'))
    folder = path.parent
    result = {'source_id':meta.get('source_id'), 'attempt_id':meta.get('attempt_id'),
              'archive_dir':folder.as_posix(), 'crawl_outcome':meta.get('outcome'),
              'url':meta.get('final_url') or meta.get('requested_url'), 'warnings':[]}
    output = folder/'readable_article.txt'
    if output.exists() and not overwrite:
        return {**result,'status':'existing','output':output.as_posix()}
    if meta.get('outcome') != 'retrieved':
        return {**result,'status':'unavailable','reason':'Crawl was not retrieved; error pages are not articles'}
    markdown = folder/'content.md'
    raw = folder/'raw.html'
    pdf = folder/'original.pdf'
    method = ''
    text = ''
    if meta.get('source_kind') == 'pdf' or pdf.exists():
        if markdown.exists():
            text = markdown_text(markdown.read_text(encoding='utf-8-sig'))
            method = 'archived_pdf_text'
            result['warnings'] += ['whole_document_not_split','review_pdf_text_order_and_completeness']
        else:
            return {**result,'status':'unavailable','reason':'PDF exists without extracted text; PDF extraction/OCR needed'}
    elif raw.exists():
        try:
            text, method, flags = extract_html(raw.read_text(encoding='utf-8-sig',errors='replace'))
            result['warnings'] += flags
        except ValueError as exc:
            result['warnings'].append(str(exc))
    if not text and markdown.exists():
        text = markdown_text(markdown.read_text(encoding='utf-8-sig'))
        method = 'archived_markdown_fallback'
        result['warnings'] += ['review_for_boilerplate','no_article_boundary_identified']
    if len(text) < 200:
        return {**result,'status':'unavailable','reason':'No substantial saved body text'}
    if meta.get('source_kind') not in ('html','pdf'):
        result['warnings'].append('non_article_source_review_required')
    title = meta.get('observed_title') or next((r.get('imported_title') for r in meta.get('discovery_records',[]) if r.get('imported_title')), '')
    fields = [('Title (archived, unverified)',title),('Publication date (archived, unverified)',meta.get('publication_date')),
              ('Source ID',meta.get('source_id')),('Requested URL (original crawl)',meta.get('requested_url')),
              ('Final URL (original crawl)',meta.get('final_url')),('Extraction method',method),
              ('Review notes','; '.join(result['warnings']))]
    body = '\n'.join(f'{k}: {v}' for k,v in fields if v) + '\n\nARTICLE BODY\n\n' + text + '\n'
    with output.open('w' if overwrite else 'x',encoding='utf-8') as f:
        f.write(body)
    return {**result,'status':'written','method':method,'characters':len(text),'output':output.as_posix()}


def convert_directory(root, report, overwrite=False):
    results=[]
    for path in sorted(root.rglob('metadata.json')):
        try:
            results.append(convert_attempt(path,overwrite))
        except (OSError,ValueError,TypeError) as exc:
            results.append({'archive_dir':path.parent.as_posix(),'status':'error','reason':str(exc)})
    # Ignore Windows folder-customization files when identifying empty folders.
    empty=[p.as_posix() for p in root.rglob('*') if p.is_dir() and not any(x.name.lower()!='desktop.ini' for x in p.iterdir())]
    summary=dict(Counter(r['status'] for r in results))
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps({'summary':summary,'empty_folders':empty,'attempts':results},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(summary), f'Report: {report}')
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',nargs='?',type=Path,default=Path('data/archive'))
    parser.add_argument('--report',type=Path,default=Path('data/reports/readable_archive_report.json'))
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    if not args.root.is_dir():
        parser.error(f'Archive directory does not exist: {args.root}')
    convert_directory(args.root,args.report,args.overwrite)


if __name__=='__main__':
    main()
