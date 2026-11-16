"""k 규칙 검증 스크립트 v1.0.0 (2026-11-14, 클로드, 방 P분석)

보고서 01_report_k-rule_20261114.md 의 숫자를 전부 재현한다.
사용: python3 -I 02_verify_k_rule.py <02_data_v9.json 경로>
외부 패키지 없음 (json, math, sys만 사용). 데이터는 읽기만 한다.

대상 식 (10-26 이후): 1번 줄 = P x (1 - 0.25% x T) + 0.50 x k
  P = 직전 체결가 (잔금 변화 / 보유 변화), T = round(보유 x 평단 / (사이클 시작 잔금 / N), 1)
정상 구간 (2025-08-01~2026-10-23): 계수 0.30%, N은 03_regen_v3.py 날짜표.
"""
import json, sys

TH = -0.004   # 매도일 종가/P - 1 문턱 (데이터상 -0.12% ~ -0.41% 사이 어디든 결과 같음)


def n_of(d):  # 03_regen_v3.py 와 같은 가격 N 날짜표
    if d <= '2026-03-24': return 14
    if d <= '2026-04-01': return 13
    if d <= '2026-07-09': return 14
    if d <= '2026-08-17': return 13
    if d <= '2026-09-24': return 14
    return 13


def near(x, y):  # 03_regen_v3.py 와 같은 일치 판정
    return abs(x - y) <= 0.011 + y * 0.00015


def build(path):
    rows = [r for r in json.load(open(path, encoding='utf-8')) if r['종가일'] != '2025-04-07']
    rows.sort(key=lambda r: (r['종가일'], 1 if (r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0) else 0))
    cs = None; lastP = None; out = []
    for i, c in enumerate(rows):
        p = rows[i - 1] if i else None
        d = c['종가일']; h = c['현재보유개수']
        kind = None; mixed = False; partial_at_limit = False; dq = 0
        if p is not None and p['종가일'] != d and p['현재보유개수'] is not None:
            dq = h - p['현재보유개수']; dc = c['잔금'] - p['잔금']
            dr = (c['시즌실현수익'] or 0) - (p['시즌실현수익'] or 0)
            if dq != 0:
                lastP = -dc / dq; kind = 'S' if dq < 0 else 'B'
                if dq > 0 and abs(dr) > 0.6: mixed = True
            elif abs(dc) > 0.5:
                mixed = True
            if kind == 'B' and p['매수']:
                L = p['매수'][0]['price']; Q = p['매수'][0]['qty']
                partial_at_limit = abs(lastP - L) < 0.006 and dq < Q
        if h == 0: cs = c['잔금']
        if cs is None or h == 0 or not c['매수'] or lastP is None or mixed: continue
        if d < '2025-08-01' or '2026-10-23' < d < '2026-10-26': continue
        new = d >= '2026-10-26'
        coef = 0.0025 if new else 0.003
        N = 13 if new else n_of(d)
        T = round(h * c['보유평단'] / (cs / N) + 1e-9, 1)
        base = lastP * (1 - coef * T)
        act = c['매수'][0]['price']
        out.append(dict(date=d, new=new, kind=kind, P=lastP, T=T, base=base, act=act,
                        k=(act - base) / 0.5, close=c['종가'], cp=c['종가'] / lastP - 1,
                        cash=c['잔금'], partial=partial_at_limit, dq=dq,
                        chg=c['종가'] / p['종가'] - 1, wd=d))
    return out


def predict(r):
    """제안 규칙 (우선순위 순)."""
    if r['cash'] < r['base']:
        return 'CAP'          # 규칙 A: 잔금 < 기본가 -> 잔금 이하로 내림 (정확한 값 미해결)
    if r['kind'] == 'B' and r['partial']:
        return 1              # 규칙 B: 전날 1번 줄이 지정가 그대로 일부만 체결 -> +0.50
    if r['kind'] == 'S' and r['cp'] <= TH:
        return -1             # 규칙 C: 매도 체결, 종가가 체결가보다 0.4% 이상 낮음 -> -0.50
    return 0


