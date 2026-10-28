#!/usr/bin/env python3
"""Loopback-only, authenticated, read-only systemd dashboard. No trading API access."""
# 사무실 v1.0.55 (2026-10-28): 첫 화면(/)을 상황판(board.html · /api/board, 보기 전용)으로 바꿈
#   · 픽셀 사무실은 /pixel-office, 예전 운영 화면은 /operations 로 그대로 남김 (기존 기능·주소 변경 없음)
# 사무실 v1.0.57 (2026-10-28): 미팅룸(/room) 연결·옛 결재(/api/deployments)·수정 요청(/api/dev-requests)·업무 흐름(/api/pipeline) 주소 삭제
# 사무실 vNEXT (2026-10-28): 픽셀 사무실(/pixel-office)·운영 화면(/operations)·시장점수·결재기록·업무 주소 삭제
#   · 해당 파일(pixel_office·index·market_manual·office_reviews·office_tasks)도 함께 삭제 · 수집기(collect_inventory·inventory 타이머)는 유지
#   · 해당 파일(ai_room·office_deploy·office_dev·office_pipeline_api 등)도 함께 삭제 · 상황판·픽셀 사무실·운영 화면은 그대로
# 사무실 v1.0.56 (2026-10-28): 상황판 서버실 '서버 정리 실행' 버튼 → POST /api/server-care
#   · 웹서버는 관리자 권한이 없으므로 요청 파일(/var/lib/bot-office/care/request)만 씀 → 서버의 bot-server-care-request.path 가 보고 bot-server-care 실행
#   · 로그인·같은 주소·전용 머리글 필요, 10분에 1번 · 한 줄 JSON 기록 (start.md 2절)
import base64, hashlib, hmac, json, os, secrets, shutil, subprocess, threading, time
from collections import deque
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUTH_PATH = Path(os.environ.get('BOT_OFFICE_AUTH', '/etc/bot-office/auth.json'))
UNITS = ('han4384tubot.service', 'bithumb_bot.service', 'toss_sniper.service', 'toss_dca.service')
SESSIONS = {}
ATTEMPTS = deque()
LOCK = threading.Lock()
CACHE = {'at': 0, 'data': None}

def snapshot():
    with LOCK:
        if CACHE['data'] and time.monotonic()-CACHE['at'] < 5:
            return CACHE['data']
    bots = []
    for i, unit in enumerate(UNITS, 1):
        try:
            p = subprocess.run(['systemctl', 'show', unit, '--no-pager',
                '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState', '-p', 'MemoryCurrent'],
                capture_output=True, text=True, timeout=2, check=True)
            fields = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
            memory = fields.get('MemoryCurrent', '')
            bots.append({'id': i, 'unit': unit, 'load': fields.get('LoadState','unknown'),
                'active': fields.get('ActiveState','unknown'), 'sub':fields.get('SubState','unknown'),
                'memory_bytes': int(memory) if memory.isdigit() else None})
        except (subprocess.SubprocessError, OSError):
            bots.append({'id': i, 'unit': unit, 'load':'unknown', 'active':'unknown', 'sub':'unknown', 'memory_bytes':None})
    mem = {}
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            k,v = line.split(':',1)
            if k in ('MemTotal','MemAvailable'): mem[k]=int(v.split()[0])*1024
    except (OSError, ValueError): pass
    disk = shutil.disk_usage('/')
    # BOT_OFFICE_INVENTORY_V1
    try:
        inventory = json.loads(Path('/var/lib/bot-office/inventory.json').read_text())
    except (OSError, ValueError):
        inventory = None
    # BOT_OFFICE_RISK_V1
    try:
        risk_report = json.loads(Path('/var/lib/bot-office/risk_report.json').read_text())
    except (OSError, ValueError):
        risk_report = None
    # BOT_OFFICE_OPT_V1
    try:
        optimization = json.loads(Path('/var/lib/bot-office/optimization.json').read_text())
    except (OSError, ValueError):
        optimization = None
    data = {'observed_at':datetime.now(timezone.utc).isoformat(), 'bots':bots,
        'disk':{'total':disk.total,'free':disk.free,'used':disk.used},
        'memory':{'total':mem.get('MemTotal'),'available':mem.get('MemAvailable')},
        'load_1m':os.getloadavg()[0], 'cpu_count':os.cpu_count(),
        'optimization':optimization, 'risk_report':risk_report, 'inventory':inventory, 'read_only':True, 'note':'Service active does not establish successful orders or fills.'}
    with LOCK: CACHE.update(at=time.monotonic(),data=data)
    return data

