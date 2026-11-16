"""P 매매 표 재생성 v3 (2026-11-11) — v6 데이터 대조용.

v2에서 추가한 것 (클로드 1번 줄 가격 분석, Muse 검토 완료):
 1) 보유 중 1번 줄 가격: 직전 체결가 P × (1 − 0.3% × T), T = 보유원가 ÷ (사이클 시작 잔금 ÷ N),
    소수 1자리 반올림. 적용 범위 2025-08-01~2026-10-23만 (10-26 이후·2025-05~07은 미적용).
 2) 수량 분모 날짜표 N (13/14): 2줄 수량 중 1번 줄만 B = 사이클 시작 잔금 ÷ N(수량용 날짜표).
    2번 줄 수량과 줄 수 경계(잔금 ≥ 2B)는 /13 고정으로 유지 (375/375, 210/360 유지 확인).
    수량용 N과 가격용 N은 2025-07-22~2026-02-19 구간만 다름 (수량 13, 가격 14).
 3) 2025-08~2026-02 구간의 N 불일치는 재매개변수화 문제임 (N=14·0.3% ≡ N=13·0.323%).
    가격·수량에 같은 날짜표 N을 쓰되, 그 구간은 계수 0.323% 대안을 주석으로 남긴다.

사용: python3 regen_table_v3_20261111.py <v6.json 경로> [결과.json 경로]
"""
import json, math, sys

def f_of(d):
    if d <= '2025-12-31': return 0.998
    if d <= '2026-05-31': return 0.9995
    return 0.9998

def n_of(d):
    """수량·1번 줄 가격 분모 N 날짜표 (클로드 대조, 가격·수량 공통).
    2025-08 이전은 미확정이라 14로 둔다 (2025-05~07 구간은 1번 줄 가격 미적용).
    2026-11-12 관찰 (클로드 2일차 분석, Muse 검토 통과):
    N 전환일 5개(03-25, 04-02, 07-10, 08-18, 09-25) 중 4개가 사이클 경계에 있다
    (보유 0인 날 또는 그 다음 날. 04-02·09-25는 종료일, 03-25·07-10은 시작일).
    우연 확률 ~3.5%. 즉 N은 사이클 단위로 정해지는 설정값으로 보인다.
    단, 사이클 시작에 13이 될지 14가 될지를 고르는 기준은 아직 모른다 (미해결).
    08-18만 예외 (사이클 도중, 종가/평단 1.120→0.971 평단 돌파일)."""
    if d <= '2026-03-24': return 14
    if d <= '2026-04-01': return 13
    if d <= '2026-07-09': return 14
    if d <= '2026-08-17': return 13
    if d <= '2026-09-24': return 14
    return 13

def n_qty(d):
    """수량 분모 N 날짜표 (클로드 대조). 가격 날짜표와 같되 2025-07-22~2026-02-19는 13.
    가격 N=14와 수량 N=13이 갈리는 구간은 재매개변수화 문제 (가격은 N=13·계수 0.323%로도 같은 적중)."""
    if d <= '2025-07-21': return 14
    if d <= '2026-02-19': return 13
    return n_of(d)

def premium_of(d):
    if d <= '2025-07-03': return 0.158
    if d <= '2025-07-08': return 0.128
    if d <= '2025-07-31': return 0.109
    if d <= '2026-01-05': return 0.0695
    if d <= '2026-01-06': return 0.0494
    if d <= '2026-02-20': return 0.0596
    return 0.0697

def near(x, y):
    """가격 일치 판정: 1센트 + 0.015% 허용"""
    return abs(x - y) <= 0.011 + y * 0.00015

