import json, difflib, os, grp, tempfile, hashlib
from pathlib import Path

def publish(folder):
 m=json.loads((folder/'manifest.json').read_text())
 old=(folder/'before.py').read_bytes()
 new=(folder/'after.py').read_bytes()
 for raw,key in [(old,'before_sha256'),(new,'after_sha256')]:
  if hashlib.sha256(raw).hexdigest()!=m[key]:
   raise ValueError('변경안 지문 불일치')
 m['diff']=''.join(difflib.unified_diff(
  old.decode('utf-8-sig').splitlines(True),
  new.decode('utf-8-sig').splitlines(True),
  fromfile='변경 전/'+m['file'],
  tofile='변경 후/'+m['file']))
 dest=Path('/var/lib/bot-office-deploy-public')
 fd,tmp=tempfile.mkstemp(dir=dest)
 try:
  with os.fdopen(fd,'w') as f:
   json.dump(m,f,ensure_ascii=False,indent=2)
  os.chown(tmp,0,grp.getgrnam('bot-office').gr_gid)
  os.chmod(tmp,0o640)
  os.replace(tmp,dest/(m['id']+'.json'))
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
