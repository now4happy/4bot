"""Bounded local resource sampling; comparison is observational, never a trading test."""
import json,os,shutil,statistics,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
BASE=Path('/var/lib/bot-office')
UNITS=('han4384tubot.service','bithumb_bot.service','toss_sniper.service','toss_dca.service')

def median(items,key):
 values=[p.get(key) for p in items if isinstance(p.get(key),(int,float))]
 return statistics.median(values) if values else None

def analyze(history):
 if not history:return None
 latest=history[-1];change=None
 for i in range(len(history)-1,0,-1):
  a,b=history[i-1],history[i]
  units=[u for u in UNITS if a['bots'].get(u,{}).get('code_hash') and b['bots'].get(u,{}).get('code_hash') and a['bots'][u]['code_hash']!=b['bots'][u]['code_hash']]
  if units:change=(i,units);break
 comparison=None
 if change:
  idx,changed=change;before=history[max(0,idx-5):idx];after=history[idx:idx+5]
  rows=[]
  for u in UNITS:
   x=[p['bots'].get(u,{}) for p in before];y=[p['bots'].get(u,{}) for p in after]
   rows.append({'unit':u,'memory_before':median(x,'memory_bytes'),'memory_after':median(y,'memory_bytes'),'cpu_before':median(x,'cpu_percent'),'cpu_after':median(y,'cpu_percent')})
  comparison={'detected_at':history[idx]['at'],'changed_units':changed,'before_count':len(before),'after_count':len(after),'ready':len(before)>=5 and len(after)>=5,'bots':rows}
 hours=(latest['ts']-history[0]['ts'])/3600
 indexes=sorted(set(round(i*(len(history)-1)/min(95,len(history)-1)) for i in range(min(96,len(history))))) if len(history)>1 else [0]
 trend=[{k:history[i].get(k) for k in ('at','disk_free','mem_available','load_1m')} for i in indexes]
 return {'checked_at':latest['at'],'sample_count':len(history),'hours':hours,'latest':latest,'trend':trend,'comparison':comparison,'method':'one_minute_samples_24h_max_1440; CPU 100%=one core; comparison=5 medians each side; not causal'}

def collect(previous,inventory,clock,stats,disk_free,mem_available,load):
 old=previous[-1] if previous else None
 bots={}
 inv={b['unit']:b for b in inventory.get('bots',[])}
 try:inv_fresh=0<=(clock-datetime.fromisoformat(inventory['collected_at'])).total_seconds()<180
 except (KeyError,ValueError,TypeError):inv_fresh=False
 for u in UNITS:
  st=stats.get(u,{});cpu=None;a=old['bots'].get(u,{}) if old else {}
  if old and isinstance(st.get('cpu_ns'),int) and isinstance(a.get('cpu_ns'),int):
   delta=st['cpu_ns']-a['cpu_ns'];seconds=clock.timestamp()-old['ts']
   if delta>=0 and seconds>0 and a.get('started_at')==st.get('started_at') and st.get('started_at'):
    cpu=delta/1e9/seconds*100
  bots[u]={'memory_bytes':st.get('memory_bytes'),'cpu_ns':st.get('cpu_ns'),'cpu_percent':cpu,'started_at':st.get('started_at'),'code_hash':inv.get(u,{}).get('code_hash') if inv_fresh else None}
 return {'at':clock.isoformat(),'ts':clock.timestamp(),'disk_free':disk_free,'mem_available':mem_available,'load_1m':load,'bots':bots}

def atomic(path,data,mode=0o644):
 t=path.with_suffix('.tmp');t.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False));t.chmod(mode);os.replace(t,path)
def main():
 BASE.mkdir(exist_ok=True)
 try:history=json.loads((BASE/'resource_history.json').read_text())
 except (OSError,ValueError):history=[]
 if not isinstance(history,list):history=[]
 now=datetime.now(timezone.utc)
 # Avoid manufacturing multiple minute samples during repeated manual checks.
 if history and now.timestamp()-history[-1]['ts']<45:
  report=analyze(history)
  if report:atomic(BASE/'optimization.json',report)
  return
 try:inventory=json.loads((BASE/'inventory.json').read_text())
 except (OSError,ValueError):inventory={}
 stats={}
 for u in UNITS:
  try:
   p=subprocess.run(['systemctl','show',u,'-p','MemoryCurrent','-p','CPUUsageNSec','-p','ExecMainStartTimestamp'],capture_output=True,text=True,timeout=2,check=True)
   f=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
   number=lambda key:int(f[key]) if f.get(key,'').isdigit() else None
   stats[u]={'memory_bytes':number('MemoryCurrent'),'cpu_ns':number('CPUUsageNSec'),'started_at':f.get('ExecMainStartTimestamp')}
  except (OSError,subprocess.SubprocessError):stats[u]={}
 mem=None
 try:
  for line in Path('/proc/meminfo').read_text().splitlines():
   if line.startswith('MemAvailable:'):mem=int(line.split()[1])*1024
 except (OSError,ValueError):pass
 history=[p for p in history if 0<=now.timestamp()-p.get('ts',0)<86400][-1439:]
 history.append(collect(history,inventory,now,stats,shutil.disk_usage('/').free,mem,os.getloadavg()[0]))
 atomic(BASE/'resource_history.json',history,0o600);atomic(BASE/'optimization.json',analyze(history))
if __name__=='__main__':main()
