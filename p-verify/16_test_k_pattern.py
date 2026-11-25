"""15_verify_k_pattern.py 단위·변조 시험 (v0.1.0, ZIP 파일명 기준).

사용:
  python3 -I 16_test_k_pattern.py                        # 데이터 없이: 합성 자료 시험만, 데이터 시험은 건너뜀
  P10_DATA=p_data_v16.json python3 -I 16_test_k_pattern.py   # 전부
-I 는 현재 폴더를 import 경로에 넣지 않으므로 모듈은 이 파일 옆 경로로 직접 불러온다.
"""
import importlib.util, io, json, os, tempfile, unittest, contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('kv', os.path.join(HERE, '15_verify_k_pattern.py'))
kv = importlib.util.module_from_spec(spec); spec.loader.exec_module(kv)
DATA = os.environ.get('P10_DATA')

def run_main(path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = kv.main(path)
    return rc, buf.getvalue()

def mkrow(d, close, hold, cash, avg, buys, real=0.0):
    return {'종가일': d, '종가': close, '매수': [{'price': p, 'qty': q} for p, q in buys], '매도': [],
            '보유평단': avg, '잔금': cash, '총수익률': 0, '직전매매개수': 0, '현재보유개수': hold,
            '시즌실현수익': real, '시즌': 2, '전부_환산': None}

class Synthetic(unittest.TestCase):
    def rows(self, act):
        # 사이클 시작(보유 0, 잔금 1300 → B=100) → 2일째 10주 매수(P=100, 평단 100) → 3일째 1번 줄
        return [mkrow('2025-04-07', 9, None, None, None, []),
                mkrow('2026-11-02', 100, 0, 1300.0, None, [(100.0, 1)]),
                mkrow('2026-11-03', 100, 10, 300.0, 100.0, [(act, 1)])]
    def k_of(self, act):
        out = kv.build(kv.prepare_rows(self.rows(act)))
        r = [x for x in out if x['date'] == '2026-11-03'][0]
        return r
    def test_base_formula(self):
        # T = round(10×100 ÷ (1300/13), 1) = 10.0, 계수 0.25% → base = 100×(1−0.025) = 97.5
        r = self.k_of(97.5)
        self.assertTrue(r['measurable']); self.assertAlmostEqual(r['base'], 97.5, 6); self.assertAlmostEqual(r['k'], 0, 6)
    def test_k_scale(self):
        self.assertAlmostEqual(self.k_of(96.5)['k'], -2.0, 6)
        self.assertAlmostEqual(self.k_of(98.0)['k'], +1.0, 6)
    def test_old_coef(self):
        rows = self.rows(97.0)
        for r in rows[1:]: r['종가일'] = r['종가일'].replace('2026-11', '2026-10')   # 구 체제(10-26 전, N=13) 0.30% → base 97.0
        out = kv.build(kv.prepare_rows(rows))
        r = out[-1]; self.assertAlmostEqual(r['base'], 97.0, 6)
    def test_mixed_excluded(self):
        rows = self.rows(97.5); rows[2]['시즌실현수익'] = 50.0   # 순매수인데 실현수익 변화 → 섞인 날
        r = kv.build(kv.prepare_rows(rows))[-1]
        self.assertTrue(r['mixed']); self.assertFalse(r['measurable'])
    def test_first_row_dropped(self):
        self.assertEqual(len(kv.prepare_rows(self.rows(97.5))), 2)
    def test_flags(self):
        r = self.k_of(97.5)
        self.assertFalse(r['A']); self.assertFalse(r['B']); self.assertFalse(r['C'])
    def test_A_flag(self):
        rows = self.rows(97.5); rows[2]['잔금'] = 300.0
        rows[1]['잔금'] = 1300.0
        r = self.k_of(97.5); self.assertFalse(r['A'])
        rows = self.rows(97.5)
        # 잔금이 기본가보다 작게 만든다 (같은 P 유지: 보유 +10, 잔금 −1000 이어야 P=100) → 잔금 = 300 고정이므로 직접 확인
        out = kv.build(kv.prepare_rows(rows)); self.assertEqual(out[-1]['A'], 300.0 < out[-1]['base'])
    def test_C_flag(self):
        rows = [mkrow('2026-11-02', 100, 0, 1300.0, None, [(100.0, 1)]),
                mkrow('2026-11-03', 100, 10, 300.0, 100.0, [(97.5, 1)]),
                mkrow('2026-11-04', 98, 5, 800.0, 100.0, [(90.0, 1)], real=0.0)]   # 5주 매도 @100 (잔금 +500), 종가 98 = −2%
        rows[2]['시즌실현수익'] = 0.0
        out = kv.build(kv.prepare_rows(rows)); r = out[-1]
        self.assertTrue(r['sell']); self.assertTrue(r['C'])
        rows[2]['종가'] = 99.9
        out = kv.build(kv.prepare_rows(rows)); self.assertFalse(out[-1]['C'])
    def test_near_matches_regen(self):
        self.assertTrue(kv.near(100.0, 100.025)); self.assertFalse(kv.near(100.0, 100.05))
    def test_stump_finds_planted_rule(self):
        rs = [{'x': float(i)} for i in range(10)]
        kv.FEATS_BACKUP = kv.FEATS
        kv.FEATS = ['x']
        try:
            resid = [-2.0 if i >= 7 else 0.0 for i in range(10)]
            bh, (gain, desc) = kv.best_stump([{'x': float(i), **{}} for i in range(10)], resid)
            self.assertEqual(bh, 7); self.assertEqual(gain, 3); self.assertEqual(desc[3], -2)
        finally:
            kv.FEATS = kv.FEATS_BACKUP

@unittest.skipUnless(DATA, 'P10_DATA 없음')
class RealData(unittest.TestCase):
    def test_pass(self):
        rc, out = run_main(DATA)
        self.assertEqual(rc, 0); self.assertIn('내부 점검 17/17', out); self.assertIn('입력 해시 0a427133 일치', out)
    def test_deterministic(self):
        self.assertEqual(run_main(DATA)[1], run_main(DATA)[1])
    def _load(self):
        with open(DATA, encoding='utf-8') as fh:
            return json.load(fh)
    def _tmp(self, data, name):
        p = os.path.join(tempfile.mkdtemp(), name)
        with open(p, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False)
        return p
    def test_tamper_price_fails(self):
        d = self._load()
        for r in d:
            if r['종가일'] == '2026-11-24': r['매수'][0]['price'] = 31.61
        p = self._tmp(d, 'p10_tamper_price.json'); rc, out = run_main(p); os.remove(p)
        self.assertNotEqual(rc, 0); self.assertIn('불일치', out)
    def test_tamper_dropped_row_fails(self):
        d = self._load()[:-1]
        p = self._tmp(d, 'p10_tamper_drop.json'); rc, out = run_main(p); os.remove(p)
        self.assertNotEqual(rc, 0)
    def test_tamper_realized_fails(self):
        d = self._load()
        for r in d:
            if r['종가일'] == '2026-11-23': r['시즌실현수익'] = 1681.54 - 1200.0   # 24주 매도처럼 보이게
        p = self._tmp(d, 'p10_tamper_real.json'); rc, out = run_main(p); os.remove(p)
        self.assertNotEqual(rc, 0)
    def test_tamper_avg_fails(self):
        d = self._load()
        for r in d:
            if r['종가일'] == '2026-11-16': r['보유평단'] = 99.0
        p = self._tmp(d, 'p10_tamper_avg.json'); rc, out = run_main(p); os.remove(p)
        self.assertNotEqual(rc, 0)

if __name__ == '__main__':
    unittest.main(verbosity=1)
