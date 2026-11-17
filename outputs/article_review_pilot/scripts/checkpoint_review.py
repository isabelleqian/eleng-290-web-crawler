"""Validate and checkpoint the standalone review, without touching source data."""
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SUPPORT = BASE / "support"
ROOT = BASE.parent.parent
FIELDS = ['source_id', 'title', 'publisher', 'publication_date', 'public_url',
          'factual_summary', 'review_status', 'review_notes', 'reviewed_at']


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    fields, rows = read_csv(BASE / 'reviewed_results.csv')
    _, inventory = read_csv(SUPPORT / 'nexis_review_inventory.csv')
    _, non = read_csv(ROOT / 'docs/data/non_nexis_metadata_reviewed.csv')
    _, selected = read_csv(SUPPORT / 'nexis_selection.csv')
    original_ids = {r['source_id'] for r in non + selected}
    non_ids = {r['source_id'] for r in non}
    nexis_ids = {r['source_id'] for r in inventory}
    ids = {r['source_id'] for r in rows}
    assert fields == FIELDS
    assert len(ids) == len(rows)
    assert len(nexis_ids) == len(inventory) == 1592
    assert len(non_ids) == 36
    assert ids <= non_ids | nexis_ids
    assert original_ids <= ids
    assert ids & non_ids == non_ids
    for row in rows:
        assert all(row[k].strip() for k in ['title', 'publisher', 'factual_summary',
                                           'review_notes', 'reviewed_at'])
        assert row['review_status'] in {'completed', 'partial_verification', 'needs_attention'}
        assert not row['publication_date'] or re.fullmatch(
            r'\d{4}(?:-\d{2}(?:-\d{2})?)?', row['publication_date'])
        assert not row['public_url'] or row['public_url'].startswith(('https://', 'http://'))
        datetime.fromisoformat(row['reviewed_at'])
    changed = [r['source_id'] for r in inventory
               if fingerprint(ROOT / r['readable_path']) != r['readable_sha256']]
    assert not changed, f'Original Nexis readable hashes changed: {changed}'
    previous_path = SUPPORT / 'validation.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8'))
    pilot = previous.get('original_pilot_validation', previous)
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    reviewed_nexis = [r for r in rows if r['source_id'] in nexis_ids]
    pending = [r for r in inventory if r['source_id'] not in ids]
    progress = {
        'updated_at': now,
        'scope': 'All 1592 Nexis records, retaining the original 36 non-Nexis reviews',
        'processing_order': ['publication_date', 'source_id'],
        'nexis_total': len(inventory),
        'nexis_reviewed': len(reviewed_nexis),
        'nexis_pending': len(pending),
        'nexis_summaries_completed': len(reviewed_nexis),
        'nexis_summaries_pending': len(pending),
        'nexis_verification_deferred_by_user': sum(
            'verification deferred at user request' in r['review_notes']
            for r in reviewed_nexis),
        'additional_nexis_reviewed_after_pilot': len(reviewed_nexis) - len(selected),
        'reviewed_status_counts': dict(Counter(r['review_status'] for r in reviewed_nexis)),
        'nexis_reviews_with_public_url': sum(bool(r['public_url']) for r in reviewed_nexis),
        'next_pending': [{k: r[k] for k in ['source_id', 'title', 'publication_date',
                                          'readable_path']} for r in pending[:5]],
        'complete': not pending,
        'pending_rule': 'Inventory IDs absent from reviewed_results.csv; no review implied.',
        'background_worker_running': False,
    }
    validation = {
        'validated_at': now, 'checks_passed': True,
        'total_rows': len(rows), 'unique_ids': len(ids),
        'non_nexis_rows': len(non_ids), 'nexis_rows': len(reviewed_nexis),
        'original_pilot_ids_preserved': original_ids <= ids,
        'no_out_of_scope_ids': ids <= non_ids | nexis_ids,
        'all_1592_original_nexis_readables_unchanged': not changed,
        'status_counts': dict(Counter(r['review_status'] for r in rows)),
        'nonblank_summaries': sum(bool(r['factual_summary']) for r in rows),
        'nonblank_public_urls': sum(bool(r['public_url']) for r in rows),
        'nonblank_dates': sum(bool(r['publication_date']) for r in rows),
        'review_is_complete': not pending,
        'original_pilot_validation': pilot,
        'sha256': {str(p.relative_to(ROOT)): fingerprint(p) for p in [
            BASE / 'reviewed_results.csv', SUPPORT / 'nexis_review_inventory.csv',
            SUPPORT / 'nexis_selection.csv', ROOT / 'docs/data/non_nexis_metadata_reviewed.csv']},
        'token_usage': None, 'cost': None,
    }
    for name, payload in [('progress.json', progress), ('validation.json', validation)]:
        (SUPPORT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n',
                                 encoding='utf-8')
    print(json.dumps({k: progress[k] for k in ['nexis_total', 'nexis_reviewed',
                     'nexis_pending', 'reviewed_status_counts', 'complete']}))


if __name__ == '__main__':
    main()
