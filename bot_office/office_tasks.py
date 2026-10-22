import json,os,tempfile,threading,uuid,shutil
from pathlib import Path
from datetime import datetime,timezone
BASE=Path('/var/lib/bot-office/market-manual')
LOCK=threading.Lock()
TASKS={'backup':'현재 시장점수·결재 기록 백업',
       'report':'저장된 자료로 운영 보고서 생성'}
def now():return datetime.now(timezone.utc).isoformat()
def read(p):
 return json.loads(p.read_text()) if p.exists() else {}
def put(p,d):
 fd,t=tempfile.mkstemp(dir=p.parent)
 try:
  with os.fdopen(fd,'w') as f:
   json.dump(d,f,ensure_ascii=False,indent=2)
   f.flush();os.fsync(f.fileno())
  os.chmod(t,0o600);os.replace(t,p)
 finally:
  if os.path.exists(t):os.unlink(t)
def listing():
 with LOCK:return {'tasks':TASKS,'records':read(BASE/'tasks.json')}
def execute(d):
 if not isinstance(d,dict):raise ValueError()
 kind=d.get('task')
 if kind not in TASKS:raise ValueError()
 token=str(uuid.UUID(d.get('request_id','')))
 with LOCK:
  p=BASE/'tasks.json';jobs=read(p)
  if token in jobs:
   if jobs[token]['task']!=kind:raise ValueError()
   return jobs[token]
  if len(jobs)>=500:raise ValueError('업무 기록 한도 도달')
  e={'task':kind,'title':TASKS[kind],
     'approved_at':now(),'status':'처리 중'}
  jobs[token]=e;put(p,jobs)
  try:
   required=[BASE/'score.json',BASE/'reviews.json']
   if kind=='report':
    required += [Path('/var/lib/bot-office/risk_report.json'),
                 Path('/var/lib/bot-office/inventory.json')]
   for source in required:
    if not source.is_file():raise FileNotFoundError()
    if source.stat().st_size>4_000_000:raise ValueError()
   if shutil.disk_usage(BASE).free<100*1024*1024:raise OSError()
   score=read(required[0]);reviews=read(required[1])
   if kind=='backup':
    result={'created_at':now(),'score':score,'reviews':reviews}
   else:
    risk=read(required[2]);inventory=read(required[3])
    result={'created_at':now(),'market_score':score.get('total'),
     'market_updated_at':score.get('updated_at'),
     'risk_checked_at':risk.get('checked_at'),
     'risk_reports':risk.get('reports',[]),
     'inventory_collected_at':inventory.get('collected_at'),
     'bots':inventory.get('bots',[])}
   dest=BASE/('approved-'+kind+'-'+token+'.json')
   put(dest,result)
   if read(dest)!=result:raise ValueError()
   e.update(status='성공',finished_at=now(),output=dest.name,result=result)
  except Exception as error:
   e.update(status='실패',finished_at=now(),error=type(error).__name__)
  put(p,jobs)
  return e
