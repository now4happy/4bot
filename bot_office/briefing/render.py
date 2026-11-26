# briefing/render.py — JSON → 텔레그램 글자 (HTML).
# 필요 달러(부족 금액) 메시지: 토스 스나이퍼 레이더 형식 (판53, 풀이님 결정 2026-11-26).
#   pre 표를 버리고 일반 글자 + 굵은 글씨 (풀이님 결정 2026-11-25, 시안 02_render_sian_readable.md) → 2026-11-26 레이더 형식으로 바꿈.
# 포트폴리오 전환 메시지는 2026-11-26에 삭제됐다 (풀이님 결정).
import datetime as dt
import html
import math

UNAVAIL = "확인 불가 ⚠️"


def fmt_num(v, cur="USD"):
    if v is None:
        return UNAVAIL
    if cur == "KRW":
        return "{:,.0f}".format(v)
    return "{:,.2f}".format(v)


def _esc(s):
    return html.escape(str(s), quote=False)


_WEEKDAY = "월화수목금토일"
ALL_CLEAR = "오늘 계좌 완충"
NEED_TIME_LABEL = "09:00"          # 풀이님 결정: 9시 기준은 KST 09:00 (타이머 00:00 UTC)


def _stamp(date_kst):
    """'11-26 (목)' — 날짜를 못 읽으면 요일 없이 원문."""
    try:
        d = dt.date.fromisoformat(date_kst)
        return "%s (%s)" % (d.strftime("%m-%d"), _WEEKDAY[d.weekday()])
    except (TypeError, ValueError):
        return str(date_kst)


def _title(date_kst):
    """'📡 [계좌별 부족 레이더] (11-26 (목) 09:00)' — 판53 레이더 형식."""
    return "📡 [계좌별 부족 레이더] (%s %s)" % (_stamp(date_kst), NEED_TIME_LABEL)


def _ts(date_kst):
    """'🕐 2026-11-26 09:00 KST' — 브리핑 기준 시각."""
    try:
        d = dt.date.fromisoformat(date_kst)
        return "🕐 %s %s KST" % (d.strftime("%Y-%m-%d"), NEED_TIME_LABEL)
    except (TypeError, ValueError):
        return "🕐 %s %s KST" % (str(date_kst), NEED_TIME_LABEL)


def _unknown(r):
    """holding 또는 need 가 null 이라 부족 여부를 모르는 줄 (need_table 의 unavailable·need_null)."""
    return r.get("status") in ("unavailable", "need_null")


def _shown_rows(rows):
    """메시지에 올릴 후보 행. 메리츠 SOXL 3번(시드 참고용, 부족 개념 없음)과 바벨 전용 행, need 를 계산 안 하는 줄
    (untracked: 한투 KRW·토스 KRW 가 need=None 일 때)은 제외한다 — 부족 목록에도 안 나오고 완충도 안 막는다."""
    return [r for r in rows if r.get("kind") not in ("soxl3", "barbell_only") and not r.get("untracked")]


def _barbell_refs(rows):
    return [r["barbell_ref"] for r in rows if r.get("barbell_ref") is not None]


def _barbell_unknown(b):
    return b.get("status") in ("unavailable", "need_null") or b.get("shortage") is None


def _degraded(res):
    """오늘 값이라고 믿을 수 없는 이유 (완충 금지). SOXL 3번 시드 읽기 실패는 여기 안 넣는다 (부족 줄이 아님)."""
    notes = res.get("notes") or []
    return bool(res.get("stale") or ("need.json ok=false" in notes)
                or (res.get("reissued") and res.get("reissue_ok") is False))


def _cents(v):
    """부족액을 센트 단위로 맞춘다 (부동소수 찌꺼기 1250.0000000000002 방지). 부족 여부도 이 값으로 본다."""
    return round(v or 0.0, 2)


def fmt_need_amount(v, cur):
    """필요 달러 메시지 전용 금액: USD 는 정수 (올림 — 부족을 적게 보이지 않게, 1달러 미만 부족도 1), KRW 등은 fmt_num 그대로."""
    if cur == "USD":
        return "{:,d}".format(int(math.ceil(_cents(v))))
    return fmt_num(v, cur)


def _fmt_total(v, cur):
    return "%s %s" % (cur, fmt_need_amount(v, cur))


