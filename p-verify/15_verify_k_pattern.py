"""판 10 (k 규칙 실패 패턴) 검증 스크립트 v0.1.0 (ZIP 파일명 기준).

사용: python3 -I 15_verify_k_pattern.py p_data_v16.json
- 첫 줄: 입력 sha256 대조. 이후: 전 행 k 계산, k≠0 날 분석, A/B/C·후보 규칙 적중 집계, 내부 점검.
- 표준 라이브러리만 사용. 출력은 결정적(난수 시드 고정)이라 15_output_v16.txt 와 같아야 한다.
- 가격식·섞인 날 판정·N 날짜표는 regen_table_v3_20261111.py 와 같다 (그 파일을 읽어 복제, 변경 없음).
"""
import hashlib, json, random, sys
from datetime import date

EXPECT_SHA = '0a427133b16a9d4e1324d2ea75ac80ae1c815e3378aea8cc8f600a095c5da4cd'
NEW_REGIME = '2026-10-26'      # 계수 0.25% 시작일 (그 전 0.30%)
COEF_START = '2025-08-01'      # 0.30% 계수 적용 시작 (k_rule_reference)
TOL_K = 0.10                   # k 일치 허용 (0.05달러 = 5센트)
BIG_K = 0.25                   # '큰 k' 기준 (3월 등 작은 잔차는 따로 센다)

def n_of(d):
    """가격용 N 날짜표 (regen_table_v3 와 동일)."""
    if d <= '2026-03-24': return 14
    if d <= '2026-04-01': return 13
    if d <= '2026-07-09': return 14
    if d <= '2026-08-17': return 13
    if d <= '2026-09-24': return 14
    return 13

def near(x, y):
    """regen_table_v3 의 가격 일치 판정: 1센트 + 0.015%."""
    return abs(x - y) <= 0.011 + y * 0.00015

def load(path):
    with open(path, 'rb') as fh:
        raw = fh.read()
    sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw.decode('utf-8'))
    return sha, data

def prepare_rows(data):
    rows = [r for r in data if r['종가일'] != '2025-04-07']
    rows.sort(key=lambda r: (r['종가일'], 1 if (r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0) else 0))
    return rows

