#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_secretary.py   (OFFICE_SECRETARY_V2)
# V2 (2026-10-23): 팬딩 가격표 주문 버튼(fd:)·/배수·/자동·/가격표 연결 (fanding_trade.py)
# 텔레그램 "사무실 비서" 대화 담당 (항상 실행: bot-office-secretary.service)
#  - 평소 말투로 보낸 메시지 → 어느 봇인지 확인 → 사무실 수정 요청으로 접수 (고칠 파일은 사무실이 자동으로 찾음)
#  - 결재 요청 메시지의 [✅ 승인] [❌ 반려] [🔍 바뀐 코드 보기] 버튼 처리 (승인은 확인 한 번 더)
#  - "브리핑", "현황", "도움말"
#  안전: 등록된 대표님 채팅방(chat_id)에서 온 것만 처리. 코드 변경은 승인 후 기존 적용 담당(deploy_worker)이 진행.
# ==========================================================
import hashlib, html, json, os, re, subprocess, sys, tempfile, time, urllib.parse, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import fanding_trade  # 팬딩 가격표 주문 (없어도 비서는 정상 동작)
except Exception as _e:
    fanding_trade = None
    print("팬딩 연결 안 됨:", _e, flush=True)
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(os.environ.get("OFFICE_ROOT", "/"))
TELEGRAM_CFG = R / "etc/bot-office/telegram.json"
OFFICE_URL = R / "etc/bot-office/office_url"
STATE = R / "var/lib/bot-office/secretary.json"
REQUESTS = R / "var/lib/bot-office/market-manual/pipeline-requests.json"
APPROVALS = R / "var/lib/bot-office/market-manual/deploy-approvals.json"
DEPLOY_PUBLIC = R / "var/lib/bot-office-deploy-public"
PIPE_PUBLIC = R / "var/lib/bot-office-pipeline-public/state.json"
TELEGRAM_API = os.environ.get("OFFICE_TELEGRAM_API", "https://api.telegram.org")
SYSTEMCTL = os.environ.get("OFFICE_SYSTEMCTL", "systemctl")
BRIEFING = os.environ.get("OFFICE_BRIEFING", "/opt/bot-office/office_briefing.py")
KST, EST = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")