def need_all_clear(res):
    """완충 메시지를 보내도 되는가: 모든 계좌 줄의 holding·need 가 확인됐고 (바벨 참고 줄 포함) 전부 충분,
    오늘 값(stale 아님·ok=false 아님·재발행 실패 아님)일 때만 True. 확인할 줄이 하나도 없으면 False."""
    rows = res.get("rows", [])
    cand = _shown_rows(rows)
    if not cand or _degraded(res):
        return False
    if any(_unknown(r) for r in cand):
        return False
    if any(_barbell_unknown(b) for b in _barbell_refs(rows)):
        return False
    if any(_cents(r.get("shortage")) > 0 for r in cand):
        return False
    return True


def need_message(res, date_kst, run_id, late=False):
    """판53 레이더 형식. 부족 있는 계좌만 한 줄씩. 전부 확인돼서 전부 충분하면 레이더 머리말 + '✅ 오늘 계좌 완충' + 시각.
    run_id 는 호환용 (메시지에는 안 넣는다 — briefing_latest.json 에 남는다)."""
    if need_all_clear(res):
        return "\n".join([_title(date_kst), "✅ " + ALL_CLEAR, _ts(date_kst)])
    rows = res.get("rows", [])
    lines = [_title(date_kst)]
    if late:
        lines.append("⚠️ 오늘 브리핑 늦음 (마감 이후 전송)")
    if res.get("stale"):
        lines.append("⚠️ %s 기준 (오늘 아님)" % _esc(res.get("as_of") or "?"))
    if "need.json ok=false" in (res.get("notes") or []):
        lines.append("⚠️ need.json 계산 실패 표시 (ok=false)")
    if res.get("reissued") and res.get("reissue_ok") is False:
        lines.append("⚠️ 재발행 실패 — 기존 파일 기준")
    totals, n_short, n_unknown = {}, 0, 0
    short_lines = []
    for r in _shown_rows(rows):
        cur = r.get("currency", "USD")
        label = _esc(r.get("label", "?"))
        if _unknown(r):
            short_lines.append("· %s %s: 확인 불가" % (label, cur))
            n_unknown += 1
        elif _cents(r.get("shortage")) > 0:
            short_lines.append("· %s %s 부족" % (label, _fmt_total(r["shortage"], cur)))
            totals[cur] = totals.get(cur, 0.0) + r["shortage"]
            n_short += 1
        else:
            continue
        if r.get("kind") == "meritz4" and r.get("skipped"):
            short_lines.append("└ %s 오늘 매수 없음" % _esc(", ".join(r["skipped"])))
    if not n_short and not n_unknown:
        lines.append("확인된 부족 계좌 없음 (위 경고 확인)")
    else:
        lines.append("💰 [부족]")
        lines.extend(short_lines)
    if n_short:
        parts = [_fmt_total(totals[c], c) for c in ("USD", "KRW") if totals.get(c, 0) > 0]
        parts += [_fmt_total(v, c) for c, v in totals.items() if c not in ("USD", "KRW") and v > 0]
        lines.append("📊 [합계] " + " · ".join(parts) + (" (확인 불가 줄 제외)" if n_unknown else ""))
    refs = []
    for b in _barbell_refs(rows):
        cur = b.get("currency", "USD")
        if _barbell_unknown(b):
            refs.append("바벨 씨드 %s: 확인 불가 (합계 제외)" % cur)
        elif _cents(b["shortage"]) > 0:
            refs.append("바벨 씨드 %s (합계 제외)" % _fmt_total(b["shortage"], cur))
    if refs:
        lines.extend(refs)
    lines.append(_ts(date_kst))
    return "\n".join(lines)


def need_failed_message(date_kst, run_id, late=False):
    lines = [_title(date_kst)]
    if late:
        lines.append("⚠️ 오늘 브리핑 늦음 (마감 이후 전송)")
    lines.append("⚠️ need.json 읽기 실패 — 확인 불가 (완충 아님)")
    lines.append(_ts(date_kst))
    return "\n".join(lines)


def streak_alert_message(n):
    return "⚠️ holding null 재발행 %d회 연속 — 근본 원인 점검 필요" % n


def streak_resolved_message():
    return "✅ holding null 재발행 연속 해소"
