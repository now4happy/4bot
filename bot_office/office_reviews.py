import json, threading, os, tempfile, hashlib
from pathlib import Path
from datetime import datetime, timezone

P=Path("/var/lib/bot-office/market-manual/reviews.json")
LOCK=threading.Lock()
PROPOSALS={
"funds":"③·④ 공용 계좌 자금 배정표 검토",
"resources":"업데이트 전후 4개 봇 자원 비교 검토",
"market":"시장점수 구간별 전략 성과 연구 검토"
}
def records():
 return json.loads(P.read_text()) if P.exists() else {}

def write(data):
 fd,tmp=tempfile.mkstemp(dir=P.parent)
 try:
  with os.fdopen(fd,"w") as f:
   json.dump(data,f,ensure_ascii=False)
  os.chmod(tmp,0o600)
  os.replace(tmp,P)
 finally:
  Path(tmp).unlink(missing_ok=True)

def read():
 with LOCK:
  data=records()
 custom=data.get("_proposals",{})
 titles=dict(PROPOSALS)
 titles.update({k:v["title"] for k,v in custom.items() if not v.get("archived")})
 return {
  "proposals":titles,"decisions":data,
  "details":{k:v["body"] for k,v in custom.items()},
  "archived":{k:v for k,v in custom.items() if v.get("archived")}
 }
def save(d):
 if not isinstance(d,dict): raise ValueError()
 with LOCK:
  data=records()
  custom=data.setdefault("_proposals",{})
  now=datetime.now(timezone.utc).isoformat()
  # REVIEW_ARCHIVE_V1
  if d.get("action") in ("archive","restore"):
   key=d.get("id")
   if not isinstance(key,str) or key not in custom:
    raise ValueError()
   archived=d["action"]=="archive"
   custom[key]["archived"]=archived
   history=data.get("_history",[])
   history.append({"id":key,"at":now,
    "status":"보관" if archived else "복원"})
   data["_history"]=history[-100:]
   write(data)
   return {"ok":True}
  # REVIEW_PROGRESS_V1
  if d.get("action")=="progress":
   key=d.get("id");stage=d.get("stage")
   if not isinstance(key,str): raise ValueError()
   if key not in PROPOSALS and key not in custom:
    raise ValueError()
   if data.get(key,{}).get("status")!="승인":
    raise ValueError()
   if stage not in ("미착수","검증 중","적용 대기","완료"):
    raise ValueError()
   data[key]["progress"]=stage
   data[key]["progress_at"]=now
   history=data.get("_history",[])
   history.append({"id":key,"at":now,
    "status":"진행: "+stage,
    "note":"사용자 직접 기록 · 자동 검증 아님"})
   data["_history"]=history[-100:]
   write(data)
   return {"ok":True}
  if d.get("action")=="submit":
   title=d.get("title");body=d.get("body")
   if not isinstance(title,str) or not isinstance(body,str):
    raise ValueError()
   title=title.strip();body=body.strip()
   if not 1<=len(title)<=80 or not 1<=len(body)<=400:
    raise ValueError()
   key="idea_"+hashlib.sha256(
    (title+"\n"+body).encode()).hexdigest()[:20]
   if key in custom:
    return {"ok":True,"duplicate":True}
   if len(custom)>=30: raise ValueError()
   custom[key]={"title":title,"body":body,"submitted_at":now}
  else:
   key=d.get("id");status=d.get("status")
   if not isinstance(key,str): raise ValueError()
   if key not in PROPOSALS and key not in custom:
    raise ValueError()
   if status not in ("승인","보류","반려"): raise ValueError()
   # REVIEW_NOTE_V1
   note=d.get("note","")
   if not isinstance(note,str) or len(note)>300:
    raise ValueError()
   data[key]={**data.get(key,{}),"status":status,"at":now,"note":note.strip()}
   history=data.get("_history",[])
   history.append({"id":key,"status":status,"at":now,"note":note.strip()})
   data["_history"]=history[-100:]
  write(data)
 return {"ok":True}
