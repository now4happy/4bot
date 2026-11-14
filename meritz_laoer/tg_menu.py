# ==========================================================
# FILE: meritz_laoer/tg_menu.py   (MERITZ_LAOER v1.0.3 — 새 파일)
# 메리츠 무매 SOXL 텔레그램 메뉴: 📈 상황판 · ☰ 메뉴 · 🛠 도구 (맨밑 키보드만, 인라인 버튼 없음)
# v1.0.4 (2026-11-14): 봇 번호 정리 — 표시 이름 '메리츠 무매 SOXL' → '7번 메리츠 무매' (머리글·도움말·상황판)
# v1.0.3 (2026-11-14): 첫 버전.
#   - 토큰: 설정 telegram_file (notifier.py 와 같은 파일, 새 토큰 없음). 토큰 원문은 어디에도 출력·기록하지 않음 (지문 token_fp 만)
#   - check_identity() 가 '텔레그램 토큰이 다른 봇과 같음' 이면 폴링하지 않음 (forbid_telegram_files 검사 그대로)
#   - 등록된 chat_id 가 아닌 방의 글자·버튼은 조용히 무시 (알림 없음)
#   - 직렬화: main.idle() 안에서만 돎 = loop() 와 같은 스레드에서 순서대로. 별도 스레드·프로세스 없음.
#     장부·설정 쓰기는 기존 함수(cmd_add_shares → ConfigManager.add_shares, cmd_inject_start → inject_start,
#     clear_halt)만 부르며, 기존 GlobalThrottle.get_file_lock() 잠금을 그대로 씀
#   - 메뉴 동작은 기존 함수만 부름: cmd_check · build_plan+fit_orders+fmt_orders+plan_head · t_and_target ·
#     cmd_add_shares · ConfigManager.clear_halt · cmd_inject_start(= --inject-start) · key_fingerprint
#   - 처음 시작 때 쌓여 있던 예전 업데이트는 건너뜀 (재시작으로 옛 버튼이 다시 실행되지 않게) · 2분 넘은 메시지 무시
# ==========================================================
import contextlib
import io
import json
import logging
import os
import time
import urllib.request

from global_throttle import GlobalThrottle
from notifier import Notifier

CHART, MENU_OPEN = "📈 상황판", "☰ 메뉴"
MAIN_ROWS = [[CHART, MENU_OPEN]]
MENU_ROWS = [["📋 오늘 계획", "📒 장부·체결 내역"], ["💰 자금", "⚙️ 전원·모드"], ["🛠 도구", "❓ 도움말"], ["🏠 처음 화면"]]
T_CHECK, T_ADD, T_HALT, T_INJECT, T_FP, BACK = "🔍 점검", "➕ 직접 산 주식 반영", "⛔ 정지 해제", "📥 장부 시작", "🔑 키 지문 확인", "🔙 메뉴"
HALT_OK, INJECT_OK, INJECT_OVER = "⛔ 정지 해제 확인", "📥 장부 시작 확인", "📥 장부 덮어쓰기 확인 (--overwrite)"
CONFIRM_SEC = 60            # 제안값: 확인 버튼 유효 시간
WAIT_SEC = 300              # 제안값: 수량·평단 입력 기다림
MSG_MAX_AGE = 120           # 이보다 오래된 메시지는 처리하지 않음
HEAD = "🟦7번 메리츠 무매"

HELP = "\n".join([
    "❓ [도움말 · 7번 메리츠 무매]",
    "▫️ 맨밑 첫 줄: 📈 상황판 · ☰ 메뉴",
    "▫️ ☰ 메뉴: 📋 오늘 계획 · 📒 장부·체결 내역 · 💰 자금 · ⚙️ 전원·모드 · 🛠 도구 · ❓ 도움말 · 🏠 처음 화면",
    "▫️ 🛠 도구: 🔍 점검(--check) · ➕ 직접 산 주식 반영(--add-shares) · ⛔ 정지 해제(--clear-halt) · "
    "📥 장부 시작(--inject-start, 장부 시작 전에만) · 🔑 키 지문 확인(--fingerprint) · 🔙 메뉴",
    "▫️ 모두 조회·장부 반영만 하고 주문은 내지 않아요. 환전 기능은 없어요.",
    "▫️ enabled·dry_run 은 메뉴에서 바꾸지 않아요 (설정 파일·기존 안전 절차 그대로).",
])


def kb(rows):
    return {"keyboard": [[{"text": t} for t in r] for r in rows], "resize_keyboard": True, "is_persistent": True}


