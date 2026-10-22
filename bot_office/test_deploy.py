import importlib.util, tempfile, json, uuid, hashlib
from pathlib import Path
from datetime import datetime, timezone

spec=importlib.util.spec_from_file_location(
 'engine','/opt/bot-office/apply_deploy.py')
engine=importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
engine.time.sleep=lambda _:None

def test(mode):
 with tempfile.TemporaryDirectory() as temp:
  base=Path(temp)
  root=base/'bot';root.mkdir()
  public=base/'public';public.mkdir()
  ident=str(uuid.uuid4())
  folder=base/'packages'/ident
  folder.mkdir(parents=True)
  unit='bithumb_bot.service'
  old=b'x=1\n';new=b'x=2\n'
  (root/'main.py').write_bytes(old)
  (folder/'before.py').write_bytes(old)
  (folder/'after.py').write_bytes(new)
  m={'id':ident,'unit':unit,'file':'main.py',
     'before_sha256':engine.sha(old),
     'after_sha256':engine.sha(new)}
  def write(p,d):p.write_text(json.dumps(d))
  write(folder/'manifest.json',m)
  write(public/(ident+'.json'),m)
  write(base/'targets.json',{'targets':{
   unit:{'root':str(root),'files':{'main.py':{}}}}})
  approval={'decision':'승인',
   'execution_authorized':mode!='old',
   'review_hash':engine.sha(json.dumps(
    m,sort_keys=True,ensure_ascii=False).encode()),
   'at':datetime.now(timezone.utc).isoformat()}
  write(base/'approvals.json',{ident:approval})
  engine.BASE=base;engine.PUBLIC=public
  engine.APPROVAL=base/'approvals.json'
  starts=[]
  def fake(*args):
   if args[0]=='show':
    if 'User' in args:return 'test-user'
    if 'WorkingDirectory' in args:return str(root)
    return '0'
   if args[0]=='is-active':return 'active'
   if args[0]=='start':
    starts.append(1)
    if mode=='rollback' and len(starts)==1:
     raise RuntimeError('모의 시작 실패')
   return ''
  engine.command=fake
  if mode=='stale':(root/'main.py').write_bytes(b'x=3\n')
  try:
   engine.apply(ident)
  except ValueError:
   assert mode in ('old','stale')
   assert not starts
   return
  assert mode not in ('old','stale')
  state=json.loads((folder/'execution.json').read_text())
  expected=new if mode=='success' else old
  assert (root/'main.py').read_bytes()==expected
  assert state['status']==(
   '적용 완료 · 시작 상태 확인' if mode=='success'
   else '적용 실패 · 이전 코드 시작 확인')

for mode in ['success','rollback','old','stale']:
 test(mode)
 print('통과:',mode)
helper=Path('/opt/bot-office/apply_deploy.py')
Path('/var/lib/bot-office-deploy/tested-helper.sha256').write_text(
 hashlib.sha256(helper.read_bytes()).hexdigest())
print('완료: 모의 적용·복구·기존승인 차단·코드변경 차단')