def build(rows):
    """모든 행의 상태·k·특징을 계산한다."""
    out = []
    cs = None; last_P = None; last_k_row = None
    for i, c in enumerate(rows):
        p = rows[i - 1] if i else None
        d = c['종가일']; hold = c['현재보유개수']; cash = c['잔금']; close = c['종가']
        mixed = False; dq = 0; dc = 0.0; dp = 0.0; p_new = False
        if p is not None and p['종가일'] != d:
            dq = hold - p['현재보유개수']; dc = cash - p['잔금']
            dp = (c['시즌실현수익'] or 0) - (p['시즌실현수익'] or 0)
            if dq != 0:
                last_P = -dc / dq; p_new = True
                if dq > 0 and abs(dp) > 0.6: mixed = True
            elif abs(dc) > 0.5:
                mixed = True
        if hold == 0: cs = cash
        buys = c['매수'] or []
        r = {'i': i, 'date': d, 'close': close, 'hold': hold, 'cash': cash, 'avg': c.get('보유평단'),
             'dq': dq, 'dc': dc, 'dp': dp, 'P': last_P, 'p_new': p_new, 'mixed': mixed, 'cs': cs,
             'buys': [(b['price'], b['qty']) for b in buys], 'measurable': False, 'why': ''}
        # 특징
        if p is not None and p['종가'] and p['종가일'] != d:
            r['gap'] = (close / p['종가'] - 1) * 100
            r['days'] = (date.fromisoformat(d) - date.fromisoformat(p['종가일'])).days
            r['wd'] = date.fromisoformat(d).weekday()      # 0=월
            r['prev_buys'] = [(b['price'], b['qty']) for b in (p['매수'] or [])]
        else:
            r['gap'] = None; r['days'] = None; r['wd'] = date.fromisoformat(d).weekday(); r['prev_buys'] = []
        r['prev_gap'] = out[-1]['gap'] if out else None
        r['prev_dq'] = out[-1]['dq'] if out else 0
        # 1번 줄 k
        if not (hold > 0 and buys):
            r['why'] = '매수 줄 없음/보유 0'
        elif not (last_P and r['avg'] and cs):
            r['why'] = '직전 P·평단·사이클 잔금 모름'
        elif d < COEF_START:
            r['why'] = '2025-08-01 이전(계수 미확정)'
        elif mixed:
            r['why'] = '섞인 날(제외)'
        else:
            coef = 0.0025 if d >= NEW_REGIME else 0.003
            N = n_of(d)
            T = round(hold * r['avg'] / (cs / N) + 1e-9, 1)
            base = last_P * (1 - coef * T)
            act = buys[0]['price']
            r.update(measurable=True, coef=coef, N=N, T=T, base=base, act=act, qty1=buys[0]['qty'],
                     k=(act - base) / 0.5, close_vs_P=(close / last_P - 1) * 100,
                     base_vs_close=(base / close - 1) * 100, close_vs_avg=close / r['avg'],
                     cash_vs_base=cash / base)
            # 규칙 A/B/C 플래그
            r['A'] = cash < base
            pb = r['prev_buys']
            r['B'] = bool(p_new and dq > 0 and pb and abs(last_P - pb[0][0]) <= 0.011 and dq < pb[0][1])
            r['sell'] = dq < 0
            r['C'] = bool(d >= NEW_REGIME and dq < 0 and close <= last_P * (1 - 0.004))
            r['k_abc'] = (1 if r['B'] else 0) + (-1 if r['C'] else 0)
            r['resid'] = r['k'] - r['k_abc']
        out.append(r)
    return out

def meas(out): return [r for r in out if r['measurable']]

def stats_line(rs):
    n = len(rs); z = sum(1 for r in rs if abs(r['k']) <= TOL_K)
    big = sum(1 for r in rs if abs(r['k']) > BIG_K); neg = sum(1 for r in rs if r['k'] < -BIG_K); pos = sum(1 for r in rs if r['k'] > BIG_K)
    mk = sum(r['k'] for r in rs) / n if n else 0
    return f"n={n} k=0(±{TOL_K}) {z} | |k|>{BIG_K}: {big} (음수 {neg}, 양수 {pos}) | 평균 k {mk:+.2f}"

# ---- 후보 규칙 탐색 ----
FEATS = ['gap', 'prev_gap', 'abs_gap', 'prev_dq', 'close_vs_avg', 'close_vs_P', 'base_vs_close', 'T', 'hold', 'dq',
         'cash_vs_base', 'qty1', 'days', 'is_mon']
VALS = [-3, -2.5, -2, -1.5, -1, -0.5, 0.5, 1, 1.5, 2, 3]

def feat(r, f):
    if f == 'abs_gap': return None if r['gap'] is None else abs(r['gap'])
    if f == 'is_mon': return 1 if r['wd'] == 0 else 0
    return r.get(f)

def best_stump(rs, resid):
    """잔차 resid[i]에 대해 'feature ≤/≥ 문턱이면 v를 더한다' 형태 중 적중 증가가 가장 큰 것."""
    base_hits = sum(1 for x in resid if abs(x) <= TOL_K)
    best = (0, None)
    for f in FEATS:
        xs = [feat(r, f) for r in rs]
        if any(x is None for x in xs): continue
        for thr in sorted(set(xs)):
            for op in ('<=', '>='):
                fire = [(x <= thr) if op == '<=' else (x >= thr) for x in xs]
                if not any(fire): continue
                for v in VALS:
                    gain = 0
                    for fi, x in zip(fire, resid):
                        if fi:
                            gain += (abs(x - v) <= TOL_K) - (abs(x) <= TOL_K)
                    if gain > best[0] or (gain == best[0] and best[1] is None and gain > 0):
                        best = (gain, (f, op, thr, v, sum(fire)))
    return base_hits, best

