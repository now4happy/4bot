import ast, fcntl, hashlib, json, os, stat
import subprocess, sys, tempfile, time, uuid
from pathlib import Path
from datetime import datetime, timezone

# APPLY_DEPLOY_V2 — 1~4번 봇 · 여러 파일 한 번에 적용 (기존 1파일 변경안도 그대로 지원)
R=Path(os.environ.get('OFFICE_ROOT','/'))
BASE=R/'var/lib/bot-office-deploy'
PUBLIC=R/'var/lib/bot-office-deploy-public'
APPROVAL=R/'var/lib/bot-office/market-manual/deploy-approvals.json'
SYSTEMCTL=os.environ.get('OFFICE_SYSTEMCTL','systemctl')
ALLOWED={'han4384tubot.service','toss_sniper.service','toss_dca.service','bithumb_bot.service'}

def now():
 return datetime.now(timezone.utc).isoformat()
def sha(raw):
 return hashlib.sha256(raw).hexdigest()
def read(p):
 if p.is_symlink() or p.stat().st_size>4_000_000:
  raise ValueError('자료 경로·크기 오류')
 return json.loads(p.read_text())
def save(p,d):
 fd,tmp=tempfile.mkstemp(dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:
   json.dump(d,f,ensure_ascii=False,indent=2)
   f.flush();os.fsync(f.fileno())
  os.chmod(tmp,0o600)
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def command(*args):
 return subprocess.run(
  [SYSTEMCTL,*args],capture_output=True,text=True,
  timeout=45,check=True).stdout.strip()
def current(fd,name):
 f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
 try:
  meta=os.fstat(f)
  if not stat.S_ISREG(meta.st_mode) or meta.st_size>1_000_000:
   raise ValueError('대상 파일 확인 필요')
  raw=os.read(f,1_000_001)
  return raw,meta
 finally:
  os.close(f)
def replace(fd,name,raw,meta):
 tmp='.office-deploy-'+str(uuid.uuid4())
 f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,
           0o600,dir_fd=fd)
 try:
  with os.fdopen(f,'wb') as stream:
   stream.write(raw);stream.flush();os.fsync(stream.fileno())
   os.fchown(stream.fileno(),meta.st_uid,meta.st_gid)
   os.fchmod(stream.fileno(),stat.S_IMODE(meta.st_mode))
  os.replace(tmp,name,src_dir_fd=fd,dst_dir_fd=fd)
  os.fsync(fd)
 finally:
  try:os.unlink(tmp,dir_fd=fd)
  except FileNotFoundError:pass

def plan(folder,m):
 """[(파일이름, 변경 전 bytes, 변경 후 bytes)]"""
 if m.get('version')==2:
  out=[]
  for f in m['files']:
   name=f['file']
   before=(folder/'before'/name).read_bytes()
   after=(folder/'after'/name).read_bytes()
   if sha(before)!=f['before_sha256'] or sha(after)!=f['after_sha256']:
    raise ValueError('준비 파일 지문 불일치')
   out.append((name,before,after))
  if not out:raise ValueError('변경 파일 없음')
  return out
 before=(folder/'before.py').read_bytes()
 after=(folder/'after.py').read_bytes()
 if sha(after)!=m['after_sha256'] or sha(before)!=m['before_sha256']:
  raise ValueError('준비 파일 지문 불일치')
 return [(m['file'],before,after)]

