"""P매매 우리 매도 P규칙 — 수익금 분리 층 합성 테스트 v0.1.0 (2026-11-19, 클로드 2번) — 방: P매매 검증 (p-verify)

사용: python3 -I 09_test_sep_layer.py     (인터넷·데이터 불필요)
손으로 계산한 값과 불변식(총합산 보존, 현금·버킷 음수 없음)을 본다.
이 테스트 통과는 '계좌 계산이 설계대로 돈다'는 뜻이지, 어떤 분리 규칙이 좋다는 증거가 아니다. 합성 데이터의 수익률은 의미가 없어 적지 않는다.
"""
import os, sys, random, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('sep', os.path.join(HERE, '08_sep_layer.py'))
S_ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S_)

PASS = 0


def ok(cond, msg):
    global PASS
    if not cond:
        print('실패:', msg)
        sys.exit(1)
    PASS += 1


def near(a, b, tol=1e-9):
    return abs(a - b) <= tol


def raises(fn):
    try:
        fn()
    except AssertionError:
        return True
    return False


def main():
    M = 10000.0
    # 1) cap, 전액, 문턱 0.10: 표의 33차 시작 잔금 14434.58 (초과분 4434.58 >= 1000)
    st = S_.new_state(14434.58); st['round_open_cash'] = M
    before = S_.total_net(st)
    S = S_.round_close(st, M, S_.GRID['C_h0.10'], 0.001, 0)
    ok(near(S, 4434.58), 'cap 전액 분리액')
    ok(near(st['cash'], M), '분리 뒤 운용 현금 = 목표 운용금액')
    ok(near(st['bucket'], 4434.58 * 0.999), '버킷 = 분리액 - 비용')
    ok(near(st['sep_cost'], 4.43458) and st['n_sep'] == 1, '비용·횟수')
    ok(near(before - S_.total_net(st), 4.43458), '총합산은 비용만큼만 줄어든다')
    ok(near(st['cash'] / 13, 10000.0 / 13), '다음 회차 B = 잔금 ÷ 13 = M*/13')
    # 2) cap, 절반
    st = S_.new_state(14434.58); st['round_open_cash'] = M
    S = S_.round_close(st, M, S_.GRID['C_h0.10_f0.5'], 0.001, 0)
    ok(near(S, 2217.29) and near(st['cash'], 12217.29), 'cap f=0.5')
    ok(near(st['bucket'], 2217.29 * 0.999), 'cap f=0.5 버킷')
    # 3) 문턱 경계 (h=0.25는 이진수로 정확)
    p = dict(mode='cap', f=1.0, h=0.25)
    ok(S_.separation_amount(12499.0, M, 0.0, p) == 0.0, '문턱 바로 아래는 0')
    ok(near(S_.separation_amount(12500.0, M, 0.0, p), 2500.0), '문턱에 닿으면 분리')
    # 4) 목표 아래면 cap은 0
    ok(S_.separation_amount(9500.0, M, 0.0, S_.GRID['C_h0.10']) == 0.0, '손실 상태에서 cap은 0')
    # 5) acc(래칫)는 손실을 상쇄하지 않는다: +300, -200, +800 (h=0.10, 문턱 1000)
    st = S_.new_state(M)
    pa, pc = S_.GRID['A_h0.10'], S_.GRID['C_h0.10']
    sc = S_.new_state(M)
    for profit in (300.0, -200.0, 800.0):
        st['cash'] += profit; S1 = S_.round_close(st, M, pa, 0.0, 0)
        sc['cash'] += profit; S2 = S_.round_close(sc, M, pc, 0.0, 0)
    ok(near(S1, 1100.0) and near(st['cash'], 9800.0) and st['acc'] == 0.0, 'acc는 양(+) 회차 수익 합 1100을 분리')
    ok(S2 == 0.0 and near(sc['cash'], 10900.0), 'cap은 초과분 900 < 문턱 1000이라 분리 안 함')
    # 6) 분리액은 현금을 넘지 못한다
    ok(near(S_.separation_amount(100.0, 0.0, 500.0, dict(mode='acc', f=1.0, h=0.0)), 100.0), '현금 상한')
    # 7) 보유가 있으면 분리 불가
    ok(raises(lambda: S_.round_close(S_.new_state(M), M, pc, 0.0, 5)), '보유>0이면 분리 거부')
    ok(raises(lambda: S_.season_reset(S_.new_state(M), M, 5)), '보유>0이면 리셋 거부')
    # 8) 시즌 리셋: 넘치면 rbucket, 모자라면 injected. 총합산은 변하지 않는다
    st = S_.new_state(10970.43)
    t0 = S_.total_net(st)
    S_.season_reset(st, M, 0)
    ok(near(st['cash'], M) and near(st['rbucket'], 970.43) and st['injected'] == 0.0, '리셋 초과분')
    ok(near(S_.total_net(st), t0), '리셋 총합산 보존 (초과)')
    st = S_.new_state(9000.0)
    t0 = S_.total_net(st)
    S_.season_reset(st, M, 0)
    ok(near(st['cash'], M) and near(st['injected'], 1000.0), '리셋 부족분은 주입으로 기록')
    ok(near(S_.total_net(st), t0), '리셋 총합산 보존 (부족: 주입을 뺀다)')
    # 9) 지표
    eq = [100, 110, 90, 95, 120]
    mdd, a, b, rec = S_.mdd_info(eq)
    ok(near(mdd, 20 / 110) and (a, b, rec) == (1, 2, 4), 'MDD·고점·저점·회복 위치')
    ok(S_.recovery_days(eq) == 2 and S_.longest_underwater(eq) == 2, '회복 2일, 수중 2일')
    ok(S_.recovery_days([100, 50, 60]) is None and S_.longest_underwater([100, 50, 60]) == 2, '미회복은 None')
    ok(S_.recovery_days([100, 100, 100]) == 0 and S_.longest_underwater([100, 100, 100]) == 0, '낙폭 없음')
    ok(S_.recovery_days([100, 90, 100, 95]) == 1 and S_.longest_underwater([100, 90, 100, 95]) == 1, '고점 되찾으면 수중 일수 초기화')
    # 10) 격자
    ok(len(S_.GRID) == 5 and 'N0' in S_.GRID, '격자 5셀 (N0 포함)')
    ok(all(g['mode'] in ('none', 'cap', 'acc') and 0.0 <= g['f'] <= 1.0 and g['h'] >= 0.0 for g in S_.GRID.values()), '격자 값 범위')
    # 11) 무작위 회차 300개: 총합산 = 시작 + 손익 합 - 분리 비용, 음수 없음, 결정론
    for gid, p in S_.GRID.items():
        runs = []
        for _ in range(2):
            rnd = random.Random(11)
            st = S_.new_state(M)
            profit_sum = 0.0
            for k in range(300):
                if k and k % 40 == 0:
                    S_.season_reset(st, M, 0)
                pr = st['cash'] * rnd.uniform(-0.03, 0.07)
                st['cash'] += pr
                profit_sum += pr
                S_.round_close(st, M, p, 0.001, 0)
                ok(st['cash'] >= 0 and st['bucket'] >= 0 and st['rbucket'] >= 0, '음수 없음 %s' % gid)
                if p['mode'] == 'cap' and p['f'] == 1.0:
                    ok(st['cash'] <= M * (1 + p['h']) + 1e-9, 'cap 전액은 현금이 M*(1+h)를 넘지 않는다 %s' % gid)
            ok(near(S_.total_net(st), M + profit_sum - st['sep_cost'], 1e-6), '총합산 보존 %s' % gid)
            runs.append((st['cash'], st['bucket'], st['n_sep']))
        ok(runs[0] == runs[1], '같은 입력 -> 같은 결과 %s' % gid)
        if p['mode'] == 'none':
            ok(runs[0][1] == 0.0 and runs[0][2] == 0, 'N0는 분리 없음')
    print('09_test_sep_layer: 확인 %d개 전부 통과' % PASS)


if __name__ == '__main__':
    main()
