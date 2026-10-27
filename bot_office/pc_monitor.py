"""Korean Windows PC and Magic Split health; notifications only, no trading."""
import fcntl
import hmac
import html
import json
import os
import re
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

R=Path(os.environ.get('OFFICE_ROOT','/'))
HOME=R/'var/lib/bot-office/fanding'
STATE=HOME/'pc-monitor.json'
LOCK=HOME/'.pc-monitor.lock'
CONFIG=R/'etc/bot-office/pc_monitor.json'
FANDING_CONFIG=R/'etc/bot-office/fanding.json'
KST=ZoneInfo('Asia/Seoul')
DEFAULTS={'device_id':'korea-windows','start':'07:50','end':'20:10',
          'grace_seconds':180,'offline_seconds':180,'app_grace_seconds':180}


def load(path,default):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default


def config():
    return {**DEFAULTS,**load(CONFIG,{})}


@contextmanager
def state():
    HOME.mkdir(parents=True,exist_ok=True)
    fd=os.open(LOCK,os.O_CREAT|os.O_RDWR,0o660)
    parent=HOME.stat()
    with os.fdopen(fd,'a') as lock:
        try:os.fchown(lock.fileno(),parent.st_uid,parent.st_gid);os.fchmod(lock.fileno(),0o660)
        except PermissionError:pass
        fcntl.flock(lock,fcntl.LOCK_EX)
        value=load(STATE,{})
        yield value
        tmp_fd,tmp=tempfile.mkstemp(dir=HOME,prefix='.pc-monitor-')
        try:
            with os.fdopen(tmp_fd,'w',encoding='utf-8') as file:
                json.dump(value,file,ensure_ascii=False,indent=2);file.flush();os.fsync(file.fileno())
                try:os.fchown(file.fileno(),parent.st_uid,parent.st_gid)
                except PermissionError:pass
                os.fchmod(file.fileno(),0o660)
            os.replace(tmp,STATE)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)


def receive(handler):
    c=config()
    token=c.get('upload_token') or load(FANDING_CONFIG,{}).get('upload_token','')
    given=handler.headers.get('X-Fanding-Token','')
    if not isinstance(token,str) or len(token)<20 or not hmac.compare_digest(token.encode(),given.encode()):
        return handler.send(403,{'error':'bad_token'})
    try:
        size=int(handler.headers.get('Content-Length','0'))
        if not 0<size<=8192:return handler.send(400,{'error':'bad_size'})
        data=json.loads(handler.rfile.read(size))
        if (not isinstance(data,dict) or data.get('device_id')!=c['device_id']
                or data.get('magic_status') not in ('running','stopped','unknown')
                or not re.fullmatch(r'[0-9a-f]{32}',str(data.get('instance','')))):
            return handler.send(400,{'error':'bad_payload'})
        names=data.get('magic_names',[])
        if not isinstance(names,list) or len(names)>20 or any(not isinstance(x,str) or len(x)>120 for x in names):
            return handler.send(400,{'error':'bad_names'})
        now=time.time()
        with state() as current:
            pc=current.setdefault('pc',{})
            if pc.get('instance')!=data['instance']:
                pc['first_at']=now
            if data['magic_status']=='running':
                pc.pop('magic_bad_since',None)
            elif pc.get('magic_status')!=data['magic_status'] or not pc.get('magic_bad_since'):
                pc['magic_bad_since']=now
            pc.update(at=now,instance=data['instance'],magic_status=data['magic_status'],
                      magic_names=names,version=str(data.get('version',''))[:20],
                      detection=str(data.get('detection',''))[:40])
            current['registered']=True
        return handler.send(200,{'ok':True,'interval_seconds':60})
    except (ValueError,TypeError):return handler.send(400,{'error':'bad_json'})
    except OSError:return handler.send(500,{'error':'storage_failed'})


def schedule(now,c):
    now=now.astimezone(KST)
    h,m=map(int,c['start'].split(':'));start=now.replace(hour=h,minute=m,second=0,microsecond=0)
    h,m=map(int,c['end'].split(':'));end=now.replace(hour=h,minute=m,second=0,microsecond=0)
    return now.weekday()<5 and start<=now<end,start,end


