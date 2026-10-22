import json, uuid, hashlib, os, tempfile, threading
from pathlib import Path
from datetime import datetime, timezone

PUBLIC=Path('/var/lib/bot-office-deploy-public')
STATE=Path('/var/lib/bot-office/market-manual/deploy-approvals.json')
LOCK=threading.Lock()

def load(p):
 return json.loads(p.read_text())
def digest(d):
 return hashlib.sha256(json.dumps(
  d,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def read():
 with LOCK:
  decisions=load(STATE) if STATE.exists() else {}
  items=[]
  for p in sorted(PUBLIC.glob('*.json'))[-100:]:
   d=load(p)
   rp=PUBLIC/'results'/(d['id']+'.json')
   execution=load(rp) if rp.exists() else None
   items.append({
    **d,'execution_result':execution,'review_hash':digest(d),
    'approval':decisions.get(d['id'])})
  return {'items':items,'execution_enabled':True}
def save(d):
 if not isinstance(d,dict):raise ValueError()
 ident=str(uuid.UUID(d.get('id','')))
 if d.get('action') not in ('approve','reject'):raise ValueError()
 with LOCK:
  manifest=load(PUBLIC/(ident+'.json'))
  if d.get('review_hash')!=digest(manifest):
   raise ValueError('변경안이 달라졌습니다')
  records=load(STATE) if STATE.exists() else {}
  # DEPLOY_EXEC_AUTH_V2
  if d['action']=='approve' and d.get('execute') is not True:
   raise ValueError('실행 동의 필요')
  entry={
   'id':ident,'review_hash':digest(manifest),
   'decision':'승인' if d['action']=='approve' else '반려',
   'at':datetime.now(timezone.utc).isoformat(),
   'execution_authorized':d['action']=='approve',
   'execution':'처리 대기' if d['action']=='approve' else '실행 제외'}
  records[ident]=entry
  fd,tmp=tempfile.mkstemp(dir=STATE.parent)
  try:
   with os.fdopen(fd,'w') as f:
    json.dump(records,f,ensure_ascii=False,indent=2)
   os.chmod(tmp,0o600)
   os.replace(tmp,STATE)
  finally:
   if os.path.exists(tmp):os.unlink(tmp)
  return entry