class Handler(BaseHTTPRequestHandler):
    server_version = 'BotOffice'
    def setup(self):
        super().setup(); self.connection.settimeout(8)
    def log_message(self, *_): pass
    def secure(self): return self.headers.get('X-Forwarded-Proto','') == 'https'
    def send(self, status, body, kind='application/json; charset=utf-8', cookie=None):
        if not isinstance(body, bytes): body=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status)
        for k,v in {'Content-Type':kind,'Content-Length':str(len(body)), 'Cache-Control':'no-store',
            'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
            'X-Frame-Options':'DENY', 'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}.items():
            self.send_header(k,v)
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(body)
    def session(self):
        try:
            c=SimpleCookie();c.load(self.headers.get('Cookie','')); token=c['office_session'].value
        except (KeyError, ValueError): return False
        with LOCK:
            now=time.monotonic()
            for k in list(SESSIONS):
                if SESSIONS[k]<now: SESSIONS.pop(k,None)
            return token in SESSIONS
    def do_GET(self):
        route=self.path.split('?',1)[0]
        if route=='/api/fanding/control':
            import fanding_trade
            return fanding_trade.http_control(self)
        if route=='/healthz': return self.send(200,{'ok':True})
        if route=='/login': return self.send(200,(ROOT/'login.html').read_bytes(),'text/html; charset=utf-8')
        if not self.session():
            if route=='/':
                self.send_response(303);self.send_header('Location','/login');self.send_header('Content-Length','0');self.end_headers();return
            return self.send(401,{'error':'login_required'})
        if route in ('/', '/board') and (ROOT/'board.html').exists(): return self.send(200,(ROOT/'board.html').read_bytes(),'text/html; charset=utf-8')
        if route=='/api/board':
            try:
                import office_board
                return self.send(200,office_board.board())
            except Exception as error:
                return self.send(500,{'error':'board_failed','detail':type(error).__name__})
        # IDEA_REPORT_V1
        if route=='/api/idea-report':
            try:
                p=Path('/var/lib/bot-office/idea_report.json')
                return self.send(200,json.loads(p.read_text()))
            except (OSError,ValueError):
                return self.send(404,{'error':'report_not_ready'})
        if route=='/api/status': return self.send(200,snapshot())
        self.send(404,{'error':'not_found'})
    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin and origin not in ('https://'+self.headers.get('Host',''),'http://'+self.headers.get('Host','')):
            return self.send(403,{'error':'origin_rejected'})
        route=self.path
        if route.split('?',1)[0]=='/api/fanding/control':
            import fanding_trade
            return fanding_trade.http_control(self)
        if route.split('?',1)[0]=='/api/pc-monitor':
            import pc_monitor
            return pc_monitor.receive(self)
        if route=='/api/fanding/upload':  # FANDING_UPLOAD_V1: 윈도우 PC가 가격표 이미지를 올리는 곳 (전용 암호 필요)
            import fanding_trade
            return fanding_trade.http_upload(self)
        if route=='/logout':
            try:
                c=SimpleCookie();c.load(self.headers.get('Cookie',''))
                with LOCK: SESSIONS.pop(c['office_session'].value,None)
            except (KeyError,ValueError): pass
            return self.send(200,{'ok':True},cookie='office_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if self.secure() else ''))
        if route=='/api/server-care':
            if not self.session(): return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='care': return self.send(403,{'error':'invalid_request'})
            import office_board
            rid=secrets.token_hex(6); now=time.time(); ts=datetime.now(timezone.utc)
            def care_log(outcome,reason=''):
                print(json.dumps({'ts_utc':ts.isoformat(timespec='seconds'),'ts_kst':ts.astimezone(office_board.KST).isoformat(timespec='seconds'),
                    'correlation_id':'care-'+rid,'service':'office-board','actor':'user','event_type':'user_event','event':'server_care_requested',
                    'outcome':outcome,'reason':reason,'version':office_board.VERSION},ensure_ascii=False),flush=True)
            c=office_board.care()
            if not c.get('installed'): care_log('skipped','care_not_installed'); return self.send(503,{'error':'care_not_installed'})
            if not c.get('button'): care_log('skipped','trigger_not_installed'); return self.send(503,{'error':'trigger_not_installed'})
            if c.get('state')=='running': care_log('skipped','already_running'); return self.send(409,{'error':'already_running'})
            if c.get('wait_sec'): care_log('skipped','too_soon'); return self.send(429,{'error':'too_soon','wait_sec':c['wait_sec']})
            try:
                p=office_board.CARE_REQUEST; tmp=p.with_name('.request.tmp')
                tmp.write_text(json.dumps({'requested_utc':ts.isoformat(timespec='seconds'),'id':rid})+'\n',encoding='utf-8'); os.replace(tmp,p)
            except OSError as e:
                care_log('failed',type(e).__name__); return self.send(500,{'error':'request_write_failed'})
            office_board._CACHE['at']=0
            care_log('ok'); return self.send(200,{'ok':True,'id':rid})
        if route!='/api/login': return self.send(404,{'error':'not_found'})
        # Passwords are accepted only through HTTPS or a loopback browser/SSH tunnel.
        if not self.secure() and self.headers.get('Host','').split(':')[0] not in ('127.0.0.1','localhost'):
            return self.send(403,{'error':'https_required'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=4096: return self.send(400,{'error':'invalid_request'})
            payload=json.loads(self.rfile.read(n))
            user=payload.get('username','');password=payload.get('password','')
            if not isinstance(user,str) or not isinstance(password,str): raise ValueError()
        except (ValueError,TypeError): return self.send(400,{'error':'invalid_request'})
        with LOCK:
            now=time.monotonic()
            while ATTEMPTS and ATTEMPTS[0]<now-300: ATTEMPTS.popleft()
            if len(ATTEMPTS)>=10: return self.send(429,{'error':'try_later'})
            ATTEMPTS.append(now)
        auth=json.loads(AUTH_PATH.read_text())
        candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(auth['salt']),auth['iterations']).hex()
        ok=hmac.compare_digest(candidate,auth['hash']) and hmac.compare_digest(user.encode(),auth['username'].encode())
        if not ok: return self.send(401,{'error':'invalid_login'})
        token=secrets.token_urlsafe(32)
        with LOCK:
            if len(SESSIONS)>=32: SESSIONS.pop(next(iter(SESSIONS)))
            SESSIONS[token]=time.monotonic()+8*3600
        self.send(200,{'ok':True},cookie='office_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if self.secure() else ''))

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    server.daemon_threads=True
    server.serve_forever()
