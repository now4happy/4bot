"""Target-scoped deployment pause controller; only GET account/order reads."""
import contextlib
import fcntl
import hashlib
import hmac
import base64
import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

UNITS = {'1': 'han4384tubot.service', '2': 'toss_sniper.service',
         '3': 'toss_dca.service', '4': 'bithumb_bot.service'}
NAMES = {v: k + '번 봇' for k, v in UNITS.items()}
_TOKENS = {}

def read(path):
    with open(path, encoding='utf-8') as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError('invalid state')
    return value

def number(value):
    if value is None or isinstance(value, bool):
        raise ValueError('missing quantity')
    n = Decimal(str(value))
    if not n.is_finite() or n < 0:
        raise ValueError('invalid quantity')
    return n

def state_path(root):
    return Path(root) / '.deployment_pause.json'

def write(root, state):
    path = state_path(root)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    owner = Path(root).stat()
    if os.geteuid() == 0:
        os.chown(tmp, owner.st_uid, owner.st_gid)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)

@contextlib.contextmanager
def lock(root, nonblocking=False):
    path = Path(root) / '.deployment_pause.lock'
    with path.open('a') as f:
        os.chmod(path, 0o644)
        fcntl.flock(f, fcntl.LOCK_EX | (fcntl.LOCK_NB if nonblocking else 0))
        yield

def runtime(app, unit, root):
    # Refuse to override time protections unless the running process loaded the gate.
    rc, pid = app.sh(app.SYSTEMCTL, 'show', unit, '-p', 'MainPID', '--value')
    if rc or not pid.isdigit() or int(pid) <= 0:
        raise ValueError('봇 실행 상태 확인 불가')
    proc = Path('/proc') / pid
    stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    boot = next(float(l.split()[1]) for l in Path('/proc/stat').read_text().splitlines() if l.startswith('btime '))
    started = boot + int(stat[19]) / os.sysconf('SC_CLK_TCK')
    gate = Path(root) / 'deployment_gate.py'
    transport = Path(root) / ('kis_api_client.py' if unit == UNITS['1'] else 'b_core.py' if unit == UNITS['4'] else 'toss_api.py')
    if not gate.is_file() or not transport.is_file() or '@__import__("deployment_gate").transport' not in transport.read_text() and unit != UNITS['4']:
        raise ValueError('신규 주문 차단 부품을 먼저 설치해야 합니다')
    if unit == UNITS['4'] and 'with gate():' not in transport.read_text():
        raise ValueError('신규 주문 차단 부품을 먼저 설치해야 합니다')
    if started < max(gate.stat().st_mtime, transport.stat().st_mtime, (Path(root)/'.deployment_pause.lock').stat().st_mtime):
        raise ValueError('차단 부품 설치 후 봇 재시작이 아직 확인되지 않았습니다')
    cmd = (proc / 'cmdline').read_bytes().split(b'\0')
    if not any(x.decode(errors='replace').endswith('main.py') for x in cmd):
        raise ValueError('봇 main.py 실행 프로세스 확인 불가')
    env = {}
    cwd = Path(os.readlink(proc / 'cwd'))
    main_paths = set()
    for raw in cmd:
        arg = raw.decode(errors='replace')
        if arg.endswith('main.py'):
            entry = Path(arg)
            main_paths.add((entry if entry.is_absolute() else cwd / entry).resolve())
    if (Path(root) / 'main.py').resolve() not in main_paths:
        raise ValueError('실행 main.py와 업데이트 대상 폴더가 다릅니다')
    for folder in [cwd, Path(root)]:
        for name in ['.env', '.env_vars']:
            path = folder / name
            if path.exists():
                for line in path.read_text().splitlines():
                    if '=' in line and not line.strip().startswith('#'):
                        k, v = line.removeprefix('export ').split('=', 1)
                        env[k.strip()] = v.strip().strip('"').strip("'")
    if unit == UNITS['2']:
        for name in ['config.json','secrets.json','toss_config.json']:
            path = Path(root)/name
            if path.exists():
                data = read(path)
                for key in ('TOSS_CLIENT_ID','TOSS_API_KEY','TOSS_APP_KEY','CLIENT_ID','APP_KEY','TOSS_CLIENT_SECRET','TOSS_API_SECRET','TOSS_APP_SECRET','CLIENT_SECRET','APP_SECRET'):
                    if key not in env and isinstance(data.get(key),(str,int,float)):
                        env[key] = str(data[key])
    env.update(dict(part.decode().split('=', 1) for part in (proc / 'environ').read_bytes().split(b'\0') if b'=' in part))
    return env, cwd