def main(path):
    rows = build(path)
    new = [r for r in rows if r['new']]
    print('== 10-26 이후 %d행 ==' % len(new))
    print('날짜       매매 P        T     기본가    실제     k      종가/P-1  잔금      일부체결 예측  판정')
    exact = dirn = miss = 0
    for r in new:
        pr = predict(r)
        k_int = round(r['k'])
        clean = abs(r['k'] - k_int) < 0.03
        if pr == 'CAP':
            ok = r['act'] <= r['cash'] and r['act'] < r['base']
            verdict = '방향맞음(값 미해결)' if ok else '틀림'; dirn += ok; miss += (not ok)
        elif clean and pr == k_int:
            verdict = '정확'; exact += 1
        else:
            verdict = '틀림' + ('(부호만 맞음)' if clean and pr != 0 and (pr > 0) == (k_int > 0) else ''); miss += 1
        print('%s %s %8.3f %4.1f %8.3f %7.2f %+6.2f %+8.2f%% %8.2f %-5s %-4s %s' % (
            r['date'], r['kind'], r['P'], r['T'], r['base'], r['act'], r['k'], r['cp'] * 100,
            r['cash'], r['partial'], pr, verdict))
    print('적중: 정확 %d/%d, 방향만 %d, 틀림 %d' % (exact, len(new), dirn, miss))

    print('\n== 정상 구간(2025-08-01~2026-10-23) 대조 ==')
    norm = [r for r in rows if not r['new']]
    hit = sum(1 for r in norm if near(r['act'], r['base']))
    print('정상 구간 1번 줄 행 %d, k=0 식 적중 %d' % (len(norm), hit))
    big = [r for r in norm if abs(r['act'] - r['base']) > 0.25]
    print('정상 구간 |잔차| > 0.25달러 행 %d개:' % len(big), ', '.join('%s(%+.2f)' % (r['date'], r['act'] - r['base']) for r in big))
    cap = [r for r in norm if r['cash'] < r['base']]
    print('정상 구간 규칙 A 조건(잔금<기본가) 행: %d' % len(cap))
    pb = [r for r in norm if r['kind'] == 'B' and r['partial']]
    print('정상 구간 규칙 B 조건(지정가 그대로 일부 체결) 행: %d' % len(pb),
          ', '.join('%s(잔차 %+.3f)' % (r['date'], r['act'] - r['base']) for r in pb))
    sc = [r for r in norm if r['kind'] == 'S' and r['cp'] <= TH]
    sc_neg = [r for r in sc if r['act'] - r['base'] < -0.25]
    print('정상 구간 규칙 C 조건(매도, 종가/P-1 <= -0.4%%) 행: %d, 그중 음수 가산: %d' % (len(sc), len(sc_neg)))

    print('\n== 문턱 범위 (10-26 이후 매도일 종가/P-1) ==')
    for r in new:
        if r['kind'] == 'S':
            print('%s 종가/P-1 %+.3f%%  k %+.2f' % (r['date'], r['cp'] * 100, r['k']))

    print('\n== 다른 후보 기각 근거 (10-26 이후, 규칙 A 행 11-02·11-05와 10-30 제외) ==')
    rest = [r for r in new if r['date'] not in ('2026-11-02', '2026-11-05', '2026-10-30')]
    nz = [r for r in rest if abs(r['k']) > 0.5]; z = [r for r in rest if abs(r['k']) <= 0.5]
    print('T  k≠0:', sorted(r['T'] for r in nz), ' k=0:', sorted(r['T'] for r in z))
    print('전일대비 종가%% k≠0:', ['%+.1f' % (r['chg'] * 100) for r in nz], ' k=0:', ['%+.1f' % (r['chg'] * 100) for r in z])
    print('종가-P(달러) k≠0:', ['%+.2f' % (r['close'] - r['P']) for r in nz], ' k=0:', ['%+.2f' % (r['close'] - r['P']) for r in z])
    print('11-04 (매수, 종가/P-1 %+.2f%%, k=0) vs 11-12 (매수, %+.2f%%, k=+1): 종가/P로는 못 가름' % (
        [r for r in new if r['date'] == '2026-11-04'][0]['cp'] * 100,
        [r for r in new if r['date'] == '2026-11-12'][0]['cp'] * 100))

    print('\n== 규칙 A 행 상세 (잔금 < 기본가) ==')
    for r in new:
        if r['cash'] < r['base']:
            print('%s 잔금 %.2f 기본가 %.3f 실제 %.2f (잔금-실제 %.2f, 잔금x0.9975=%.3f)' % (
                r['date'], r['cash'], r['base'], r['act'], r['cash'] - r['act'], r['cash'] * 0.9975))
    r = [x for x in new if x['date'] == '2026-10-30'][0]
    print('10-30 잔금 %.2f, 1번 줄 수량 13, 잔금/13 = %.4f, 실제 %.2f, 기본가 %.3f' % (r['cash'], r['cash'] / 13, r['act'], r['base']))


if __name__ == '__main__':
    main(sys.argv[1])
