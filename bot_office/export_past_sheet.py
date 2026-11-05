#!/usr/bin/env python3
# FANDING_PAST_SHEET_EXPORT_V1.1.0 — standalone, no trading imports
# 1.1.0 (사무실 v1.3.0, 2026-11-05): 자동 실행 지원 — fanding_trade 1.14.1 이 매일 12:00 KST 뒤 서비스 계정으로 호출
#   · auto_export(): history.jsonl 이 바뀌었을 때만 다시 씀 (원본은 읽기만) · 결과 0640 + 폴더 그룹
#   · --check: 파일을 쓰지 않고 개수만 (수동 확인용) · 쓰기 권한 없으면 Traceback 대신 안내 문구, 종료코드 2
#   · 뽑는 범위·필드·중복 기준·원자적 저장은 1.0.0 그대로
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

def export(source, destination, mode=0o600, dir_group=False):
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
        os.fchmod(fd, mode)
        if dir_group:   # 자동 실행: 결과 파일 그룹을 폴더 그룹과 같게 (실패해도 진행)
            try:
                os.fchown(fd, -1, destination.parent.stat().st_gid)
            except OSError:
                pass
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

def count_only(source):
    """파일을 쓰지 않고 개수만 (읽기 전용)"""
    selected, invalid = set(), 0
    with Path(source).open('r', encoding='utf-8') as f:
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
            selected.add((record['글 주소'], record['종가일']))
    return len(selected), invalid


def needs_update(directory):
    """결과 파일이 없거나 history.jsonl 이 그 뒤에 바뀌었으면 True"""
    directory = Path(directory)
    src, dst = directory / 'history.jsonl', directory / OUT_NAME
    if not src.exists():
        return False
    if not dst.exists():
        return True
    return src.stat().st_mtime_ns > dst.stat().st_mtime_ns


def auto_export(directory=DEFAULT_DIR):
    """자동 실행 진입점 (fanding_trade 상시 프로그램 = 폴더 주인 서비스 계정이 부름). 알림·주문 없음"""
    directory = Path(directory)
    if not needs_update(directory):
        return {'status': 'skip', 'count': 0, 'invalid': 0}
    count, skipped = export(directory / 'history.jsonl', directory / OUT_NAME, mode=0o640, dir_group=True)
    return {'status': 'exported', 'count': count, 'invalid': skipped}


def main():
    parser = argparse.ArgumentParser(description='Export past_sheet numeric fields only; no orders or notifications')
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--check', action='store_true', help='count only, write nothing')
    args = parser.parse_args()
    try:
        if args.check:
            count, skipped = count_only(args.directory / 'history.jsonl')
            print(f'check(no write) past_sheet={count} invalid_past_sheet_or_json={skipped}')
            return 0
        count, skipped = export(args.directory / 'history.jsonl', args.directory / OUT_NAME)
    except PermissionError:
        print('권한 없음: 이 폴더는 팬딩 서비스 계정 소유입니다. 숫자 파일은 매일 12:00 KST 뒤 자동으로 갱신됩니다. '
              '지금 바로 하려면 sudo 로 실행하세요. (--check 는 파일을 쓰지 않음)')
        return 2
    print(f'exported={count} invalid_past_sheet_or_json={skipped}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
