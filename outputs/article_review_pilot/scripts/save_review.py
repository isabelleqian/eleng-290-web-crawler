"""Write only standalone pilot results; never accesses a database."""
import csv
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SUPPORT = BASE / "support"
ROOT = BASE.parent.parent
FIELDS = ['source_id', 'title', 'publisher', 'publication_date', 'public_url',
          'factual_summary', 'review_status', 'review_notes', 'reviewed_at']

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

NON = read_csv(ROOT / 'docs/data/non_nexis_metadata_reviewed.csv')
NEXIS = read_csv(SUPPORT / 'nexis_selection.csv')

def save(index, summary, notes, status='completed', date=None, title=None,
         url=None, publisher=None, nexis=False):
    source = (NEXIS if nexis else NON)[index]
    row = dict(source_id=source['source_id'], title=title or source['title'],
               publisher=publisher or source['publisher'],
               publication_date=source['publication_date'] if date is None else date,
               public_url=(source.get('requested_url', '') if url is None else url),
               factual_summary=summary, review_status=status, review_notes=notes,
               reviewed_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    rows = {r['source_id']: r for r in read_csv(BASE / 'reviewed_results.csv')}
    rows[row['source_id']] = row
    inventory = SUPPORT / 'nexis_review_inventory.csv'
    order = [r['source_id'] for r in NON + (read_csv(inventory) if inventory.exists() else NEXIS)]
    with (BASE / 'reviewed_results.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows[key] for key in order if key in rows)

def save_nexis_record(index, summary, notes, status='partial_verification',
                      date=None, title=None, url='', publisher=None):
    source = read_csv(SUPPORT / 'nexis_review_inventory.csv')[index]
    row = dict(source_id=source['source_id'], title=title or source['title'],
               publisher=publisher or source['publisher'],
               publication_date=source['publication_date'] if date is None else date,
               public_url=url, factual_summary=summary, review_status=status,
               review_notes=notes,
               reviewed_at=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    rows = {r['source_id']: r for r in read_csv(BASE / 'reviewed_results.csv')}
    rows[row['source_id']] = row
    order = [r['source_id'] for r in NON + read_csv(SUPPORT / 'nexis_review_inventory.csv')]
    assert set(rows).issubset(set(order))
    with (BASE / 'reviewed_results.csv').open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows[key] for key in order if key in rows)


def save_nexis_summary(index, summary, notes=''):
    """Add a summary-first row without overwriting any existing review."""
    source = read_csv(SUPPORT / 'nexis_review_inventory.csv')[index]
    existing = {r['source_id'] for r in read_csv(BASE / 'reviewed_results.csv')}
    if source['source_id'] in existing:
        raise ValueError(f"Already reviewed: {source['source_id']}")
    prefix = ('Summary complete from archived article; public URL and '
              'title/publisher/date verification deferred at user request. '
              'Starting metadata retained without independent verification. ')
    save_nexis_record(index, summary, prefix + notes)
