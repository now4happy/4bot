#!/usr/bin/env python3
"""Store a Gemini API key securely after a models-list connectivity check.
No generateContent call, scheduler, billing change, or bot modification.
"""
import getpass,grp,json,os,secrets,sys,urllib.request,urllib.error,warnings
from pathlib import Path

ENDPOINT='https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000'
DEST=Path('/etc/bot-office/gemini.json')

def check_key(key,open_url=urllib.request.urlopen):
 request=urllib.request.Request(ENDPOINT,headers={'x-goog-api-key':key,'Accept':'application/json'})
 with open_url(request,timeout=20) as response:
  data=json.loads(response.read(2*1024**2))
 if not isinstance(data,dict):raise ValueError('invalid_response')
 models=[]
 for m in data.get('models',[]):
  if isinstance(m,dict) and isinstance(m.get('name'),str) and 'generateContent' in m.get('supportedGenerationMethods',[]):
   name=m['name']
   if name.startswith('models/gemini-') and len(name)<150:models.append(name)
 if not models:raise ValueError('no_text_models')
 return sorted(set(models))

def main():
 if os.geteuid()!=0:raise SystemExit('sudo python3 bot_office_gemini_setup.py 로 실행하세요.')
 if not DEST.parent.is_dir():raise SystemExit('사무실 설치 경로가 없습니다. 변경 없이 중단합니다.')
 if DEST.exists():raise SystemExit('Gemini 설정이 이미 있습니다. 키를 덮어쓰지 않고 중단합니다.')
 if not sys.stdin.isatty():raise SystemExit('SSH 터미널에서 파일을 직접 실행하세요. 파이프로 키를 입력하지 마세요.')
 warnings.simplefilter('error',getpass.GetPassWarning)
 try:key=getpass.getpass('Gemini API 키 붙여넣기 (화면에 표시되지 않음): ').strip()
 except (getpass.GetPassWarning,EOFError,KeyboardInterrupt):raise SystemExit('\n안전한 숨김 입력을 사용할 수 없어 중단합니다.')
 if not 20<=len(key)<=512 or any(c.isspace() for c in key):raise SystemExit('키 형식을 확인하세요. 저장하지 않았습니다.')
 try:models=check_key(key)
 except urllib.error.HTTPError as e:
  messages={400:'키 또는 요청을 확인하세요.',401:'인증 실패: API 키를 확인하세요.',403:'접근 권한 또는 지역/프로젝트 설정을 확인하세요.',429:'사용량 제한: 잠시 후 다시 시도하세요.'}
  raise SystemExit('연결 실패 HTTP '+str(e.code)+' — '+messages.get(e.code,'잠시 후 다시 실행하세요.')+' 키는 저장하지 않았습니다.')
 except (urllib.error.URLError,TimeoutError,OSError,ValueError):raise SystemExit('연결 또는 모델 목록 확인 실패. 키는 저장하지 않았습니다.')
 data={'provider':'gemini','api_key':key,'available_text_models':models,'model':None,'analysis_enabled':False,'automatic_calls_enabled':False}
 gid=grp.getgrnam('bot-office').gr_gid
 temp=DEST.parent/('.gemini-'+secrets.token_hex(8)+'.tmp')
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 try:
  with os.fdopen(fd,'w') as stream:json.dump(data,stream);stream.flush();os.fsync(stream.fileno())
  os.chown(temp,0,gid);temp.chmod(0o640)
  # Never replace an existing key if another setup completed concurrently.
  os.link(temp,DEST)
 finally:temp.unlink(missing_ok=True)
 print('완료: Gemini 키 저장 / 인증·모델 목록 조회 성공')
 print('텍스트 생성 후보 '+str(len(models))+'개 / 분석 모델은 아직 미선택')
 print('자동 호출·과금 설정 변경·봇 변경 없음. AI 생성 시험은 아직 하지 않았습니다.')
if __name__=='__main__':main()
