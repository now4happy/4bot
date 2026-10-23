#!/usr/bin/env python3
# =====================================================================
# FILE: averaging_merge.py   (💧 물타기 자동 합치기 도구 · 사용자 추가)
# 사용: python3 averaging_merge.py <스나이퍼 폴더> [--commit 원작커밋] [--check]
#
#  원작자 새 버전 파일을 폴더에 덮어쓴 뒤 이 도구를 돌리면,
#  원작 코드는 그대로 둔 채 '# [💧물타기 HOOK]' 몇 줄만 자동으로 끼워 넣어 averaging_plugin.py 를 연결합니다.
#   ① 원작 자동 업데이트(git reset --hard origin/main) 해제  ← 4bot 저장소 보호, 필수
#   ② 메인 루프: 손절 라인 / 추가 매수 연결
#   ③ 텔레그램: 💧 물타기 설정 화면 연결, 메뉴·제어반·/sync 에 물타기 줄 추가
#   ④ 물타기가 기대는 원작 기능(장부·주문·트레일링 함수 등)이 그대로인지 점검
#  하나라도 필수 항목이 안 맞으면 아무것도 확정하지 않고 '실패 사유'를 출력합니다 (종료 코드 2).
#  업데이트 비서(bot_office/sniper_upstream.py)가 이 도구를 자동으로 호출합니다.
# =====================================================================
import json
import os
import py_compile
import re
import sys

KEEP = ("averaging_plugin.py", "averaging_merge.py")
MARK = "[💧물타기 HOOK"
STUB_MSG = "자가 업데이트 해제: 직접 관리 모드입니다. (원작 업데이트는 업데이트 비서가 💧물타기를 붙여 staging 으로 올립니다)"

README_HEAD = """# 🔫 2번 토스 스나이퍼 + 💧 물타기

원작자(pipios4006-boop/pipiosToss_bot) 코드는 **그대로** 두고, 내 물타기(추가 매수)만 `averaging_plugin.py` 로 얹은 봇입니다.
원작 파일에는 `# [💧물타기 HOOK]` 표시가 붙은 몇 줄만 `averaging_merge.py` 가 자동으로 끼워 넣습니다.

## 💧 물타기 규칙
- 원작이 자동으로 산 포지션만 · RSI 35 회복 뒤 RSI≤30 재포착 + 직전 매수가 -N%(0.3~1.0, 기본 0.7) → 1회 추가 (1회 금액 = 통합 시드)
- 최대 1·2·3·5·7·10회(첫 매수 포함) · 원작 본진 매수 시간 안에서만
- 추가 매수 체결 → 전체 평단 기준으로 +5% 안전캡·+1% 트레일링 점화가 재장전 (익절·방어는 원작 그대로)
- 손절 라인(0=끄기, 1.0~5.0%): 추가 매수가 끝난 뒤 평단 -N% → 전량 매도, 그날 신규 진입 중지
- 텔레그램 `/avg` 또는 `/settlement` → 💧 물타기 설정 · 물타기 끄기 = 원작 그대로

## 🔄 원작 업데이트 받는 법 (자동)
1. 업데이트 비서(사무실 봇)가 하루 1번(아침 브리핑 직후 09:02 KST) 원작 저장소를 확인 → 새 버전이면 🔴[중요] 텔레그램 알림 (처리할 때까지 매일 다시 알림)
   (원작 제목·버전, 물타기 자동 합치기 가능 여부를 미리 점검해서 보여 줌) · 바로 확인: 비서에게 `원작 확인`
2. **🔀 물타기 합쳐서 올리기** → 백업 태그 2개 저장 → 원작 새 파일 + 물타기 HOOK 자동 적용 → GitHub staging
3. 평소처럼 **📦 새 수정 알림의 ✅ 업데이트** → 적용·재시작·버전 기록
4. 자동 합치기가 안 되는 경우(원작 구조가 크게 바뀜) → 알림의 실패 사유를 Claude 에게 보여 주고
   "averaging_merge.py / averaging_plugin.py 를 새 원작에 맞춰 줘" 라고 요청

## 🗄 백업 (GitHub 태그 · 자동)
- `backup/toss_sniper-날짜시각` : 원작 업데이트 직전의 내 봇 전체(이전 원작 + 물타기)
- `upstream/pipiosToss_bot-커밋` : 원작자 코드 원본 그대로
- `toss_sniper-v1.x.x` : 업데이트 비서가 적용할 때마다 남기는 버전
- 되돌리기: Claude 에게 "toss_sniper 를 태그 ○○ 로 되돌려 staging 에 올려 줘"

---

> 아래는 원작자의 공식 매뉴얼 원문입니다.

"""

