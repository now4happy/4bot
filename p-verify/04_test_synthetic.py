"""P매매 우리 매도 규칙 1단계 — 합성 데이터 테스트 v0.1.2 (2026-11-17, 클로드 2번) — 방: P매매 검증 (p-verify)

사용: python3 -I 04_test_synthetic.py
실제 v10 데이터를 쓰지 않는다. v10과 같은 필드 구조로 만든 가짜 383행(난수 고정)과 손으로 계산한 작은 표로
틀이 맞게 도는지만 본다. 이 테스트 통과는 '코드가 설계대로 돈다'는 뜻이지, 어떤 규칙이 좋다는 증거가 아니다.

버전 기록: v0.1.0 (53개) -> v0.1.1 시즌 리셋 테스트 추가 -> v0.1.2 (이 파일) 리셋 손계산·--holdout 다중 id 테스트.
주의: v0.1.1 04(fa1c0850, 67개)의 원문은 이 작업 공간에 없어 v0.1.0 검사 + 새로 쓴 리셋·다중 id 검사로 다시 만들었다.
"""
import sys, os, io, json, random, datetime, tempfile, contextlib, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(fname, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, fname))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SB = _load('01_sell_blocks.py', 'sell_blocks')
BT = _load('03_backtest.py', 'backtest')

PASS = 0


def ok(cond, msg):
    global PASS
    if not cond:
        print('실패:', msg)
        sys.exit(1)
    PASS += 1


