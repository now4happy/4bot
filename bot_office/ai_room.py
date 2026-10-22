#!/usr/bin/env python3
"""AI 협업 채팅방 - bot-office 내부 서비스 (127.0.0.1 전용, 로그인은 server.py가 담당)"""
VERSION = 'room-1.0.0'
import json, os, re, sqlite3, threading, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
DB = os.environ.get('ROOM_DB', '/var/lib/ai-room/room.db')
ENV_FILE = os.environ.get('ROOM_ENV', '/etc/bot-office/ai.env')
PORT = int(os.environ.get('ROOM_PORT', '8770'))
KST = timezone(timedelta(hours=9))
LOCK = threading.Lock()
HIST = 20          # 직접 연결 AI에게 보내는 최근 메시지 수
CTX_CHARS = 6000   # 간접 연결 AI용 문맥 복사 최대 글자 수

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY, name TEXT NOT NULL, note TEXT DEFAULT '', created TEXT);
CREATE TABLE IF NOT EXISTS agents(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, kind TEXT NOT NULL,
  model TEXT DEFAULT '', base_url TEXT DEFAULT '', key_env TEXT DEFAULT '', site_url TEXT DEFAULT '',
  account TEXT DEFAULT '', end_date TEXT DEFAULT '', cooldown_until TEXT DEFAULT '',
  enabled INTEGER DEFAULT 1, color TEXT DEFAULT '#888888', persona TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS members(room_id INTEGER, agent_id INTEGER, PRIMARY KEY(room_id, agent_id));
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, room_id INTEGER, agent_id INTEGER, content TEXT,
  status TEXT DEFAULT 'done', created TEXT, tok INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_msg_room ON messages(room_id, id);
CREATE TABLE IF NOT EXISTS usage(agent_id INTEGER, day TEXT, tokens INTEGER DEFAULT 0, PRIMARY KEY(agent_id, day));
"""
# kind: direct = API로 자동 답변 / indirect = 아이디로 로그인해 쓰는 사이트(문맥 복사·답변 붙여넣기)
SEED = [
    ('딥시크', 'direct', 'deepseek-chat', 'https://api.deepseek.com', 'DEEPSEEK_API_KEY', 'https://chat.deepseek.com', 1, '#4D6BFE'),
    ('제미나이', 'direct', 'gemini-2.5-flash', 'https://generativelanguage.googleapis.com/v1beta/openai', 'GEMINI_API_KEY', 'https://gemini.google.com', 0, '#1A73E8'),
    ('뮤즈', 'direct', '', '', 'MUSE_API_KEY', 'https://www.meta.ai', 0, '#0866FF'),
    ('GPT', 'indirect', '', '', '', 'https://chatgpt.com', 1, '#10A37F'),
    ('클로드', 'indirect', '', '', '', 'https://claude.ai', 1, '#D97757'),
]
AGENT_FIELDS = ('name', 'kind', 'model', 'base_url', 'key_env', 'site_url', 'account', 'end_date', 'enabled', 'color', 'persona')


def now():
    return datetime.now(KST)


def today():
    return now().strftime('%Y-%m-%d')


def est_tokens(text):
    return max(1, round(len(text or '') / 2))


def db():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with LOCK, db() as c:
        c.executescript(SCHEMA)
        if not c.execute('SELECT 1 FROM agents LIMIT 1').fetchone():
            for s in SEED:
                c.execute('INSERT INTO agents(name,kind,model,base_url,key_env,site_url,enabled,color) VALUES(?,?,?,?,?,?,?,?)', s)
        if not c.execute('SELECT 1 FROM rooms LIMIT 1').fetchone():
            c.execute('INSERT INTO rooms(name,note,created) VALUES(?,?,?)', ('AI 협업방', '기본 방', now().isoformat()))
            rid = c.execute('SELECT id FROM rooms ORDER BY id LIMIT 1').fetchone()[0]
            for a in c.execute('SELECT id FROM agents'):
                c.execute('INSERT OR IGNORE INTO members VALUES(?,?)', (rid, a[0]))


def keys():
    out = {}
    try:
        for line in Path(ENV_FILE).read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k, v = line.split('=', 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def add_usage(agent_id, tokens):
    with LOCK, db() as c:
        c.execute('INSERT INTO usage VALUES(?,?,?) ON CONFLICT(agent_id,day) DO UPDATE SET tokens=tokens+excluded.tokens',
                  (agent_id, today(), int(tokens)))


def agent_status(a, k, used):
    d = dict(a)
    d['today_tokens'] = used.get(a['id'], 0)
    d['dday'] = None
    if a['end_date']:
        try:
            d['dday'] = (datetime.strptime(a['end_date'], '%Y-%m-%d').date() - now().date()).days
        except ValueError:
            pass
    d['cooldown_left'] = 0
    if a['cooldown_until']:
        try:
            left = (datetime.fromisoformat(a['cooldown_until']) - now()).total_seconds()
            d['cooldown_left'] = max(0, int(left))
        except ValueError:
            pass
    d['key_ok'] = bool(a['key_env'] and k.get(a['key_env'])) if a['kind'] == 'direct' else None
    d['ready'] = bool(a['enabled']) and (d['key_ok'] and bool(a['model'] and a['base_url']) if a['kind'] == 'direct' else True)
    return d


def state():
    k = keys()
    with db() as c:
        used = {r[0]: r[1] for r in c.execute('SELECT agent_id,tokens FROM usage WHERE day=?', (today(),))}
        agents = [agent_status(a, k, used) for a in c.execute('SELECT * FROM agents ORDER BY id')]
        rooms = []
        for r in c.execute('SELECT * FROM rooms ORDER BY id'):
            d = dict(r)
            d['members'] = [m[0] for m in c.execute('SELECT agent_id FROM members WHERE room_id=?', (r['id'],))]
            last = c.execute('SELECT MAX(id) FROM messages WHERE room_id=?', (r['id'],)).fetchone()[0]
            d['last_id'] = last or 0
            rooms.append(d)
    return {'version': VERSION, 'rooms': rooms, 'agents': agents, 'today': today()}


def names(c):
    return {a['id']: a['name'] for a in c.execute('SELECT id,name FROM agents')}


def history(c, room_id, before_id, limit):
    rows = c.execute("SELECT * FROM messages WHERE room_id=? AND id<? AND status='done' ORDER BY id DESC LIMIT ?",
                     (room_id, before_id, limit)).fetchall()
    return list(reversed(rows))


def build_chat(c, room_id, agent, before_id):
    room = c.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
    nm = names(c)
    system = (f"너는 '{agent['name']}'(이)야. 사용자와 여러 AI가 함께 쓰는 협업 채팅방 '{room['name']}'에 참여하고 있어. "
              "다른 참가자의 발언 앞에는 [이름]이 붙어 있어. 다른 AI의 의견도 참고해서, 한국어로 간결하고 정확하게 답해. "
              "네 답변 앞에는 이름을 붙이지 마.")
    if room['note']:
        system += f"\n방 설명: {room['note']}"
    if agent['persona']:
        system += f"\n추가 지시: {agent['persona']}"
    msgs = []
    for m in history(c, room_id, before_id, HIST):
        if m['agent_id'] == agent['id']:
            role, text = 'assistant', m['content']
        else:
            who = '나' if not m['agent_id'] else nm.get(m['agent_id'], '?')
            role, text = 'user', f"[{who}] {m['content']}"
        if msgs and msgs[-1]['role'] == role:
            msgs[-1]['content'] += '\n\n' + text
        else:
            msgs.append({'role': role, 'content': text})
    while msgs and msgs[0]['role'] == 'assistant':
        msgs.pop(0)
    return [{'role': 'system', 'content': system}] + msgs


def finish(msg_id, content, status, tok=0):
    with LOCK, db() as c:
        c.execute('UPDATE messages SET content=?, status=?, tok=? WHERE id=?', (content, status, tok, msg_id))


def call_direct(agent_id, room_id, msg_id):
    try:
        with db() as c:
            a = c.execute('SELECT * FROM agents WHERE id=?', (agent_id,)).fetchone()
            payload = build_chat(c, room_id, a, msg_id)
        key = keys().get(a['key_env'] or '')
        if not key:
            return finish(msg_id, f"API 키가 없어요. 서버의 {ENV_FILE} 에 {a['key_env'] or '키 이름'}=... 을 넣어주세요.", 'error')
        if not (a['model'] and a['base_url']):
            return finish(msg_id, '모델 이름이나 API 주소가 비어 있어요. AI 설정에서 채워주세요.', 'error')
        body = json.dumps({'model': a['model'], 'messages': payload}).encode()
        req = urllib.request.Request(a['base_url'].rstrip('/') + '/chat/completions', data=body,
                                     headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
        text = (d['choices'][0]['message'].get('content') or '').strip() or '(빈 답변)'
        u = d.get('usage') or {}
        tok = int(u.get('total_tokens') or (est_tokens(body.decode()) + est_tokens(text)))
        add_usage(agent_id, tok)
        finish(msg_id, text, 'done', tok)
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:300]
        finish(msg_id, f'API 오류 {e.code}: {detail}', 'error')
    except Exception as e:
        finish(msg_id, f'연결 오류: {e}', 'error')


def context_text(room_id, msg_id):
    with db() as c:
        m = c.execute('SELECT * FROM messages WHERE id=? AND room_id=?', (msg_id, room_id)).fetchone()
        if not m:
            return None, None
        a = c.execute('SELECT * FROM agents WHERE id=?', (m['agent_id'],)).fetchone()
        room = c.execute('SELECT * FROM rooms WHERE id=?', (room_id,)).fetchone()
        nm = names(c)
        lines = []
        for h in history(c, room_id, msg_id, HIST):
            who = '나' if not h['agent_id'] else nm.get(h['agent_id'], '?')
            lines.append(f'[{who}] {h["content"]}')
    body = '\n\n'.join(lines)
    if len(body) > CTX_CHARS:
        body = '…(앞부분 생략)…\n' + body[-CTX_CHARS:]
    head = (f"[AI 협업방 '{room['name']}']\n여러 AI와 함께 쓰는 채팅방의 최근 대화야. "
            f"너는 '{a['name']}'(으)로 참여하고 있어. 다른 AI의 의견도 참고해서 마지막 [나]의 말에 한국어로 답해줘.\n\n")
    return head + body, a


class H(BaseHTTPRequestHandler):
    server_version = 'AIRoom'

    def log_message(self, *a):
        pass

    def out(self, code, obj=None, ctype='application/json; charset=utf-8', raw=None):
        data = raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n > 2_000_000:
            raise ValueError('too large')
        return json.loads(self.rfile.read(n) or b'{}') if n else {}

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        p = u.path.rstrip('/') or '/room'
        try:
            if p == '/room':
                return self.out(200, raw=(ROOT / 'room.html').read_bytes(), ctype='text/html; charset=utf-8')
            if p == '/room/api/state':
                return self.out(200, state())
            if p == '/room/api/messages':
                rid, after = int(q.get('room', 0)), int(q.get('after', 0))
                with db() as c:
                    if after:
                        rows = c.execute('SELECT * FROM messages WHERE room_id=? AND id>? ORDER BY id', (rid, after)).fetchall()
                    else:
                        rows = list(reversed(c.execute('SELECT * FROM messages WHERE room_id=? ORDER BY id DESC LIMIT 200', (rid,)).fetchall()))
                    pend = [r[0] for r in c.execute("SELECT id FROM messages WHERE room_id=? AND status IN ('pending','waiting')", (rid,))]
                return self.out(200, {'messages': [dict(r) for r in rows], 'open': pend})
            if p == '/room/api/message':
                with db() as c:
                    r = c.execute('SELECT * FROM messages WHERE id=?', (int(q.get('id', 0)),)).fetchone()
                return self.out(200, dict(r) if r else {})
            if p == '/room/api/context':
                text, a = context_text(int(q.get('room', 0)), int(q.get('msg', 0)))
                if text is None:
                    return self.out(404, {'error': 'not_found'})
                return self.out(200, {'text': text, 'site_url': a['site_url'], 'name': a['name']})
            if p == '/room/api/models':
                with db() as c:
                    a = c.execute('SELECT * FROM agents WHERE id=?', (int(q.get('agent', 0)),)).fetchone()
                key = keys().get(a['key_env'] or '') if a else None
                if not a or not key or not a['base_url']:
                    return self.out(400, {'error': 'API 주소나 키가 없어요'})
                req = urllib.request.Request(a['base_url'].rstrip('/') + '/models', headers={'Authorization': 'Bearer ' + key})
                with urllib.request.urlopen(req, timeout=20) as r:
                    d = json.load(r)
                return self.out(200, {'models': sorted(m.get('id', '') for m in d.get('data', []))})
            return self.out(404, {'error': 'not_found'})
        except Exception as e:
            return self.out(500, {'error': str(e)})

    def do_POST(self):
        p = urlparse(self.path).path.rstrip('/')
        try:
            b = self.body()
            if p == '/room/api/send':
                return self.send_msg(b)
            if p == '/room/api/paste':
                text = (b.get('text') or '').strip()
                if not text:
                    return self.out(400, {'error': '답변이 비어 있어요'})
                with db() as c:
                    m = c.execute('SELECT * FROM messages WHERE id=?', (int(b['id']),)).fetchone()
                tok = est_tokens(text)
                finish(m['id'], text, 'done', tok)
                add_usage(m['agent_id'], tok)
                return self.out(200, {'ok': True})
            if p == '/room/api/copied':
                add_usage(int(b['agent_id']), est_tokens('x' * int(b.get('chars', 0))))
                return self.out(200, {'ok': True})
            if p == '/room/api/cancel':
                finish(int(b['id']), '(건너뜀)', 'skipped')
                return self.out(200, {'ok': True})
            if p == '/room/api/retry':
                with LOCK, db() as c:
                    m = c.execute('SELECT * FROM messages WHERE id=?', (int(b['id']),)).fetchone()
                    c.execute("UPDATE messages SET status='pending', content='' WHERE id=?", (m['id'],))
                threading.Thread(target=call_direct, args=(m['agent_id'], m['room_id'], m['id']), daemon=True).start()
                return self.out(200, {'ok': True})
            if p == '/room/api/room/save':
                return self.save_room(b)
            if p == '/room/api/room/delete':
                with LOCK, db() as c:
                    if c.execute('SELECT COUNT(*) FROM rooms').fetchone()[0] <= 1:
                        return self.out(400, {'error': '마지막 방은 지울 수 없어요'})
                    rid = int(b['id'])
                    c.execute('DELETE FROM messages WHERE room_id=?', (rid,))
                    c.execute('DELETE FROM members WHERE room_id=?', (rid,))
                    c.execute('DELETE FROM rooms WHERE id=?', (rid,))
                return self.out(200, {'ok': True})
            if p == '/room/api/agent/save':
                return self.save_agent(b)
            if p == '/room/api/agent/cooldown':
                until = ''
                if b.get('until'):
                    hh, mm = map(int, b['until'].split(':'))
                    t = now().replace(hour=hh, minute=mm, second=0, microsecond=0)
                    if t <= now():
                        t += timedelta(days=1)
                    until = t.isoformat()
                with LOCK, db() as c:
                    c.execute('UPDATE agents SET cooldown_until=? WHERE id=?', (until, int(b['id'])))
                return self.out(200, {'ok': True})
            return self.out(404, {'error': 'not_found'})
        except Exception as e:
            return self.out(500, {'error': str(e)})

    def send_msg(self, b):
        rid = int(b['room'])
        text = (b.get('text') or '').strip()
        if not text:
            return self.out(400, {'error': '내용이 비어 있어요'})
        with LOCK, db() as c:
            members = {a['id']: a for a in c.execute(
                'SELECT a.* FROM agents a JOIN members m ON m.agent_id=a.id WHERE m.room_id=? AND a.enabled=1', (rid,))}
            targets = [int(x) for x in b.get('to', []) if int(x) in members]
            if '@모두' in text:
                targets = list(members)
            for aid, a in members.items():
                if '@' + a['name'] in text and aid not in targets:
                    targets.append(aid)
            ts = now().isoformat()
            c.execute('INSERT INTO messages(room_id,agent_id,content,status,created) VALUES(?,?,?,?,?)', (rid, None, text, 'done', ts))
            jobs = []
            for aid in targets:
                st = 'pending' if members[aid]['kind'] == 'direct' else 'waiting'
                cur = c.execute('INSERT INTO messages(room_id,agent_id,content,status,created) VALUES(?,?,?,?,?)', (rid, aid, '', st, ts))
                if st == 'pending':
                    jobs.append((aid, rid, cur.lastrowid))
        for j in jobs:
            threading.Thread(target=call_direct, args=j, daemon=True).start()
        return self.out(200, {'ok': True, 'targets': targets})

    def save_room(self, b):
        name = (b.get('name') or '').strip()
        if not name:
            return self.out(400, {'error': '방 이름을 넣어주세요'})
        with LOCK, db() as c:
            if b.get('id'):
                rid = int(b['id'])
                c.execute('UPDATE rooms SET name=?, note=? WHERE id=?', (name, b.get('note', ''), rid))
            else:
                rid = c.execute('INSERT INTO rooms(name,note,created) VALUES(?,?,?)', (name, b.get('note', ''), now().isoformat())).lastrowid
            c.execute('DELETE FROM members WHERE room_id=?', (rid,))
            for aid in b.get('members', []):
                c.execute('INSERT OR IGNORE INTO members VALUES(?,?)', (rid, int(aid)))
        return self.out(200, {'ok': True, 'id': rid})

    def save_agent(self, b):
        vals = {f: b.get(f) for f in AGENT_FIELDS if f in b}
        if 'name' in vals:
            vals['name'] = (vals['name'] or '').strip()
            if not vals['name'] or re.search(r'\s', vals['name']):
                return self.out(400, {'error': '이름은 띄어쓰기 없이 넣어주세요 (@이름 으로 부르기 때문)'})
        if vals.get('kind') not in (None, 'direct', 'indirect'):
            return self.out(400, {'error': 'kind 오류'})
        if 'enabled' in vals:
            vals['enabled'] = 1 if vals['enabled'] else 0
        with LOCK, db() as c:
            if b.get('id'):
                if vals:
                    c.execute('UPDATE agents SET ' + ','.join(f'{k}=?' for k in vals) + ' WHERE id=?', (*vals.values(), int(b['id'])))
                aid = int(b['id'])
            else:
                vals.setdefault('kind', 'indirect')
                aid = c.execute('INSERT INTO agents(' + ','.join(vals) + ') VALUES(' + ','.join('?' * len(vals)) + ')',
                                tuple(vals.values())).lastrowid
        return self.out(200, {'ok': True, 'id': aid})


def recover():
    # 서비스가 재시작되면 답변 중이던 메시지를 오류로 표시 (다시 시도 가능)
    with LOCK, db() as c:
        c.execute("UPDATE messages SET status='error', content='서비스 재시작으로 중단됨 - 다시 시도를 눌러주세요' WHERE status='pending'")


if __name__ == '__main__':
    init_db()
    recover()
    print(f'{VERSION} listening on 127.0.0.1:{PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
