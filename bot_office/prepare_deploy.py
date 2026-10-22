import ast, hashlib, json, os, sys, uuid
from pathlib import Path
from datetime import datetime, timezone

def digest(raw):
 return hashlib.sha256(raw).hexdigest()

def main():
 if os.geteuid()!=0:
  raise SystemExit('sudo로 실행해 주세요')
 if len(sys.argv)!=5:
  raise SystemExit('사용법: 서비스명 대상파일 새파일경로 변경설명')

 unit,name,candidate,title=sys.argv[1:]
 allowed={'bithumb_bot.service','toss_dca.service'}
 if unit not in allowed:
  raise SystemExit('2번·4번 봇만 등록 가능합니다')
 if not 1<=len(title.strip())<=200:
  raise SystemExit('변경설명은 1~200자로 입력해 주세요')

 os.umask(0o077)
 base=Path('/var/lib/bot-office-deploy')
 cfg=json.loads((base/'targets.json').read_text())
 target=cfg['targets'].get(unit)
 if not target or name not in target['files']:
  raise SystemExit('등록된 대상 파일이 아닙니다')

 root=Path(target['root'])
 current=root/name
 source=Path(candidate)
 if root.resolve()!=root or current.is_symlink():
  raise SystemExit('대상 연결 경로는 허용하지 않습니다')
 if source.is_symlink() or not source.is_file():
  raise SystemExit('새 코드는 일반 파일이어야 합니다')
 if current.stat().st_size>1_000_000 or source.stat().st_size>1_000_000:
  raise SystemExit('파일 크기 확인 필요')

 old=current.read_bytes()
 new=source.read_bytes()
 compile(new,name,'exec',ast.PyCF_ONLY_AST)
 if old==new:
  raise SystemExit('변경 내용이 없습니다')

 ident=str(uuid.uuid4())
 packages=base/'packages'
 packages.mkdir(mode=0o700,exist_ok=True)
 if packages.is_symlink():
  raise SystemExit('준비 폴더 확인 필요')
 folder=packages/ident
 folder.mkdir(mode=0o700)
 (folder/'before.py').write_bytes(old)
 (folder/'after.py').write_bytes(new)
 stat=current.stat()
 manifest={
  'id':ident,'unit':unit,'file':name,
  'title':title.strip(),
  'created_at':datetime.now(timezone.utc).isoformat(),
  'before_sha256':digest(old),'after_sha256':digest(new),
  'uid':stat.st_uid,'gid':stat.st_gid,
  'mode':stat.st_mode&0o777,
  'status':'승인 대기',
  'validation':'Python 문법 검사만 통과 · 매매 동작 검증 전'}
 (folder/'manifest.json').write_text(
  json.dumps(manifest,ensure_ascii=False,indent=2))
 # DEPLOY_PUBLISH_V1
 from publish_deploy import publish
 publish(folder)
 print('완료: 변경안 등록')
 print('번호:',ident)
 print('대상:',unit,name)
 print('설명:',title.strip())
 print('승인 대기 · 봇 변경·재시작 없음')

if __name__=='__main__':
 main()