def main(path, out=None):
    rows = [r for r in json.load(open(path, encoding='utf-8')) if r['종가일'] != '2025-04-07']
    # 2026-01-05 두 행: 시즌1 종료 행(잔금 != 10000)이 먼저 오게 정렬
    rows.sort(key=lambda r: (r['종가일'], 1 if (r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0) else 0))
    cycle_start = None; last_P = None; res = []
    for i, cur in enumerate(rows):
        prev = rows[i-1] if i else None
        hold, cash, close, d = cur['현재보유개수'], cur['잔금'], cur['종가'], cur['종가일']
        mixed = False
        if prev is not None and prev['종가일'] != d:
            dq = hold - prev['현재보유개수']; dc = cash - prev['잔금']
            dp = (cur['시즌실현수익'] or 0) - (prev['시즌실현수익'] or 0)
            if dq != 0:
                last_P = -dc / dq
                if dq > 0 and abs(dp) > 0.6: mixed = True   # 순매수인데 실현수익이 변함 = 매도도 섞임
            elif abs(dc) > 0.5:
                mixed = True
        if hold == 0:
            cycle_start = cash
        if cycle_start is None:
            res.append({'date': d, 'skip': '사이클 시작 잔금 모름'}); continue
        B = cycle_start / 13.0
        N = n_of(d)
        Bq = cycle_start / N
        Bq_qty = cycle_start / n_qty(d)
        buys = cur['매수'] or []
        avg = cur.get('보유평단')
        r = {'date': d, 'close': close, 'hold': hold, 'cash': cash, 'B': round(B, 2),
             'N': N, 'Bq': round(Bq, 2),
             'last_P': round(last_P, 3) if last_P else None, 'mixed': mixed,
             'actual': [(b['price'], b['qty']) for b in buys]}
        # 줄 수
        r['pred_lines'] = 2 if cash >= 2 * B else 1
        r['lines_ok'] = (r['pred_lines'] == len(buys)) if buys else None
        # 새 사이클 1번 줄
        if hold == 0 and buys:
            r['pred_p1_new'] = round(close * (1 + premium_of(d)), 2)
            r['p1_new_ok'] = abs(r['pred_p1_new'] / buys[0]['price'] - 1) < 0.005
        # 보유 중 1번 줄 가격 (2025-08-01~2026-10-23만, 섞인 날 제외)
        if hold > 0 and buys and last_P and avg and '2025-08-01' <= d <= '2026-10-23' and not mixed:
            T = round(hold * avg / Bq + 1e-9, 1)
            p = last_P * (1 - 0.003 * T)
            r['pred_p1'] = round(p, 2); r['T'] = T; r['p1_ok'] = near(buys[0]['price'], p)
        # 2번 줄 가격 (보유 중, 2줄)
        if hold > 0 and len(buys) == 2 and last_P:
            p = min(close * 0.999, last_P * f_of(d))
            r['pred_p2'] = round(p, 2); r['p2_ok'] = near(buys[1]['price'], p)
        # 새 사이클(보유 0)의 2번 줄: 종가*0.999만 적용
        if hold == 0 and len(buys) == 2:
            p = close * 0.999
            r['pred_p2_new'] = round(p, 2); r['p2_new_ok'] = near(buys[1]['price'], p)
        # 수량 (1번 줄만 날짜표 N 분모 Bq_qty, 2번 줄은 /13 B 유지)
        if len(buys) == 1:
            r['pred_q'] = [math.floor(min(cash, B) / buys[0]['price'])]
        elif len(buys) == 2:
            r['pred_q'] = [math.floor(Bq_qty / buys[0]['price']), math.floor(B / buys[1]['price'])]
        if buys:
            r['q_ok'] = [pq == b['qty'] for pq, b in zip(r['pred_q'], buys)]
        res.append(r)

    def rate(key, rows_):
        v = [x[key] for x in rows_ if x.get(key) is not None]
        return sum(1 for t in v if t), len(v)
    ok = [x for x in res if 'skip' not in x]
    print('대상 행:', len(ok))
    print('매수 줄 수: %d/%d' % rate('lines_ok', ok))
    print('새 사이클 1번 줄 가격(±0.5%%): %d/%d' % rate('p1_new_ok', ok))
    print('새 사이클 2번 줄 가격(종가×0.999): %d/%d' % rate('p2_new_ok', ok))
    print('보유 중 1번 줄 가격 (2025-08-01~2026-10-23, 섞인 날 제외): %d/%d' % rate('p1_ok', [x for x in ok if not x['mixed']]))
    print('보유 중 2번 줄 가격: %d/%d' % rate('p2_ok', ok))
    print('  └ 섞인 날 제외: %d/%d' % rate('p2_ok', [x for x in ok if not x['mixed']]))
    one = [x for x in ok if len(x['actual']) == 1]; two = [x for x in ok if len(x['actual']) == 2]
    print('1줄 수량: %d/%d' % (sum(1 for x in one if x['q_ok'][0]), len(one)))
    print('2줄 수량 1번 줄: %d/%d, 2번 줄: %d/%d' % (sum(1 for x in two if x['q_ok'][0]), len(two), sum(1 for x in two if x['q_ok'][1]), len(two)))
    for a, b in (('2025-05', '2025-12'), ('2026-01', '2026-05'), ('2026-06', '2026-08'), ('2026-09', '2026-12')):
        s = [x for x in ok if a <= x['date'][:7] <= b]
        print('  %s~%s 보유 중 2번 줄: %d/%d' % ((a, b) + rate('p2_ok', s)))
    print('--- 줄 수 불일치 ---')
    for x in ok:
        if x['lines_ok'] is False: print(x['date'], '예측', x['pred_lines'], '실제', len(x['actual']), '잔금', x['cash'], '2B', round(2 * x['B'], 2))
    print('--- 새 사이클 1번 줄 불일치 ---')
    for x in ok:
        if x.get('p1_new_ok') is False: print(x['date'], '예측', x['pred_p1_new'], '실제', x['actual'][0][0], '종가', x['close'])
    print('--- 보유 중 2번 줄 불일치 (차이 0.3% 이상만) ---')
    for x in ok:
        if x.get('p2_ok') is False and abs(x['pred_p2'] / x['actual'][1][0] - 1) >= 0.003:
            print(x['date'], '예측', x['pred_p2'], '실제', x['actual'][1][0], '종가', x['close'], '직전P', x['last_P'], '섞인 날' if x['mixed'] else '')
    print('--- 보유 중 1번 줄 가격 불일치 (적용 범위 안, 차이 0.3% 이상만) ---')
    for x in ok:
        if x.get('p1_ok') is False and abs(x['pred_p1'] / x['actual'][0][0] - 1) >= 0.003:
            print(x['date'], '예측', x['pred_p1'], '실제', x['actual'][0][0], 'T', x.get('T'), '직전P', x['last_P'])
    if out:
        json.dump(res, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
