"""Rule-based operations checks only. No AI, orders, credentials, or bot imports."""
import json,os,shutil
from datetime import datetime,timezone
from pathlib import Path
BASE=Path('/var/lib/bot-office')

def evaluate(inv,previous,now,disk_free,mem_available,states):
 reports=[];events=list(previous.get('events',[]));old={b['unit']:b for b in previous.get('observed_bots',[])}
 clock=now.isoformat();check_time=str(inv.get('collected_at',''))
 def report(key,title,body,level='warning'):
  reports.append({'key':key,'title':title,'body':body,'level':level,'team':1,'tag':{'warning':'주의','critical':'확인 필요','info':'정보'}[level]+' · 실제 규칙 점검'})
 try:fresh=0<=(now-datetime.fromisoformat(check_time)).total_seconds()<180
 except (ValueError,TypeError):fresh=False
 if not fresh:report('stale','봇 정보 수집 지연','최근 3분 안의 수집 결과가 없습니다. 버전·코드 변경 정보는 확인 불가 상태입니다.','critical')
 if disk_free<512*1024**2:report('disk','디스크 여유 512MB 미만',f'현재 여유 {disk_free/1024**2:.0f}MB. 상태 저장과 로그 기록에 필요한 공간을 확인하세요.','critical')
 elif disk_free<1024**3:report('disk','디스크 여유 1GB 미만',f'현재 여유 {disk_free/1024**2:.0f}MB. 자동 정리 후에도 공간 증가 추이를 확인하세요.')
 if mem_available is not None:
  if mem_available<128*1024**2:report('memory','사용 가능 메모리 128MB 미만',f'현재 {mem_available/1024**2:.0f}MB. 프로세스별 메모리와 스왑 사용 추이를 확인하세요.','critical')
  elif mem_available<256*1024**2:report('memory','사용 가능 메모리 256MB 미만',f'현재 {mem_available/1024**2:.0f}MB. 일시적인 수치일 수 있으며, 신규 작업을 추가할 때 추이를 확인하세요.')
 for b in inv.get('bots',[]) if fresh else []:
  u=b['unit'];n={'han4384tubot.service':'① 한투','bithumb_bot.service':'② 빗썸','toss_sniper.service':'③ 스나이퍼','toss_dca.service':'④ 토스 적립'}.get(u,u)
  state=states.get(u,{})
  if state.get('active')!='active' or state.get('sub')!='running':report(u+':state',n+' 실행 상태 확인 필요','현재 상태: '+state.get('active','unknown')+'/'+state.get('sub','unknown')+'. 주문 실패 여부는 별도 확인이 필요합니다.','critical')
  if b.get('boot_setting')=='disabled':report(u+':boot',n+' 부팅 자동 시작 꺼짐','현재 실행과는 별개입니다. 서버 재부팅 후 해당 서비스가 자동으로 시작되는지 설정을 검토하세요.')
  if not b.get('code_hash'):report(u+':code',n+' 코드 지문 확인 불가','버전 수집 대상과 파일 접근 상태를 확인하세요.')
  before=old.get(u,{})
  a=before.get('restart_count');z=b.get('restart_count')
  restart=isinstance(a,int) and isinstance(z,int) and z>a
  changed=bool(before.get('code_hash') and b.get('code_hash') and before['code_hash']!=b['code_hash'])
  for flag,kind,msg in ((restart,'restart',n+' 자동 재시작 횟수 증가'),(changed,'code_change',n+' 코드 지문 변경 감지')):
   if flag:events.append({'at':clock,'unit':u,'kind':kind,'title':msg})
  if restart:report(u+':restart',n+' 자동 재시작 감지',f'직전 수집 이후 systemd 자동 재시작 횟수 {a} → {z}. 수동 재시작 전체 이력은 이 숫자에 포함되지 않습니다.')
 for event in reversed(events[-100:]):
  try:recent=(now-datetime.fromisoformat(event['at'])).total_seconds()<86400
  except (ValueError,KeyError):continue
  key=event['unit']+':'+event['kind']
  if recent and event['kind']=='code_change' and not any(r['key']==key for r in reports):report(key,event['title'],'최상위 파이썬 파일 지문이 바뀌었습니다. 실행에 쓰이지 않는 파일도 포함될 수 있으며, 승인 여부와 실제 기능 영향은 별도 검토가 필요합니다.')
 if not reports:report('ok','현재 운영 점검 항목에 이상 신호 없음','서비스 실행·수집 최신성·자원 임계값 기준입니다. 주문·체결·전략 수익성이나 가상매매를 검증한 결과는 아닙니다.','info')
 return {'checked_at':clock,'mode':'rules_only','scope':'operations_only','reports':reports,'events':events[-100:],'observed_bots':inv.get('bots',[]) if fresh else previous.get('observed_bots',[])}

def main():
 import subprocess
 try:inv=json.loads((BASE/'inventory.json').read_text())
 except (OSError,ValueError):inv={}
 try:prev=json.loads((BASE/'risk_report.json').read_text())
 except (OSError,ValueError):prev={}
 mem=None
 try:
  for line in Path('/proc/meminfo').read_text().splitlines():
   if line.startswith('MemAvailable:'):mem=int(line.split()[1])*1024
 except (OSError,ValueError):pass
 states={}
 for b in inv.get('bots',[]):
  # Fixed allowlist; file contents cannot introduce a shell command or arbitrary service.
  u=b.get('unit')
  if u not in ('han4384tubot.service','bithumb_bot.service','toss_sniper.service','toss_dca.service'):continue
  try:
   p=subprocess.run(['systemctl','show',u,'-p','ActiveState','-p','SubState'],capture_output=True,text=True,timeout=2,check=True)
   f=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
   states[u]={'active':f.get('ActiveState','unknown'),'sub':f.get('SubState','unknown')}
  except (OSError,subprocess.SubprocessError):pass
 data=evaluate(inv,prev,datetime.now(timezone.utc),shutil.disk_usage('/').free,mem,states)
 BASE.mkdir(exist_ok=True);tmp=BASE/'risk_report.tmp';tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.chmod(0o644);os.replace(tmp,BASE/'risk_report.json')
if __name__=='__main__':main()