def apply(ident):
 ident=str(uuid.UUID(ident))
 folder=BASE/'packages'/ident
 state=folder/'execution.json'
 if state.exists():
  print('기존 처리 상태:',read(state).get('status'))
  return
 m=read(folder/'manifest.json')
 public=read(PUBLIC/(ident+'.json'))
 approval=read(APPROVAL).get(ident,{})
 review_hash=sha(json.dumps(
  public,sort_keys=True,ensure_ascii=False).encode())
 if not (
  approval.get('decision')=='승인'
  and approval.get('execution_authorized') is True
  and approval.get('review_hash')==review_hash
 ):
  raise ValueError('실행 권한을 포함한 새 승인이 필요합니다')
 age=(datetime.now(timezone.utc)-
      datetime.fromisoformat(approval['at'])).total_seconds()
 if not 0<=age<=900:
  raise ValueError('승인 후 15분 초과 · 다시 승인 필요')
 unit=m['unit']
 cfg=read(BASE/'targets.json')['targets']
 if unit not in ALLOWED or unit not in cfg:
  raise ValueError('허용되지 않은 봇')
 for key in ['id','unit','file','before_sha256','after_sha256','files']:
  if public.get(key)!=m.get(key):
   raise ValueError('화면 변경안과 원본 불일치')
 items=plan(folder,m)
 for name,_,after in items:
  if name not in cfg[unit]['files'] or Path(name).name!=name:
   raise ValueError('허용되지 않은 파일: '+name)
  compile(after,name,'exec',ast.PyCF_ONLY_AST)
 user=command('show',unit,'-p','User','--value')
 if user in ('','root','0') and not os.environ.get('OFFICE_TEST_ALLOW_ROOT'):
  raise ValueError('root로 실행되는 봇은 자동 적용 제외')
 root=Path(cfg[unit]['root'])
 cwd=command('show',unit,'-p','WorkingDirectory','--value')
 if cwd!=str(root) or root.resolve()!=root:
  raise ValueError('작업 경로 변경 감지')
 if command('is-active',unit)!='active':
  raise ValueError('현재 실행 중인 봇만 적용 가능')
 fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  olds={}
  for name,before,_ in items:
   old,meta=current(fd,name)
   if sha(old)!=sha(before):
    raise ValueError('등록 이후 코드 변경 감지 · 재등록 필요 ('+name+')')
   olds[name]=(old,meta)
  if os.fstatvfs(fd).f_bavail*os.fstatvfs(fd).f_frsize<200*1024*1024:
   raise ValueError('저장 공간 부족')
  (folder/'immediate-before').mkdir(exist_ok=True)
  for name,(old,_) in olds.items():
   with (folder/'immediate-before'/name).open('xb') as f:
    f.write(old);f.flush();os.fsync(f.fileno())
  result={'id':ident,'started_at':now(),'status':'처리 중','files':[n for n,_,_ in items]}
  save(state,result)
  changed=[]
  try:
   command('stop',unit)
   for name,before,after in items:
    latest,_=current(fd,name)
    if sha(latest)!=sha(before):
     raise ValueError('적용 직전 코드 변경 감지')
    replace(fd,name,after,olds[name][1])
    changed.append(name)
   command('start',unit)
   restart=command('show',unit,'-p','NRestarts','--value')
   for _ in range(5):
    time.sleep(float(os.environ.get('OFFICE_CHECK_SLEEP','2')))
    if command('is-active',unit)!='active':
     raise ValueError('시작 상태 확인 실패')
    if command('show',unit,'-p','NRestarts','--value')!=restart:
     raise ValueError('반복 재시작 감지')
   result['status']='적용 완료 · 시작 상태 확인'
  except Exception as e:
   result['error']=type(e).__name__
   try:
    command('stop',unit)
    after_map={n:a for n,_,a in items}
    for name in changed:
     live,_=current(fd,name)
     if sha(live)!=sha(after_map[name]):
      raise ValueError('다른 변경 감지 · 자동 덮어쓰기 중단')
     replace(fd,name,olds[name][0],olds[name][1])
    command('start',unit)
    command('is-active',unit)
    result['status']='적용 실패 · 이전 코드 시작 확인'
   except Exception as recovery:
    result['status']='수동 복구 필요'
    result['recovery_error']=type(recovery).__name__
  result['finished_at']=now()
  save(state,result)
  print(result['status'])
 finally:
  os.close(fd)

def main():
 if os.geteuid()!=0 and 'OFFICE_ROOT' not in os.environ:
  raise SystemExit('sudo 실행 필요')
 if len(sys.argv)!=2:
  raise SystemExit('사용법: 변경안 번호')
 os.umask(0o077)
 with (BASE/'execution.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  apply(sys.argv[1])

if __name__=='__main__':
 try:
  main()
 except Exception as e:
  print('실행 중단:',str(e)[:200])
  raise SystemExit(1)
