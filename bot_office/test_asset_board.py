#!/usr/bin/env python3
# 사무실 v1.3.7: asset_board.py · office_board.assets() 확인 (표준 라이브러리만 · 네트워크·비밀키 안 씀)
# 사무실 v1.3.8: 자산 구성 1% 미만 숨김 테스트 추가
# 사무실 vNEXT: 수익률(월별 표 A67:H78 → returns) · office_board returns 전달 · 보드 하이브리드(도넛+막대) 테스트 추가
#   python3 test_asset_board.py      → 마지막 줄 'OK n개' 면 통과
import json, os, sys, tempfile, unittest
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TMP = Path(tempfile.mkdtemp())
os.environ["OFFICE_ROOT"] = str(TMP)
import asset_board as AB      # noqa: E402
import office_board as OB     # noqa: E402

SA = TMP / "sa.json"
SA.write_text(json.dumps({"client_email": "test@example.iam.gserviceaccount.com", "private_key": "x",
                          "token_uri": "https://oauth2.googleapis.com/token"}))
FAKE_SIGN = lambda key, data: b"sig"


MIX_NAMES = ("현금", "주식·ETF", "코인", "간접자산")
STOCK_NAMES = ("미국", "한국관련주", "중국관련주", "일본관련주", "SOXL", "TQQQ", "토스 해외주식", "코인")
# 실제 시트 A열 형식 (퍼센트가 앞에 붙어 있음 · 퍼센트 숫자는 예시)
MIX_REAL = ("42.7% 현금", "32.3% 주식·ETF", "0.1% 코인", "24.9% 간접자산")
STOCK_REAL = ("3.4% 미국", "49.3% 한국관련주", "7.1% 중국관련주", "3.8% 일본관련주", "26.4% SOXL", "8.9% TQQQ",
              "0.8% 토스 해외주식", "0.3% 코인")


def ret_rows(upto=11, nov_d=-0.0773, nov_h=0.00466):
    """가짜 월별 표 A67:H78 (2026-01~12) · upto 월까지 B(총자산) 채움 · 11월 D·H 는 실제 값"""
    rows = []
    for m in range(1, 13):
        if m <= upto:
            d, h = (nov_d, nov_h) if m == 11 else (0.012 * m, 0.03)
            rows.append([f"2026-{m:02d}", 70351.21 if m == 11 else 70000 + m, -5893.1, d, -3100, -0.043, 70024.5, h])
        else:
            rows.append([f"2026-{m:02d}", "", "", "", "", "", "", ""])
    return rows


def sheet(mix, stock, date="2026.11.6", mix_total=None, stock_total=None, mix_names=MIX_NAMES, stock_names=STOCK_NAMES,
          ret=None):
    rows = lambda names, vals, tot: [[n, v] for n, v in zip(names, vals)] + [["합계", sum(v for v in vals if isinstance(v, int)) if tot is None else tot]]
    return {"valueRanges": [{"values": [["기준일", date]]},
                            {"values": rows(mix_names, mix, mix_total)},
                            {"values": rows(stock_names, stock, stock_total)},
                            {"values": ret_rows() if ret is None else ret}]}


class Http:
    def __init__(self, body=None, status=200, fail=False):
        self.body, self.status, self.fail, self.calls = body, status, fail, []

    def __call__(self, method, url, headers, body, timeout=20):
        self.calls.append((method, url))
        if self.fail:
            raise OSError("network down")
        if "oauth2" in url:
            return 200, {}, {"access_token": "tok"}
        return self.status, {}, self.body


MIX = [500, 3000, 900, 600]
STOCK = [800, 2000, 160, 80, 380, 250, 140, 220]