def get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=8) as response:
        data = json.loads(response.read(4_000_000))
        if isinstance(data,dict) and (data.get('error') or data.get('success') is False):
            raise ValueError('보유/주문 API 오류')
        return data, dict(response.headers)

def rows(result):
    if isinstance(result, list):
        out = result
    elif isinstance(result, dict) and isinstance(result.get('items'), list):
        if any(result.get(k) for k in ('nextCursor', 'nextPageToken', 'hasNext', 'hasNextPage', 'hasMore', 'nextPage')):
            raise ValueError('보유/주문 연속조회 필요')
        out = result['items']
    else:
        raise ValueError('보유/주문 응답 불명')
    if not all(isinstance(x, dict) for x in out):
        raise ValueError('보유/주문 행 오류')
    return out

def toss(env, scope):
    # Use one in-memory token per probe; no bot's token/cache/state is written.
    cid = next((env[k] for k in ('TOSS_CLIENT_ID','TOSS_API_KEY','TOSS_APP_KEY','CLIENT_ID','APP_KEY') if env.get(k)),None)
    secret = next((env[k] for k in ('TOSS_CLIENT_SECRET','TOSS_API_SECRET','TOSS_APP_SECRET','CLIENT_SECRET','APP_SECRET') if env.get(k)),None)
    if not cid or not secret:
        raise ValueError('토스 조회 인증 설정 확인 필요')
    body = urllib.parse.urlencode({'grant_type':'client_credentials', 'client_id':cid, 'client_secret':secret}).encode()
    identity = hashlib.sha256(body).hexdigest()
    cached = _TOKENS.get(identity)
    if cached and cached[1] > time.time():
        token = cached[0]
    else:
        req = urllib.request.Request('https://openapi.tossinvest.com/oauth2/token', data=body)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
            token = data['access_token']
            _TOKENS[identity] = (token, time.time() + min(900, max(0, int(data.get('expires_in',900))-60)))
    headers = {'Authorization':'Bearer ' + token}
    accounts, _ = get('https://openapi.tossinvest.com/api/v1/accounts', headers)
    accounts = rows(accounts['result'])
    selected = [x for x in accounts if x.get('accountType') == 'BROKERAGE']
    if len(selected) != 1 or selected[0].get('accountSeq') is None:
        raise ValueError('거래계좌 식별 불가')
    headers['X-Tossinvest-Account'] = str(selected[0]['accountSeq'])
    holdings, _ = get('https://openapi.tossinvest.com/api/v1/holdings', headers)
    hs = rows(holdings['result'])
    for row in hs:
        if not row.get('symbol'):
            raise ValueError('보유종목 식별 불가')
        if scope is None or row['symbol'] in scope:
            if number(row.get('quantity')) > 0:
                return False, '보유 수량이 남아 있습니다'
    orders, _ = get('https://openapi.tossinvest.com/api/v1/orders?status=OPEN', headers)
    for row in rows(orders['result']):
        if not row.get('symbol'):
            raise ValueError('미체결 종목 식별 불가')
        if scope is None or row['symbol'] in scope:
            return False, '미체결 주문이 남아 있습니다'
    return True, '보유 수량 0 · 미체결 없음'

