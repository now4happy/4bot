# briefing/render.py — JSON → 텔레그램 글자 (HTML, pre 블록 글자 표). Q8 (가).
# 열 규격(설계 3-1): 부족액(오른쪽 정렬) / 계좌명(가운데) / 보유 현금(오른쪽). 전체 40칸을 14·12·14칸 근사.
# 한글·이모지는 2칸으로 센다. 계좌명은 줄바꿈하지 않으므로, 내용이 기본 폭을 넘으면 그 열만 넓힌다
# (비율 근사 포기 — 설계 3-1 의 해결 (a)).
import html
import unicodedata

BASE_WIDTHS = (14, 12, 14)
SEP = " | "
UNAVAIL = "확인 불가 ⚠️"
_WIDE = set("⚠")


def cw(ch):
    if unicodedata.combining(ch) or ch in ("️", "‍"):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F") or ch in _WIDE:
        return 2
    return 1


def dw(s):
    return sum(cw(c) for c in s)


def pad(s, w, align):
    gap = max(w - dw(s), 0)
    if align == "r":
        return " " * gap + s
    if align == "l":
        return s + " " * gap
    left = gap // 2
    return " " * left + s + " " * (gap - left)


def fmt_num(v, cur="USD"):
    if v is None:
        return UNAVAIL
    if cur == "KRW":
        return "{:,.0f}".format(v)
    return "{:,.2f}".format(v)


def row_lines(r):
    """한 행을 (부족액 줄들, 보유 줄들) 로 바꾼다."""
    cur = r.get("currency", "USD")
    kind = r.get("kind")
    if kind == "barbell_only":
        short, hold = ["—"], [""]
    elif kind == "soxl3":
        short = ["—"]
        s = r.get("soxl")
        hold = ["전체 " + fmt_num(s["total"], cur), "당일 " + fmt_num(s["day"], cur)] if s else [UNAVAIL]
    else:
        st = r.get("status")
        if st == "unavailable":
            short, hold = [UNAVAIL], [UNAVAIL]
        elif st == "need_null":
            short, hold = ["계산 불가"], [fmt_num(r.get("holding"), cur)]
        else:
            short, hold = [fmt_num(r.get("shortage"), cur)], [fmt_num(r.get("holding"), cur)]
    b = r.get("barbell_ref")
    if b is not None:
        if b.get("shortage") is None:
            short.append("바벨 참고 " + UNAVAIL)
        else:
            short.append("바벨 참고 " + fmt_num(b["shortage"], b.get("currency", cur)))
    sk = r.get("skipped")
    if sk and kind == "meritz4":
        short.append(", ".join(sk) + " 오늘 매수 없음")
    return short, hold


