"""Local image-reading usage estimate; never presents this as billing balance."""
import fcntl
import json
import math
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get('OFFICE_ROOT', '/'))
STATE = ROOT / 'var/lib/bot-office/gemini-usage.json'


@contextmanager
def state(write=True):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with open(str(STATE) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if STATE.exists():
            data = json.loads(STATE.read_text())
        else:
            data = {'calls': 0, 'models': {}, 'unknown_usage': 0}
        yield data
        if write:
            fd, tmp = tempfile.mkstemp(dir=STATE.parent)
            try:
                with os.fdopen(fd, 'w') as out:
                    json.dump(data, out, ensure_ascii=False)
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(tmp, STATE)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)


def record(response, model):
    usage = response.get('usageMetadata') or {}
    with state() as data:
        data['calls'] += 1
        if 'promptTokenCount' not in usage or 'candidatesTokenCount' not in usage:
            data['unknown_usage'] += 1
            return
        row = data['models'].setdefault(model, {'input': 0, 'output': 0, 'calls': 0})
        row['input'] += int(usage['promptTokenCount'])
        row['output'] += int(usage['candidatesTokenCount']) + int(usage.get('thoughtsTokenCount', 0))
        row['calls'] += 1


def number(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('0 이상의 유한한 숫자를 입력하세요.')
    return value


def report():
    with state(write=False) as data:
        snap = data.get('snapshot')
        lines = ['💳 <b>Gemini 선불 · 판독 사용 기록</b>',
                 f"▫️ 기록 시작 후 API 응답 {data['calls']}회 (이미지 수와 다름)"]
        if not snap:
            return '\n'.join(lines + ['▫️ 기준 잔액 미등록 · /제미나이잔액 달러금액',
                                      '▫️ 청구계정 실시간 잔액 조회가 아닙니다.'])
        lines.append(f"▫️ 직접 등록한 기준 잔액 ${snap['usd']:.2f} · {snap['at']}")
        cost, calls = 0.0, 0
        complete = data['unknown_usage'] == snap['unknown_usage']
        for model, row in data['models'].items():
            old = snap['models'].get(model, {})
            count = row['calls'] - old.get('calls', 0)
            if not count:
                continue
            rates = data.get('rates', {}).get(model)
            if rates is None:
                complete = False
                continue
            cost += ((row['input'] - old.get('input', 0)) * rates[0]
                     + (row['output'] - old.get('output', 0)) * rates[1]) / 1_000_000
            calls += count
        if complete:
            remaining = max(0, snap['usd'] - cost)
            lines.append(f'▫️ 기준 등록 후 판독 추정 비용 ${cost:.4f} · 추정 잔액 ${remaining:.2f}')
            if cost > 0 and calls:
                lines.append(f'▫️ 같은 평균 사용량이면 약 {math.floor(remaining / (cost / calls)):,}회 API 호출 가능')
            else:
                lines.append('▫️ 잔여 호출 횟수: 단가와 사용 기록이 쌓이면 계산')
        else:
            lines.append('▫️ 단가 또는 토큰 기록 부족 · 추정 잔액/횟수 계산 보류')
        lines += ['▫️ 판독 호출만 반영 · 다른 프로그램 사용·재시도 중 응답 유실·청구 할인 미반영',
                  '▫️ 단가 등록: /제미나이단가 모델명 입력단가 출력단가 (USD/100만 토큰)']
        return '\n'.join(lines)


def handle(tg, text):
    parts = text.split()
    command = parts[0] if parts else ''
    if command not in ('/제미나이잔액', '/제미나이단가'):
        return False
    try:
        if command == '/제미나이잔액' and len(parts) == 2:
            usd = number(parts[1])
            with state() as data:
                data['snapshot'] = {'usd': usd, 'models': json.loads(json.dumps(data['models'])),
                                    'unknown_usage': data['unknown_usage'],
                                    'at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
        elif command == '/제미나이단가' and len(parts) == 4:
            rates = [number(parts[2]), number(parts[3])]
            with state() as data:
                data.setdefault('rates', {})[parts[1]] = rates
        elif len(parts) != 1:
            raise ValueError('사용법: /제미나이잔액 달러금액 또는 /제미나이단가 모델명 입력단가 출력단가')
        tg.send(report())
    except (ValueError, OSError) as exc:
        import html
        tg.send('Gemini 기록 확인 필요: ' + html.escape(str(exc)))
    return True
