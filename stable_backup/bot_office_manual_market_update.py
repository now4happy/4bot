#!/usr/bin/env python3
import ast, os, subprocess, shutil, time, urllib.request
from pathlib import Path
from datetime import datetime
MODULE="import json, os, tempfile, threading\nfrom pathlib import Path\nfrom datetime import datetime, timezone\nP=Path('/var/lib/bot-office/market-manual/score.json')\nL=threading.Lock()\ndef read():\n    with L:\n        if P.exists(): return json.loads(P.read_text())\n    return {'items':[{'name':n,'score':None} for n in ['금리','물가','시장심리']], 'revision':0, 'total':None, 'updated_at':None}\ndef save(d):\n    items=d.get('items')\n    if not isinstance(items,list) or not 1<=len(items)<=20: raise ValueError()\n    clean=[]\n    for x in items:\n        name=x.get('name')\n        score=x.get('score')\n        if not isinstance(name,str) or not 1<=len(name.strip())<=40: raise ValueError()\n        if score is not None and (type(score) is not int or not 1<=score<=10): raise ValueError()\n        clean.append({'name':name.strip(),'score':score})\n    if len({x['name'] for x in clean})!=len(clean): raise ValueError()\n    with L:\n        old=json.loads(P.read_text()) if P.exists() else {'revision':0}\n        if type(d.get('revision')) is not int or d['revision']!=old['revision']: return None\n        scores=[x['score'] for x in clean if x['score'] is not None]\n        result={'items':clean,'revision':old['revision']+1,'total':round(sum(scores)/len(scores)*10,1) if len(scores)==len(clean) else None,'updated_at':datetime.now(timezone.utc).isoformat()}\n        fd,tmp=tempfile.mkstemp(dir=P.parent)\n        try:\n            with os.fdopen(fd,'w') as f: json.dump(result,f,ensure_ascii=False)\n            os.chmod(tmp,0o600); os.replace(tmp,P)\n        finally:\n            if os.path.exists(tmp): os.unlink(tmp)\n        return result\n"
GET="        if route=='/api/market-manual':\n            import market_manual\n            return self.send(200,market_manual.read())\n"
POST="        if route=='/api/market-manual':\n            if not self.session(): return self.send(401,{'error':'login_required'})\n            if self.headers.get('X-Bot-Office')!='market-manual': return self.send(403,{'error':'invalid_request'})\n            try:\n                n=int(self.headers.get('Content-Length','0'))\n                if not 0<n<=16000: raise ValueError()\n                import market_manual\n                result=market_manual.save(json.loads(self.rfile.read(n)))\n            except (ValueError,TypeError,AttributeError,KeyError): return self.send(400,{'error':'invalid_scores'})\n            except OSError: return self.send(500,{'error':'save_failed'})\n            if result is None: return self.send(409,{'error':'changed_elsewhere'})\n            return self.send(200,result)\n"
UI='<script id="market-manual-v1">\n(()=>{\nconst box=document.createElement(\'section\');box.style.cssText=\'margin:20px auto;padding:20px;max-width:1000px;background:#f1f5ed;border:1px solid #bacab5;border-radius:16px;color:#244533\';\nbox.innerHTML=\'<h2>시장분석팀 · 직접 평가</h2><p>1단계: 투자에 매우 불리 · 10단계: 매우 우호적</p><p>종합점수 = 모든 항목의 단계 평균 × 10 (동일 비중). 미입력 항목이 있으면 점수 산출을 보류합니다.</p><div class="rows"></div><button type="button" class="add">항목 추가</button> <button type="button" class="save">서버에 저장</button><h3 class="total"></h3><p class="message" role="status"></p><small>사용자 판단 기록입니다. 실제 금리·물가 수치나 자동 매매 신호가 아닙니다. 저장해야 다른 기기에도 반영됩니다.</small>\';\n(document.querySelector(\'main\')||document.body).prepend(box);\nlet revision=0,ready=false;\nconst rows=box.querySelector(\'.rows\'),message=box.querySelector(\'.message\');\nfunction total(){const values=[...rows.querySelectorAll(\'select\')].map(x=>x.value);box.querySelector(\'.total\').textContent=values.length&&values.every(Boolean)?\'종합점수 \'+(values.reduce((s,x)=>s+Number(x),0)/values.length*10).toFixed(1)+\' / 100점\':\'종합점수: 입력 대기\';}\nfunction row(x={name:\'\',score:null}){const r=document.createElement(\'div\');r.style.cssText=\'display:flex;gap:8px;margin:10px 0;flex-wrap:wrap\';const name=document.createElement(\'input\');name.value=x.name;name.maxLength=40;name.placeholder=\'항목 이름\';name.setAttribute(\'aria-label\',\'평가 항목 이름\');name.style.cssText=\'min-width:100px;flex:1;padding:10px\';const score=document.createElement(\'select\');score.setAttribute(\'aria-label\',\'투자 우호도 단계\');score.add(new Option(\'미입력\',\'\'));for(let i=1;i<=10;i++)score.add(new Option(i+\'단계\',String(i)));score.value=x.score==null?\'\':String(x.score);score.onchange=()=>{total();message.textContent=\'변경 사항을 저장하세요.\'};const del=document.createElement(\'button\');del.textContent=\'삭제\';del.type=\'button\';del.onclick=()=>{r.remove();total();message.textContent=\'변경 사항을 저장하세요.\'};name.oninput=()=>message.textContent=\'변경 사항을 저장하세요.\';r.append(name,score,del);rows.append(r);total();}\nbox.querySelector(\'.add\').onclick=()=>{if(rows.children.length>=20){message.textContent=\'최대 20개입니다.\';return}row();};\nbox.querySelector(\'.save\').onclick=async()=>{if(!ready)return;const button=box.querySelector(\'.save\');button.disabled=true;try{const items=[...rows.children].map(r=>({name:r.querySelector(\'input\').value.trim(),score:r.querySelector(\'select\').value?Number(r.querySelector(\'select\').value):null}));if(!items.length||items.some(x=>!x.name)||new Set(items.map(x=>x.name)).size!==items.length)throw Error(\'항목은 1개 이상이며 이름은 중복 없이 입력하세요.\');const res=await fetch(\'/api/market-manual\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\',\'X-Bot-Office\':\'market-manual\'},body:JSON.stringify({items,revision})});if(res.status===409)throw Error(\'다른 기기에서 변경했습니다. 새로고침 후 다시 입력하세요.\');if(!res.ok)throw Error(\'저장 실패: 로그인 또는 입력값을 확인하세요.\');const d=await res.json();revision=d.revision;message.textContent=\'저장 완료 · \'+new Date(d.updated_at).toLocaleString(\'ko-KR\');}catch(e){message.textContent=e.message}finally{button.disabled=false}};\nfetch(\'/api/market-manual\',{cache:\'no-store\'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>{revision=d.revision;d.items.forEach(row);ready=true;message.textContent=d.updated_at?\'마지막 저장 · \'+new Date(d.updated_at).toLocaleString(\'ko-KR\'):\'첫 평가를 입력하세요.\'}).catch(()=>message.textContent=\'평가 불러오기 실패. 다시 로그인하거나 새로고침하세요.\');\n})();\n</script>'
if os.geteuid()!=0: raise SystemExit('sudo로 실행하세요.')
root=Path('/opt/bot-office'); server=root/'server.py'; html=root/'index.html'
s=server.read_text(); h=html.read_text()
if 'market-manual-v1' in h: raise SystemExit('이미 설치되어 있습니다.')
a="        if route=='/api/status': return self.send(200,snapshot())"
b="        if route!='/api/login': return self.send(404,{'error':'not_found'})"
if s.count(a)!=1 or s.count(b)!=1 or h.count('</body>')!=1: raise SystemExit('구조가 달라 변경을 중단했습니다.')
s=s.replace(a,GET+a).replace(b,POST+b); ast.parse(s);ast.parse(MODULE)
h=h.replace('</body>',UI+'</body>')
backup=root/('backup_manual_'+datetime.now().strftime('%Y%m%d_%H%M%S'));backup.mkdir()
for p in [server,html]: shutil.copy2(p,backup/p.name)
state=Path('/var/lib/bot-office/market-manual');state.mkdir(exist_ok=True)
shutil.chown(state,user='bot-office',group='bot-office');state.chmod(0o700)
drop=Path('/etc/systemd/system/bot-office.service.d/market-manual.conf');drop.parent.mkdir(exist_ok=True)
if drop.exists(): raise SystemExit('기존 설정이 있어 중단했습니다.')
try:
    (root/'market_manual.py').write_text(MODULE)
    for p,content in [(server,s),(html,h)]:
        tmp=p.with_suffix('.manual-new');tmp.write_text(content);tmp.chmod(0o644);tmp.replace(p)
    drop.write_text('[Service]\nReadWritePaths=/var/lib/bot-office/market-manual\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','restart','bot-office.service'],check=True)
    for _ in range(15):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8765/healthz',timeout=2) as r:
                if r.status==200: break
        except OSError: time.sleep(1)
    else: raise RuntimeError('healthcheck')
except Exception:
    for p in [server,html]: shutil.copy2(backup/p.name,p)
    drop.unlink(missing_ok=True)
    subprocess.run(['systemctl','daemon-reload']);subprocess.run(['systemctl','restart','bot-office.service'])
    raise SystemExit('설치 실패: 사무실 원본을 복구했습니다.')
print('완료: 직접 평가 시장점수판 설치. 사무실에 다시 로그인하세요.')
print('금리·물가·시장심리 / 항목 편집 / 서버 저장 / 평균×10 종합점수')
print('Gemini 호출·매매봇 변경 없음. 백업:',backup)
