#!/usr/bin/env python3
"""Loopback-only, authenticated, read-only systemd dashboard. No trading API access."""
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
        if route=='/healthz': return self.send(200,{'ok':True})
        if route=='/login': return self.send(200,(ROOT/'login.html').read_bytes(),'text/html; charset=utf-8')
        if not self.session():
            if route=='/':
                self.send_response(303);self.send_header('Location','/login');self.send_header('Content-Length','0');self.end_headers();return
            return self.send(401,{'error':'login_required'})
        if route=='/': return self.send(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
        if route=='/api/market-manual':
            import market_manual
            return self.send(200,market_manual.read())
        # OFFICE_REVIEWS_V1
        if route=='/api/reviews':
            import office_reviews
            return self.send(200,office_reviews.read())
        # IDEA_REPORT_V1
        if route=='/api/idea-report':
            try:
                p=Path('/var/lib/bot-office/idea_report.json')
                return self.send(200,json.loads(p.read_text()))
            except (OSError,ValueError):
                return self.send(404,{'error':'report_not_ready'})
        # OFFICE_EXPORT_V1
        if route=='/api/office-export':
            result={
                'format':'bot-office-records-v1',
                'exported_at':datetime.now(timezone.utc).isoformat(),
                'records':{}
            }
            files={
                'market':'/var/lib/bot-office/market-manual/score.json',
                'reviews':'/var/lib/bot-office/market-manual/reviews.json'
            }
            for name,path in files.items():
                try:
                    result['records'][name]=json.loads(Path(path).read_text())
                except FileNotFoundError:
                    result['records'][name]=None
                except (OSError,ValueError):
                    return self.send(500,{'error':'export_failed'})
            return self.send(200,result)
        # OFFICE_TASKS_V1
        if route=='/api/office-tasks':
            import office_tasks
            return self.send(200,office_tasks.listing())
        # OFFICE_DEPLOY_V1
        if route=='/api/deployments':
            import office_deploy
            return self.send(200,office_deploy.read())
        # OFFICE_DEV_API_V1
        if route=='/api/dev-requests':
            if not self.session():
                return self.send(401,{'error':'login_required'})
            import office_dev
            return self.send(200,office_dev.read())
        # OFFICE_PIPELINE_V1
        if route=='/api/pipeline':
            import office_pipeline_api
            return self.send(200,office_pipeline_api.read())
        if route=='/api/status': return self.send(200,snapshot())
        self.send(404,{'error':'not_found'})
    def do_POST(self):
        origin=self.headers.get('Origin')
        if origin and origin not in ('https://'+self.headers.get('Host',''),'http://'+self.headers.get('Host','')):
            return self.send(403,{'error':'origin_rejected'})
        route=self.path
        if route=='/logout':
            try:
                c=SimpleCookie();c.load(self.headers.get('Cookie',''))
                with LOCK: SESSIONS.pop(c['office_session'].value,None)
            except (KeyError,ValueError): pass
            return self.send(200,{'ok':True},cookie='office_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if self.secure() else ''))
        if route=='/api/market-manual':
            if not self.session(): return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='market-manual': return self.send(403,{'error':'invalid_request'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=16000: raise ValueError()
                import market_manual
                result=market_manual.save(json.loads(self.rfile.read(n)))
            except (ValueError,TypeError,AttributeError,KeyError): return self.send(400,{'error':'invalid_scores'})
            except OSError: return self.send(500,{'error':'save_failed'})
            if result is None: return self.send(409,{'error':'changed_elsewhere'})
            return self.send(200,result)
        if route=='/api/reviews':
            if not self.session():
                return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='reviews':
                return self.send(403,{'error':'invalid_request'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=2048: raise ValueError()
                import office_reviews
                result=office_reviews.save(json.loads(self.rfile.read(n)))
            except (ValueError,TypeError,AttributeError):
                return self.send(400,{'error':'invalid_review'})
            except OSError:
                return self.send(500,{'error':'save_failed'})
            return self.send(200,result)
        if route=='/api/office-tasks':
            if not self.session():
                return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='tasks':
                return self.send(403,{'error':'invalid_request'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=1024: raise ValueError()
                import office_tasks
                result=office_tasks.execute(json.loads(self.rfile.read(n)))
                return self.send(200,result)
            except (ValueError,TypeError,AttributeError):
                return self.send(400,{'error':'invalid_task'})
            except OSError:
                return self.send(500,{'error':'storage_failed'})
        if route=='/api/deployments':
            if not self.session():
                return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='deploy':
                return self.send(403,{'error':'invalid_request'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=1024: raise ValueError()
                import office_deploy
                d=office_deploy.save(json.loads(self.rfile.read(n)))
                return self.send(200,d)
            except (ValueError,TypeError,AttributeError):
                return self.send(400,{'error':'invalid_deployment'})
            except OSError:
                return self.send(500,{'error':'storage_failed'})
        if route=='/api/dev-requests':
            if not self.session():
                return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='dev':
                return self.send(403,{'error':'invalid_request'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=2048:
                    raise ValueError('요청 크기 확인 필요')
                import office_dev
                result=office_dev.save(json.loads(self.rfile.read(n)))
            except (ValueError,TypeError,KeyError,AttributeError) as e:
                return self.send(400,{'error':str(e)[:160]})
            except OSError:
                return self.send(500,{'error':'저장 실패'})
            return self.send(200,result)
        # OFFICE_PIPELINE_V1
        if route=='/api/pipeline':
            if not self.session():
                return self.send(401,{'error':'login_required'})
            if self.headers.get('X-Bot-Office')!='pipeline':
                return self.send(403,{'error':'invalid_request'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=8000: raise ValueError('요청 크기 확인 필요')
                import office_pipeline_api
                return self.send(200,office_pipeline_api.save(json.loads(self.rfile.read(n))))
            except (ValueError,TypeError,AttributeError) as e:
                return self.send(400,{'error':str(e)[:160]})
            except OSError:
                return self.send(500,{'error':'저장 실패'})
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
