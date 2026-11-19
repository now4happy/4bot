"""P매매 수익금 분리 설계용 — 원작자 표의 사이클(회차) 규모 v0.1.0 (2026-11-19, 클로드 2번) — 방: P매매 검증 (p-verify)

사용: python3 -I 10_cycle_scale.py p_data_v12.json
데이터만으로 센다. 우리 매도 규칙·백테스트는 쓰지 않는다 (원작자 매도표가 만든 사이클이다).
사이클 = 보유 0 -> 보유 > 0 -> 다시 보유 0.  수익 = 종료 행 잔금 - 시작 직전 행 잔금.
시즌 리셋 행(2026-01-05, 잔금 10000)과 2025-04-07 행은 05/06번 스크립트와 같은 처리로 정렬·제외한다.
"""
import json, sys, hashlib, statistics as st

EXPECT = 'bcedc40142bac16ad71cb1ccf01e92fc0298d4fe4096f2f421005e04ec32ee24'


def load(path):
    rows = [r for r in json.load(open(path, encoding='utf-8')) if r['종가일'] != '2025-04-07']
    rows.sort(key=lambda r: (r['종가일'], 1 if (r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0) else 0))
    return rows


def cycles(rows):
    out, open_ = [], None
    for i in range(1, len(rows)):
        pv, r = rows[i - 1], rows[i]
        if r['종가일'] == '2026-01-05' and r['잔금'] == 10000.0:      # 시즌2 시작 행: 열린 사이클 없음 확인용
            assert open_ is None, '리셋 행에서 열린 사이클이 있다'
            continue
        if pv['현재보유개수'] == 0 and r['현재보유개수'] > 0:
            open_ = dict(start_date=pv['종가일'], open_cash=pv['잔금'], i0=i)
        if pv['현재보유개수'] > 0 and r['현재보유개수'] == 0 and open_ is not None:
            open_.update(end_date=r['종가일'], profit=r['잔금'] - open_['open_cash'], days=i - open_['i0'] + 1)
            out.append(open_)
            open_ = None
    return out, open_


def q(v, p):
    s = sorted(v)
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def main(path):
    h = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    print('입력 해시', h[:8], '일치' if h == EXPECT else '불일치(기대 %s)' % EXPECT[:8])
    rows = load(path)
    cs, still = cycles(rows)
    print('행', len(rows), '| 닫힌 사이클', len(cs), '| 열린 사이클', 1 if still else 0)
    if still:
        print('  열린 사이클 시작', still['start_date'], '시작 현금 %.2f' % still['open_cash'])
    rel = [c['profit'] / c['open_cash'] for c in cs]
    pos = [x for x in rel if x > 0]
    print('수익 > 0 사이클 %d / %d, 수익 <= 0 %d' % (len(pos), len(cs), len(cs) - len(pos)))
    print('사이클 수익률(수익/시작 현금) 최소 %.4f  25%% %.4f  중앙 %.4f  75%% %.4f  최대 %.4f' % (
        min(rel), q(rel, .25), q(rel, .5), q(rel, .75), max(rel)))
    if pos:
        print('  수익 사이클만: 최소 %.4f 중앙 %.4f 최대 %.4f' % (min(pos), st.median(pos), max(pos)))
    d = [c['days'] for c in cs]
    print('사이클 길이(행 수) 최소 %d 중앙 %d 최대 %d' % (min(d), st.median(d), max(d)))
    for thr in (0.0, 0.05, 0.10, 0.20, 0.30):
        print('  수익률 > %.2f 인 사이클 %d개' % (thr, sum(x > thr for x in rel)))
    # 시즌 리셋 날 계좌 (시즌 단위 누적)
    for i, r in enumerate(rows):
        if r['종가일'] == '2026-01-05' and r['잔금'] != 10000.0:
            print('시즌1 종료 행 잔금 %.2f 보유 %d (시즌 원금 10000 기준 초과분 %.2f)' % (
                r['잔금'], r['현재보유개수'], r['잔금'] - 10000.0))
    # 시즌별 사이클 수
    by = {}
    for c in cs:
        s = 1 if c['end_date'] <= '2026-01-05' else 2
        by.setdefault(s, []).append(c)
    for s, v in sorted(by.items()):
        print('시즌%d: 사이클 %d개, 사이클 수익 합 %.2f' % (s, len(v), sum(c['profit'] for c in v)))
    # 사이클 시작 현금이 시즌 원금(10000)을 넘은 사이클 (분리 'cap' 방식이 걸렸을 사이클 수의 상한 참고)
    over = [c for c in cs if c['open_cash'] > 10000.0]
    print('시작 현금 > 10000 인 사이클 %d개 (시즌2 복리 구간)' % len(over))
    proxy(cs)


def proxy(cs):
    """참고 산술 (우리 규칙의 백테스트가 아니다): 닫힌 사이클의 수익률 열을 운용금액에 비례한다고 보고 분리 규칙(08번)을 씌운다.
    열린 사이클의 평가손익·우리 매도줄·C 청산은 들어 있지 않다. 분리 횟수가 문턱 h에 얼마나 민감한지만 본다. 비용 0."""
    import importlib.util, os
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location('sep', os.path.join(here, '08_sep_layer.py'))
    sep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sep)
    M = 10000.0
    print('[참고 산술] 닫힌 사이클 %d개의 수익률 열에 분리 규칙을 씌운 횟수 (수익은 운용금액에 비례 가정, 비용 0)' % len(cs))
    extra = [('C_h%.2f' % h, dict(mode='cap', f=1.0, h=h)) for h in (0.0, 0.05, 0.20)] + [('A_h0.30', dict(mode='acc', f=1.0, h=0.30))]   # 격자 밖 민감도 (횟수만 본다)
    for name, p in list(sep.GRID.items()) + extra:
        s = sep.new_state(M)
        season, ops = 1, 0
        for c in cs:
            if season == 1 and c['end_date'] > '2026-01-05':
                sep.season_reset(s, M, 0)
                season = 2
            rel = c['profit'] / c['open_cash']
            s['cash'] *= (1 + rel)
            sep.round_close(s, M, p, 0.0, 0)
        print('  %-8s 분리 %2d회  분리 합계 %9.2f  버킷 %9.2f  리셋인출 %9.2f  운용현금(끝) %9.2f' % (
            name, s['n_sep'], s['sep_total'], s['bucket'], s['rbucket'], s['cash']))
    print('  (N0 = 분리 없음: 시즌 리셋 때만 초과분이 나감. 합계·현금은 표 단위 10000 기준 연구용 숫자)')


if __name__ == '__main__':
    main(sys.argv[1])