BOTS = [
    ("han4384tubot.service", "1번 한투 라오어", r"1\s*번|한투|라오어|한국투자|kis"),
    ("toss_sniper.service", "2번 토스 스나이퍼", r"2\s*번|스나이퍼|soxs|sniper"),
    ("toss_dca.service", "3번 토스 적립", r"3\s*번|토스\s*(주식|적립)|토스적립|dca"),
    ("bithumb_bot.service", "4번 빗썸 적립", r"4\s*번|빗썸|bithumb|코인|비트코인"),
]
NAME = {u: n for u, n, _ in BOTS}
HELP = ("🏢 <b>사무실 비서 사용법</b>\n"
        "▫️ <b>고칠 내용을 평소 말투로</b> 보내세요. 예) <i>4번 봇 잔액 부족 알림을 1시간에 한 번만 보내줘</i>\n"
        "   → 어느 봇인지 확인 → 사무실이 고칠 파일을 스스로 찾아 수정안 작성 → 결재 요청이 오면 버튼으로 승인\n"
        "▫️ <b>브리핑</b> : 지금 바로 비서 브리핑 받기\n"
        "▫️ <b>현황</b> : 결재 대기·진행 중인 안건 보기\n"
        "▫️ <b>/가격표</b> : 최근 팬딩 가격표·주문 상태 · <b>/배수</b> 6 : 배수 변경 · <b>/자동</b> : 자동주문 켜기/끄기\n"
        "▫️ 큰 기능 추가나 매매 로직 변경은 Claude에게 요청하면 시뮬레이션까지 해서 결재함에 올려 드립니다.")


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_like(p, data, mode=0o600):
    """원래 파일의 소유자를 그대로 유지하며 원자적으로 저장 (웹 서버가 계속 읽고 쓸 수 있게)"""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        st = p.stat(); uid, gid = st.st_uid, st.st_gid
    except FileNotFoundError:
        st = p.parent.stat(); uid, gid = st.st_uid, st.st_gid
    fd, tmp = tempfile.mkstemp(dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush(); os.fsync(f.fileno())
        try:
            os.chown(tmp, uid, gid)
        except PermissionError:
            pass
        os.chmod(tmp, mode)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class TG:
    def __init__(self):
        cfg = load(TELEGRAM_CFG, {})
        self.token, self.chat = cfg.get("token"), str(cfg.get("chat_id", ""))

    def call(self, method, payload, timeout=15):
        req = urllib.request.Request(f"{TELEGRAM_API}/bot{self.token}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def send(self, text, rows=None, reply_to=None):
        p = {"chat_id": self.chat, "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
        if rows:
            p["reply_markup"] = {"inline_keyboard": rows}
        if reply_to:
            p["reply_to_message_id"] = reply_to
        try:
            return self.call("sendMessage", p).get("result", {})
        except Exception as e:
            print("send 실패:", e, flush=True); return {}

    def buttons(self, msg_id, rows):
        try:
            self.call("editMessageReplyMarkup", {"chat_id": self.chat, "message_id": msg_id,
                                                 "reply_markup": {"inline_keyboard": rows or []}})
        except Exception as e:
            print("버튼 변경 실패:", e, flush=True)

    def answer(self, cb_id, text=""):
        try:
            self.call("answerCallbackQuery", {"callback_query_id": cb_id, "text": text[:180]})
        except Exception:
            pass

    def document(self, name, data, caption=""):
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (("chat_id", self.chat), ("caption", caption[:900])):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{name}"\r\n'
                     f'Content-Type: text/plain; charset=utf-8\r\n\r\n'.encode() + data + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        req = urllib.request.Request(f"{TELEGRAM_API}/bot{self.token}/sendDocument", data=b"".join(parts), method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            print("파일 전송 실패:", e, flush=True)


def kick(unit):
    try:
        subprocess.run([SYSTEMCTL, "start", "--no-block", unit], capture_output=True, timeout=10)
    except Exception:
        pass


# ---------------------------------------------------------- 요청 접수
def detect(text):
    hits = [u for u, _, rx in BOTS if re.search(rx, text, re.I)]
    if len(hits) > 1 and "toss_dca.service" in hits and "toss_sniper.service" in hits:
        hits = [h for h in hits if h != "toss_dca.service"] if re.search(r"스나이퍼|soxs", text, re.I) else hits
    return hits[0] if len(hits) == 1 else None


def bot_rows(pid):
    return [[{"text": n, "callback_data": f"rb:{pid}:{i}"} for i, (_, n, _) in enumerate(BOTS[:2])],
            [{"text": n, "callback_data": f"rb:{pid}:{i + 2}"} for i, (_, n, _) in enumerate(BOTS[2:])],
            [{"text": "❌ 취소", "callback_data": f"cx:{pid}"}]]


def confirm_rows(pid):
    return [[{"text": "✅ 이대로 요청", "callback_data": f"rq:{pid}"}, {"text": "🔁 다른 봇", "callback_data": f"ch:{pid}"}],
            [{"text": "❌ 취소", "callback_data": f"cx:{pid}"}]]


def submit_request(unit, text):
    data = load(REQUESTS, {})
    items = data.get("items", []) if isinstance(data, dict) else []
    first = text.strip().splitlines()[0]
    title = (first[:60] + ("…" if len(first) > 60 else "")) if len(first) >= 2 else "텔레그램 요청"
    items.append({"id": uuid.uuid4().hex, "action": "request", "case": "", "at": datetime.now(timezone.utc).isoformat(),
                  "unit": unit, "file": "auto", "title": title, "body": text.strip()[:1500], "via": "telegram"})
    save_like(REQUESTS, {"items": items[-50:]})
    kick("bot-office-pipeline.service")
    return title


# ---------------------------------------------------------- 결재
def digest(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def find_package(key):
    if not re.fullmatch(r"[0-9a-f-]{8,36}", key or ""):
        return None
    p = DEPLOY_PUBLIC / f"{key}.json"
    if p.exists():
        return load(p, None)
    return None


def trading_warning(unit):
    k, e = datetime.now(KST), datetime.now(EST)
    hm_k, hm_e, wk_k, wk_e = k.strftime("%H:%M"), e.strftime("%H:%M"), k.weekday() < 5, e.weekday() < 5
    if unit == "toss_sniper.service" and wk_e and ("04:00" <= hm_e <= "09:30" or "15:55" <= hm_e <= "16:05"):
        return "⚠️ 지금은 스나이퍼 매매 시간(프리장/장마감 청산)입니다. 재시작 중 몇 초간 감시가 멈춥니다."
    if unit == "toss_dca.service" and ((wk_k and "11:00" <= hm_k <= "15:00") or (wk_e and "11:30" <= hm_e <= "15:50")):
        return "⚠️ 지금은 3번 봇 정기 매매 시간입니다."
    if unit == "bithumb_bot.service" and "19:00" <= hm_k <= "19:15":
        return "⚠️ 지금은 4번 빗썸 19:00 정기 매수 시간입니다."
    if unit == "han4384tubot.service" and wk_e and "04:00" <= hm_e <= "20:00":
        return "⚠️ 지금은 미국 주식 거래 시간대입니다. 1번 봇 주문 처리 중일 수 있습니다."
    return ""


def decide(dep, approve):
    m = find_package(dep)
    if not m:
        return False, "변경안을 찾지 못했습니다"
    records = load(APPROVALS, {})
    if dep in records:
        return False, f"이미 처리된 결재입니다 ({records[dep].get('decision')})"
    records[dep] = {"id": dep, "review_hash": digest(m), "decision": "승인" if approve else "반려",
                    "at": datetime.now(timezone.utc).isoformat(), "execution_authorized": bool(approve),
                    "execution": "처리 대기" if approve else "실행 제외", "via": "telegram"}
    save_like(APPROVALS, records)
    if approve:
        kick("bot-office-deploy.service")
    kick("bot-office-pipeline.service")
    return True, m


# ---------------------------------------------------------- 현황
def status_text():
    st = load(PIPE_PUBLIC, {})
    cases = st.get("cases") or []
    by = {}
    for c in cases:
        by.setdefault(c.get("stage"), []).append(c)
    lines = ["📋 <b>사무실 현황</b>"]
    for stg, label in (("awaiting_approval", "📝 결재 대기"), ("drafting", "✍️ 수정안 작성 중"), ("found", "🔎 접수·대기"),
                       ("applied", "⏫ 적용 완료·업로드 대기"), ("draft_failed", "⚠️ 수정안 실패"), ("verify_failed", "⚠️ 검증 탈락"),
                       ("apply_failed", "🚨 적용 실패"), ("push_failed", "🚨 업로드 실패")):
        for c in by.get(stg, [])[:5]:
            lines.append(f"{label} · {html.escape(c.get('bot', ''))} · {html.escape(str(c.get('title', ''))[:50])}")
    if len(lines) == 1:
        lines.append("▫️ 진행 중인 안건 없음 ✅")
    g = st.get("gemini") or {}
    lines.append(f"\n▫️ 오늘 Gemini 사용 {g.get('used', 0)}/{g.get('limit', '-')}회")
    return "\n".join(lines)


# ---------------------------------------------------------- 메인 루프
def handle_message(tg, st, msg):
    text = (msg.get("text") or "").strip()
    if not text:
        return
    if text.split()[0] in ("/제미나이잔액", "/제미나이단가"):
        import gemini_usage
        if gemini_usage.handle(tg, text):
            return
    if fanding_trade and fanding_trade.secretary_message(tg, text):
        return
    low = text.lower()
    if low in ("/start", "/help", "도움말", "help", "?"):
        tg.send(HELP); return
    if low in ("/brief", "브리핑", "/briefing"):
        tg.send("🗞 브리핑을 준비하고 있어요…")
        subprocess.Popen([sys.executable, BRIEFING], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); return
    if low in ("/status", "현황", "상태"):
        tg.send(status_text()); return
    if text.startswith("/"):
        tg.send("모르는 명령이에요. <b>도움말</b>을 보내 보세요."); return
    if len(text) < 5:
        tg.send("고칠 내용을 조금 더 자세히 적어 주세요. 예) <i>4번 봇 잔액 부족 알림을 1시간에 한 번만 보내줘</i>"); return
    pid = uuid.uuid4().hex[:10]
    unit = detect(text)
    st.setdefault("pending", {})[pid] = {"text": text[:1500], "unit": unit, "at": time.time()}
    if unit:
        tg.send(f"📥 <b>수정 요청으로 접수할까요?</b>\n▫️ 대상: <b>{NAME[unit]}</b>\n▫️ 내용: {html.escape(text[:300])}\n\n"
                "고칠 파일은 사무실이 스스로 찾아요.", confirm_rows(pid), reply_to=msg.get("message_id"))
    else:
        tg.send(f"📥 <b>어느 봇을 고칠까요?</b>\n▫️ 내용: {html.escape(text[:300])}", bot_rows(pid), reply_to=msg.get("message_id"))


def handle_callback(tg, st, cb):
    data, cb_id = cb.get("data", ""), cb.get("id")
    msg_id = (cb.get("message") or {}).get("message_id")
    if data.startswith("fd:"):
        if fanding_trade:
            fanding_trade.secretary_callback(tg, cb)
        else:
            tg.answer(cb_id, "팬딩 모듈이 꺼져 있어요")
        return
    kind, _, rest = data.partition(":")
    pend = st.setdefault("pending", {})
    if kind in ("rb", "ch", "rq", "cx"):
        pid, _, idx = rest.partition(":")
        p = pend.get(pid)
        if not p:
            tg.answer(cb_id, "오래된 요청이에요. 다시 보내 주세요."); tg.buttons(msg_id, []); return
        if kind == "cx":
            pend.pop(pid, None); tg.answer(cb_id, "취소했어요"); tg.buttons(msg_id, []); return
        if kind == "ch":
            tg.answer(cb_id); tg.buttons(msg_id, bot_rows(pid)); return
        if kind == "rb":
            try:
                p["unit"] = BOTS[int(idx)][0]
            except (ValueError, IndexError):
                tg.answer(cb_id); return
            tg.answer(cb_id, NAME[p["unit"]])
            tg.buttons(msg_id, [])
            tg.send(f"📥 <b>{NAME[p['unit']]}</b> 수정 요청으로 접수할까요?\n▫️ 내용: {html.escape(p['text'][:300])}", confirm_rows(pid))
            return
        if kind == "rq":
            if not p.get("unit"):
                tg.answer(cb_id); tg.buttons(msg_id, bot_rows(pid)); return
            title = submit_request(p["unit"], p["text"])
            pend.pop(pid, None)
            tg.answer(cb_id, "접수했어요")
            tg.buttons(msg_id, [])
            tg.send(f"✅ <b>접수 완료</b> · {NAME[p['unit']]}\n▫️ 안건: {html.escape(title)}\n"
                    "▫️ 사무실이 고칠 파일을 찾아 수정안을 만들고 있어요. 보통 2~6분 뒤 결재 요청이 옵니다.")
            return
    if kind in ("ap", "apy", "keep", "rj", "df"):
        dep = rest
        m = find_package(dep)
        if not m:
            tg.answer(cb_id, "변경안을 찾지 못했어요"); return
        unit = m.get("unit", "")
        if kind == "df":
            tg.answer(cb_id, "바뀐 코드를 보내요")
            diff = m.get("diff", "") or "(차이 없음)"
            if len(diff) <= 3300:
                tg.send(f"🔍 <b>{html.escape(NAME.get(unit, unit))} · {html.escape(m.get('file', ''))}</b>\n<pre>{html.escape(diff)}</pre>")
            else:
                tg.document(f"change_{dep[:8]}.diff.txt", diff.encode(),
                            f"{NAME.get(unit, unit)} · {m.get('file', '')} 바뀐 코드 (- 지운 줄 / + 새 줄)")
            return
        if kind == "ap":
            tg.answer(cb_id)
            warn = trading_warning(unit)
            tg.buttons(msg_id, [[{"text": "⚠️ 네, 적용합니다", "callback_data": f"apy:{dep}"},
                                 {"text": "↩️ 취소", "callback_data": f"keep:{dep}"}]])
            tg.send(f"정말 승인할까요? <b>{html.escape(NAME.get(unit, unit))}</b> 봇이 잠깐 재시작됩니다.\n"
                    + (f"{warn}\n" if warn else "") + "위 메시지의 <b>⚠️ 네, 적용합니다</b>를 누르면 진행돼요.")
            return
        if kind == "keep":
            tg.answer(cb_id, "취소했어요")
            tg.buttons(msg_id, [[{"text": "✅ 승인", "callback_data": f"ap:{dep}"}, {"text": "❌ 반려", "callback_data": f"rj:{dep}"}],
                                [{"text": "🔍 바뀐 코드 보기", "callback_data": f"df:{dep}"}]])
            return
        ok, res = decide(dep, kind == "apy")
        tg.answer(cb_id, "처리했어요" if ok else str(res))
        tg.buttons(msg_id, [])
        if ok:
            if kind == "apy":
                tg.send(f"✅ <b>승인 완료</b> · {html.escape(NAME.get(unit, unit))} · {html.escape(m.get('file', ''))}\n"
                        "▫️ 적용 → 재시작 확인 → GitHub 업로드가 자동으로 진행됩니다. 끝나면 다시 알려 드릴게요.")
            else:
                tg.send(f"❌ <b>반려 완료</b> · {html.escape(NAME.get(unit, unit))} · 봇과 GitHub 모두 그대로입니다.")
        else:
            tg.send(f"ℹ️ {html.escape(str(res))}")


def main():
    tg = TG()
    if not tg.token or not tg.chat:
        print("사무실 비서 텔레그램 설정 없음 (/etc/bot-office/telegram.json)", flush=True)
        time.sleep(300); return
    st = load(STATE, {})
    offset = st.get("offset")
    print("사무실 비서 대화 담당 시작", flush=True)
    while True:
        try:
            q = {"timeout": 30, "allowed_updates": json.dumps(["message", "callback_query"])}
            if offset:
                q["offset"] = offset
            url = f"{TELEGRAM_API}/bot{tg.token}/getUpdates?" + urllib.parse.urlencode(q)
            with urllib.request.urlopen(url, timeout=40) as r:
                res = json.load(r)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    if "message" in upd:
                        m = upd["message"]
                        if str((m.get("chat") or {}).get("id")) == tg.chat:
                            handle_message(tg, st, m)
                    elif "callback_query" in upd:
                        cb = upd["callback_query"]
                        if str(((cb.get("message") or {}).get("chat") or {}).get("id")) == tg.chat:
                            handle_callback(tg, st, cb)
                except Exception as e:
                    print("처리 오류:", type(e).__name__, e, flush=True)
            cutoff = time.time() - 86400
            st["pending"] = {k: v for k, v in st.get("pending", {}).items() if v.get("at", 0) > cutoff}
            st["offset"] = offset
            save_like(STATE, st)
        except Exception as e:
            print("텔레그램 연결 오류:", type(e).__name__, e, flush=True)
            time.sleep(5)
        if os.environ.get("OFFICE_SECRETARY_ONCE"):
            return


if __name__ == "__main__":
    main()
