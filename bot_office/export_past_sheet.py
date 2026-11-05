#!/usr/bin/env python3
# FANDING_PAST_SHEET_EXPORT_V1.0.0 — standalone, no trading imports
"""Read history.jsonl, export only past_sheet numeric fields to a server-local JSONL."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import date

DEFAULT_DIR = Path('/var/lib/bot-office/fanding')
OUT_NAME = 'past_sheet_numbers.jsonl'

def numeric(v):
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        raise ValueError('invalid number')
    import decimal
    d = decimal.Decimal(str(v))
    if not d.is_finite() or d <= 0:
        raise ValueError('invalid number')
    return float(d)

def levels(value):
    if not isinstance(value, list):
        raise ValueError('invalid levels')
    out = []
    for row in value:
        if not isinstance(row, dict):
            raise ValueError('invalid row')
        price = numeric(row['price'])
        qty = numeric(row['qty'])
        if not qty.is_integer():
            raise ValueError('invalid quantity')
        out.append({'price': price, 'qty': int(qty)})
    return out

def convert(item):
    if not isinstance(item, dict) or item.get('kind') != 'past_sheet':
        return None
    parsed = item.get('parsed')
    if not isinstance(parsed, dict):
        raise ValueError('missing parsed')
    day = parsed.get('close_date')
    if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('invalid close date')
    date.fromisoformat(day)
    post = item.get('post')
    if not isinstance(post, str) or not post.strip():
        raise ValueError('missing post URL')
    return {'종가일': day, '종가': numeric(parsed['close']),
            '매수': levels(parsed['buys']), '매도': levels(parsed['sells']),
            '글 주소': post.strip()}

def export(source, destination):
    source = Path(source)
    destination = Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('source and destination must differ')
    if destination.parent.resolve() != source.parent.resolve():
        raise ValueError('destination must share history directory')
    selected = {}
    invalid = 0
    with source.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except (ValueError, TypeError):
                invalid += 1
                continue
            if not isinstance(item, dict) or item.get('kind') != 'past_sheet':
                continue
            try:
                record = convert(item)
            except (ValueError, TypeError, KeyError, OverflowError):
                invalid += 1
                continue
            selected[(record['글 주소'], record['종가일'])] = record
    rows = sorted(selected.values(), key=lambda x: (x['종가일'], x['글 주소']))
    # Restrict output to a fixed basename; prevent symlink overwrite.
    if destination.name != OUT_NAME or destination.is_symlink():
        raise ValueError('unsafe destination')
    fd, tmp = tempfile.mkstemp(prefix='.past_sheet_numbers.', suffix='.tmp', dir=destination.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for record in rows:
                f.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, destination)
        dirfd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return len(rows), invalid

def main():
    parser = argparse.ArgumentParser(description='Export past_sheet numeric fields only; no orders or notifications')
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIR)
    args = parser.parse_args()
    count, skipped = export(args.directory / 'history.jsonl', args.directory / OUT_NAME)
    print(f'exported={count} invalid_past_sheet_or_json={skipped}')

if __name__ == '__main__':
    main()