class T(unittest.TestCase):
    def run_update(self, http):
        out = TMP / "assets.json"
        rec = AB.update(http, out_path=out, signer=FAKE_SIGN, sa=SA)
        AB.save(out, rec)
        return rec, json.loads(out.read_text(encoding="utf-8"))

    def setUp(self):
        for p in (TMP / "assets.json",):
            p.unlink(missing_ok=True)

    def test_readonly_scope_and_get_only(self):
        h = Http(sheet(MIX, STOCK))
        self.run_update(h)
        self.assertEqual(AB.SCOPE, "https://www.googleapis.com/auth/spreadsheets.readonly")
        sheet_calls = [c for c in h.calls if "sheets.googleapis.com" in c[1]]
        self.assertTrue(sheet_calls and all(m == "GET" and "values:batchGet" in u for m, u in sheet_calls))

    def test_percent_only_no_amounts(self):
        rec, disk = self.run_update(Http(sheet(MIX, STOCK)))
        self.assertEqual(disk["base_date"], "2026.11.6")
        stock = [c for c in disk["charts"] if c["key"] == "stock"][0]
        self.assertEqual(len(stock["items"]), 8)                       # 8개 항목 모두
        self.assertAlmostEqual(sum(i["pct"] for i in stock["items"]), 100, delta=0.3)
        self.assertEqual({i["name"]: i["pct"] for i in stock["items"]}["한국관련주"], round(2000 * 100 / 4030, 1))
        raw = json.dumps(disk, ensure_ascii=False)
        for amount in ("4030", "3000", "2000", "5000"):                   # 금액·합계 원문이 파일에 없음
            self.assertNotIn(amount, raw)
        self.assertEqual(oct((TMP / "assets.json").stat().st_mode & 0o777), "0o644")

    def test_data_change_changes_chart(self):
        _, a = self.run_update(Http(sheet(MIX, STOCK)))
        _, b = self.run_update(Http(sheet(MIX, [3000, 100, 160, 80, 380, 250, 140, 220], date="2026.11.7")))
        self.assertNotEqual(a["charts"][1]["items"], b["charts"][1]["items"])
        self.assertEqual(b["base_date"], "2026.11.7")

    def test_sheet_unreachable_keeps_last_values(self):
        _, good = self.run_update(Http(sheet(MIX, STOCK)))
        rec, bad = self.run_update(Http(fail=True))
        self.assertEqual(bad["charts"], good["charts"])
        self.assertEqual(bad["fetched_kst"], good["fetched_kst"])
        self.assertTrue(bad["error"])
        OB.ASSETS_FILE = TMP / "assets.json"
        a = OB.assets()
        self.assertTrue(a["ok"] and a["stale"])

    def test_http_error_and_bad_cell(self):
        rec, _ = self.run_update(Http({"error": {"status": "PERMISSION_DENIED"}}, status=403))
        self.assertIn("403", rec["error"])
        rec, disk = self.run_update(Http(sheet(MIX, STOCK[:7] + ["#REF!"])))
        self.assertIn("투자 종목", rec["error"])
        self.assertEqual([c["key"] for c in disk["charts"]], ["mix"])   # 자산 구성은 그대로 그림

    def test_total_check_and_zero(self):
        _, disk = self.run_update(Http(sheet(MIX, [800, 2000, 0, 80, 380, 250, 140, 220], stock_total=9999)))
        stock = disk["charts"][1]
        self.assertEqual(stock["check"], "diff")
        self.assertEqual(stock["zero"], ["중국관련주"])
        self.assertEqual(len(stock["items"]), 7)

    def test_real_a_column_percent_stripped(self):
        """수정 1: A열 '42.7% 현금' → 이름 '현금' (보드 라벨 '42.7% 42.7% 현금' 이중 표시 방지)"""
        _, disk = self.run_update(Http(sheet(MIX, STOCK, mix_names=MIX_REAL, stock_names=STOCK_REAL)))
        names = [i["name"] for c in disk["charts"] for i in c["items"]]
        self.assertEqual(names, list(MIX_NAMES) + list(STOCK_NAMES))
        self.assertFalse([n for n in names if "%" in n])
        for raw, want in (("42.7%현금", "현금"), (" 0.1 % 코인", "코인"), ("100% 오피스텔", "오피스텔"),
                          ("SOXL", "SOXL"), ("3x 레버리지", "3x 레버리지"), ("", "기본")):
            self.assertEqual(AB.chart([[raw, 1], ["합계", 1]], ("기본",))["items"][0]["name"], want)

    def test_no_kiwoom_dependency(self):
        """수정 2: kiwoom_holdings 없이 동작 (import 금지 · 부품 내장)"""
        src = (HERE / "asset_board.py").read_text(encoding="utf-8")
        self.assertNotIn("import kiwoom", src)
        self.assertNotIn("from kiwoom", src)
        self.assertTrue(callable(AB.rs256_sign) and callable(AB.urllib_http))
        self.assertNotIn("kiwoom_holdings", sys.modules)

    def test_missing_service_account_file(self):
        """수정 3: 키 파일이 없으면 명확한 오류 + 이전 값 유지 (kiwoom.json 대체 없음)"""
        self.assertEqual(AB.SA_FILE, TMP / "etc/bot-office/google_sa.json")
        self.assertFalse(hasattr(AB, "KIWOOM_KEYS"))
        _, good = self.run_update(Http(sheet(MIX, STOCK)))
        out = TMP / "assets.json"
        rec = AB.update(Http(sheet(MIX, STOCK)), out_path=out, signer=FAKE_SIGN, sa=TMP / "nope_sa.json")
        self.assertIn("서비스 계정 키 없음", rec["error"])
        self.assertEqual(rec["charts"], good["charts"])

    def test_real_openssl_signature(self):
        """내장 서명이 실제 openssl 로 동작 (임시 테스트 키 · 서버 키 아님)"""
        import subprocess
        key = subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"],
                             capture_output=True, text=True)
        if key.returncode != 0:
            self.skipTest("openssl 없음")
        self.assertEqual(len(AB.rs256_sign(key.stdout, b"hello")), 256)

    # ---- v1.3.8: 자산 구성(mix)만 1% 미만 숨김
    MIX_NOW = [427, 323, 1, 249]                      # 현재 비율과 같은 예시 (코인 0.1%)
    STOCK_NOW = [34, 493, 71, 38, 264, 89, 8, 3]      # 토스 해외주식 0.8% · 코인 0.3%

    def charts_of(self, mix, stock):
        _, disk = self.run_update(Http(sheet(mix, stock, mix_names=MIX_REAL, stock_names=STOCK_REAL)))
        return {c["key"]: c for c in disk["charts"]}

    def test_mix_hides_coin_below_1pct(self):
        c = self.charts_of(self.MIX_NOW, self.STOCK_NOW)
        self.assertEqual([i["name"] for i in c["mix"]["items"]], ["현금", "주식·ETF", "간접자산"])
        self.assertEqual({i["name"]: i["pct"] for i in c["mix"]["items"]}, {"현금": 42.7, "주식·ETF": 32.3, "간접자산": 24.9})
        self.assertEqual(c["mix"]["check"], "ok")          # 숨긴 코인 금액도 합계에 포함 → 시트 합계와 일치
        self.assertEqual(c["mix"]["zero"], [])

    def test_stock_keeps_small_items(self):
        c = self.charts_of(self.MIX_NOW, self.STOCK_NOW)
        st = {i["name"]: i["pct"] for i in c["stock"]["items"]}
        self.assertEqual(len(st), 8)
        self.assertEqual((st["코인"], st["토스 해외주식"], st["한국관련주"]), (0.3, 0.8, 49.3))
        self.assertEqual(c["stock"]["check"], "ok")

    def test_mix_coin_returns_at_1pct(self):
        c = self.charts_of([4170, 3230, 100, 2500], self.STOCK_NOW)    # 코인 1.0% → 보임 (경계)
        self.assertIn({"name": "코인", "pct": 1.0}, c["mix"]["items"])
        c = self.charts_of([4170, 3230, 96, 2504], self.STOCK_NOW)     # 0.96% → 반올림 1.0% → 보임
        self.assertIn({"name": "코인", "pct": 1.0}, c["mix"]["items"])
        c = self.charts_of([4170, 3230, 95, 2505], self.STOCK_NOW)     # 0.95% → 기존 round() 로 0.9% → 숨김 (계산 방식 그대로)
        self.assertNotIn("코인", [i["name"] for i in c["mix"]["items"]])
        c = self.charts_of([4170, 3230, 94, 2506], self.STOCK_NOW)     # 0.94% → 0.9% → 숨김
        self.assertNotIn("코인", [i["name"] for i in c["mix"]["items"]])

    def test_hiding_does_not_change_other_pct(self):
        a = AB.chart([["현금", 427], ["주식·ETF", 323], ["코인", 1], ["간접자산", 249], ["합계", 1000]], MIX_NAMES)
        b = AB.chart([["현금", 427], ["주식·ETF", 323], ["코인", 1], ["간접자산", 249], ["합계", 1000]], MIX_NAMES, 1.0)
        self.assertEqual([i for i in a["items"] if i["name"] != "코인"], b["items"])
        self.assertEqual((a["check"], a["zero"]), (b["check"], b["zero"]))
        self.assertEqual(AB.HIDE_BELOW, {"mix": 1.0})
        self.assertEqual(AB.CHARTS[0][3][3], "간접자산")

    # ---- vNEXT: 수익률 (월별 표)
    def test_returns_current_month(self):
        rec, disk = self.run_update(Http(sheet(MIX, STOCK)))
        self.assertEqual(disk["returns"], {"month": "2026-11", "monthly": -7.7, "yearly": 0.5})
        self.assertEqual(rec["error"], "")
        raw = json.dumps(disk, ensure_ascii=False)
        for amount in ("70351", "5893", "70024", "-4.3", "0.0773", "0.00466"):   # 금액·연초 수익률·원래 소수 저장 안 함
            self.assertNotIn(amount, raw)
        self.assertEqual(AB.RETURNS_RANGE, "'입력정리'!A67:H78")
        self.assertEqual(AB.READ_RANGES[-1], AB.RETURNS_RANGE)

    def test_returns_moves_to_december(self):
        rows = ret_rows(upto=12)
        rows[11][3], rows[11][7] = 0.021, -0.0149
        _, disk = self.run_update(Http(sheet(MIX, STOCK, ret=rows)))
        self.assertEqual(disk["returns"], {"month": "2026-12", "monthly": 2.1, "yearly": -1.5})

    def test_returns_empty_table_charts_still_shown(self):
        _, good = self.run_update(Http(sheet(MIX, STOCK)))
        self.assertIn("returns", good)
        for ret in ([], ret_rows(upto=0)):                     # 표가 비었거나 B가 모두 빈칸
            rec, disk = self.run_update(Http(sheet(MIX, STOCK, ret=ret)))
            self.assertNotIn("returns", disk)
            self.assertEqual(rec["error"], "")                 # 오류 아님
            self.assertEqual([c["key"] for c in disk["charts"]], ["mix", "stock"])

    def test_returns_blank_d_or_h_means_none(self):
        for d, h in (("", 0.00466), (-0.0773, ""), (-0.0773, None)):
            _, disk = self.run_update(Http(sheet(MIX, STOCK, ret=ret_rows(nov_d=d, nov_h=h))))
            self.assertNotIn("returns", disk)
            self.assertEqual(len(disk["charts"]), 2)

    def test_returns_kept_when_sheet_unreachable(self):
        _, good = self.run_update(Http(sheet(MIX, STOCK)))
        rec, bad = self.run_update(Http(fail=True))
        self.assertTrue(bad["error"])
        self.assertEqual(bad["returns"], good["returns"])
        rec, bad = self.run_update(Http({"error": {"status": "PERMISSION_DENIED"}}, status=403))
        self.assertEqual(bad["returns"], good["returns"])

    def test_returns_month_text_and_sign(self):
        self.assertEqual(AB.returns([["2026. 3", 1, 0, 0.05, 0, 0, 0, -0.0004]]), {"month": "2026-03", "monthly": 5.0, "yearly": 0.0})
        self.assertEqual(AB.returns([["", 1, 0, -0.0773, 0, 0, 0, 0.00466]])["month"], "2026-01")   # 글자 없으면 행 순서
        self.assertEqual(AB.returns_line({"month": "2026-11", "monthly": -7.7, "yearly": 0.5}),
                         "수익률 월 -7.7% · 수익률 년 +0.5% (2026-11)")
        self.assertIn("없음", AB.returns_line(None))

    def test_returns_with_mix_hide_still_works(self):
        c = self.charts_of(self.MIX_NOW, self.STOCK_NOW)
        self.assertNotIn("코인", [i["name"] for i in c["mix"]["items"]])   # 코인 0.1% 숨김 그대로
        self.assertEqual(len(c["stock"]["items"]), 8)

    def test_dry_run_prints_returns_line(self):
        lines, real = [], AB.update
        AB.update = lambda http, out_path=None, **k: real(Http(sheet(MIX, STOCK)), out_path=TMP / "dry.json", signer=FAKE_SIGN, sa=SA)
        try:
            AB.main([], http=Http(), out=lines.append)
        finally:
            AB.update = real
        self.assertIn("수익률 월 -7.7% · 수익률 년 +0.5% (2026-11)", lines)
        self.assertFalse((TMP / "dry.json").exists())          # dry-run 은 파일 안 씀

    def test_office_board_passes_returns(self):
        self.run_update(Http(sheet(MIX, STOCK)))
        OB.ASSETS_FILE = TMP / "assets.json"
        self.assertEqual(OB.assets()["returns"], {"month": "2026-11", "monthly": -7.7, "yearly": 0.5})
        p = TMP / "ret_bad.json"
        good = json.loads(OB.ASSETS_FILE.read_text(encoding="utf-8"))
        for bad in ({"month": "2026-11", "monthly": "x", "yearly": 0.5}, {"month": "<b>", "monthly": 1, "yearly": 1},
                    {"month": "2026-11", "monthly": float("nan"), "yearly": 1}, "oops", None):
            p.write_text(json.dumps(dict(good, returns=bad)))
            OB.ASSETS_FILE = p
            a = OB.assets()
            self.assertNotIn("returns", a)
            self.assertTrue(a["ok"])                           # 도넛·막대는 그대로

    def test_board_hybrid(self):
        html = (HERE / "board.html").read_text(encoding="utf-8")
        self.assertNotIn("minHalf", html)                      # 두 도넛 맞추기 로직 삭제
        self.assertIn("function donutSVG(ch){", html)
        self.assertIn("function barsHTML(ch)", html)
        self.assertNotIn("bandHTML", html)
        self.assertIn('id="assetRet"', html)
        self.assertIn(".donut.mix svg{max-width:240px}", html)

    def test_date_formats(self):
        for txt, want in (("2026.11.6", "2026.11.6"), ("2026. 11. 6", "2026.11.6"), ("2026-11-06", "2026.11.6"),
                          ("2026년 11월 6일", "2026.11.6"), ("없음", "")):
            self.assertEqual(AB.base_date([["기준일", txt]]), want)

    def test_office_board_missing_and_broken_file(self):
        OB.ASSETS_FILE = TMP / "nope.json"
        self.assertEqual(OB.assets(), {"ok": False, "why": "no_file"})
        p = TMP / "broken.json"
        p.write_text("{not json")
        OB.ASSETS_FILE = p
        self.assertEqual(OB.assets()["why"], "unreadable")
        p.write_text(json.dumps({"charts": [{"items": [{"name": "x", "pct": "bad"}]}]}))
        self.assertFalse(OB.assets()["ok"])

    def test_office_board_fresh(self):
        self.run_update(Http(sheet(MIX, STOCK)))
        OB.ASSETS_FILE = TMP / "assets.json"
        d = json.loads(OB.ASSETS_FILE.read_text(encoding="utf-8"))
        now = datetime.strptime(d["fetched_kst"], "%Y-%m-%d %H:%M").replace(tzinfo=OB.KST)
        a = OB.assets(now=now)
        self.assertTrue(a["ok"])
        self.assertFalse(a["stale"])
        self.assertEqual(len(a["charts"]), 2)

    def test_board_has_assets_and_services_kept(self):
        src = (HERE / "office_board.py").read_text(encoding="utf-8")
        self.assertIn('"assets": assets()', src)
        self.assertIn('"services": svc', src)          # 기존 필드 그대로
        html = (HERE / "board.html").read_text(encoding="utf-8")
        self.assertNotIn('id="lights"', html)          # 봇 신호등 삭제
        self.assertIn('id="donuts"', html)
        for tab in ('data-t="sniper"', 'data-t="fanding"', 'data-t="server"', 'data-t="log"'):
            self.assertIn(tab, html)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1).result
    print(("OK " if r.wasSuccessful() else "FAIL ") + f"{r.testsRun}개")
    sys.exit(0 if r.wasSuccessful() else 1)
