#!/usr/bin/env python3
"""봇 4개 텔레그램/키 상태 점검 (2026-10-21) — 키 값은 화면에 출력하지 않습니다.
사용법: python3 check_bots_20261021.py
"""
import json, os, re, subprocess, time, urllib.request
from pathlib import Path

HOME = Path(os.environ.get("BOT_HOME", str(Path.home())))

def read_env(path, key):
    p = Path(path)
    if not p.exists(): return None
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r'^\s*(?:export\s+)?' + key + r'\s*=\s*["\']?(.*?)["\']?\s*$', line)
        if m: return m.group(1).strip()
    return None

def read_json(path, key):
    try: return str(json.loads(Path(path).read_text(encoding="utf-8")).get(key) or "") or None
    except Exception: return None

def get_me(token):
    if not token: return "❌ 토큰 없음"
    if not re.fullmatch(r'\d{6,12}:[A-Za-z0-9_-]{30,}', token): return "❌ 토큰 형식이 이상함 (앞뒤 공백/따옴표/잘림 확인)"
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=10) as r:
            d = json.load(r)
        return f"✅ 유효 (@{d['result']['username']})" if d.get("ok") else "❌ 텔레그램이 거부"
    except urllib.error.HTTPError as e:
        return "❌ 무효한 토큰 (옛 토큰이거나 잘못 붙여넣음)" if e.code in (401, 404) else f"⚠️ HTTP {e.code}"
    except Exception as e:
        return f"⚠️ 확인 불가: {type(e).__name__}"

def unit_info(unit):
    def sh(*a):
        try: return subprocess.run(a, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception: return ""
    active = sh("systemctl", "is-active", unit) or "unknown"
    started = sh("systemctl", "show", unit, "-p", "ActiveEnterTimestamp", "--value")
    envfiles = [l.split("=", 1)[1].strip() for l in sh("systemctl", "cat", unit).splitlines() if l.startswith("EnvironmentFile=")]
    return active, started, envfiles

def mtime(p):
    try: return Path(p).stat().st_mtime
    except Exception: return None

def started_epoch(s):
    try: return time.mktime(time.strptime(" ".join(s.split()[1:3]), "%Y-%m-%d %H:%M:%S"))
    except Exception: return None

BOTS = [
    ("1번 한투 라오어", "han4384tubot.service", [(HOME / ".env", "TELEGRAM_TOKEN")]),
    ("2번 토스 스나이퍼", "toss_sniper.service", [(HOME / "toss_sniper" / ".env", "TELEGRAM_BOT_TOKEN")]),
    ("3번 토스 적립", "toss_dca.service", [(HOME / "toss_dca_bot" / ".env", "TELEGRAM_BOT_TOKEN")]),
    ("4번 빗썸 적립", "bithumb_bot.service", [(HOME / "bithumb_laoeo_bot" / ".env_vars", "TELEGRAM_BOT_TOKEN"),
                                          (HOME / "bithumb_laoeo_bot" / "config.json", "TELEGRAM_TOKEN"),
                                          (HOME / ".bashrc", "TELEGRAM_BOT_TOKEN")]),
]

print("\n========== 봇 점검 결과 ==========")
for name, unit, sources in BOTS:
    active, started, envfiles = unit_info(unit)
    print(f"\n[{name}]  서비스 {unit}: {'✅ 실행 중' if active == 'active' else '❌ ' + active}")
    srcs = list(sources) + [(Path(f.lstrip('-')), sources[0][1]) for f in envfiles if Path(f.lstrip('-')) not in [s[0] for s in sources]]
    last_change = 0
    for path, key in srcs:
        tok = read_json(path, key) if str(path).endswith(".json") else read_env(path, key)
        if tok is None:
            print(f"   - {path.relative_to(HOME) if str(path).startswith(str(HOME)) else path}: (항목 없음)")
            continue
        print(f"   - {path.relative_to(HOME) if str(path).startswith(str(HOME)) else path}: {get_me(tok)}")
        m = mtime(path)
        if m: last_change = max(last_change, m)
    if envfiles: print(f"   - 서비스가 읽는 키 파일: {', '.join(envfiles)}")
    st = started_epoch(started)
    if st and last_change and st < last_change:
        print("   ⚠️ 키를 바꾼 뒤에 봇을 재시작하지 않았습니다 → 재시작 필요")
    elif st:
        print(f"   - 마지막 시작: {started}")
print("\n==================================\n")