def make_rows(seed=7, n_days=381, crash_at=None):
    """v10과 같은 필드의 가짜 표. 04-07 행 1개 + 영업일 n_days + 2026-01-05 리셋 행 1개 = 383행."""
    rnd = random.Random(seed)
    d = datetime.date(2025, 5, 13)
    rows = [dict(종가일='2025-04-07', 종가=9.15, 매수=[], 매도=[], 보유평단=None, 잔금=10000.0, 총수익률=None,
                 직전매매개수=None, 현재보유개수=0, 시즌실현수익=None, 시즌=None, 전부_환산=None)]
    cash, qty, price, basis = 10000.0, 0, 18.0, 0.0
    made = 0
    while made < n_days:
        if d.weekday() < 5:
            price *= 1 + rnd.gauss(0.002, 0.04)
            if crash_at is not None and made == crash_at:
                price *= 0.6
            price = max(price, 2.0)
            if rnd.random() < 0.4 and cash > 500:
                q = rnd.randint(5, 30)
                pr = round(price * (1 + rnd.uniform(-0.01, 0.01)), 2)
                q = min(q, int(cash // pr))
                cash -= q * pr; basis += q * pr; qty += q
            if qty > 0 and rnd.random() < 0.08:        # 원작자 쪽 매도 (우리 백테스트는 이 매도를 버린다)
                sq = rnd.randint(1, qty)
                cash += sq * price; basis -= basis / qty * sq; qty -= sq
            rows.append(dict(종가일=d.isoformat(), 종가=round(price, 2), 매수=[dict(price=round(price * .99, 2), qty=10)],
                             매도=[], 보유평단=round(basis / qty, 2) if qty else None, 잔금=round(cash, 2), 총수익률=0.0,
                             직전매매개수=0, 현재보유개수=qty, 시즌실현수익=0.0, 시즌=1, 전부_환산=None))
            made += 1
            if d.isoformat() == '2026-01-05':
                rows.append(dict(rows[-1], 잔금=10000.0, 현재보유개수=0, 보유평단=None))   # 리셋 행(같은 날짜 둘째 행)
                cash, qty, basis = 10000.0, 0, 0.0
        d += datetime.timedelta(days=1)
    return rows


def mk(date, close, cash, qty):
    """손계산용 한 행 (v10 필드 구조)."""
    return dict(종가일=date, 종가=close, 매수=[], 매도=[], 보유평단=None, 잔금=cash, 총수익률=None,
                직전매매개수=0, 현재보유개수=qty, 시즌실현수익=0.0, 시즌=1, 전부_환산=None)


def run_main(argv):
    """BT.main을 부르고 (반환값, 출력 문자열)을 돌려준다."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = BT.main(argv)
    return rc, buf.getvalue()


def main():
    # 1) 블록
    SB.__name__
    ok(SB.s2_steps('2026-11-12', '2026-11-13') == 0, '금요일 0계단')
    ok(SB.s2_steps('2026-11-13', '2026-11-16') == 2, '월요일 2계단')
    ok(SB.s2_steps('2026-11-17', '2026-11-18') == 1, '평일 1계단')
    ok(SB.s2_steps('2026-11-25', '2026-11-27') == 1, '휴일 낀 금요일(차이 2일)은 1계단')
    ok(SB.s2_carry(73.74, '2026-11-13', '2026-11-16') == 73.59, '73.74 -> 73.59')
    ok(SB.s2_carry(73.74, '2026-02-26', '2026-03-02') == 73.74, '03-03 전 이월 없음')
    ok(SB.s3_price(100.0) == 100.15, 'S3')
    ok(SB.s4_price(48.76, 40, '2026-11-16') == 48.78, 'S4 하한')
    ok(SB.s4_price(48.76, 40, '2026-11-16', p1=True) == 49.78, 'S4 P1')
    ok(SB.s4_price(48.76, 40, '2026-10-07', p1=True) == 48.78, 'P1은 10-08부터')
    t = SB.trim_lines([dict(price=10, qty=5), dict(price=12, qty=5)], 7)
    ok(sum(l['qty'] for l in t) == 7 and t[0]['price'] == 10 and t[0]['qty'] == 5, '높은 줄부터 줄임')
    # 2) 데이터 구조·체결 역산
    raw = make_rows()
    ok(len(raw) == 383, '합성 383행')
    rows = BT.prepare_rows(raw)
    ok(len(rows) == 382 and all(r['종가일'] != '2025-04-07' for r in rows), '04-07 행 제외')
    fills = BT.derive_buy_fills(rows)
    ok(len(fills) > 30 and all(f['qty'] > 0 and f['price'] > 0 for f in fills), '매수 체결 역산')
    ok(not any(f['date'] == '2026-01-05' and f['qty'] > 100000 for f in fills), '리셋 행은 체결로 안 셈')
    # 3) 백테스트 불변식
    for pr in (dict(), dict(exit_mode='A'), dict(exit_mode='B'), dict(exit_mode='C'), dict(p1=True)):
        r1 = BT.run_backtest(rows, fills, pr)
        r2 = BT.run_backtest(rows, fills, pr)
        ok(r1['equity'] == r2['equity'] and r1['equity_adj'] == r2['equity_adj'], '같은 입력 -> 같은 결과 %s' % pr)
        ok(r1['pos'] >= 0 and r1['cash'] >= -1e-6, '보유·현금 음수 없음 %s' % pr)
        ok(len(r1['equity']) == 381 and len(r1['equity_adj']) == 381, '날짜 중복 행은 한 번만 %s' % pr)
        ok(all(v > 0 for v in r1['equity']) and all(v > 0 for v in r1['equity_adj']), '평가금 양수')
    # 4) 급락 -> 손절 A는 다음 행 종가에서 청산, 신호 당일에는 청산 안 함
    craw = make_rows(seed=3, crash_at=120)
    crow = BT.prepare_rows(craw)
    cf = BT.derive_buy_fills(crow)
    ra = BT.run_backtest(crow, cf, dict(exit_mode='A', stop_x=0.15))
    ok(ra['stats']['exits'] >= 1, '급락 합성에서 A 청산 발생')
    d_exit = ra['exit_log'][0][0]
    dates = [r['종가일'] for r in crow]
    ok(dates.index(d_exit) >= 1, '청산은 신호 다음 행')
    rn = BT.run_backtest(crow, cf, dict(exit_mode='none'))
    ok(rn['stats']['exits'] == 0, '기준선에는 청산 없음')
    # 5) 현금 고갈 카운트 (시작 현금을 작게)
    rs = BT.run_backtest(rows, fills, dict(), init_cash=300.0)
    ok(rs['stats']['exhaust'] > 0 and rs['cash'] >= -1e-6, '현금 고갈 카운트·음수 방지')
    # 6) 비용: 비용이 클수록 최종 평가금이 작다
    lo = BT.run_backtest(rows, fills, dict(cost_bps=0.0))['equity'][-1]
    hi = BT.run_backtest(rows, fills, dict(cost_bps=50.0))['equity'][-1]
    ok(hi < lo, '비용 반영')
    # 7) 구간 분리
    ev = BT.evaluate(rows, fills, dict())
    ok(ev['split_date'] > rows[0]['종가일'], '구간 나눔')
    tot = ev['stats']
    ok(all(ev['stats_explore'][x] + ev['stats_holdout'][x] == tot[x] for x in tot if x != 'cost') and
       abs(ev['stats_explore']['cost'] + ev['stats_holdout']['cost'] - tot['cost']) < 1e-6, '구간별 집계 합 = 전체')
    # 8) 시즌 리셋 손계산 (비용 0, 청산 없음): 4일, 01-05에 100주 매수 -> 같은 날 리셋 -> 01-06에 50주 매수
    hand = [mk('2026-01-02', 10.0, 10000.0, 0), mk('2026-01-05', 12.0, 9000.0, 100),
            mk('2026-01-05', 12.0, 10000.0, 0), mk('2026-01-06', 15.0, 9250.0, 50), mk('2026-01-07', 14.0, 9250.0, 50)]
    hr = BT.prepare_rows(hand)
    ok([r['잔금'] for r in hr] == [10000.0, 9000.0, 10000.0, 9250.0, 9250.0], '리셋 행은 같은 날짜 맨 뒤')
    hf = BT.derive_buy_fills(hr)
    ok(hf == [dict(date='2026-01-05', qty=100, price=10.0), dict(date='2026-01-06', qty=50, price=15.0)], '손계산 체결')
    ok(BT.reset_days(hr) == {'2026-01-05'}, '리셋 날 찾기')
    h0 = BT.run_backtest(hr, hf, dict(cost_bps=0.0))
    ok(h0['equity'] == [10000.0, 10200.0, 10000.0, 9950.0], '리셋 원값 평가금 [10000,10200,10000,9950]')
    ok([round(v, 6) for v in h0['equity_adj']] == [10000.0, 10200.0, 10200.0, 10149.0], '보정 평가금 [10000,10200,10200,10149]')
    ok(h0['reset_info'] == [('2026-01-05', 100, 10200.0)], '리셋 때 버린 보유 100주·평가금 10200')
    ok(h0['stats']['reset_qty'] == 100, 'reset_qty 100')
    ok(h0['pos'] == 50 and abs(h0['cash'] - 9250.0) < 1e-9, '리셋 날 남은 줄이 지워져 01-06에 안 팔림 (보유 50·현금 9250)')
    he = BT.evaluate(hr, hf, dict(cost_bps=0.0))      # 4일 -> 앞 2일 탐색, 뒤 2일 검증
    ok(abs(he['explore']['ret'] - 0.02) < 1e-12 and he['explore_adj']['ret'] == he['explore']['ret'], '탐색 구간 +2% (원값=보정)')
    ok(abs(he['holdout']['ret'] - (9950 / 10200 - 1)) < 1e-12 and abs(he['holdout']['mdd'] - 250 / 10200) < 1e-12,
       '원값 검증 구간: 리셋 폭(10200->10000)이 손실로 들어간다')
    ok(abs(he['holdout_adj']['ret'] - (10149 / 10200 - 1)) < 1e-9 and abs(he['holdout_adj']['mdd'] - 51 / 10200) < 1e-9,
       '보정 검증 구간: 리셋 폭이 빠진 값')
    ok(he['holdout']['mdd'] > he['holdout_adj']['mdd'], '원값 MDD > 보정 MDD')
    ok(he['stats_explore']['reset_qty'] == 100 and he['stats_holdout']['reset_qty'] == 0, '리셋폐기 주수는 탐색 구간에 잡힘')
    # 리셋 없음 (잔금 10000인 리셋 행이 없으면 한 계좌로 이어감, 보정 = 원값)
    nr = BT.prepare_rows([hand[0], hand[1], mk('2026-01-06', 15.0, 8250.0, 150), mk('2026-01-07', 14.0, 8250.0, 150)])
    ok(BT.reset_days(nr) == set(), '리셋 행 없으면 리셋 없음')
    n0 = BT.run_backtest(nr, BT.derive_buy_fills(nr), dict(cost_bps=0.0))
    ok(n0['equity_adj'] == n0['equity'] and n0['stats']['reset_qty'] == 0 and n0['reset_info'] == [], '리셋 없으면 보정=원값')
    # 리셋 때 고점(peak)이 지워진다: 안 지워지면 01-06 새 보유가 옛 고점 12 대비 -12.5%로 보여 C 청산 신호가 난다
    pk = BT.prepare_rows([mk('2026-01-02', 10.0, 10000.0, 0), mk('2026-01-05', 12.0, 9000.0, 100),
                          mk('2026-01-05', 12.0, 10000.0, 0), mk('2026-01-06', 10.5, 9475.0, 50),
                          mk('2026-01-07', 10.5, 9475.0, 50)])
    pr_ = BT.run_backtest(pk, BT.derive_buy_fills(pk), dict(exit_mode='C', trail_y=0.10, cost_bps=0.0))
    ok(pr_['stats']['exits'] == 0 and pr_['pos'] == 50, '리셋 뒤 고점 초기화 -> 새 시즌에 옛 고점 기준 청산 없음')
    # 9) 횟수 상한·해시 가드 (파일 입출력)
    ok(len(BT.PARAM_KEYS) <= 10, '파라미터 10개 이하')
    ok(len(BT.GRID) == 11 and BT.MAX_EXPLORE_RUNS == 30 and BT.MAX_HOLDOUT_RUNS == 1, '격자 11회, 탐색 30회·검증 1회 상한')
    ok(BT.parse_ids(['A_x0.15', 'B_n50_m2_r1.0,C_y0.10', 'A_x0.15']) == ['A_x0.15', 'B_n50_m2_r1.0', 'C_y0.10'], 'id 공백·쉼표·중복 처리')
    ok(BT.parse_ids(None) == [] and BT.parse_ids(['', ' , ']) == [], '빈 id')
    three = ['A_x0.15', 'B_n50_m2_r1.0', 'C_y0.10']
    with tempfile.TemporaryDirectory() as td:
        dp = os.path.join(td, 'fake.json'); lg = os.path.join(td, 'log.json')
        json.dump(raw, open(dp, 'w', encoding='utf-8'), ensure_ascii=False)
        rc, out = run_main([dp, '--grid', '--log', lg])
        ok(rc == 2 and '불일치' in out, '해시 불일치면 중단')
        ok(not os.path.exists(lg), '중단 시 횟수를 세지 않음')
        for _ in range(2):
            rc, out = run_main([dp, '--grid', '--allow-unverified', '--log', lg])
            ok(rc == 0 and out.count('보정 수익률') == 11, '격자 실행 (보정 열 출력)')
        ok(json.load(open(lg))['explore_runs'] == 22, '22회 누적')
        ok(run_main([dp, '--grid', '--allow-unverified', '--log', lg])[0] == 3, '33회째는 거부')
        ok(json.load(open(lg))['explore_runs'] == 22, '거부 시 횟수 유지')
        # 다중 id 검증: 나쁜 id가 섞이면 아무것도 안 세고 중단
        rc, out = run_main([dp, '--holdout'] + three[:2] + ['NOPE', '--allow-unverified', '--log', lg])
        ok(rc == 2 and '알 수 없는 격자 id' in out and json.load(open(lg))['holdout_runs'] == 0, '나쁜 id -> 중단, 검증 횟수 안 씀')
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                run_main([dp, '--holdout', '--allow-unverified', '--log', lg])
            ok(False, '--holdout에 id가 없으면 거부해야 한다')
        except SystemExit as e:
            ok(e.code == 2 and json.load(open(lg))['holdout_runs'] == 0, '--holdout에 id 없음 -> 거부, 검증 횟수 안 씀')
        # 다중 id 검증 1회
        rc, out = run_main([dp, '--holdout'] + three + ['--allow-unverified', '--log', lg])
        ok(rc == 0, '다중 id 검증 실행')
        lgd = json.load(open(lg))
        ok(lgd['holdout_runs'] == 1 and lgd['explore_runs'] == 22, '3개 id를 넣어도 검증 1회, 탐색 횟수는 그대로')
        ok(lgd['entries'][-1] == dict(kind='holdout', ids=three, input=lgd['entries'][-1]['input']), '장부에 id 목록 기록')
        ok(all(('%-18s 수익률' % i) in out for i in three) and out.count('리셋폐기') == 3, '세 id 모두 검증 행 출력')
        ok('[탐색 구간' not in out and '검증 구간' in out, '탐색 구간 표는 안 냄 (참고 줄만)')
        # 같은 id를 단독으로 평가한 결과와 다중 실행의 행이 같다 (id 개수와 무관)
        rr = BT.prepare_rows(json.load(open(dp, encoding='utf-8')))
        ff = BT.derive_buy_fills(rr)
        for i in three:
            ok(BT.fmt(i, BT.evaluate(rr, ff, BT.GRID[i]), 'holdout') in out, '다중 실행 행 = 단독 평가 행 (%s)' % i)
        ok(run_main([dp, '--holdout', 'base', '--allow-unverified', '--log', lg])[0] == 3, '검증 2회째 거부')
        ok(json.load(open(lg))['holdout_runs'] == 1, '거부 시 검증 횟수 유지')
        # 쉼표 문법·중복
        lg2 = os.path.join(td, 'log2.json')
        rc, out = run_main([dp, '--holdout', 'A_x0.15,C_y0.10', 'A_x0.15', '--allow-unverified', '--log', lg2])
        l2 = json.load(open(lg2))
        ok(rc == 0 and l2['holdout_runs'] == 1 and l2['entries'][-1]['ids'] == ['A_x0.15', 'C_y0.10'], '쉼표·중복 -> id 2개, 검증 1회')
        # 단일 id(기존 사용법)도 그대로
        lg3 = os.path.join(td, 'log3.json')
        rc, out = run_main([dp, '--holdout', 'base', '--allow-unverified', '--log', lg3])
        ok(rc == 0 and json.load(open(lg3))['holdout_runs'] == 1, '단일 id 검증 1회 (기존 사용법)')
        # --run 한 개는 탐색 1회
        lg4 = os.path.join(td, 'log4.json')
        rc, out = run_main([dp, '--run', 'base', '--allow-unverified', '--log', lg4])
        ok(rc == 0 and json.load(open(lg4))['explore_runs'] == 1 and json.load(open(lg4))['holdout_runs'] == 0, '--run은 탐색 1회')
        # 해시 불일치 + 다중 id: 중단, 장부 파일 안 만듦
        lg5 = os.path.join(td, 'log5.json')
        rc, out = run_main([dp, '--holdout'] + three + ['--log', lg5])
        ok(rc == 2 and not os.path.exists(lg5), '해시 불일치 + 다중 id -> 중단, 장부 없음')
    print('04_test_synthetic: 확인 %d개 전부 통과' % PASS)


if __name__ == '__main__':
    main()
