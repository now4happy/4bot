"""P매매 우리 매도 P규칙 — 수익금 분리 층(계좌 계산) v0.1.0 (2026-11-19, 클로드 2번) — 방: P매매 검증 (p-verify)

사용: python3 -I 08_sep_layer.py     (자체 점검만 출력, 데이터 없음)
이 파일은 '수익금 분리'의 계좌 계산만 담은 순수 함수 모음이다. 매매 규칙·백테스트 틀(03_backtest.py)은 들어 있지 않다.
03_backtest.py v0.1.2에 붙일 위치는 VERIFY.md 6절에 있다. 숫자(수익률 등)는 이 파일이 내지 않는다.

용어
  운용계좌 O : 우리 매도 P규칙이 굴리는 계좌 (현금 + 보유). 분리는 보유 0일 때만 하므로 그 순간 O = 현금.
  목표 운용금액 M* : 분리 후 운용계좌가 돌아갈 금액. 기본 = 시즌 시작 원금 (표 기준 10,000 = 연구 단위, 실제 금액 아님).
  버킷 bucket : 분리한 돈 (SGOV 역할). 이번 단계에서는 재투입 없음, 수익은 기본 0으로 둔다 (미확인).
  rbucket : 시즌 리셋(매년 1월 6일)에서 표가 운용계좌 밖으로 내보내는 초과분. 분리 없음(N0)과 공평하게 비교하려고 따로 쌓는다.
  injected : 시즌 리셋 때 운용계좌가 M* 아래라 표가 M*로 채워 준 금액. 총합산에서 빼야 수익이 부풀지 않는다.

분리 방식 mode
  'none' : 분리 없음 (비교 기준 N0)
  'cap'  : 후보액 = 회차 종료 현금 - M*   (목표 운용금액 위로 넘친 부분. 손실이 있으면 그만큼 상쇄된다)
  'acc'  : 후보액 = 마지막 분리 이후 쌓인 양(+) 회차 수익의 합 (손실은 상쇄하지 않는다 = 래칫)
  분리액 S = min(f * 후보액, 현금). 후보액 <= 0 이거나 후보액 < h * M* 이면 0.
  분리 비용 = S * cost_rate (버킷에는 S - 비용이 들어간다). 분리하면 acc는 0으로 되돌린다.
  회차 수익 단독(문턱 없이 매 회차)은 원작자 표 사이클 기준 수익이 작아(최대 6.58%, VERIFY.md 4절) 문턱 h를 걸 수 없어 mode로 두지 않는다.
"""

GRID = {   # 값은 근거 없는 출발점 (VERIFY.md 4절). C_h0.30은 옛 30% 임계(누적 초과분 전액)의 근사 대조군.
    'N0': dict(mode='none', f=0.0, h=0.0),
    'C_h0.10': dict(mode='cap', f=1.0, h=0.10),
    'C_h0.30': dict(mode='cap', f=1.0, h=0.30),
    'C_h0.10_f0.5': dict(mode='cap', f=0.5, h=0.10),
    'A_h0.10': dict(mode='acc', f=1.0, h=0.10),
}


def new_state(cash):
    """초기 상태. round_open_cash = 현재 회차가 시작될 때의 현금 (회차 수익 계산 기준)."""
    return dict(cash=float(cash), bucket=0.0, rbucket=0.0, injected=0.0,
                n_sep=0, sep_total=0.0, sep_cost=0.0, round_open_cash=float(cash), acc=0.0)


def separation_amount(cash, target, acc, p):
    """분리액 S (>= 0). 입력: 회차 종료 현금, 목표 운용금액, 쌓인 양(+) 회차 수익 acc, 파라미터 dict(mode, f, h)."""
    mode = p['mode']
    if mode == 'none':
        return 0.0
    basis = acc if mode == 'acc' else cash - target
    if basis <= 0 or basis < p.get('h', 0.0) * target:
        return 0.0
    return min(p.get('f', 1.0) * basis, cash)


def round_close(st, target, p, cost_rate, pos):
    """회차 종료 시점 분리. 보유 0일 때만 부른다 (주식을 팔아서 분리하지 않는다).
    st를 제자리에서 갱신하고 분리액 S를 돌려준다. 다음 회차 기준 현금(round_open_cash)도 갱신한다."""
    assert pos == 0, '분리는 보유 0일 때만 한다'
    profit = st['cash'] - st['round_open_cash']
    st['acc'] += max(0.0, profit)
    S = separation_amount(st['cash'], target, st['acc'], p)
    if S > 0:
        st['acc'] = 0.0
        fee = S * cost_rate
        st['cash'] -= S
        st['bucket'] += S - fee
        st['n_sep'] += 1
        st['sep_total'] += S
        st['sep_cost'] += fee
    st['round_open_cash'] = st['cash']
    return S


def season_reset(st, target, pos):
    """시즌 리셋: 운용계좌를 M*로 되돌린다 (표 규칙 그대로). 넘친 부분은 rbucket, 모자란 부분은 injected로 기록."""
    assert pos == 0, '리셋 때 보유는 0이어야 한다 (표 v10 2026-01-05 행이 그렇다)'
    st['rbucket'] += max(0.0, st['cash'] - target)
    st['injected'] += max(0.0, target - st['cash'])
    st['cash'] = float(target)
    st['round_open_cash'] = float(target)
    st['acc'] = 0.0


def total_net(st, pos_value=0.0):
    """총합산 자산 = 운용계좌(현금+보유 평가) + 분리 버킷 + 리셋 인출분 - 외부 주입."""
    return st['cash'] + pos_value + st['bucket'] + st['rbucket'] - st['injected']


def mdd_info(eq):
    """eq = [시작 평가금, 일별 평가금...]. 출력: (MDD, 고점 인덱스, 저점 인덱스, 회복 인덱스 또는 None).
    MDD 계산에 쓰인 고점은 그 저점 직전의 최고점이다."""
    pk, pk_i = eq[0], 0
    best = (0.0, 0, 0)
    for i, v in enumerate(eq):
        if v > pk:
            pk, pk_i = v, i
        d = (pk - v) / pk if pk > 0 else 0.0
        if d > best[0]:
            best = (d, pk_i, i)
    mdd, a, b = best
    if mdd == 0.0:
        return 0.0, 0, 0, 0
    rec = next((j for j in range(b + 1, len(eq)) if eq[j] >= eq[a]), None)
    return mdd, a, b, rec


def recovery_days(eq):
    """MDD 저점에서 직전 고점을 되찾기까지 일수. 못 되찾았으면 None (자료 끝까지 미회복)."""
    mdd, a, b, rec = mdd_info(eq)
    if mdd == 0.0:
        return 0
    return None if rec is None else rec - b


def longest_underwater(eq):
    """고점 아래에 연속으로 머문 가장 긴 일수 (고점 갱신 없이 이어진 날 수)."""
    pk, run, best = eq[0], 0, 0
    for v in eq[1:]:
        if v >= pk:
            pk, run = v, 0
        else:
            run += 1
            best = max(best, run)
    return best


if __name__ == '__main__':
    st = new_state(14434.58)
    st['round_open_cash'] = 10000.0
    S = round_close(st, 10000.0, GRID['C_h0.10'], 0.001, 0)
    assert abs(S - 4434.58) < 1e-9 and abs(st['cash'] - 10000.0) < 1e-9
    print('08_sep_layer 자체 점검 통과')
