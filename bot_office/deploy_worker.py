import hashlib,json,os,grp,subprocess,tempfile,uuid
from pathlib import Path
from datetime import datetime,timezone

BASE=Path('/var/lib/bot-office-deploy')
HELPER=Path('/opt/bot-office/apply_deploy.py')
PUBLIC=Path('/var/lib/bot-office-deploy-public')
APPROVAL=Path('/var/lib/bot-office/market-manual/deploy-approvals.json')

def write(p,data,public=False):
 fd,tmp=tempfile.mkstemp(dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:
   json.dump(data,f,ensure_ascii=False,indent=2)
   f.flush();os.fsync(f.fileno())
  if public:
   os.chown(tmp,0,grp.getgrnam('bot-office').gr_gid)
  os.chmod(tmp,0o640 if public else 0o600)
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def main():
 tested=BASE/'tested-helper.sha256'
 if not tested.exists():return
 actual=hashlib.sha256(HELPER.read_bytes()).hexdigest()
 if tested.read_text().strip()!=actual:return
 if not APPROVAL.exists() or APPROVAL.is_symlink():return
 if APPROVAL.stat().st_size>4_000_000:return
 decisions=json.loads(APPROVAL.read_text())
 for p in sorted(PUBLIC.glob('*.json'))[-100:]:
  try:
   ident=str(uuid.UUID(p.stem))
   approval=decisions.get(ident,{})
   folder=BASE/'packages'/ident
   if not folder.is_dir() or folder.is_symlink():continue
   state=folder/'execution.json'
   output=PUBLIC/'results'/(ident+'.json')
   if state.exists():
    write(output,json.loads(state.read_text()),True)
    continue
   if approval.get('decision')!='승인':continue
   if approval.get('execution_authorized') is not True:continue
   age=(datetime.now(timezone.utc)-
        datetime.fromisoformat(approval['at'])).total_seconds()
   if not 0<=age<=900:
    write(output,{'id':ident,
     'status':'승인 유효시간 초과 · 다시 승인 필요'},True)
    continue
   try:
    r=subprocess.run(
     ['/usr/bin/python3','-I',str(HELPER),ident],
     timeout=170,check=False,capture_output=True,text=True)
   except subprocess.TimeoutExpired:
    write(output,{'id':ident,
     'status':'처리 시간 초과 · 수동 확인 필요'},True)
    continue
   if state.exists():
    result=json.loads(state.read_text())
   elif r.returncode:
    message=(r.stdout.strip().splitlines() or [''])[ -1]
    reason=message[6:].strip() if message.startswith('실행 중단:') else ''
    result={
     'id':ident,
     'status':'적용 중단 · '+(reason[:160] or '사전 검사 실패'),
     'finished_at':datetime.now(timezone.utc).isoformat()}
    write(state,result)
   else:
    result={'id':ident,'status':'실행 결과 확인 필요'}
   write(output,result,True)
  except (ValueError,TypeError,KeyError,OSError):
   continue

if __name__=='__main__':
 main()
