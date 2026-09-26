import csv
import json

from analyze_results import audit, quantile


def test_quantile_uses_linear_interpolation():
    assert quantile([1, 2, 3, 4], .25) == 1.75
    assert quantile([5], .75) == 5


def test_audit_detects_export_mismatch_duplicates_and_unclean_text(tmp_path):
    path = tmp_path / 'data.json'
    rows = [{'title': 'BAD  text', 'url': 'https://example.org/1', 'price': 12.5}] * 2
    path.write_text(json.dumps(rows), encoding='utf-8')
    with path.with_suffix('.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerow(dict(rows[0], price=99))
    report = audit(path, min_items=100)
    assert report['duplicate_urls'] == 1
    assert 'JSON/CSV row count mismatch' in report['errors']
    assert 'JSON/CSV field mismatch: price' in report['errors']
    assert 'Unclean text: title' in report['errors']
    assert any('expected >= 100' in error for error in report['errors'])


def test_audit_accepts_missing_optional_rating(tmp_path):
    path = tmp_path / 'data.json'
    row = {'title': 'model', 'url': 'https://example.org/1', 'price': 0.0, 'rating': None}
    path.write_text(json.dumps([row]), encoding='utf-8')
    with path.with_suffix('.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=row.keys())
        writer.writeheader()
        writer.writerow(row)
    assert audit(path, min_items=1)['errors'] == []