class MenuBot:
    def __init__(self, ops):
        self.o = ops                 # meritz_laoer/main.py 모듈 (기존 함수를 그대로 부름)
        self.offset = None
        self.primed = False
        self.wait = None             # {"kind": "add", "ts"}
        self.confirm = {}            # 확인 버튼 글자 → 누를 수 있는 마지막 시각
        self._cred = (0.0, None)     # (확인 시각, (토큰, chat_id) 또는 None) — 60초마다 다시 확인

    # ---------------------------------------------------------- 텔레그램
    def creds(self, s):
        """notifier 와 같은 telegram_file. check_identity 가 '다른 봇 토큰과 같음'이면 None (폴링 안 함)"""
        now = time.time()
        if now - self._cred[0] > 60:
            c = None
            n = Notifier(s.get("telegram_file") or "")
            if n.ok and not any("텔레그램 토큰이 다른 봇과 같음" in b for b in self.o.check_identity(s)[0]):
                c = (n.token, n.chat_id)
            self._cred = (now, c)
        return self._cred[1]

    def _call(self, tok, method, payload, timeout):
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def send(self, c, text, rows=None, dry=True):
        tok, chat = c
        msg = (("🧪[모의] " if dry else "") + HEAD + "\n" + str(text)).replace(tok, "***")[:3900]
        try:
            self._call(tok, "sendMessage", {"chat_id": chat, "text": msg, "reply_markup": kb(rows or MAIN_ROWS)}, 15)
        except Exception as e:
            logging.warning(f"텔레그램 메뉴 전송 실패: {type(e).__name__}")

    def idle(self, s, t_end):
        """t_end 까지 getUpdates → 받은 것을 순서대로 처리 (이 스레드에서만)"""
        c = self.creds(s)
        if not c:
            return
        tok, chat = c
        if not self.primed:          # 쌓인 옛 업데이트 건너뜀
            r = self._call(tok, "getUpdates", {"offset": -1, "timeout": 0}, 10)
            res = r.get("result") or []
            self.offset = (res[-1]["update_id"] + 1) if res else None
            self.primed = True
        while True:
            left = t_end - time.time()
            if left < 1:
                return
            q = {"timeout": int(min(25, max(0, left - 1))), "allowed_updates": ["message"]}
            if self.offset is not None:
                q["offset"] = self.offset
            r = self._call(tok, "getUpdates", q, q["timeout"] + 10)
            for upd in r.get("result") or []:
                self.offset = upd["update_id"] + 1
                m = upd.get("message")
                if not isinstance(m, dict):
                    continue
                if str((m.get("chat") or {}).get("id", "")).strip() != str(chat):
                    continue          # 다른 방: 조용히 무시
                if time.time() - float(m.get("date") or 0) > MSG_MAX_AGE:
                    continue
                try:
                    self.handle(s, c, (m.get("text") or "").strip())
                except Exception as e:
                    logging.warning(f"텔레그램 메뉴 처리 실패: {type(e).__name__}")
                    self.send(c, f"⚠️ 처리 오류: {type(e).__name__}", dry=s.get("dry_run", True))

    # ---------------------------------------------------------- 기존 함수 부르기
    def _out(self, fn, *a, **k):
        """기존 CLI 함수(print 출력)를 그대로 부르고 출력만 받아 옴 → (반환값, 출력 글자)"""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fn(*a, **k)
        return rc, buf.getvalue().strip()

    def _api(self, s):
        o = self.o
        return o.MeritzApi(s["key_file"], os.path.join(s["state_dir"], "data", "meritz_token.json"))

    def _local(self, s):
        o = self.o
        os.makedirs(os.path.join(s["state_dir"], "data"), exist_ok=True)
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            pos, halt = cfg.get_position(), cfg.get_halt()
            avg = cfg.avg_price(pos) if pos else 0.0
            tv, tgt = o.t_and_target(s, cfg, pos) if pos else (None, None)
        return pos, halt, avg, tv, tgt

    def _api_ok(self, s):
        """cmd_check 와 같은 조건: 설정 문제·키 파일 없음·키 형식 오류면 메리츠 조회 안 함 → 문제 목록"""
        bad = self.o.validate_settings(s)
        idb, _ = self.o.check_identity(s)
        return bad + [b for b in idb if b in ("새 메리츠 키 파일 없음 (key_file)", "키 파일 형식 오류 (app_key/app_secret)")]

    def board(self, s):
        """B1 상황판 값 (조회만 — 주문·장부·설정을 바꾸지 않음). cmd_check 와 같은 입력으로 오늘 계획 미리보기"""
        o = self.o
        d = {"pos": None, "halt": None, "avg": 0.0, "t": None, "target": None, "api_bad": [], "hold": None, "sellable": None,
             "price": None, "prev": None, "ma5": None, "cash": None, "plan": None, "orders": [], "notes": [], "plan_err": None}
        d["pos"], d["halt"], d["avg"], d["t"], d["target"] = self._local(s)
        d["api_bad"] = self._api_ok(s)
        if d["api_bad"]:
            return d
        api = self._api(s)
        d["hold"], d["sellable"], _ = api.holding(s["symbol"])
        d["price"], d["prev"], d["ma5"] = o.market_inputs(s, api)
        d["cash"] = api.usd_cash()
        try:
            pos, st = d["pos"], s["start"]
            q = int(pos["qty"]) if pos else int(float(st["qty"]))
            principal = float(pos["principal"]) if pos else float(st["principal_usd"])
            avg = round(principal / q, 4) if q else 0.0
            with o.in_dir(o.sandbox_dir(s["state_dir"])):
                d["plan"] = o.build_plan(s, o.ConfigManager(s), d["prev"], d["ma5"], d["cash"], q, avg, snapshot=True)
            d["orders"], d["notes"] = o.fit_orders(d["plan"], d["cash"], d["sellable"], q)
        except Exception as e:
            d["plan_err"] = type(e).__name__
        return d

    def plan_lines(self, s, d):
        if d["api_bad"]:
            return ["📋 오늘 계획: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")"]
        if d["plan"] is None:
            return [f"📋 오늘 계획: 미확인 ({d['plan_err']})"]
        return ["📋 오늘 계획 (미리보기 · 주문 안 냄)", self.o.plan_head(d["plan"], s), self.o.fmt_orders(d["orders"])] + \
               ["ℹ️ " + n for n in d["notes"]]

    def mode_line(self, s, halt):
        return (f"▫️ 모드: enabled={s.get('enabled')} · dry_run={s.get('dry_run')}\n"
                f"▫️ 정지 표시: {(halt or {}).get('reason') if halt else '없음'}")

    def board_text(self, s):
        d = self.board(s)
        pos = d["pos"]
        lines = [f"📈 [7번 메리츠 무매 상황판 ({self.o.BOT_VERSION})]", self.mode_line(s, d["halt"])]
        if pos:
            lines.append(f"▫️ 장부: {pos['qty']}주 · 평단 ${d['avg']:.4f} · T {d['t']:.2f} · 목표 ${d['target']:.2f}")
        else:
            lines.append("▫️ 장부: 시작 전 (🛠 도구 → 📥 장부 시작)")
        if d["api_bad"]:
            lines.append("▫️ 메리츠 조회: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")")
        else:
            lq = int(pos["qty"]) if pos else None
            lines.append(f"▫️ 메리츠 잔고: {d['hold']}주 (매도가능 {d['sellable']}) · 장부 {lq if lq is not None else '시작 전'}주"
                         + (" · ⚠️ 잔고 ≠ 장부" if lq is not None and d["hold"] != lq else ""))
            lines.append(f"▫️ 현재가 ${d['price']:.2f} · 전일종가 ${d['prev']:.2f} · 5일선 ${d['ma5']:.2f}")
            lines.append(f"▫️ USD 예수금 ${d['cash']:,.2f}")
        lines.append("─────────────────")
        lines += self.plan_lines(s, d)
        return "\n".join(lines)

    def ledger_text(self, s):
        o = self.o
        pos, halt, avg, _, _ = self._local(s)
        lines = ["📒 [장부 · 체결 내역 — 조회만]"]
        lines.append(f"▫️ 장부: {pos['qty']}주 · 원금 ${float(pos['principal']):,.2f} · 평단 ${avg:.4f}" if pos else "▫️ 장부: 시작 전")
        lines.append(f"▫️ 정지 표시: {halt.get('reason') if halt else '없음'}")
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            hist = cfg._load_json("data/add_shares_log.json", None)
            d = o.now_et().strftime("%Y-%m-%d")
            marks = [(n, cfg._load_json(f"data/{n}_{d}.json", None)) for n in ("orders", "dry_orders")]
        if isinstance(hist, list) and hist:
            h = hist[-1]
            lines.append(f"▫️ 직접 산 주식 반영 기록: {len(hist)}건 · 최근 {str(h.get('at', ''))[:16]} {h.get('qty')}주 @ ${float(h.get('avg') or 0):.4f}"
                         f" ({(h.get('before') or {}).get('qty')}→{(h.get('after') or {}).get('qty')}주)")
        else:
            lines.append("▫️ 직접 산 주식 반영 기록: 없음")
        for n, m in marks:
            name = f"{n}_{d}.json"
            if m is None:
                lines.append(f"▫️ 오늘 주문 기록 {name}: 없음")
            elif m.get("skipped"):
                lines.append(f"▫️ 오늘 주문 기록 {name}: 주문 안 함 — {str(m.get('skipped'))[:160]}")
            else:
                lines.append(f"▫️ 오늘 주문 기록 {name}: 주문 {len(m.get('orders') or [])}건 · 오류 {len(m.get('errors') or [])}건 · "
                             f"체결 반영 {'됨' if m.get('synced') else '전'}")
                lines += ["   " + x for x in self.o.fmt_orders(m.get("orders") or []).split("\n")]
        return "\n".join(lines)

    def funds_text(self, s):
        d = self.board(s)
        lines = ["💰 [자금 — 조회만 · 이 봇에는 환전 기능이 없어요]"]
        if d["api_bad"]:
            return "\n".join(lines + ["▫️ 메리츠 조회: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")"])
        buy = sum(int(x["qty"]) * float(x["price"]) for x in d["orders"] if x.get("side") == "BUY" and x.get("type") != "MOC")
        lq = int(d["pos"]["qty"]) if d["pos"] else None
        lines += [f"▫️ USD 예수금 ${d['cash']:,.2f}",
                  (f"▫️ 오늘 계획 필요액 ${buy:,.2f} (fit_orders 로 정리한 매수 주문 합계 · MOC 제외 — fit_orders 와 같은 계산)"
                   if d["plan"] is not None else f"▫️ 오늘 계획 필요액: 미확인 ({d['plan_err']})"),
                  f"▫️ 보유 주수: 메리츠 {d['hold']}주 · 장부 {lq if lq is not None else '시작 전'}"
                  + (" · ⚠️ 잔고 ≠ 장부" if lq is not None and d["hold"] != lq else "")]
        return "\n".join(lines)

    def power_text(self, s):
        idb, fp = self.o.check_identity(s)
        exp = str(s.get("expected_key_fp") or "").strip()
        _, halt, _, _, _ = self._local(s)
        fp_txt = ("없음" if not fp else "있음 · " + ("기대값과 일치" if exp and fp == exp else ("기대값 없음" if not exp else "기대값과 다름")))
        return "\n".join(["⚙️ [전원 · 모드 — 표시만]",
                          f"▫️ enabled={s.get('enabled')} · dry_run={s.get('dry_run')}",
                          f"▫️ transfer_confirmed={s.get('transfer_confirmed')} · toss_sniper_stopped_confirmed={s.get('toss_sniper_stopped_confirmed')}",
                          f"▫️ 키 지문: {fp_txt}",
                          f"▫️ 정지 표시: {halt.get('reason') if halt else '없음'}",
                          "▫️ enabled·dry_run 은 메뉴에서 바꾸지 않아요 (설정 파일·기존 안전 절차 그대로)."])

    def tools_rows(self, s):
        pos = self._local(s)[0]
        return [[T_CHECK, T_ADD], [T_HALT] + ([] if pos else [T_INJECT]), [T_FP, BACK]]

    # ---------------------------------------------------------- 글자 처리
    def _ok_confirm(self, label):
        until = self.confirm.pop(label, 0)
        return time.time() <= until

    def handle(self, s, c, text):
        if not text:
            return
        dry = s.get("dry_run", True)
        say = lambda t, rows=None: self.send(c, t, rows, dry)
        fixed = {CHART, MENU_OPEN, *sum(MENU_ROWS, []), T_CHECK, T_ADD, T_HALT, T_INJECT, T_FP, BACK, HALT_OK, INJECT_OK, INJECT_OVER}
        if self.wait and text not in fixed:
            w, self.wait = self.wait, None
            if time.time() - w["ts"] > WAIT_SEC:
                return say("⏱ 입력 시간이 지났어요. 🛠 도구 → ➕ 직접 산 주식 반영을 다시 눌러 주세요.")
            parts = text.replace(",", " ").split()
            qty = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else None
            try:
                avg = float(parts[1]) if len(parts) >= 2 else None
            except ValueError:
                avg = None
            rc, out = self._out(self.o.cmd_add_shares, s, qty, avg)
            return say(("✅ " if rc == 0 else "") + (out or "결과 없음"))
        if text in fixed:
            self.wait = None
        if text == CHART:
            return say(self.board_text(s))
        if text == "🏠 처음 화면":
            return say("🏠 처음 화면 · 아래 버튼을 눌러 주세요")
        if text in (MENU_OPEN, BACK):
            return say("☰ 메뉴 · 아래 버튼을 눌러 주세요", MENU_ROWS)
        if text == "📋 오늘 계획":
            d = self.board(s)
            return say("\n".join(self.plan_lines(s, d)))
        if text == "📒 장부·체결 내역":
            return say(self.ledger_text(s))
        if text == "💰 자금":
            return say(self.funds_text(s))
        if text == "⚙️ 전원·모드":
            return say(self.power_text(s))
        if text == "🛠 도구":
            return say("🛠 도구 · 가끔 쓰는 기능이에요 (주문 없음)", self.tools_rows(s))
        if text == "❓ 도움말":
            return say(HELP)
        if text == T_CHECK:
            _, out = self._out(self.o.cmd_check, s)
            return say(out or "점검 결과 없음")
        if text == T_ADD:
            self.wait = {"kind": "add", "ts": time.time()}
            return say("➕ 직접 산 주식 수량과 평단(달러)을 띄어 써서 보내 주세요. 예: 3 52.10\n"
                       "• 메리츠 잔고 == 장부 + 수량 일 때만 반영 · enabled=true·미국장 주문 시간(미 동부 "
                       f"{s.get('order_time_et')}~{s.get('order_deadline_et')})이면 거부 · 주문 없음", [[BACK]])
        if text == T_HALT:
            halt = self._local(s)[1]
            if not halt:
                return say("⛔ 정지 표시가 없어요. 해제할 것이 없습니다.", self.tools_rows(s))
            self.confirm[HALT_OK] = time.time() + CONFIRM_SEC
            return say(f"⛔ 정지 표시: {halt.get('reason')}\n원인을 확인한 뒤에 쓰는 기능이에요 (--clear-halt 와 같음).\n"
                       f"확인했으면 {CONFIRM_SEC}초 안에 [{HALT_OK}] 를 눌러 주세요.", [[HALT_OK, BACK]])
        if text == HALT_OK:
            if not self._ok_confirm(HALT_OK):
                return say("⏱ 확인 시간이 지났어요. ⛔ 정지 해제를 다시 눌러 주세요.", self.tools_rows(s))
            with self.o.in_dir(s["state_dir"]):
                cfg = self.o.ConfigManager(s)
                with GlobalThrottle.get_file_lock(cfg.FILES["HALT"]):
                    cfg.clear_halt()
            return say("정지 표시 해제", self.tools_rows(s))
        if text == T_INJECT:
            pos = self._local(s)[0]
            label = INJECT_OVER if pos else INJECT_OK
            self.confirm[label] = time.time() + CONFIRM_SEC
            if pos:
                return say(f"📥 이미 장부가 있어요 ({pos['qty']}주). 덮어쓰려면 --overwrite 와 같은 확인이 필요해요.\n"
                           f"{CONFIRM_SEC}초 안에 [{INJECT_OVER}] 를 누르면 같은 검사(설정·키·입고 확인·잔고 == 시작 수량) 뒤 덮어써요.",
                           [[INJECT_OVER, BACK]])
            return say("📥 장부 시작 (--inject-start 와 같음): 설정·키 점검 · transfer_confirmed · 메리츠 잔고 == 시작 수량 일 때만.\n"
                       f"{CONFIRM_SEC}초 안에 [{INJECT_OK}] 를 눌러 주세요.", [[INJECT_OK, BACK]])
        if text in (INJECT_OK, INJECT_OVER):
            if not self._ok_confirm(text):
                return say("⏱ 확인 시간이 지났어요. 📥 장부 시작을 다시 눌러 주세요.", self.tools_rows(s))
            rc, out = self._out(self.o.cmd_inject_start, s, text == INJECT_OVER)
            return say(out or ("완료" if rc == 0 else "실패"), self.tools_rows(s))
        if text == T_FP:
            try:
                fp = self.o.key_fingerprint(s["key_file"])
            except Exception as e:
                return say(f"🔑 키 지문: 읽지 못함 ({type(e).__name__})", self.tools_rows(s))
            exp = str(s.get("expected_key_fp") or "").strip()
            return say(f"🔑 키 지문 (sha256 앞 12자리, 키 원문 아님): {fp}\n기대값(expected_key_fp): "
                       + ("일치" if exp and exp == fp else ("없음" if not exp else "다름")), self.tools_rows(s))
        return say("아래 버튼 메뉴로 써 주세요.")