def alerts(current,now,c):
    """Pure evaluation: flags are recorded only after Telegram acknowledges delivery."""
    active,start,_=schedule(now,c)
    if not active or not current.get('registered') or now.timestamp()<start.timestamp()+c['grace_seconds']:
        return []
    pc=current.get('pc',{})
    flags=current.get('notified',{}) if current.get('alert_date')==now.astimezone(KST).date().isoformat() else {}
    online=bool(pc.get('at') and now.timestamp()-pc['at']<=c['offline_seconds'])
    result=[]
    if not online:
        if not flags.get('pc'):
            result.append(('pc','offline','⚠️ <b>한국 Windows PC 연결 미확인</b>\n평일 07:50~20:10 감시 중, 3분 이상 상태 보고가 없습니다.\nPC 전원·인터넷·감시 프로그램을 원격 관리 도구에서 확인해 주세요.'))
        return result
    if flags.get('pc'):
        result.append(('pc',None,'✅ <b>한국 Windows PC 연결 복구</b>\n상태 보고가 다시 도착했습니다.'))
    magic=pc.get('magic_status','unknown')
    if magic=='running':
        if flags.get('magic'):
            result.append(('magic',None,'✅ <b>매직스플릿 실행 복구</b>\n프로그램 실행이 다시 확인됐습니다.'))
    elif (now.timestamp()>=max(pc.get('first_at',now.timestamp()),pc.get('magic_bad_since',now.timestamp()))+c['app_grace_seconds']
            and flags.get('magic')!=magic):
        if magic=='stopped':
            text='⚠️ <b>매직스플릿 미실행</b>\nPC 연결은 정상이나 매직스플릿 프로세스가 3분 이상 확인되지 않습니다. 원격으로 프로그램을 확인해 주세요.'
        else:
            text='⚠️ <b>매직스플릿 실행 확인 필요</b>\nPC 연결은 정상이나 프로그램을 식별하거나 조회하지 못했습니다.\nPC에서 매직스플릿을 한 번 실행하거나 실제 실행 파일명을 감시 설정에 지정해 주세요.'
        result.append(('magic',magic,text))
    return result


def tick(tg,now=None):
    now=now or datetime.now(KST)
    c=config()
    snapshot=load(STATE,{})
    for kind,value,text in alerts(snapshot,now,c):
        reply=tg.send(text)
        if not isinstance(reply,dict) or not reply.get('message_id'):
            continue
        with state() as current:
            day=now.astimezone(KST).date().isoformat()
            if current.get('alert_date')!=day:
                current['alert_date']=day;current['notified']={}
            if value is None:current.setdefault('notified',{}).pop(kind,None)
            else:current.setdefault('notified',{})[kind]=value


def status_text(now=None):
    now=now or datetime.now(KST)
    current=load(STATE,{});pc=current.get('pc',{});c=config()
    age=max(0,int(now.timestamp()-pc['at'])) if pc.get('at') else None
    active,_,_=schedule(now,c)
    magic={'running':'실행 중','stopped':'미실행','unknown':'식별/조회 확인 필요'}.get(pc.get('magic_status'),'미확인')
    return ('🖥 <b>한국 PC · 매직스플릿</b>\n감시: 평일 '+html.escape(c['start'])+'~'+html.escape(c['end'])+' 한국시간'
            +'\n등록: '+('완료' if current.get('registered') else '미등록 · PC 감시 프로그램 첫 연결 필요')
            +'\n현재: '+('감시 시간' if active else '감시 시간 밖')
            +'\nPC 연결: '+(str(age)+'초 전' if age is not None else '기록 없음')
            +'\n매직스플릿: '+magic+'\n확인한 실행 파일: '+html.escape(', '.join(pc.get('magic_names',[])) or '없음')
            +'\n감시 프로그램: '+html.escape(pc.get('version','미확인')))
