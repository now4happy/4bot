#!/usr/bin/env python3
# FANDING_PAST_SHEET_EXPORT_V1.1.1 — standalone, no trading imports
# 1.1.1 (사무실 v1.3.1, 2026-11-05): ① 당일 표(kind=sheet)도 뽑음 — 과거 표(past_sheet)와 같은 5칸, 중복 기준 종가일+글 주소
#   (같은 키는 history.jsonl 에서 나중 줄이 이김 = 다시 읽은 최신 숫자) ② 빠진 매매일 찾기 coverage()·missing_text()
#   · 주말 제외 · 미국 휴장일은 따로 표시(빠진 날짜에서 뺌) · 조기 폐장일(11/27·12/24 등)은 매매일
#   · 숫자를 추측으로 채우지 않음 (찾아서 보여 주기만) · --missing: 파일을 쓰지 않고 빠진 날짜만 출력
#   · 원본 history.jsonl 은 읽기만 · 숫자 파일의 칸(5칸)·원자적 저장·권한은 1.1.0 그대로
# 1.1.0 (사무실 v1.3.0, 2026-11-05): 자동 실행 지원 — fanding_trade 1.14.1 이 매일 12:00 KST 뒤 서비스 계정으로 호출
#   · auto_export(): history.jsonl 이 바뀌었을 때만 다시 씀 (원본은 읽기만) · 결과 0640 + 폴더 그룹
#   · --check: 파일을 쓰지 않고 개수만 (수동 확인용) · 쓰기 권한 없으면 Traceback 대신 안내 문구, 종료코드 2
#   · 뽑는 범위·필드·중복 기준·원자적 저장은 1.0.0 그대로
"""Read history.jsonl, export past_sheet + sheet numeric fields to a server-local JSONL."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import date, timedelta

VERSION = '1.1.1'
DEFAULT_DIR = Path('/var/lib/bot-office/fanding')
OUT_NAME = 'past_sheet_numbers.jsonl'
KINDS = ('past_sheet', 'sheet')          # 1.1.1: 과거 표 + 당일 표

# 미국 정규장 휴장일 (조기 폐장일은 장이 열린 날이라 넣지 않음)
# 2026~2028: fanding_trade.US_CLOSED 와 같은 표 (NYSE 공식). 2026 = 사용자 확정 목록과 같음
# 2025: 숫자 파일이 2025-04-07 부터라 추가 (NYSE 2025 휴장일, 1/9 카터 전 대통령 애도일 포함)
# 표에 없는 연도는 주말만 빼고 셈 (coverage()['unknown_years'] 로 표시)
US_CLOSED = {
    2025: '01-01 01-09 01-20 02-17 04-18 05-26 06-19 07-04 09-01 11-27 12-25',
    2026: '01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25',
    2027: '01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24',
    2028: '01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25',
}


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
    if not isinstance(item, dict) or item.get('kind') not in KINDS:
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

def collect(source):
    """history.jsonl → ({(글 주소, 종가일): 5칸}, 잘못된 줄 수, 종류별 개수). 읽기만"""
    selected, invalid, kinds = {}, 0, {k: 0 for k in KINDS}
    with Path(source).open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except (ValueError, TypeError):
                invalid += 1
                continue
            if not isinstance(item, dict) or item.get('kind') not in KINDS:
                continue
            try:
                record = convert(item)
            except (ValueError, TypeError, KeyError, OverflowError):
                invalid += 1
                continue
            selected[(record['글 주소'], record['종가일'])] = record     # 같은 키 → 나중 줄이 이김
            kinds[item['kind']] += 1
    return selected, invalid, kinds

def export(source, destination, mode=0o600, dir_group=False):
    source = Path(source)
    destination = Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('source and destination must differ')
    if destination.parent.resolve() != source.parent.resolve():
        raise ValueError('destination must share history directory')
    selected, invalid, _ = collect(source)
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
    selected, invalid, _ = collect(source)
    return len(selected), invalid


# ---------------------------------------------------------- 1.1.1 빠진 매매일 찾기 (채우지 않음, 보여 주기만)
def is_holiday(d):
    return d.weekday() < 5 and d.strftime('%m-%d') in US_CLOSED.get(d.year, '').split()

def is_trading_day(d):
    return d.weekday() < 5 and not is_holiday(d)

def coverage(dates):
    """종가일 목록 → 첫·마지막 종가일 사이 매매일 중 빠진 날·휴장일.
    {'first','last','trading','have','missing':[iso], 'runs':[{'start','end','n','holidays'}],
     'holidays':[iso], 'off_days':[주말·휴장일인데 있는 종가일], 'unknown_years':[연도]}"""
    days = sorted({date.fromisoformat(x) for x in dates})
    out = {'first': None, 'last': None, 'trading': 0, 'have': 0, 'missing': [], 'runs': [],
           'holidays': [], 'off_days': [], 'unknown_years': []}
    if not days:
        return out
    have = set(days)
    out['first'], out['last'] = days[0].isoformat(), days[-1].isoformat()
    out['off_days'] = [d.isoformat() for d in days if not is_trading_day(d)]
    out['unknown_years'] = sorted({y for y in range(days[0].year, days[-1].year + 1) if y not in US_CLOSED})
    run, pend = None, []      # pend: 지금 이어지는 빠진 구간 안의 휴장일
    d = days[0]
    while d <= days[-1]:
        if is_holiday(d):
            out['holidays'].append(d.isoformat())
            if run:
                pend.append(d.isoformat())
        elif is_trading_day(d):
            out['trading'] += 1
            if d in have:
                out['have'] += 1
                run, pend = None, []
            else:
                out['missing'].append(d.isoformat())
                if run is None:
                    run = {'start': d.isoformat(), 'end': d.isoformat(), 'n': 0, 'holidays': []}
                    out['runs'].append(run)
                run['end'] = d.isoformat()
                run['n'] += 1
                run['holidays'] += pend
                pend = []
        d += timedelta(days=1)
    return out

def _run_text(r):
    s, e = r['start'], r['end']
    txt = s if s == e else f"{s}~{e[5:] if e[:4] == s[:4] else e}"
    txt += f" ({r['n']}일"
    if r['holidays']:
        txt += ", 휴장 " + "·".join(h[5:] for h in r['holidays']) + " 뺌"
    return txt + ")"

def missing_text(cov, limit=3000):
    """사람이 읽는 빠진 날짜 요약 (텔레그램 답장용). limit 글자를 넘으면 뒤 구간은 개수만"""
    if not cov.get('first'):
        return "숫자 파일에 종가일이 없어요."
    lines = [f"기간 {cov['first']} ~ {cov['last']} · 매매일 {cov['trading']}일 중 {cov['have']}일 있음",
             f"빠진 매매일 {len(cov['missing'])}일 ({len(cov['runs'])}구간, 주말 제외·휴장일 뺌)"]
    used = sum(len(x) + 1 for x in lines)
    for i, r in enumerate(cov['runs']):
        t = "· " + _run_text(r)
        if used + len(t) + 1 > limit - 120:
            lines.append(f"· …외 {len(cov['runs']) - i}구간")
            break
        lines.append(t)
        used += len(t) + 1
    if cov['holidays']:
        lines.append("휴장일(빠진 날짜 아님): " + " ".join(cov['holidays']))
    if cov['off_days']:
        lines.append("⚠️ 주말·휴장일인데 표가 있는 종가일(오독 의심): " + " ".join(cov['off_days']))
    if cov['unknown_years']:
        lines.append("⚠️ 휴장일 표가 없는 연도(주말만 뺌): " + " ".join(map(str, cov['unknown_years'])))
    return "\n".join(lines)[:limit]

def coverage_of_file(path):
    """숫자 파일(past_sheet_numbers.jsonl) → coverage(). 읽기만"""
    dates = []
    with Path(path).open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                dates.append(json.loads(line)['종가일'])
    return coverage(dates)


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
    parser = argparse.ArgumentParser(description='Export past_sheet + sheet numeric fields only; no orders or notifications')
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIR)
    parser.add_argument('--check', action='store_true', help='count only, write nothing')
    parser.add_argument('--missing', action='store_true', help='show missing trading days, write nothing')
    args = parser.parse_args()
    try:
        if args.check or args.missing:
            selected, skipped, kinds = collect(args.directory / 'history.jsonl')
            if args.check:
                print(f'check(no write) rows={len(selected)} past_sheet={kinds["past_sheet"]} sheet={kinds["sheet"]} '
                      f'invalid_sheet_or_json={skipped}')
            print(missing_text(coverage([r['종가일'] for r in selected.values()]), limit=100000))
            return 0
        count, skipped = export(args.directory / 'history.jsonl', args.directory / OUT_NAME)
    except PermissionError:
        print('권한 없음: 이 폴더는 팬딩 서비스 계정 소유입니다. 숫자 파일은 매일 12:00 KST 뒤 자동으로 갱신됩니다. '
              '지금 바로 하려면 sudo 로 실행하세요. (--check·--missing 은 파일을 쓰지 않음)')
        return 2
    print(f'exported={count} invalid_sheet_or_json={skipped}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
