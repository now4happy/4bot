"""Read-only bot metadata collector. Never imports bot code or reads env files."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from datetime import datetime,timezone
OUT=Path('/var/lib/bot-office/inventory.json')
UNITS=('han4384tubot.service','bithumb_bot.service','toss_sniper.service','toss_dca.service')
def collect(unit,previous,clock):
 fields={};notes=[]
 try:
  p=subprocess.run(['systemctl','show',unit,'--no-pager','-p','LoadState','-p','WorkingDirectory','-p','MainPID','-p','NRestarts','-p','ExecMainStartTimestamp','-p','UnitFileState'],capture_output=True,text=True,timeout=3,check=True)
  fields=dict(s.split('=',1) for s in p.stdout.splitlines() if '=' in s)
 except (OSError,subprocess.SubprocessError):notes.append('service_metadata_unavailable')
 cwd=Path(fields.get('WorkingDirectory') or '/')
 entry=None
 try:
  pid=int(fields.get('MainPID','0'))
  if pid>0 and cwd.is_absolute() and cwd!=Path('/'):
   args=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
   for raw in args[1:]:
    a=raw.decode(errors='replace')
    if not a.endswith('.py') or '=' in a:continue
    path=Path(a) if Path(a).is_absolute() else cwd/a
    if path.is_symlink():continue
    if path.resolve().is_relative_to(cwd.resolve()) and path.is_file():entry=path;break
 except (OSError,ValueError):notes.append('entry_unavailable')
 version=None;fingerprint=None;count=0
 if entry:
  dig=hashlib.sha256()
  for path in sorted(cwd.glob('*.py'))[:100]:
   if path.is_symlink() or not path.is_file() or path.name.startswith('bot_office_'):continue
   try:
    if path.stat().st_size>1024**2:continue
    content=path.read_bytes();dig.update(path.name.encode()+b'\0'+content);count+=1
    match=re.search(rb'(?m)^BOT_VERSION\s*=\s*[\x22\x27](v?[0-9][0-9A-Za-z._~ -]{0,39})[\x22\x27]',content)
    if match and version is None:version=match.group(1).decode()
   except OSError:notes.append('code_read_unavailable')
  if count:fingerprint=dig.hexdigest()
 else:notes.append('entry_not_identified')
 oldhash=previous.get('code_hash');changed=bool(oldhash and fingerprint and oldhash!=fingerprint)
 last_changed=clock if changed else previous.get('last_change_detected_at')
 return {'unit':unit,'declared_version':version,'entry':entry.name if entry else None,'code_hash':fingerprint,'code_files_count':count,'changed_on_this_check':changed,'last_change_detected_at':last_changed,'restart_count':int(fields['NRestarts']) if fields.get('NRestarts','').isdigit() else None,'started_at':fields.get('ExecMainStartTimestamp') or None,'boot_setting':fields.get('UnitFileState','unknown'),'notes':sorted(set(notes))}
def main():
 OUT.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
 try:old=json.loads(OUT.read_text())
 except (OSError,ValueError):old={}
 before={b.get('unit'):b for b in old.get('bots',[]) if isinstance(b,dict)}
 clock=datetime.now(timezone.utc).isoformat()
 data={'collected_at':clock,'scope':'top_level_python_files_only','bots':[collect(u,before.get(u,{}),clock) for u in UNITS]}
 tmp=OUT.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False));tmp.chmod(0o644);os.replace(tmp,OUT)
if __name__=='__main__':main()
