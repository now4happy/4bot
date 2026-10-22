#!/usr/bin/env python3
# 업데이트 비서 안전장치 (systemd ExecStartPre) — 자기 업데이트 뒤 2분 안에 정상 신호가 없으면 이전 버전으로 되돌림
import json, os, shutil, time, urllib.request
OFFICE = os.environ.get("U_OFFICE", "/opt/bot-office")
STATE = os.environ.get("U_STATE", "/var/lib/bot-updater/state.json")
TG_CFG = os.environ.get("U_TG", "/etc/bot-office/telegram.json")
TG_API = os.environ.get("U_TG_API", "https://api.telegram.org")
try:
    st = json.load(open(STATE, encoding="utf-8"))
except Exception:
    st = {}
p = st.get("self_pending")
prev = os.path.join(OFFICE, "bot_updater.prev.py")
if p and time.time() - float(p.get("since", 0)) > float(os.environ.get("U_GRACE", "120")) and os.path.exists(prev):
    shutil.copy2(prev, os.path.join(OFFICE, "bot_updater.py"))
    st.pop("self_pending", None)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1); os.replace(tmp, STATE)
    try:
        c = json.load(open(TG_CFG))
        d = json.dumps({"chat_id": c["chat_id"], "text": "🚨 [업데이트 비서] 새 버전이 정상 시작하지 않아 이전 버전으로 자동 복구했습니다. (GitHub main 에는 새 버전이 올라가 있으니 Gemini에게 수정 요청해 주세요)"}).encode()
        urllib.request.urlopen(urllib.request.Request(f"{TG_API}/bot{c['token']}/sendMessage", data=d, headers={"Content-Type": "application/json"}), timeout=10)
    except Exception:
        pass
    print("이전 버전으로 복구")