def main(path):
    sha, data = load(path)
    print(f"입력 해시 {sha[:8]} {'일치' if sha == EXPECT_SHA else '불일치(!!)'} — 기대 {EXPECT_SHA[:8]}")
    ok = (sha == EXPECT_SHA)
    rows = prepare_rows(data)
    out = build(rows)
    M = meas(out)
    checks = []
    def chk(name, cond): checks.append((name, bool(cond)))
    chk('해시 일치', ok)
    chk('입력 389행, 분석 대상 388행(2025-04-07 제외)', len(data) == 389 and len(rows) == 388)
    chk('2026-01-05 두 행', sum(1 for r in rows if r['종가일'] == '2026-01-05') == 2)
    print(f"행: 입력 {len(data)}, 분석 {len(rows)} (2025-04-07 오기 행 제외)")
    why = {}
    for r in out:
        if not r['measurable']: why[r['why']] = why.get(r['why'], 0) + 1
    print(f"1번 줄 가격을 잴 수 있는 행: {len(M)} (제외 사유: " + ', '.join(f"{k} {v}" for k, v in sorted(why.items())) + ")")
    new = [r for r in M if r['date'] >= NEW_REGIME]; old = [r for r in M if r['date'] < NEW_REGIME]
    print(f"  구 체제(0.30%, 2025-08-01~2026-10-23): {stats_line(old)}")
    print(f"  신 체제(0.25%, 2026-10-26~): {stats_line(new)}")

    # 1) 전체 k 표
    print("\n[1] 신 체제 전 행 k (2026-10-01~, 보유 중 1번 줄)")
    print("날짜        종가    갭%   보유  dq   직전P    T    기본가   실제    k     플래그")
    for r in M:
        if r['date'] < '2026-10-01': continue
        fl = ''.join(x for x, c in (('A', r['A']), ('B', r['B']), ('C', r['C']), ('월', r['wd'] == 0)) if c)
        print(f"{r['date']} {r['close']:7.2f} {r['gap']:+6.1f} {r['hold']:4d} {r['dq']:+4d} {r['P']:7.3f} {r['T']:5.1f} {r['base']:7.2f} {r['act']:7.2f} {r['k']:+6.2f}  {fl}")

    # 2) k≠0 날 모음
    print(f"\n[2] 큰 k(|k|>{BIG_K}) 날 전부 (구 체제 포함)")
    print("날짜        체제  갭%    전날갭%  dq   종가/직전P%  기본가vs종가%  잔금/기본가  T     수량  k      A B C")
    nz = [r for r in M if abs(r['k']) > BIG_K]
    for r in nz:
        pg = '   -  ' if r['prev_gap'] is None else f"{r['prev_gap']:+6.1f}"
        print(f"{r['date']} {'신' if r['date'] >= NEW_REGIME else '구'}  {r['gap']:+6.1f} {pg} {r['dq']:+4d}  {r['close_vs_P']:+7.2f}     {r['base_vs_close']:+7.2f}      {r['cash_vs_base']:8.2f}  {r['T']:5.1f} {r['qty1']:4d} {r['k']:+6.2f}  {'Y' if r['A'] else '-'} {'Y' if r['B'] else '-'} {'Y' if r['C'] else '-'}")
    print(f"  큰 k 날 수: {len(nz)} (구 체제 {sum(1 for r in nz if r['date'] < NEW_REGIME)}, 신 체제 {sum(1 for r in nz if r['date'] >= NEW_REGIME)})")
    mixed_big = [r for r in out if r['why'] == '섞인 날(제외)' and r['hold'] > 0 and r['buys'] and r['P'] and r['avg'] and r['cs'] and r['date'] >= COEF_START]
    print(f"  (제외한 섞인 날 중 보유·1번 줄 있는 행: {len(mixed_big)} — {', '.join(r['date'] for r in mixed_big)})")

    # 3) 갭하락 날 검증
    print("\n[3] 갭 크기별 k (잴 수 있는 행; 갭 = 종가 ÷ 전 행 종가 − 1)")
    buckets = [('갭 ≤ -20%', -1e9, -20), ('-20% < 갭 ≤ -10%', -20, -10), ('-10% < 갭 ≤ 0', -10, 0), ('0 < 갭 ≤ +10%', 0, 10), ('갭 > +10%', 10, 1e9)]
    for lab, lo, hi in buckets:
        for nm, grp in (('구', old), ('신', new)):
            g = [r for r in grp if r['gap'] is not None and (lo < r['gap'] <= hi or (lo == -1e9 and r['gap'] <= hi))]
            print(f"  {lab:18s} {nm}체제: {stats_line(g) if g else 'n=0'}")
    gd_new = [r for r in new if r['gap'] <= -10]
    gd_old = [r for r in old if r['gap'] <= -10]
    print(f"  갭 ≤ -10% 날: 신 체제 {len(gd_new)}개 중 k<-{BIG_K} {sum(1 for r in gd_new if r['k'] < -BIG_K)}개, k>+{BIG_K} {sum(1 for r in gd_new if r['k'] > BIG_K)}개, k=0 {sum(1 for r in gd_new if abs(r['k']) <= TOL_K)}개")
    print(f"                    구 체제 {len(gd_old)}개 중 k<-{BIG_K} {sum(1 for r in gd_old if r['k'] < -BIG_K)}개, k>+{BIG_K} {sum(1 for r in gd_old if r['k'] > BIG_K)}개, k=0 {sum(1 for r in gd_old if abs(r['k']) <= TOL_K)}개")
    for r in new:
        if r['gap'] <= -10: print(f"    신 {r['date']} 갭 {r['gap']:+.1f}% k {r['k']:+.2f}")
    print("  k<0 인데 갭하락이 아닌 날: " + ', '.join(f"{r['date']}(갭 {r['gap']:+.1f}%, k {r['k']:+.2f})" for r in M if r['k'] < -BIG_K and r['gap'] > -10))
    # 갭과 k 상관 (신 체제)
    def corr(xs, ys):
        n = len(xs); mx = sum(xs) / n; my = sum(ys) / n
        sx = sum((x - mx) ** 2 for x in xs) ** .5; sy = sum((y - my) ** 2 for y in ys) ** .5
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else float('nan')
    print(f"  신 체제 상관계수 corr(갭, k) = {corr([r['gap'] for r in new], [r['k'] for r in new]):+.2f}, corr(갭, 잔차 k−ABC) = {corr([r['gap'] for r in new], [r['resid'] for r in new]):+.2f} (n={len(new)})")

    # 4) 전날 체결/부분체결/잔금/T/보유·평단
    print("\n[4] 신 체제 k 와 다른 변수")
    print("  요일 (월=0):")
    for wd in range(5):
        g = [r for r in new if r['wd'] == wd]
        print(f"    {wd}: " + (stats_line(g) if g else 'n=0') + ('  [' + ', '.join(f"{r['date'][5:]}:{r['k']:+.2f}" for r in g) + ']' if g else ''))
    oldmon = [r for r in old if r['wd'] == 0]
    print(f"  (구 체제 월요일: {stats_line(oldmon)})")
    sell_new = [r for r in new if r['sell']]; buy_new = [r for r in new if r['dq'] > 0]; none_new = [r for r in new if r['dq'] == 0]
    print(f"  매도 체결 날(dq<0): {stats_line(sell_new)}")
    print(f"  매수 체결 날(dq>0): {stats_line(buy_new)}")
    print(f"  체결 0 날(dq=0, 직전 P 이월): {stats_line(none_new)}")
    for lab, grp in (('T ≥ 10', [r for r in new if r['T'] >= 10]), ('T < 10', [r for r in new if r['T'] < 10])):
        print(f"  {lab}: {stats_line(grp) if grp else 'n=0'}")
    print(f"  corr(T, k)={corr([r['T'] for r in new],[r['k'] for r in new]):+.2f}, corr(보유, k)={corr([r['hold'] for r in new],[r['k'] for r in new]):+.2f}, corr(종가/평단, k)={corr([r['close_vs_avg'] for r in new],[r['k'] for r in new]):+.2f}")
    print("  전날 체결·부분체결 (신 체제, B 플래그 날): " + ', '.join(f"{r['date']}(k {r['k']:+.2f})" for r in new if r['B']))
    print("  잔금 < 기본가 날 (A 플래그, 전 기간): " + ', '.join(f"{r['date']}(실제 {r['act']} / 잔금 {r['cash']} / 기본가 {r['base']:.2f})" for r in M if r['A']))

    # 5) A/B/C 와 새 후보 적중
    print("\n[5] 규칙별 적중 (적중 = 예측 가격이 실제 1번 줄 가격과 |Δk| ≤ 0.10, 즉 5센트 이내)")
    def hits(rs, f):
        return sum(1 for r in rs if abs(r['k'] - f(r)) <= TOL_K), len(rs)
    def hits_strict(rs, f):
        return sum(1 for r in rs if near(r['act'], r['base'] + 0.5 * f(r))), len(rs)
    notA_all = [r for r in M if not r['A']]; notA_new = [r for r in new if not r['A']]; notA_old = [r for r in old if not r['A']]
    rules = [('k=0 (기본값만)', lambda r: 0),
             ('B만 (+1)', lambda r: 1 if r['B'] else 0),
             ('C만 (−1, 10-26 이후)', lambda r: -1 if r['C'] else 0),
             ('A+B+C → B+C (A 행은 값 미해결이라 분모에서 뺌)', lambda r: r['k_abc'])]
    print(f"  분모에서 A 행 제외: 전체 {len(notA_all)}, 구 {len(notA_old)}, 신 {len(notA_new)} (A 행 {len(M)-len(notA_all)}개는 별도 [A 정성 점검])")
    for nm, f in rules:
        a = hits(notA_all, f); o = hits(notA_old, f); n_ = hits(notA_new, f)
        print(f"  {nm:48s} 전체 {a[0]}/{a[1]} | 구 {o[0]}/{o[1]} | 신 {n_[0]}/{n_[1]}")
        a = hits_strict(notA_all, f); o = hits_strict(notA_old, f); n_ = hits_strict(notA_new, f)
        print(f"  {'  └ 더 엄격한 판정(near: 1센트+0.015%)':48s} 전체 {a[0]}/{a[1]} | 구 {o[0]}/{o[1]} | 신 {n_[0]}/{n_[1]}")
    for r in M:
        if r['A']:
            print(f"  [A 정성 점검] {r['date']}: 실제 {r['act']} ≤ 잔금 {r['cash']} → {'예' if r['act'] <= r['cash'] else '아니오'}, 기본가 {r['base']:.2f}, k {r['k']:+.2f}")
    # B/C 플래그 날 개별 확인
    print("  B 플래그 날 k: " + ', '.join(f"{r['date']} {r['k']:+.2f}" for r in M if r['B']))
    print("  C 플래그 날 k: " + ', '.join(f"{r['date']} {r['k']:+.2f}" for r in M if r['C']))
    print("  C 문턱 근처(매도 체결·신 체제) 비플래그: " + ', '.join(f"{r['date']}(종가/체결가 {r['close_vs_P']:+.2f}%, k {r['k']:+.2f})" for r in new if r['sell'] and not r['C']))
    cs_ = sorted((r['close_vs_P'], r['date'], r['k'], r['C']) for r in new if r['sell'])
    print("  C 문턱 감싸기 (신 체제 매도 체결 날, 종가/체결가 % 순): " + ', '.join(f"{d_[5:]}({x:+.2f}%, k {k_:+.2f})" for x, d_, k_, _c in cs_))
    print("    → 문턱은 −0.41%(k=−1)와 −0.12%(k=0) 사이 어디든 표본과 맞다. −0.4%는 이 범위 안이지만 값이 고정되진 않는다. 11-23(−0.02%)은 문턱 밖인데 k=−2.")
    unexpl = [r for r in M if (not r['A']) and abs(r['resid']) > TOL_K]
    print(f"  A/B/C 로도 못 맞힌 행: {len(unexpl)}개 (큰 잔차 {sum(1 for r in unexpl if abs(r['resid'])>BIG_K)}개)")
    for r in unexpl:
        if abs(r['resid']) > BIG_K: print(f"    {r['date']} 잔차 k {r['resid']:+.2f} (k {r['k']:+.2f}, ABC 예측 {r['k_abc']:+d})")

    # 6) 후보 규칙 D 탐색 (신 체제 한정, 사후 맞춤임을 표시)
    print("\n[6] 후보 규칙 D 탐색 (신 체제 A 제외 행의 잔차에 'feature 문턱이면 v 더함' 한 개를 붙임)")
    rsN = notA_new; residN = [r['resid'] for r in rsN]
    bh, (gain, desc) = best_stump(rsN, residN)
    print(f"  기준 적중 {bh}/{len(rsN)} (A/B/C). 후보 {len(FEATS)}개 특징 × 문턱 × 2방향 × {len(VALS)}개 v 전수 탐색")
    if desc:
        f, op, thr, v, nf = desc
        print(f"  표본 안 최선 D: {f} {op} {thr:.4g} 이면 k += {v:+} (발동 {nf}행) → 적중 {bh}+{gain} = {bh+gain}/{len(rsN)}")
        # 표본 밖 점검: 구 체제에서 같은 D 발동 시 오발
        fire_old = [r for r in notA_old if (feat(r, f) is not None) and ((feat(r, f) <= thr) if op == '<=' else (feat(r, f) >= thr))]
        fp = sum(1 for r in fire_old if abs(r['resid']) <= TOL_K)
        print(f"  같은 D 를 구 체제에 적용하면 발동 {len(fire_old)}행, 그중 실제 k(ABC 제외)=0 인 오발 {fp}행")
    else:
        f = None; print("  표본 안에서 적중을 늘리는 D 없음")
    rng = random.Random(20261125)
    obs = gain; cnt = 0; trials = 300
    perm_gains = []
    for _ in range(trials):
        sh = residN[:]; rng.shuffle(sh)
        g_, (g2, _d) = best_stump(rsN, sh)
        perm_gains.append(g2)
        if g2 >= obs: cnt += 1
    print(f"  순열 점검 (잔차를 행 사이에서 섞고 같은 탐색, {trials}회, 시드 20261125): 섞은 자료로 같거나 더 큰 증가({obs})를 얻은 비율 {cnt}/{trials} = {cnt/trials:.2f}; 섞은 자료 증가 중앙값 {sorted(perm_gains)[trials//2]}, 최대 {max(perm_gains)}")
    print("  → 비율이 크면(예: ≥0.05) 그 D 는 우연으로도 나오는 수준이라 규칙으로 채택 안 함")

    # 7) 사전 지정 후보 (지시문 예시) — 탐색 없이 한 번만 평가
    print("\n[7] 지시문 예시 후보 (사전 지정, 탐색 없음)")
    def cand(name, cond, v):
        fired = [r for r in notA_new if cond(r)]
        h0 = sum(1 for r in notA_new if abs(r['resid']) <= TOL_K)
        h1 = sum(1 for r in notA_new if abs(r['resid'] - (v if cond(r) else 0)) <= TOL_K)
        fo = [r for r in notA_old if cond(r)]
        fpo = sum(1 for r in fo if abs(r['resid']) <= TOL_K)
        print(f"  {name}: 발동(신) {len(fired)}행 [{', '.join(r['date'][5:] for r in fired)}], 적중 {h0}→{h1}/{len(notA_new)}; 구 체제 발동 {len(fo)}행 중 오발 {fpo}")
        return h1
    cand('D1 갭 ≤ -10% 이면 k −2', lambda r: r['gap'] <= -10, -2)
    cand('D2 갭 ≤ -15% 이면 k −2', lambda r: r['gap'] <= -15, -2)
    cand('D3 월요일(주말 뒤 첫 행)이면 k −2', lambda r: r['wd'] == 0, -2)
    cand('D4 갭 ≤ -10% 이거나 월요일이면 k −2', lambda r: r['gap'] <= -10 or r['wd'] == 0, -2)
    # 선형: k = a*gap (최소제곱) → 적중
    xs = [r['gap'] for r in notA_new]; ys = residN
    mx = sum(xs) / len(xs); my = sum(ys) / len(ys)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    b = my - a * mx
    lin_hits = sum(1 for r in notA_new if abs(r['resid'] - (a * r['gap'] + b)) <= TOL_K)
    print(f"  D5 k = a×갭 + b (신 체제 최소제곱 a={a:+.4f}, b={b:+.3f}): 적중 {lin_hits}/{len(notA_new)} (연속 함수라 정수 k 에 거의 안 맞음)")

    # 7b) 월요일 관찰 (신 체제)
    print("\n[7b] 신 체제 월요일 (주말 뒤 첫 행) 잔차 = k − (B+C 예측)")
    for r in new:
        if r['wd'] == 0:
            print(f"  {r['date']} k {r['k']:+.2f}  A/B/C 예측 {r['k_abc']:+d}{' (A 행: 값 미해결)' if r['A'] else ''}  잔차 {r['resid']:+.2f}  갭 {r['gap']:+.1f}%  dq {r['dq']:+d}")
    monN = [r for r in notA_new if r['wd'] == 0]; nonmonN = [r for r in notA_new if r['wd'] != 0]
    print(f"  A 제외 월요일 {len(monN)}개 중 잔차 −2 (±0.1): {sum(1 for r in monN if abs(r['resid']+2) <= TOL_K)}개. 월요일 아닌 {len(nonmonN)}개 중 큰 잔차(|잔차|>{BIG_K}): {sum(1 for r in nonmonN if abs(r['resid'])>BIG_K)}개 ({', '.join(r['date'][5:] for r in nonmonN if abs(r['resid'])>BIG_K)}).")
    print(f"  구 체제 월요일 {len(oldmon)}개 중 k=0: {sum(1 for r in oldmon if abs(r['k'])<=TOL_K)}개. 신 체제 시작일(10-26)이 월요일이라 '월요일'과 '체제 전환'이 겹쳐 분리 안 됨.")
    print("  → 관찰일 뿐 규칙 아님: 표본 5개, 11-09는 −2가 없고 11-24(화)·10-30(금)은 월요일 아닌데 큰 잔차. 앞으로 월요일(11-30~)에서 검증할 후보.")

    # 8) 지시문 사실 대조
    print("\n[8] 지시문 사실 대조")
    byd = {r['date']: r for r in out}
    def mrow(d_):
        r_ = byd.get(d_)
        return r_ if (r_ is not None and r_.get('measurable')) else None
    for d_, base_, act_, k_ in (('2026-11-16', 47.97, 46.97, -2.0), ('2026-11-23', 42.12, 41.12, -2.0), ('2026-11-24', 31.61, 30.37, -2.5)):
        r = mrow(d_)
        if r is None:
            print(f"  {d_}: 잴 수 없음 또는 행 없음"); chk(f'{d_} 기본가·실제 재현', False); continue
        print(f"  {d_}: 기본가 {r['base']:.2f} (지시문 {base_}), 실제 {r['act']} (지시문 {act_}), k {r['k']:+.2f} (지시문 {k_:+}), 갭 {r['gap']:+.1f}%")
        chk(f'{d_} 기본가·실제 재현', abs(r['base'] - base_) < 0.01 and abs(r['act'] - act_) < 0.001)
    r = mrow('2026-11-23')
    if r is not None:
        sold = -r['dq']; pf = r['dp']
        print(f"  11-23 매도 체결: 보유 변화 {r['dq']:+d}주 (125→121), 체결가 {r['P']:.2f}, 시즌실현수익 변화 {pf:+.2f} → (체결가−전날평단 93.376)×4 = {(r['P']-93.376)*4:+.2f}. 지시문의 '24주'는 파일에서 확인 안 됨(4주로 읽힘).")
        chk('11-23 매도 4주(24주 아님)', sold == 4 and abs(pf - (r['P'] - 93.376) * 4) < 0.05)
        print(f"  11-23 종가/체결가 {r['close_vs_P']:+.2f}% (C 문턱 −0.4% 미달), 갭 {r['gap']:+.1f}% — 11-20 종가 30.88 → 11-23 43.21 은 갭상승이다 (지시문 '갭하락 날'과 다름).")
        chk('11-23 갭상승', r['gap'] > 0)
    else:
        chk('11-23 매도 4주(24주 아님)', False); chk('11-23 갭상승', False)
    r10 = mrow('2026-10-30'); r26 = mrow('2026-10-26')
    chk('10-30 k +3.81', r10 is not None and abs(r10['k'] - 3.81) < 0.01)
    chk('10-26 k −3', r26 is not None and abs(r26['k'] + 3.0) < 0.02)
    chk('11-17~11-20 매수 줄 없음(측정 불가)', all(x in byd and not byd[x]['measurable'] for x in ('2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20')))
    chk('섞인 날 제외', all(not r['mixed'] for r in M))
    chk('신 체제 잴 수 있는 행 18', len(new) == 18)
    chk('B 플래그 날 11-10, 11-12 k=+1', all(mrow(x) is not None and abs(mrow(x)['k'] - 1) < 0.05 and mrow(x)['B'] for x in ('2026-11-10', '2026-11-12')))
    chk('C 플래그 날 11-06, 11-09, 11-11 k=−1', all(mrow(x) is not None and abs(mrow(x)['k'] + 1) < 0.05 and mrow(x)['C'] for x in ('2026-11-06', '2026-11-09', '2026-11-11')))

    # 9) regen_table_v3 의 1번 줄 가격(0.30%, 구 체제)과의 일치 확인용
    old_script = [r for r in old if r['date'] <= '2026-10-23']
    ok_near = sum(1 for r in old_script if near(r['act'], r['base']))
    print(f"\n[9] 교차 확인: 구 체제 {len(old_script)}행 중 기본가(k=0)가 near 판정(1센트+0.015%)으로 일치: {ok_near}/{len(old_script)} — regen_table_v3_20261111.py 를 v16 에 돌린 '보유 중 1번 줄 가격' 188/246 과 같아야 함")
    chk('regen_table_v3 의 1번 줄 가격 188/246 재현', ok_near == 188 and len(old_script) == 246)
    chk('regen_table_v3 판정식과 동일 near 사용', near(1.0, 1.0105) and not near(1.0, 1.02))
    print("\n[내부 점검]")
    for nm, c in checks: print(f"  {'통과' if c else '실패'}: {nm}")
    npass = sum(1 for _, c in checks if c)
    print(f"내부 점검 {npass}/{len(checks)}")
    return 0 if npass == len(checks) else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
