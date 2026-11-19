"""P매매 우리 매도 규칙 1단계 — 백테스트 틀 v0.2.0 (2026-11-19, 클로드 2번) — 방: P매매 검증 (p-verify)

버전 기록:
  v0.1.0  틀 (격자 11회, 탐색 30회 상한, 검증 1회)
  v0.1.1  시즌 리셋(2026-01-05) 처리 + 보정 지표 (Muse 검증 통과 2026-11-17)
  v0.1.2  --holdout 다중 id: 한 번의 실행으로 여러 격자 id의 검증 구간 지표를 낸다. 검증 횟수는 그 실행 1회로만 센다.
          시뮬레이션·격자·상한 로직은 v0.1.1과 같다 (바뀐 곳: 인자 처리·검증 구간 출력·장부 기록 형식만).
  v0.2.0  수익금 분리 층(08_sep_layer.py) 연결 (판 6 VERIFY.md 6절 (a)~(e)) + 격자 5셀 실행 --sep-grid (탐색 5회로 셈).
          분리 인자(sep)가 없으면 시뮬레이션은 v0.1.2와 글자 그대로 같다 (11_test_integration.py가 N0·인자 없음 동일을 확인).
          입력 해시는 v10(b73e8337)과 v12(bcedc401)를 둘 다 받는다. 판정은 12_judge_q23.py (Q23 임계값 고정).

사용:
  python3 -I 03_backtest.py p_data_v10.json --grid                 # 미리 정한 격자 11회 (탐색 구간만 출력)
  python3 -I 03_backtest.py p_data_v10.json --run B_n20_m2_r1.0    # 격자 1개만
  python3 -I 03_backtest.py p_data_v12.json --sep-grid             # 분리 격자 5셀 (N0·C_h0.10·C_h0.30·C_h0.10_f0.5·A_h0.10), 탐색 5회로 셈
  python3 -I 03_backtest.py p_data_v10.json --holdout <격자id> [<격자id> ...]   # 검증 구간, 전체에서 딱 1번
      (id는 공백 또는 쉼표로 여러 개. 데이터 파일 이름을 --holdout보다 앞에 쓴다. 몇 개를 넣어도 검증 1회로 센다)
옵션: --log bt_run_log.json (실행 횟수 기록 파일, 기본 현재 폴더)  --allow-unverified (입력 해시 불일치 허용, 횟수는 센다)

구조: 입력 = 원작자 표 v10 행 + 매수 체결 내역(fills). 원작자의 매도 줄은 버리고 우리 매도 규칙(01·02번 파일)만 적용한다.
  매수 체결 = 원작자 표의 보유 수량 증가분 (derive_buy_fills). 같은 날 원작자 매도가 겹치면 과소 추정된다(알려진 한계).
  체결 가정: 어제 매도 줄은 오늘 종가 >= 줄 가격이면 그 가격에 체결 (고가 자료가 없어 보수적으로 종가로 판정).
  청산 신호: 오늘 종가로 판단, 다음 행 종가에 시장가 청산. 거래비용: 매수·매도 각각 cost_bps (편도).
  계좌: 시작 현금 10000. 시즌 리셋(2026-01-05, 잔금 10000 행이 있는 날)은 그날 기록까지 마친 뒤 보유 0·현금 10000으로 되돌리고
        남은 줄·청산 신호·고점·연속 이탈 일수를 지운다. 원값 수익률·MDD는 평가금을 그대로 이어 붙인 값(리셋 때 10000으로 돌아가는
        폭이 손실로 들어감), 보정 값은 리셋 시점 인출분을 빼고 시즌별 평가금 비율을 곱해 이은 값(시간가중). 후보 비교는 보정 값으로 한다.
  매도 가격 X 자리는 임시: 평단*(1+target_pct) 한 줄. 최종 매도 가격·수량이 아니다.

과최적화 방지 (코드가 강제):
  - 파라미터 PARAM_KEYS 9개 (<=10). 격자 11회는 아래 GRID에 미리 적어 둔 것이다.
  - 탐색 구간 실행 총 30회 상한 (--log 파일에 누적, 넘으면 실행 거부). 검증 구간(뒤 30%)은 전체에서 1회만 출력.
  - 구간: 앞 70% 탐색, 뒤 30% 검증. 한 번의 연속 시뮬레이션에서 구간별 지표만 나눠 낸다.
"""
import sys, os, json, hashlib, math, argparse, datetime, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(fname, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SB = _load('01_sell_blocks.py', 'sell_blocks')
XR = _load('02_exit_rules.py', 'exit_rules')
SEP = _load('08_sep_layer.py', 'sep_layer')
JG = _load('12_judge_q23.py', 'judge_q23')

EXPECT = 'b73e83372a305b4de8f8ed553816ebb73a706b58553f2c61cfa26307e65487d6'      # p_data_v10.json
EXPECT_V12 = 'bcedc40142bac16ad71cb1ccf01e92fc0298d4fe4096f2f421005e04ec32ee24'  # p_data_v12.json (385행, 판 6 이후 기준)
INIT_CASH = 10000.0
SPLIT = 0.7
MAX_EXPLORE_RUNS = 30
MAX_HOLDOUT_RUNS = 1

PARAM_KEYS = ('exit_mode', 'stop_x', 'ma_n', 'ma_m', 'exit_ratio', 'trail_y', 'cost_bps', 'target_pct', 'p1')
assert len(PARAM_KEYS) <= 10
DEFAULTS = dict(exit_mode='none', stop_x=0.15, ma_n=20, ma_m=2, exit_ratio=1.0, trail_y=0.15,
                cost_bps=10.0, target_pct=0.10, p1=False)

# 미리 정한 격자 (탐색에 쓰는 전부). cost_bps·target_pct·p1은 탐색하지 않는다.
GRID = {'base': dict(exit_mode='none')}
for _x in (0.10, 0.15, 0.20):
    GRID['A_x%.2f' % _x] = dict(exit_mode='A', stop_x=_x)
for _n, _m, _r in ((20, 2, 1.0), (20, 2, 0.5), (50, 2, 1.0), (50, 3, 1.0)):
    GRID['B_n%d_m%d_r%.1f' % (_n, _m, _r)] = dict(exit_mode='B', ma_n=_n, ma_m=_m, exit_ratio=_r)
for _y in (0.10, 0.15, 0.20):
    GRID['C_y%.2f' % _y] = dict(exit_mode='C', trail_y=_y)


def prepare_rows(raw):
    """원작자 표 -> 정렬된 행. 2025-04-07 행 제외, 2026-01-05 잔금 10000 리셋 행은 같은 날짜 맨 뒤 (05/06번 스크립트와 같은 처리)."""
    rows = [r for r in raw if r['종가일'] != '2025-04-07']
    rows.sort(key=lambda r: (r['종가일'], 1 if (r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0) else 0))
    return rows


RESET_DATE = '2026-01-05'   # 시즌 리셋일 (v10: 같은 날짜에 시즌1 종료 행·시즌2 시작 행 두 개)


def reset_days(rows):
    """시즌 리셋 날짜 집합. 조건: 날짜가 RESET_DATE이고 잔금이 정확히 10000인 행이 있을 때."""
    return {r['종가일'] for r in rows if r['종가일'] == RESET_DATE and r['잔금'] == 10000.0}


def derive_buy_fills(rows):
    """매수 체결 내역. 출력: [{date, qty, price}]. qty = 보유 증가분, price = -잔금변화/증가분. 리셋 행은 건너뛴다."""
    fills = []
    for i in range(1, len(rows)):
        pv, r = rows[i - 1], rows[i]
        if r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0:
            continue
        dq = r['현재보유개수'] - pv['현재보유개수']
        dc = r['잔금'] - pv['잔금']
        if dq > 0 and dc < 0:
            fills.append(dict(date=r['종가일'], qty=int(dq), price=round(-dc / dq, 2)))
    return fills


def run_backtest(rows, fills, params, init_cash=INIT_CASH, sep=None):
    """입력: 정렬된 행, 매수 체결 내역, 파라미터. 출력: dict(equity=[...], 지표 카운터).
    sep = None이면 분리 없음(v0.1.2와 같은 계산), sep = 08_sep_layer.GRID의 값(dict)이면 회차 종료 때 분리를 하고 total(총합산)을 같이 낸다.
    rows 중 날짜가 같은 행(리셋 행)은 종가 시계열에서 한 번만 쓴다."""
    p = dict(DEFAULTS); p.update(params)
    assert set(p) <= set(PARAM_KEYS), '알 수 없는 파라미터'
    c_ = p['cost_bps'] / 1e4
    fmap = {f['date']: f for f in fills}
    days, seen = [], set()
    for r in rows:
        if r['종가일'] in seen:
            continue
        seen.add(r['종가일']); days.append((r['종가일'], float(r['종가'])))

    rdays = reset_days(rows)
    cash, pos, basis = init_cash, 0, 0.0
    # 분리 층 (VERIFY.md 6절 (a)): 목표 운용금액 M* = 시즌 시작 원금 x 1.0 (Q18)
    sst = SEP.new_state(init_cash) if sep is not None else None
    round_was_open = False
    total, sep_hist = [], []
    lines, peak, closes, run, pend = [], None, [], 0, None
    eq, st = [], dict(cost=0.0, sell_fills=0, exits=0, exhaust=0, buys=0, buy_qty_cut=0, reset_qty=0)
    eq_adj, scale, reset_info = [], 1.0, []
    exit_log, hist = [], []

    def sell(q, price, d, why):
        nonlocal cash, pos, basis
        q = min(q, pos)
        if q <= 0:
            return 0
        avg = basis / pos
        notional = q * price
        fee = notional * c_
        cash += notional - fee
        st['cost'] += fee
        basis -= avg * q
        pos -= q
        if pos == 0:
            basis = 0.0
        return q

    for i, (d, C) in enumerate(days):
        closes.append(C)
        prev_d = days[i - 1][0] if i else d
        # 1) 어제 줄 체결 (종가 >= 줄 가격)
        live = lines
        pos0 = pos
        left = []
        for l in sorted(live, key=lambda x: x['price']):
            if C >= l['price'] and pos > 0:
                q = sell(l['qty'], l['price'], d, 'line')
                if q:
                    st['sell_fills'] += 1
                rest = l['qty'] - q
                if rest > 0:
                    left.append(dict(l, qty=rest))
            else:
                left.append(dict(l))
        # 2) 어제 신호의 청산 (오늘 종가)
        if pend is not None and pos > 0:
            frac, why = pend
            q = pos if frac >= 1.0 else max(1, int(pos * frac))
            q = sell(q, C, d, why)
            if q:
                st['exits'] += 1
                st['sell_fills'] += 1
                exit_log.append((d, why, q))
        pend = None
        # 2.5) 회차 종료 분리 (VERIFY.md 4.2: 청산 뒤·매수 앞, 보유 0일 때만)
        if sep is not None and round_was_open and pos == 0:
            sst['cash'] = cash
            SEP.round_close(sst, init_cash, sep, c_, pos)
            cash = sst['cash']
            round_was_open = False
        # 3) 오늘 매수 체결 (표에서 역산한 내역)
        bq = 0
        bprice = None
        f = fmap.get(d)
        if f:
            want, pr = f['qty'], f['price']
            afford = int(cash // (pr * (1 + c_)))
            bq = min(want, afford)
            if bq < want:
                st['exhaust'] += 1
                st['buy_qty_cut'] += want - bq
            if bq > 0:
                notional = bq * pr
                fee = notional * c_
                cash -= notional + fee
                st['cost'] += fee
                basis += notional
                pos += bq
                st['buys'] += 1
                bprice = pr
        if sep is not None and pos > 0:
            round_was_open = True
        # 4) 청산 신호 판단 (오늘 종가까지)
        if pos == 0:
            peak = None
        else:
            peak = C if peak is None else max(peak, C)
        run = XR.below_run_update(run, closes, p['ma_n']) if p['exit_mode'] == 'B' else 0
        if pos > 0:
            avg = basis / pos
            if p['exit_mode'] == 'A':
                fr = XR.exit_A(C, avg, p['stop_x'])
                if fr > 0:
                    pend = (fr, 'A')
            elif p['exit_mode'] == 'B':
                fr, run = XR.exit_B(run, p['ma_m'], p['exit_ratio'])
                if fr > 0:
                    pend = (fr, 'B')
            elif p['exit_mode'] == 'C':
                fr = XR.exit_C(C, peak, p['trail_y'])
                if fr > 0:
                    pend = (fr, 'C')
        # 5) 내일 줄 만들기 (S2 이월 + S3 묶음 + 임시 목표 줄)
        nl = [dict(l, price=SB.s2_carry(l['price'], prev_d, d)) for l in left] if i else []
        if bq > 0:
            nl.append(dict(price=SB.s3_price(bprice), qty=bq, tag='S3'))
        nl = SB.trim_lines(nl, pos)
        resid = pos - sum(l['qty'] for l in nl)
        if resid > 0:
            X = (basis / pos) * (1 + p['target_pct'])
            nl.append(dict(price=SB.s4_price(C, X, d, p['p1']), qty=resid, tag='S4'))
        lines = SB.merge_lines(nl, SB.MAX_LINES) if pos > 0 else []
        eq.append(cash + pos * C)
        eq_adj.append(eq[-1] * scale)
        # 6) 시즌 리셋: 그날 기록까지 마친 뒤 보유 0·현금 init_cash로 되돌린다 (버려진 보유 주수는 reset_qty, 청산 비용은 0으로 가정)
        if d in rdays:
            end_eq = eq[-1]
            reset_info.append((d, pos, round(end_eq, 2)))
            st['reset_qty'] += pos
            scale *= end_eq / init_cash
            if sep is not None:
                # 보유가 남았으면 종가로 청산한 것으로 본다 (비용 0, v0.1.1 가정과 같음). 이 경우 reset_qty에 주수가 남는다.
                cash += pos * C
                sst['cash'] = cash
                SEP.season_reset(sst, init_cash, 0)
                cash = sst['cash']
                round_was_open = False
            cash, pos, basis = init_cash, 0, 0.0
            lines, peak, run, pend = [], None, 0, None
        if sep is not None:
            sst['cash'] = cash
            total.append(SEP.total_net(sst, pos * C))
            sep_hist.append((sst['n_sep'], sst['sep_total'], sst['sep_cost'], sst['bucket']))
        hist.append(dict(st))   # 날짜별 누적 집계 (구간별로 나눠 내기 위함)
    return dict(equity=eq, equity_adj=eq_adj, dates=[d for d, _ in days], closes=[c for _, c in days], cash=cash, pos=pos, stats=st, hist=hist,
                exit_log=exit_log, reset_info=reset_info, total=total, sep_hist=sep_hist, sep_state=sst)


def segment_metrics(eq, a, b, base):
    """eq[a:b] 구간 지표. base = 구간 직전 평가금(없으면 시작 현금). 수익률·MDD는 구간 안에서 잰다."""
    seg = eq[a:b]
    if not seg:
        return dict(ret=float('nan'), mdd=float('nan'))
    pk, mdd = base, 0.0
    for v in seg:
        pk = max(pk, v)
        mdd = max(mdd, (pk - v) / pk if pk > 0 else 0.0)
    return dict(ret=seg[-1] / base - 1, mdd=mdd)


def evaluate(rows, fills, params, init_cash=INIT_CASH):
    res = run_backtest(rows, fills, params, init_cash)
    eq = res['equity']
    k = int(len(eq) * SPLIT)
    res['explore'] = segment_metrics(eq, 0, k, init_cash)
    res['holdout'] = segment_metrics(eq, k, len(eq), eq[k - 1] if k else init_cash)
    ea = res['equity_adj']
    res['explore_adj'] = segment_metrics(ea, 0, k, init_cash)
    res['holdout_adj'] = segment_metrics(ea, k, len(ea), ea[k - 1] if k else init_cash)
    res['split_date'] = res['dates'][k] if k < len(res['dates']) else None
    h0 = res['hist'][k - 1] if k else {x: 0 for x in res['stats']}
    res['stats_explore'] = dict(h0)
    res['stats_holdout'] = {x: res['stats'][x] - h0[x] for x in res['stats']}
    return res


def seg_dd(vals, base):
    """총합산 구간 지표. vals = 구간 일별 총합산, base = 구간 직전 값. MDD·회복은 [base]+vals 안에서 잰다 (구간 시작이 첫 고점)."""
    eq = [base] + list(vals)
    mdd, a, b, rec = SEP.mdd_info(eq)
    if mdd == 0.0:
        rec_days, unrec = 0, 0
    elif rec is None:
        rec_days, unrec = None, len(eq) - 1 - b      # 미회복: 저점 뒤 자료 끝까지 지난 거래일
    else:
        rec_days, unrec = rec - b, 0
    return dict(ret=eq[-1] / base - 1, mdd=mdd, rec=rec_days, unrec=unrec, wet=SEP.longest_underwater(eq), n=len(vals))


def evaluate_sep(rows, fills, exit_params, sep, init_cash=INIT_CASH):
    """분리 있음/없음 한 셀의 지표 (VERIFY.md 5절). 총합산 = 운용(현금+보유) + 버킷 + 리셋 인출분 - 외부 주입.
    상승/급락 경계 = 종가 최고일 (데이터로 자동). 상승 = 처음~최고일, 급락 = 최고일 다음~끝. 탐색 앞 70%·뒤 30%는 참고
    (뒤 30%는 판 4 검증 1/1로 이미 본 구간이라 오염 표기)."""
    res = run_backtest(rows, fills, exit_params, init_cash, sep=sep)
    tot, dates, closes = res['total'], res['dates'], res['closes']
    n = len(tot)
    pk = max(range(n), key=lambda i: (closes[i], -i))   # 종가 최고일 (같으면 앞선 날)
    k = int(n * SPLIT)
    out = dict(dates=dates, total=tot, peak_date=dates[pk], peak_close=closes[pk], split_date=dates[k] if k < n else None)
    out['full'] = seg_dd(tot, init_cash)
    out['explore'] = seg_dd(tot[:k], init_cash)
    out['holdout'] = seg_dd(tot[k:], tot[k - 1])
    out['rise'] = seg_dd(tot[:pk + 1], init_cash)
    out['crash'] = seg_dd(tot[pk + 1:], tot[pk])
    sh = res['sep_hist']
    at = lambda i: sh[i]
    last = sh[-1]
    out['sep_n'], out['sep_total'], out['sep_cost'], out['bucket'] = last
    out['sep_n_rise'] = at(pk)[0]
    out['sep_n_crash'] = last[0] - at(pk)[0]
    out['trade_cost'] = res['stats']['cost']
    st = res['stats']
    out['exhaust'], out['buy_cut'], out['buys'], out['exits'], out['reset_qty'] = st['exhaust'], st['buy_qty_cut'], st['buys'], st['exits'], st['reset_qty']
    sst = res['sep_state']
    out['rbucket'], out['injected'] = sst['rbucket'], sst['injected']
    out['end_total'] = tot[-1]
    out['total_profit'] = tot[-1] - init_cash
    out['op_end'] = res['cash'] + res['pos'] * closes[-1]
    out['unsep_profit_end'] = max(0.0, out['op_end'] - init_cash)   # 보호 지연: 기말 운용계좌가 M*를 넘는 부분 (분리 안 된 이익)
    out['acc_end'] = sst['acc']
    out['equity'] = res['equity']
    out['stats'] = dict(st)
    return out


def sep_judge_input(m):
    return dict(crash_mdd=m['crash']['mdd'], crash_rec=m['crash']['rec'], rise_ret=m['rise']['ret'],
                n_sep=m['sep_n'], sep_cost=m['sep_cost'], total_profit=m['total_profit'])


def _rec_txt(d):
    return '미회복 %d일째' % d['unrec'] if d['rec'] is None else '%d거래일' % d['rec']


def fmt_sep(name, m):
    f, r, c = m['full'], m['rise'], m['crash']
    return ('%-14s 총합산 %+8.2f%% MDD %6.2f%% 회복 %s 최장수중 %d일 | 상승 %+8.2f%% MDD %6.2f%% | 급락 %+8.2f%% MDD %6.2f%% 회복 %s 최장수중 %d일 | '
            '분리 %2d회(상승 %d·급락 %d) 합계 %9.2f 분리비용 %7.2f 매매비용 %8.2f | 고갈 %2d회 절단 %4d주 매수 %3d회 청산 %2d회 | '
            '기말 버킷 %9.2f 리셋인출 %9.2f 미분리이익 %9.2f') % (
        name, f['ret'] * 100, f['mdd'] * 100, _rec_txt(f), f['wet'], r['ret'] * 100, r['mdd'] * 100,
        c['ret'] * 100, c['mdd'] * 100, _rec_txt(c), c['wet'], m['sep_n'], m['sep_n_rise'], m['sep_n_crash'],
        m['sep_total'], m['sep_cost'], m['trade_cost'], m['exhaust'], m['buy_cut'], m['buys'], m['exits'],
        m['bucket'], m['rbucket'], m['unsep_profit_end'])


def run_sep_grid(rows, fills, init_cash=INIT_CASH):
    """격자 5셀 전부 계산해서 돌려준다. 공통 청산은 C_y0.10 (격자 GRID의 값 그대로). 장부는 main이 센다."""
    ex = dict(GRID['C_y0.10'])
    out = {}
    for cid, sp in SEP.GRID.items():
        out[cid] = evaluate_sep(rows, fills, ex, sp, init_cash)
    # N0 자기 점검: 분리 인자 없는 기존 C_y0.10과 평가금·집계가 완전히 같아야 한다
    plain = run_backtest(rows, fills, ex, init_cash)
    assert plain['equity'] == out['N0']['equity'] and plain['stats'] == out['N0']['stats'], 'N0가 기존 C_y0.10과 다르다'
    return out


# ---- 실행 횟수 장부 ----
def load_log(path):
    if os.path.exists(path):
        return json.load(open(path, encoding='utf-8'))
    return dict(explore_runs=0, holdout_runs=0, entries=[])


def save_log(path, log):
    json.dump(log, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def charge(log, kind, n=1):
    """횟수를 세고, 상한을 넘으면 False. 실제 실행 전에 부른다."""
    if kind == 'explore':
        if log['explore_runs'] + n > MAX_EXPLORE_RUNS:
            return False
        log['explore_runs'] += n
    else:
        if log['holdout_runs'] + n > MAX_HOLDOUT_RUNS:
            return False
        log['holdout_runs'] += n
    return True


def fmt(name, res, which):
    m, ma, s = res[which], res[which + '_adj'], res['stats_' + which]
    return ('%-18s 수익률 %+7.2f%%  MDD %6.2f%%  | 보정 수익률 %+7.2f%%  MDD %6.2f%%  | '
            '현금고갈 %2d회  비용 %7.2f  청산 %2d회  매수 %3d회  리셋폐기 %3d주') % (
        name, m['ret'] * 100, m['mdd'] * 100, ma['ret'] * 100, ma['mdd'] * 100,
        s['exhaust'], s['cost'], s['exits'], s['buys'], s['reset_qty'])


def parse_ids(vals):
    """--holdout 값(공백·쉼표로 나눈 id들) -> 중복 뺀 id 목록(입력 순서 유지). 비면 빈 목록."""
    out = []
    for v in vals or []:
        for t in v.split(','):
            t = t.strip()
            if t and t not in out:
                out.append(t)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('data')
    ap.add_argument('--grid', action='store_true')
    ap.add_argument('--run')
    ap.add_argument('--holdout', nargs='+')   # 격자 id 하나 이상 (공백 또는 쉼표). 몇 개든 검증 1회로 센다
    ap.add_argument('--log', default='bt_run_log.json')
    ap.add_argument('--allow-unverified', action='store_true')
    ap.add_argument('--sep-grid', action='store_true')   # 분리 격자 5셀 (탐색 5회로 셈)
    ap.add_argument('--out', default='sep_grid_result.json')
    a = ap.parse_args(argv)
    h = hashlib.sha256(open(a.data, 'rb').read()).hexdigest()
    ok = (h in (EXPECT, EXPECT_V12))
    print('입력 해시', h[:8], ('일치 (%s)' % ('v10' if h == EXPECT else 'v12')) if ok else '불일치(기대 %s 또는 %s)' % (EXPECT[:8], EXPECT_V12[:8]))
    if not ok and not a.allow_unverified:
        print('중단: 입력 해시 불일치. 횟수는 세지 않았다. (--allow-unverified로 강행하면 횟수를 센다)')
        return 2
    ids = list(GRID) if a.grid else ([a.run] if a.run else [])
    hids = parse_ids(a.holdout)
    if a.holdout is not None:
        if not hids:
            print('--holdout에 격자 id가 필요하다'); return 2
        bad = [i for i in hids if i not in GRID]
        if bad:
            print('알 수 없는 격자 id:', ', '.join(bad), '(횟수는 세지 않았다)'); return 2
        ids = []
    if a.sep_grid:
        if ids or hids:
            print('--sep-grid는 다른 실행 옵션과 같이 쓰지 않는다'); return 2
        ids = list(SEP.GRID)
    if not ids and not hids:
        print('--grid, --run, --holdout, --sep-grid 중 하나가 필요하다'); return 2
    for i in ids:
        if i not in (SEP.GRID if a.sep_grid else GRID):
            print('알 수 없는 격자 id:', i); return 2
    log = load_log(a.log)
    kind = 'holdout' if hids else 'explore'
    n = 1 if hids else len(ids)   # 검증은 id가 몇 개든 이 실행 1회로 센다
    if not charge(log, kind, n):
        print('중단: %s 실행 횟수 상한 초과 (이미 %d회, 상한 %d). 실행하지 않았다.' % (
            kind, log[kind + '_runs'], MAX_HOLDOUT_RUNS if hids else MAX_EXPLORE_RUNS))
        return 3
    save_log(a.log, log)   # 실행 전에 먼저 기록 (실패해도 횟수는 소모)
    rows = prepare_rows(json.load(open(a.data, encoding='utf-8')))
    fills = derive_buy_fills(rows)
    print('행 %d, 매수 체결 %d건' % (len(rows), len(fills)))
    if a.sep_grid:
        res = run_sep_grid(rows, fills)
        n0 = res['N0']
        print('[분리 격자 5셀 — 탐색 5회로 셈. 공통 청산 C_y0.10, M*=10000, 비용 편도 0.1%, 버킷 수익 0%, 매수 수량은 표 체결 그대로]')
        print('[전체 구간 %s~%s %d거래일. 상승/급락 경계 = 종가 최고일 %s (종가 %.2f): 상승 = 처음~최고일, 급락 = 최고일 다음~끝]' % (
            n0['dates'][0], n0['dates'][-1], len(n0['dates']), n0['peak_date'], n0['peak_close']))
        print('[이미 본 구간 표기(오염): 판 4 검증 1/1이 본 뒤 30%% = %s~ 는 참고로만 쓴다. 이번 제출은 탐색 결과이며 검증 통과가 아니다]' % n0['split_date'])
        print('N0 자기 점검: 분리 없는 기존 C_y0.10 평가금·집계와 완전히 같음')
        for cid in SEP.GRID:
            print(fmt_sep(cid, res[cid]))
        print('[참고: 탐색 앞 70%% (~%s 이전) / 뒤 30%% 오염 구간 총합산 수익률·MDD]' % n0['split_date'])
        for cid in SEP.GRID:
            e, o = res[cid]['explore'], res[cid]['holdout']
            print('%-14s 앞 70%% %+8.2f%% MDD %6.2f%% | 뒤 30%%(오염) %+8.2f%% MDD %6.2f%%' % (cid, e['ret'] * 100, e['mdd'] * 100, o['ret'] * 100, o['mdd'] * 100))
        print('[Q23 채택 기준 판정 — 임계값은 12_judge_q23.py에 실행 전 고정]')
        verdicts = {}
        for cid in SEP.GRID:
            if cid == 'N0':
                continue
            j = JG.judge(sep_judge_input(res[cid]), sep_judge_input(n0))
            verdicts[cid] = j
            print('%s: %s' % (cid, j['verdict']))
            for key, nm in (('c1', '①'), ('c2', '②'), ('c3', '③')):
                print('   %s %s %s' % (nm, '통과' if j[key][0] else '불통과', j[key][1]))
        log['entries'].append(dict(kind='explore', ids=list(SEP.GRID), grid='sep', input=h[:8],
                                   note='분리 격자 5셀(N0 재실행 포함) = 탐색 5회, Muse Q20 정정 2026-11-19'))
        save_log(a.log, log)
        slim = {cid: {k: v for k, v in res[cid].items() if k not in ('total', 'equity', 'dates')} for cid in res}
        json.dump(dict(input=h, verdicts={c: {k: list(v) if isinstance(v, tuple) else v for k, v in j.items()} for c, j in verdicts.items()},
                       cells=slim), open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('누적 탐색 %d/%d회, 검증 %d/%d회' % (log['explore_runs'], MAX_EXPLORE_RUNS, log['holdout_runs'], MAX_HOLDOUT_RUNS))
        return 0
    if hids:
        results = [(i, evaluate(rows, fills, GRID[i])) for i in hids]   # 먼저 전부 계산한 뒤 한꺼번에 출력
        print('[검증 구간 %s~ = 뒤 30%%, 격자 id %d개를 이 실행 1회로 셈]' % (results[0][1]['split_date'], len(hids)))
        for i, res in results:
            print(fmt(i, res, 'holdout'))
        print('[참고: 같은 시뮬레이션의 탐색 구간 보정값 — 이미 본 값, 재현 대조용]')
        for i, res in results:
            m = res['explore_adj']
            print('%-18s 보정 수익률 %+7.2f%%  MDD %6.2f%%' % (i, m['ret'] * 100, m['mdd'] * 100))
        log['entries'].append(dict(kind='holdout', ids=hids, input=h[:8]))
    else:
        print('[탐색 구간 = 앞 70%]')
        for i in ids:
            res = evaluate(rows, fills, GRID[i])
            print(fmt(i, res, 'explore'))
            log['entries'].append(dict(kind='explore', id=i, params=GRID[i], input=h[:8]))
    save_log(a.log, log)
    print('누적 탐색 %d/%d회, 검증 %d/%d회' % (log['explore_runs'], MAX_EXPLORE_RUNS, log['holdout_runs'], MAX_HOLDOUT_RUNS))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