def render_need_table(rows):
    header = ("부족액", "계좌명", "보유 현금")
    parsed = []
    for r in rows:
        short, hold = row_lines(r)
        parsed.append((r.get("label", "?"), short, hold))
    # 폭: 전체 40칸을 14·12·14 로 나누는 것이 기본. 계좌명(가운데 열)은 줄바꿈하지 않으므로 이름이 12칸을 넘으면
    # 가운데 열을 넓히고 남은 칸을 양쪽에 나눈다. 양쪽 열도 첫 줄 내용이 넘으면 그만큼만 넓힌다(40칸 초과 가능).
    total = sum(BASE_WIDTHS)
    wm = max(BASE_WIDTHS[1], dw(header[1]), *(dw(p[0]) for p in parsed)) if parsed \
        else max(BASE_WIDTHS[1], dw(header[1]))
    min_l = max(dw(header[0]), *(dw(p[1][0]) for p in parsed)) if parsed else dw(header[0])
    min_r = max(dw(header[2]), *(dw(h) for p in parsed for h in p[2])) if parsed else dw(header[2])
    rem = total - wm
    wl = max(min_l, rem // 2)
    wr = max(min_r, rem - wl)
    out = [SEP.join((pad(header[0], wl, "r"), pad(header[1], wm, "c"), pad(header[2], wr, "r")))]
    out.append("-" * (wl + wm + wr + 2 * len(SEP)))
    for label, short, hold in parsed:
        n = max(len(short), len(hold))
        for i in range(n):
            s = short[i] if i < len(short) else ""
            h = hold[i] if i < len(hold) else ""
            lab = label if i == 0 else ""
            if i > 0 and not lab and dw(s) > wl:
                span = wl + wm + len(SEP)         # 계좌명 칸이 비어 있으니 두 칸을 이어 쓴다
                if dw(s) <= span:
                    out.append(SEP.join((pad(s, span, "r"), pad(h, wr, "r"))))
                    continue
            out.append(SEP.join((pad(s, wl, "r"), pad(lab, wm, "c"), pad(h, wr, "r"))))
    return "\n".join(out)


def table_width(table_text):
    return max((dw(l) for l in table_text.split("\n")), default=0)


def _esc(s):
    return html.escape(str(s), quote=False)


def _totals_line(totals):
    parts = []
    for cur in ("USD", "KRW"):
        if totals.get(cur, 0) > 0:
            parts.append("%s 부족 합계 %s" % (cur, fmt_num(totals[cur], cur)))
    for cur, v in totals.items():
        if cur not in ("USD", "KRW") and v > 0:
            parts.append("%s 부족 합계 %s" % (cur, fmt_num(v, cur)))
    return " · ".join(parts) if parts else "부족 합계 없음"


def need_message(res, date_kst, run_id, late=False):
    lines = ["💵 필요 달러 · %s 09:30 CST   (need.json %s)" % (date_kst, _esc(res.get("as_of") or "?"))]
    if late:
        lines.append("⚠️ 오늘 브리핑 늦음 (마감 이후 전송)")
    if res.get("stale"):
        lines.append("⚠️ %s 기준 (오늘 아님)" % _esc(res.get("as_of") or "?"))
    if res.get("unavailable"):
        lines.append("⚠️ 일부 계좌 확인 불가 — 문제 있음")
    if res.get("reissued") and res.get("reissue_ok") is False:
        lines.append("⚠️ 재발행 실패 — 기존 파일 기준")
    lines.append(_totals_line(res.get("totals", {})))
    lines.append("<pre>" + _esc(render_need_table(res.get("rows", []))) + "</pre>")
    lines.append("run " + run_id)
    return "\n".join(lines)


def need_failed_message(date_kst, run_id, late=False):
    s = "⚠️ need.json 읽기 실패 — 문제 있음 (%s)" % date_kst
    if late:
        s += "\n⚠️ 오늘 브리핑 늦음 (마감 이후 전송)"
    return s + "\nrun " + run_id


def streak_alert_message(n):
    return "⚠️ holding null 재발행 %d회 연속 — 근본 원인 점검 필요" % n


def streak_resolved_message():
    return "✅ holding null 재발행 연속 해소"


def _sgn(n):
    return ("+%s" % _qty(n)) if n > 0 else _qty(n)


def _qty(v):
    if v is None:
        return "—"
    return str(int(v)) if float(v).is_integer() else ("%g" % v)


def portfolio_message(p, run_id, late=False):
    """설계 3-2: 변동이 먼저, 상태는 뒤."""
    head = "📊 포트폴리오 전환 · %s" % p.get("date")
    if p.get("prev_date"):
        head += " (비교 기준일 %s)" % p["prev_date"]
    if p.get("targets_confirmed") is False:
        head += "   (목표 미확정)"
    lines = [head]
    if late:
        lines.append("⚠️ 오늘 브리핑 늦음 (마감 이후 전송)")
    body = []
    if p.get("first_snapshot"):
        lines.append("첫 기준 스냅샷 — 변동 비교 없음")
    else:
        n = len(p.get("changes", []))
        lines.append("오늘 바뀐 것 %d건" % n if n else "변동 없음")
    if p.get("snapshot_save_failed"):
        lines.append("⚠️ 스냅샷 저장 실패 — 내일 변동 비교 불가")
    body.append("[계좌별 수량 변동]")
    cc = p.get("changes", [])
    for c in cc:
        body.append("%-8s%s  %s → %s  (%s주)" % (_acct_pad(c["account"]), c["ticker"], _qty(c["prev_qty"]),
                                                  _qty(c["today_qty"]), _sgn(c["delta"])))
    for a in p.get("incomparable", []):
        body.append("%s  비교 불가 ⚠️" % a)
    kw = p.get("kiwoom", {})
    if kw.get("mode") == "fixed":
        body.append("키움    고정(%s) — 변동 비교 안 함" % kw.get("as_of"))
        if kw.get("recaptured"):
            body.append("키움    캡처 갱신으로 바뀐 값 (실제 거래 변동 아님)")
    if not cc and not p.get("incomparable") and not p.get("first_snapshot"):
        pass
    body.append("")
    bk = p.get("buckets")
    if bk is None:
        body.append("[버킷 변화] 목표 파일 없음 — 생략")
    else:
        body.append("[버킷 변화]   목표 │ 어제 │ 오늘 │ 변화(%p)")
        for b in bk:
            body.append("%s  %s │ %s │ %s │ %s" % (b["key"], _pct(b.get("target")), _pct(b.get("prev_pct")),
                                                   _pct(b.get("today_pct")), _delta(b.get("delta"), b.get("highlight"))))
        if p.get("buckets_note"):
            body.append(p["buckets_note"])
    lines.append("<pre>" + _esc("\n".join(body)) + "</pre>")
    lines.append("소스: " + _sources_line(p))
    lines.append("run " + run_id)
    return "\n".join(lines)


def _acct_pad(a):
    return a + " " * max(8 - dw(a), 0) if dw(a) < 8 else a + " "


def _pct(v):
    return "—" if v is None else ("%g%%" % round(v, 1))


def _delta(v, hl=False):
    if v is None:
        return "—"
    if abs(v) < 0.05:
        return "0"
    s = "%s%g" % ("▲" if v > 0 else "▼", round(abs(v), 1))
    return s + (" !" if hl else "")


def _sources_line(p):
    st = p.get("sources", {})
    out = []
    for name, label in (("toss", "토스"), ("meritz", "메리츠")):
        s = st.get(name, {}).get("status")
        out.append("%s %s" % (label, "✅" if s == "ok" else ("⚠️ 일부" if s == "partial" else "⚠️")))
    kw = st.get("kiwoom", {})
    if kw.get("mode") == "fixed":
        d = kw.get("elapsed_days")
        out.append("키움 고정(%s%s)" % (kw.get("as_of"), (", %s일 경과" % d) if d is not None else ""))
    else:
        out.append("키움 %s %s" % (kw.get("mode"), "✅" if kw.get("status") == "ok" else "⚠️"))
    return " · ".join(out)
