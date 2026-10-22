import json, os, tempfile, threading, uuid
from pathlib import Path
from datetime import datetime, timezone

BASE = Path('/var/lib/bot-office/market-manual')
STATE = BASE / 'dev-requests.json'
PUBLIC = Path('/var/lib/bot-office-dev-public')
LOCK = threading.Lock()

def load(path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default

def read():
    with LOCK:
        requests = load(STATE, {})
    catalog = load(PUBLIC / 'catalog.json', {})
    results = {}
    for ident in requests:
        result = load(PUBLIC / (ident + '.json'), None)
        if result is not None:
            results[ident] = result
    return {
        'catalog': catalog,
        'requests': requests,
        'results': results
    }

def save(d):
    if not isinstance(d, dict):
        raise ValueError('잘못된 요청')
    ident = str(uuid.UUID(d.get('request_id', '')))
    proposal = d.get('proposal')
    unit = d.get('unit')
    name = d.get('file')
    if not all(isinstance(x, str) for x in (proposal, unit, name)):
        raise ValueError('요청 항목 확인 필요')
    if unit not in ('bithumb_bot.service', 'toss_dca.service'):
        raise ValueError('허용하지 않은 봇')
    catalog = load(PUBLIC / 'catalog.json', {})
    if name not in catalog.get(unit, []):
        raise ValueError('등록되지 않은 파일')
    reviews = load(BASE / 'reviews.json', {})
    idea = reviews.get('_proposals', {}).get(proposal)
    if not isinstance(idea, dict) or idea.get('archived'):
        raise ValueError('사용할 수 없는 제안')
    with LOCK:
        records = load(STATE, {})
        if ident in records:
            old = records[ident]
            if (old['proposal'], old['unit'], old['file']) != (
                proposal, unit, name
            ):
                raise ValueError('요청 번호 중복')
            return {'ok': True, 'request': old}
        if len(records) >= 100:
            raise ValueError('개발 요청 보관 한도 도달')
        record = {
            'id': ident,
            'proposal': proposal,
            'unit': unit,
            'file': name,
            'title': str(idea.get('title', ''))[:80],
            'created_at': datetime.now(timezone.utc).isoformat(),
            'status': '초안 생성 대기'
        }
        records[ident] = record
        fd, tmp = tempfile.mkstemp(dir=BASE)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(records, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, STATE)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return {'ok': True, 'request': record}