def kis(env, cwd):
    ticker_path = cwd / 'data/active_tickers.json'
    if ticker_path.exists():
        scope = json.loads(ticker_path.read_text())
        if not isinstance(scope, list) or not all(isinstance(x, str) for x in scope):
            raise ValueError('한투 관리종목 확인 불가')
    else:
        scope = ['SOXL', 'TQQQ']  # Same defaults as ConfigManager.get_active_tickers.
    scope = set(scope) - {'SOXS','SQQQ','SPXU'}
    token = read(cwd / 'data' / ('token_' + env['CANO'] + '.dat'))['token']
    headers = {'authorization':'Bearer ' + token, 'appkey':env['APP_KEY'],
               'appsecret':env['APP_SECRET'], 'custtype':'P'}
    # Configured symbols only; all exchanges and complete pagination.
    day = datetime.now(ZoneInfo('America/New_York')).date()
    for exchange in ['NASD', 'NYSE', 'AMEX']:
        definitions = [
            ('TTTS3012R', 'inquire-balance', 'output1', {'TR_CRCY_CD':'USD'}, 'ovrs_cblc_qty'),
            ('TTTS3018R', 'inquire-nccs', 'output', {'SORT_SQN':'DS'}, None),
            ('TTTT3039R', 'order-resv-list', 'output', {'INQR_STRT_DT':(day-timedelta(days=365)).strftime('%Y%m%d'),
              'INQR_END_DT':day.strftime('%Y%m%d'), 'INQR_DVSN_CD':'01', 'PRDT_TYPE_CD':''}, None),
        ]
        for tr, endpoint, field, extra, quantity in definitions:
            fk = nk = ''
            for page in range(20):
                params = {'CANO':env['CANO'], 'ACNT_PRDT_CD':env.get('ACNT_PRDT_CD','01'),
                          'OVRS_EXCG_CD':exchange, 'CTX_AREA_FK200':fk, 'CTX_AREA_NK200':nk, **extra}
                h = dict(headers, tr_id=tr)
                if page:
                    h['tr_cont'] = 'N'
                result, rh = get('https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/' + endpoint + '?' + urllib.parse.urlencode(params), h)
                if result.get('rt_cd') != '0' or not isinstance(result.get(field), list):
                    raise ValueError('한국투자 보유/미체결 확인 불가')
                for row in result[field]:
                    if not isinstance(row, dict):
                        raise ValueError('한국투자 응답 행 오류')
                    symbol = row.get('ovrs_pdno') if quantity else row.get('pdno')
                    if not symbol:
                        raise ValueError('한국투자 관리종목 식별 불가')
                    if symbol not in scope:
                        continue
                    if quantity:
                        if number(row.get(quantity)) > 0:
                            return False, '한국투자 계좌 보유 수량이 남아 있습니다'
                    else:
                        if endpoint == 'order-resv-list' and row.get('cncl_yn') == 'Y':
                            continue
                        return False, '미체결/예약 주문이 남아 있습니다 (자동 취소 안 함)'
                lower = {k.lower():v for k,v in rh.items()}
                if lower.get('tr_cont') not in ('M','F'):
                    break
                fk, nk = result.get('ctx_area_fk200'), result.get('ctx_area_nk200')
                if not nk or page == 19:
                    raise ValueError('한국투자 연속조회 미완료')
                time.sleep(.2)
    return True, '보유 수량 0 · 미체결/예약 없음'

def bithumb(env, root):
    scope = set(read(Path(root)/'bot_config.json')['coins'])
    if not scope:
        raise ValueError('관리 코인 확인 불가')
    def auth(query=None):
        b64=lambda x:base64.urlsafe_b64encode(x).rstrip(b'=')
        head=b64(b'{"alg":"HS256","typ":"JWT"}')
        data={'access_key':env['BITHUMB_ACCESS_KEY'], 'nonce':str(uuid.uuid4()), 'timestamp':round(time.time()*1000)}
        if query:
            data.update(query_hash=hashlib.sha512(urllib.parse.urlencode(query).encode()).hexdigest(),query_hash_alg='SHA512')
        body=b64(json.dumps(data,separators=(',',':')).encode())
        sig=b64(hmac.new(env['BITHUMB_SECRET_KEY'].encode(),head+b'.'+body,hashlib.sha256).digest())
        return {'Authorization':'Bearer '+(head+b'.'+body+b'.'+sig).decode()}
    accs,_=get('https://api.bithumb.com/v1/accounts',auth())
    for row in rows(accs):
        if not row.get('currency'):
            raise ValueError('코인 식별 불가')
        if row['currency'] in scope and number(row.get('balance'))+number(row.get('locked'))>0:
            return False,'보유/주문 잠금 코인이 남아 있습니다'
    query={'state':'wait','limit':100,'page':1}
    orders,_=get('https://api.bithumb.com/v1/orders?'+urllib.parse.urlencode(query),auth(query))
    for row in rows(orders):
        if not row.get('market'):
            raise ValueError('미체결 코인 식별 불가')
        if row['market'].removeprefix('KRW-') in scope:
            return False,'미체결 주문이 남아 있습니다'
    if len(orders)>=100:
        raise ValueError('미체결 연속조회 필요')
    return True,'보유 수량 0 · 미체결 없음'

def probe(app, unit, root):
    env,cwd=runtime(app,unit,root)
    if unit == UNITS['1']:
        return kis(env,cwd)
    if unit in (UNITS['2'],UNITS['3']):
        scope = {'SOXL'} if unit == UNITS['2'] else set(read(Path(root)/'dca_config.json')['stocks'])
        try:
            return toss(env,scope)
        except urllib.error.HTTPError as error:
            if error.code == 401:
                _TOKENS.clear()
            raise
    return bithumb(env,root)

