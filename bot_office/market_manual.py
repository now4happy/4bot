import json, os, tempfile, threading
from pathlib import Path
from datetime import datetime, timezone
P=Path('/var/lib/bot-office/market-manual/score.json')
L=threading.Lock()
def read():
    with L:
        if P.exists(): return json.loads(P.read_text())
    return {'items':[{'name':n,'score':None} for n in ['금리','물가','시장심리']], 'revision':0, 'total':None, 'updated_at':None}
def save(d):
    items=d.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=20: raise ValueError()
    clean=[]
    for x in items:
        name=x.get('name')
        score=x.get('score')
        if not isinstance(name,str) or not 1<=len(name.strip())<=40: raise ValueError()
        if score is not None and (type(score) is not int or not 1<=score<=10): raise ValueError()
        clean.append({'name':name.strip(),'score':score})
    if len({x['name'] for x in clean})!=len(clean): raise ValueError()
    with L:
        old=json.loads(P.read_text()) if P.exists() else {'revision':0}
        if type(d.get('revision')) is not int or d['revision']!=old['revision']: return None
        scores=[x['score'] for x in clean if x['score'] is not None]
        result={'items':clean,'revision':old['revision']+1,'total':round(sum(scores)/len(scores)*10,1) if len(scores)==len(clean) else None,'updated_at':datetime.now(timezone.utc).isoformat()}
        # MARKET_HISTORY_V1
        history=list(old.get('history',[]))
        history.append({'at':result['updated_at'],
         'total':result['total'],'items':clean})
        result['history']=history[-100:]
        fd,tmp=tempfile.mkstemp(dir=P.parent)
        try:
            with os.fdopen(fd,'w') as f: json.dump(result,f,ensure_ascii=False)
            os.chmod(tmp,0o600); os.replace(tmp,P)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        return result