R = {"ok": True, "applied": [], "warn": [], "fail": []}


def ok(msg):
    R["applied"].append(msg)
    print("✅", msg)


def warn(msg):
    R["warn"].append(msg)
    print("⚠️", msg)


def fail(msg):
    R["ok"] = False
    R["fail"].append(msg)
    print("⛔", msg)


def rd(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def wr(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)


# ---------------------------------------------------------------- 코드 조각 도구
def _indent(line):
    return len(line) - len(line.lstrip(" \t"))


def find_block(lines, pat):
    """pat 에 맞는 def 줄부터 그 함수가 끝나는 줄까지 (시작, 머리 끝, 끝) 목록"""
    out = []
    rx = re.compile(pat)
    for i, ln in enumerate(lines):
        if not rx.match(ln):
            continue
        ind = _indent(ln)
        j, depth = i, 0
        while j < len(lines):   # 함수 머리(여러 줄일 수 있음) 끝 찾기
            depth += lines[j].count("(") - lines[j].count(")")
            if depth <= 0 and lines[j].rstrip().endswith(":"):
                break
            j += 1
        k = j + 1
        while k < len(lines) and (not lines[k].strip() or _indent(lines[k]) > ind):
            k += 1
        while k - 1 > j and not lines[k - 1].strip():
            k -= 1
        out.append((i, j, k))
    return out


def stub_function(src, name, body):
    lines = src.split("\n")
    blocks = find_block(lines, rf"^\s*(async\s+)?def\s+{re.escape(name)}\s*\(")
    n = 0
    for i, j, k in reversed(blocks):
        if MARK in "\n".join(lines[i:k]):
            continue
        ind = " " * (_indent(lines[i]) + 4)
        new = [f"{ind}# {MARK} A] 원작 자동 업데이트 해제 (4bot 저장소 보호 · 원작 업데이트는 업데이트 비서가 처리)"]
        new += [ind + b for b in body]
        lines[j + 1:k] = new
        n += 1
    return "\n".join(lines), n


def add_import(src, line):
    if line in src:
        return src
    lines = src.split("\n")
    last, i, depth = -1, 0, 0
    while i < len(lines):
        ln = lines[i]
        if depth == 0 and re.match(r"^(def |async def |class |@|if __name__)", ln):
            break
        if depth == 0 and re.match(r"^(from \S+ import|import )", ln):
            depth = ln.count("(") - ln.count(")")
            while depth > 0 and i + 1 < len(lines):
                i += 1
                depth += lines[i].count("(") - lines[i].count(")")
            last = i
        i += 1
    lines.insert(last + 1, line)
    return "\n".join(lines)


def py_files(d):
    return sorted(f for f in os.listdir(d) if f.endswith(".py") and f not in KEEP)


def short_title(readme_first_line):
    t = re.sub(r"^#+\s*", "", readme_first_line or "").strip()
    ver = re.search(r"v\d+(?:\.\d+)*", t)
    name = re.split(r"\(|시스템|공식", t)[0]
    name = re.sub(r"[^\w\s가-힣·\-]", "", name).strip()
    name = re.sub(r"\s+", " ", name)
    return f"원작 {name} {ver.group(0) if ver else ''}".strip() if name else "원작 (제목 미확인)"


# ---------------------------------------------------------------- 단계별 작업
def step_disable_update(d, srcs):
    total = 0
    stubs = {
        "_run_git_update_sync": [f'return (False, "{STUB_MSG}")'],
        "_run_git_update": [f'return (False, "{STUB_MSG}")'],
        "auto_update_loop": ["return None"],
    }
    for f in srcs:
        s = srcs[f]
        for name, body in stubs.items():
            s, n = stub_function(s, name, body)
            total += n
        if f == "plugin_updater.py":
            s, n = stub_function(s, "main", [f'print("{STUB_MSG}")', "return"])
            total += n
        srcs[f] = s
    ok(f"원작 자동 업데이트 함수 {total}곳 해제") if total else warn("자동 업데이트 함수를 못 찾음 (원작이 이름을 바꿨을 수 있음 · 아래 남은 코드 검사로 확인)")
    left = []
    rx = re.compile(r"reset[\"',\s]+--hard|fetch[\"',\s]+origin[\"',\s]+main|[\"']git[\"',\s]+pull|git pull")
    for f, s in srcs.items():
        for no, ln in enumerate(s.split("\n"), 1):
            if rx.search(ln) and not ln.lstrip().startswith("#"):
                left.append(f"{f}:{no}")
    if left:
        fail("원작 자동 업데이트(git reset/pull) 코드가 남아 있음 → 4bot 저장소를 덮어쓸 위험: " + ", ".join(left[:6]))


def step_compat(srcs):
    allsrc = "\n".join(srcs.values())
    need = {
        "def manage_mechanical_profit_trap_plugin": "원작 익절(안전캡) 플러그인",
        "class AssassinLedger": "원작 장부",
        "class MacroDataCache": "원작 NQ 데이터",
        "def reset_all_ledgers": "장부 초기화 함수",
        "def get_cached_nq_data": "NQ 진폭 조회",
        "def get_symbol_holdings_detail": "잔고 조회 API",
        "def get_order_detail": "주문 조회 API",
        "def create_order": "주문 API",
        "def cancel_order": "취소 API",
        "def modify_order": "정정 API",
        "def get_orderbook": "호가 API",
        "def get_usd_buying_power": "주문가능금액 API",
        "def get_orders": "주문 목록 API",
        "\"PRE_SNIPER\"": "자동 진입 표식 PRE_SNIPER",
        "\"PRE_SNIPER_REARM\"": "자동 진입 표식 PRE_SNIPER_REARM",
    }
    miss = [v for k, v in need.items() if k not in allsrc]
    for k in ("_cancel_open_orders_and_wait_sellable", "get_trailing_runtime_status"):
        if not re.search(rf"def {k}\(", allsrc):
            miss.append(k)
    for k in ("TRAIL_ARM_PROFIT_RATE", "TRAIL_SAFETY_CAP_RATE"):
        if not re.search(rf"\b{k}\s*=", allsrc):
            warn(f"{k} 상수가 없음 → 물타기는 기본값(+1% / +5%)으로 계산")
    # 물타기 모듈이 찾는 파일(defense_plugin 등)에 실제로 있는지
    mods = ("defense_plugin.py", "defense_state_plugin.py", "sniper_plugin.py", "sniper_exit_plugin.py")
    for k in ("_cancel_open_orders_and_wait_sellable", "get_trailing_runtime_status"):
        if not any(re.search(rf"\b{k}\b", srcs.get(m, "")) for m in mods):
            miss.append(f"{k} 위치(defense/sniper 파일 밖으로 이동)")
    qe = srcs.get("quant_engine.py", "")
    m = re.search(r"async def save_state\((.*?)\):", qe, re.S)
    for p in ("price", "target_sell_price", "sell_order_id", "entry_session", "is_session_done"):
        if not m or not re.search(rf"\b{p}\b", m.group(1)):
            miss.append(f"장부 save_state 의 {p}")
    if miss:
        fail("물타기가 기대는 원작 기능이 없거나 바뀜: " + ", ".join(miss))
    else:
        ok("물타기가 기대는 원작 기능 점검 통과 (장부·주문·트레일링·진입 표식)")


def step_loop(srcs):
    fname = next((f for f, s in srcs.items() if re.search(r"^async def assassin_loop\(", s, re.M)), None)
    if not fname:
        return fail("메인 매매 루프(assassin_loop)를 못 찾음")
    s = srcs[fname]
    if MARK + " B" in s:
        return ok(f"메인 루프 연결 이미 있음 ({fname})")
    lines = s.split("\n")
    i, _, k = find_block(lines, r"^async def assassin_loop\(")[0]
    body = "\n".join(lines[i:k])
    head, tail = "\n".join(lines[:i]), "\n".join(lines[k:])

    m_sl = re.search(r"^(?P<i>[ \t]+)if not is_open or current_price <= 0\.0:[ \t]*\n(?P=i)[ \t]+continue", body, re.M)
    m_tk = re.search(r"^(?P<i>[ \t]+)(?:[\w, ]+=\s*)?await manage_mechanical_profit_trap_plugin\(", body, re.M)
    if not m_sl:
        fail("손절 라인 연결 위치(if not is_open or current_price <= 0.0: continue)를 못 찾음")
    if not m_tk:
        fail("추가 매수 연결 위치(await manage_mechanical_profit_trap_plugin)를 못 찾음")
    if not (m_sl and m_tk):
        return
    names_sl = ["ctx", "symbol", "now_est", "is_active", "holdings_qty", "current_price", "avg_price_dump",
                "sell_order_id", "entry_session", "current_session_id"]
    names_tk = ["holdings_detail", "live_rsi_val", "budget", "last_buy_price", "target_sell_price"]
    miss = [n for n in names_sl if not re.search(rf"\b{n}\b", body[:m_sl.start()])]
    miss += [n for n in names_tk if not re.search(rf"\b{n}\b", body[:m_tk.start()])]
    if miss:
        return fail("메인 루프 변수 이름이 바뀜: " + ", ".join(sorted(set(miss))))

    ind = m_sl.group("i")
    blk_sl = "\n".join(ind + x for x in [
        f"# {MARK} B1] 추가 매수 종료 후 평단 대비 손절 라인 → 전량 매도 (averaging_plugin.py)",
        "if await averaging_stop_loss_tick(",
        "    ctx, symbol, now_est, is_active=is_active, holdings_qty=holdings_qty,",
        "    current_price=current_price, avg_price=avg_price_dump, sell_order_id=sell_order_id,",
        "    entry_session=entry_session, current_session_id=current_session_id,",
        "):",
        "    continue",
    ]) + "\n"
    ind2 = m_tk.group("i")
    blk_tk = "\n".join(ind2 + x for x in [
        f"# {MARK} B2] 보유 중 RSI 35 회복 → RSI≤30 + 직전 매수가 -N% 면 추가 매수 · 체결되면 새 평단으로 안전캡 재장전",
        "if await averaging_tick(",
        "    ctx, symbol, now_est, is_active=is_active, holdings_qty=holdings_qty, holdings_detail=holdings_detail,",
        "    current_price=current_price, live_rsi=live_rsi_val, budget=budget,",
        "    entry_session=entry_session, sell_order_id=sell_order_id,",
        "):",
        "    _avg_st = await AssassinLedger.get_state(symbol)",
        "    last_buy_price, target_sell_price, sell_order_id, entry_session = _avg_st[0], _avg_st[6], _avg_st[7], _avg_st[8]",
        "    try:",
        "        holdings_detail = await ctx.client.get_symbol_holdings_detail(symbol)",
        "        holdings_qty = int(math.floor(holdings_detail[\"qty\"]))",
        "        ctx.shared_holdings[symbol] = holdings_qty",
        "    except Exception:",
        "        continue",
    ]) + "\n"
    # 뒤쪽부터 삽입해 위치가 밀리지 않게
    pos = sorted([(m_sl.start(), blk_sl), (m_tk.start(), blk_tk)], reverse=True)
    for p, blk in pos:
        body = body[:p] + blk + body[p:]
    s = head + "\n" + body + ("\n" + tail if tail else "")
    s = add_import(s, f"from averaging_plugin import averaging_tick, averaging_stop_loss_tick  # {MARK} B]")
    if not re.search(r"^import math\b|^import .*\bmath\b", s, re.M):
        s = add_import(s, "import math")
    if not re.search(r"\bAssassinLedger\b", s.split("async def assassin_loop")[0]):
        s = add_import(s, "from quant_engine import AssassinLedger")
    srcs[fname] = s
    ok(f"메인 루프에 손절 라인·추가 매수 연결 ({fname})")


def step_router(srcs):
    fname = next((f for f, s in srcs.items() if re.search(r"^\s*dp\.include_router\(router\)", s, re.M)), None)
    if not fname:
        return fail("텔레그램 연결 위치(dp.include_router(router))를 못 찾음 → 💧 물타기 설정 화면을 열 수 없음")
    s = srcs[fname]
    if MARK + " C" not in s:
        for n in ("ADMIN_CHAT_ID", "wakeup_event"):
            if not re.search(rf"\b{n}\b", s):
                return fail(f"{fname} 에 {n} 가 없음 (텔레그램 연결 불가)")
        m = re.search(r"^(?P<i>\s*)dp\.include_router\(router\)[^\n]*\n", s, re.M)
        ind = m.group("i")
        blk = (f"{ind}# {MARK} C] 💧 물타기 설정 화면(텔레그램) 연결\n"
               f"{ind}inject_averaging_tg(ADMIN_CHAT_ID, wakeup_event)\n"
               f"{ind}dp.include_router(averaging_router)\n")
        s = s[:m.end()] + blk + s[m.end():]
        s = add_import(s, f"from averaging_plugin import averaging_router, inject_averaging_tg, VERSION_LABEL  # {MARK} C]")
        boot = re.search(r'text="✅ <b>정상작동 중입니다\.</b>"', s)
        if boot:
            s = s[:boot.start()] + f'text=f"✅ <b>정상작동 중입니다.</b>\\n▫️ <code>{{VERSION_LABEL}}</code>"' + s[boot.end():]
        else:
            warn("기동 메시지에 버전 표시 위치를 못 찾음 (메뉴에는 표시됨)")
        srcs[fname] = s
    ok(f"텔레그램 💧 물타기 설정 화면 연결 ({fname})")


def step_ui(srcs):
    target = None
    for s in srcs.values():
        m = re.search(r"^from (\w+) import \((?:[^)]*?)\b(build_settlement_board|get_main_menu_text)\b", s, re.M | re.S)
        if m and "@router" in s:
            target = m.group(1) + ".py"
            break
    if not target or target not in srcs:
        target = next((f for f, s in srcs.items() if re.search(r"^async def (build_settlement_board|get_main_menu_text)\(", s, re.M)), None)
    if not target:
        return warn("메뉴·제어반 화면 함수를 못 찾음 → 💧 버튼 없이 /avg 명령으로만 물타기 설정 가능")
    s = srcs[target]
    if MARK + " D" not in s:
        s = s.rstrip("\n") + (f"\n\n\n# {MARK} D] 메뉴·제어반·/sync 화면에 버전·💧 물타기 줄과 버튼 덧붙이기 (원작 함수는 그대로 감싸기만)\n"
                              "from averaging_plugin import install_ui_wrappers as _avg_install_ui\n"
                              "_avg_install_ui(globals())\n")
        srcs[target] = s
    ok(f"메뉴·제어반·/sync 화면에 💧 물타기 표시 연결 ({target})")


def step_backport(srcs):
    s = srcs.get("sniper_plugin.py", "")
    old = """            if st in ["PENDING", "PARTIAL_FILLED", "PENDING_CANCEL", "PENDING_REPLACE"]:
                can_clear = False
        except Exception:
            can_clear = False
"""
    if "Case 100" in s or old not in s:
        return
    new = """            filled_q_b = float((od.get("execution") or {}).get("filledQuantity") or 0.0)
            if st in ["PENDING", "PARTIAL_FILLED", "PENDING_CANCEL", "PENDING_REPLACE", "REPLACED"]:
                can_clear = False
            # [💧물타기 HOOK E] 원작 후속 버전(초과 Case 100) 수정 미리 적용: 방금 체결됐는데 잔고 반영이 늦은 순간
            # 장부를 '매수 취소'로 지워 MANUAL(수동)로 둔갑시키는 사고 방지 (물타기 대상에서 빠지는 문제도 차단)
            elif (st == "FILLED" or filled_q_b > 0.0) and not sell_order_id and last_buy_price <= 0.0:
                can_clear = False
                ctx.wakeup_event.set()
        except Exception:
            can_clear = False
"""
    srcs["sniper_plugin.py"] = s.replace(old, new, 1)
    ok("원작 후속 버전 버그 수정(Case 100) 미리 적용 (sniper_plugin.py)")


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        print(__doc__ or "사용: python3 averaging_merge.py <폴더> [--commit SHA] [--check]")
        sys.exit(1)
    d = os.path.abspath(args[0])
    commit = args[args.index("--commit") + 1] if "--commit" in args else ""
    check_only = "--check" in args
    if not os.path.exists(os.path.join(d, "averaging_plugin.py")):
        fail("averaging_plugin.py 가 폴더에 없음")
        return finish(d, check_only, {})

    srcs = {f: rd(os.path.join(d, f)) for f in py_files(d)}
    step_disable_update(d, srcs)
    step_compat(srcs)
    step_loop(srcs)
    step_router(srcs)
    step_ui(srcs)
    step_backport(srcs)

    # 원작 정보·README
    readme = os.path.join(d, "README.md")
    first = ""
    if os.path.exists(readme):
        rs = rd(readme)
        if "averaging_merge.py" in rs and "> 아래는 원작자의 공식 매뉴얼 원문입니다." in rs:
            rs = rs.split("> 아래는 원작자의 공식 매뉴얼 원문입니다.", 1)[1].lstrip("\n")
        first = next((ln for ln in rs.split("\n") if ln.strip()), "")
        if not check_only and R["ok"]:
            wr(readme, README_HEAD + rs)
    title = short_title(first)
    R["title"] = title
    R["commit"] = commit
    finish(d, check_only, srcs, title, commit)


def finish(d, check_only, srcs, title="", commit=""):
    if R["ok"] and srcs:
        # 문법 검사는 임시 파일로 먼저 → 통과해야 실제로 저장
        import tempfile
        tmpd = tempfile.mkdtemp(prefix="avg_merge_")
        bad = []
        for f, s in srcs.items():
            p = os.path.join(tmpd, f)
            wr(p, s)
            try:
                py_compile.compile(p, doraise=True)
            except Exception as e:
                bad.append(f"{f}: {str(e).splitlines()[-1][:120]}")
        if bad:
            fail("합친 뒤 문법 오류: " + "; ".join(bad))
        elif not check_only:
            for f, s in srcs.items():
                wr(os.path.join(d, f), s)
            ap = os.path.join(d, "averaging_plugin.py")
            a = rd(ap)
            if commit:
                a = re.sub(r'^UPSTREAM_COMMIT = "[^"]*"', f'UPSTREAM_COMMIT = "{commit}"', a, flags=re.M)
            if title:
                a = re.sub(r'^BASE_VERSION = "[^"]*"', f'BASE_VERSION = "{title}"', a, flags=re.M)
            wr(ap, a)
            ok("averaging_plugin.py 에 원작 커밋·제목 기록")
    print("RESULT " + json.dumps(R, ensure_ascii=False))
    sys.exit(0 if R["ok"] else 2)


if __name__ == "__main__":
    main()