def request(app, unit, offer_key):
    root = app.targets().get(unit)
    if not root:
        return app.say('⛔ 업데이트 대상 경로를 찾을 수 없습니다.')
    try:
        # Bootstrap lock before writing any state. Bots open it read-only for SH locks.
        with lock(root):
            runtime(app,unit,root)
            state = read(state_path(root)) if state_path(root).exists() else {}
            if state.get('phase') == 'paused':
                return app.say('⏸ 이미 업데이트용 일시중지 상태입니다.', resume_rows(unit))
            write(root, {'phase':'waiting','requested':time.time(),'notice':False,'offer_key':offer_key})
        app.say('⏳ '+NAMES[unit]+' 보유 수량·미체결을 30초 주기로 확인합니다. 0 확인 후 신규 주문을 차단합니다. 대기 중 기존 매매는 계속됩니다.',resume_rows(unit))
    except Exception as e:
        app.say('⛔ 일시중지 준비 실패: '+app.esc(str(e) if isinstance(e,ValueError) else type(e).__name__))

def resume_rows(unit):
    key=next(k for k,v in UNITS.items() if v==unit)
    return [[{'text':'▶️ 거래 재개 / 중지 대기 취소','callback_data':'rs:'+key}]]

def resume(app, unit):
    root=app.targets().get(unit)
    if not root:
        return
    with lock(root):
        write(root,{'phase':'running','resumed':time.time()})
    app.say('▶️ '+NAMES[unit]+' 업데이트용 차단/대기를 해제했습니다. 기존 전원·종목 설정 그대로 동작합니다.')

def tick(app, unit):
    root=app.targets().get(unit)
    if not root or not state_path(root).exists():
        return
    try:
        before=read(state_path(root))
        if before.get('phase') not in ('waiting','paused'):
            return
        # Do not hold the order lock during normal inventory polling with positions.
        candidate = probe(app,unit,root) if before['phase']=='waiting' else None
        with lock(root,nonblocking=True):
            state=read(state_path(root))
            if state.get('phase') not in ('waiting','paused'):
                return  # A resume/cancel happened while the network lookup ran.
            if state['phase']=='waiting':
                if candidate is None:
                    return
                ok,reason=candidate
                if ok:
                    # Atomic transition: wait for in-flight orders, recheck inventory
                    # and open orders with the gate exclusively held, then close it.
                    ok,reason=probe(app,unit,root)
                state['checked']=time.time()
                state['reason']=reason
                if ok:
                    state.update(phase='paused',notice=False)
                write(root,state)
            if state['phase']=='paused' and not state.get('notice'):
                rows=([[{'text':'✅ 업데이트 진행','callback_data':'up:'+state['offer_key']}]] if state.get('offer_key') else []) + resume_rows(unit)
                if app.say('⏸ '+NAMES[unit]+' 보유 수량 0·주문 없음 확인 → 신규 매수/매도 주문을 일시중지했습니다. 업데이트 후 재개 버튼을 눌러 주세요.',rows).get('ok'):
                    state['notice']=True
                    write(root,state)
    except BlockingIOError:
        pass
    except Exception:
        try:
            with lock(root):
                state=read(state_path(root))
                if state.get('phase')=='waiting' and not state.get('error_notice'):
                    if app.say('⚠️ '+NAMES[unit]+' 보유/미체결 또는 차단 부품 실행 확인 실패. 0으로 처리하지 않고 대기합니다.',resume_rows(unit)).get('ok'):
                        state['error_notice']=True
                        write(root,state)
        except Exception:
            pass


def ready(app,unit):
    root=app.targets().get(unit)
    if not root or not state_path(root).exists():
        return False
    try:
        with lock(root,nonblocking=True):
            if read(state_path(root)).get('phase') != 'paused':
                return False
            ok,_=probe(app,unit,root)
            return ok
    except Exception:
        return False

def monitor(app):
    # Create locks BEFORE first installation/restart of the bot hooks.
    for unit, root in app.targets().items():
        if unit in UNITS.values():
            try:
                with lock(root):
                    pass
            except OSError:
                print('업데이트 주문 잠금 준비 실패:', unit, flush=True)
    def loop(unit):
        while True:
            start=time.monotonic()
            tick(app,unit)
            time.sleep(max(0,30-(time.monotonic()-start)))
    for unit in UNITS.values():
        threading.Thread(target=loop,args=(unit,),daemon=True).start()
