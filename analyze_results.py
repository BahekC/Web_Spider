"""Validate both export formats and calculate data-quality indicators offline."""
import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import median
from urllib.parse import urlsplit


def quantile(values, q):
    values = sorted(values)
    position = (len(values) - 1) * q
    low = int(position)
    return values[low] + (values[min(low + 1, len(values) - 1)] - values[low]) * (position - low)


def audit(path, min_items=100):
    rows = json.loads(path.read_text(encoding='utf-8'))
    with path.with_suffix('.csv').open(encoding='utf-8', newline='') as stream:
        csv_rows = list(csv.DictReader(stream))
    errors = []
    if len(rows) < min_items:
        errors.append(f'Only {len(rows)} records, expected >= {min_items}')
    if len(csv_rows) != len(rows):
        errors.append('JSON/CSV row count mismatch')
    for row, csv_row in zip(rows, csv_rows):
        for key, value in row.items():
            expected = '' if value is None else str(value)
            if csv_row.get(key) != expected:
                errors.append(f'JSON/CSV field mismatch: {key}')
                break
    urls = [r.get('url') for r in rows]
    duplicates = len(urls) - len(set(urls))
    if duplicates:
        errors.append(f'Duplicate URLs: {duplicates}')
    missing = {key: sum(row.get(key) in (None, '') for row in rows)
               for key in sorted({key for row in rows for key in row})}
    for row in rows:
        if not row.get('title') or not row.get('url'):
            errors.append('Missing required field')
        if urlsplit(row.get('url', '')).scheme not in ('http', 'https'):
            errors.append('Invalid URL')
        for field in ('title', 'summary'):
            value = row.get(field, '')
            if value != value.lower() or value != re.sub(r'\s+', ' ', value).strip() or re.search(r'</?[A-Za-z][^>]*>', value):
                errors.append(f'Unclean text: {field}')
    report = {'path': str(path), 'count': len(rows), 'csv_count': len(csv_rows),
              'duplicate_urls': duplicates, 'missing': missing, 'errors': sorted(set(errors))}
    prices = [row['price'] for row in rows if isinstance(row.get('price'), (float, int)) and math.isfinite(row['price'])]
    if prices:
        q1, q3 = quantile(prices, .25), quantile(prices, .75)
        lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        report['price_analysis'] = {'currency': 'USD', 'min': min(prices), 'max': max(prices),
                                    'median': median(prices), 'q1': q1, 'q3': q3,
                                    'iqr_lower': lower, 'iqr_upper': upper,
                                    'outliers': [r for r in rows if r.get('price') is not None and (r['price'] < lower or r['price'] > upper)]}
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=Path('outputs'))
    parser.add_argument('--min-items', type=int, default=100)
    args = parser.parse_args()
    reports = {name: audit(args.directory / f'{name}.json', args.min_items) for name in ('news', 'ecommerce')}
    path = args.directory / 'quality_report.json'
    path.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    for name, report in reports.items():
        print(f'{name}: {report["count"]} rows; errors={report["errors"]}')
    return int(any(report['errors'] for report in reports.values()))


if __name__ == '__main__':
    raise SystemExit(main())
