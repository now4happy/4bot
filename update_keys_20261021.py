#!/usr/bin/env python3
"""재발급한 키를 봇별 설정 파일에 넣어주는 스크립트 (2026-10-21)

- 입력한 값은 화면에 보이지 않습니다(붙여넣기 후 Enter).
- 그냥 Enter 를 누르면 그 항목은 바꾸지 않습니다.
- 바꾸기 전 원본은 <파일>.bak_keys_<시각> 으로 백업하고, 권한은 600 으로 맞춥니다.
- 입력값은 어디에도 출력/기록하지 않습니다.
사용법 (홈 폴더에서): python3 update_keys_20261021.py
"""
import getpass, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

HOME = Path(os.environ.get("BOT_HOME", str(Path.home())))
STAMP = time.strftime("%Y%m%d_%H%M%S")
changed = []

def ask(label, default_label=None):
    hint = f" (Enter={default_label})" if default_label else " (Enter=건너뛰기)"
    v = getpass.getpass(f"  {label}{hint}: ").strip().strip('"').strip("'")
    return v

def backup(p):
    b = p.with_name(p.name + f".bak_keys_{STAMP}")
    shutil.copy2(p, b); b.chmod(0o600)

def set_env(path, values, create=False):
    """KEY=값 / export KEY=값 형식 파일의 해당 줄을 교체(없으면 추가)."""
    values = {k: v for k, v in values.items() if v}
    if not values: return
    p = Path(path)
    if not p.exists():
        if not create: return
        p.write_text("", encoding="utf-8")
    else:
        backup(p)
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    done = set()
    for i, line in enumerate(lines):
        m = re.match(r'^(\s*(?:export\s+)?)([A-Z0-9_]+)(\s*=\s*)(["\']?)(.*?)(["\']?)\s*$', line)
        if m and m.group(2) in values:
            q = m.group(4)
            lines[i] = f"{m.group(1)}{m.group(2)}{m.group(3)}{q}{values[m.group(2)]}{q}"
            done.add(m.group(2))
    if p.name.startswith(".env") and not p.name.endswith(".env_vars"):
        for k, v in values.items():
            if k not in done:
                lines.append(f"{k}={v}"); done.add(k)
    if done:
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        changed.append(f"{p.relative_to(HOME) if str(p).startswith(str(HOME)) else p}: {', '.join(sorted(done))}")
    p.chmod(0o600)

def set_json(path, values):
    values = {k: v for k, v in values.items() if v}
    p = Path(path)
    if not values or not p.exists(): return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        print(f"  ⚠️ {p} JSON 읽기 실패 - 건너뜀"); return
    done = [k for k in values if isinstance(data, dict) and k in data]
    if not done: return
    backup(p)
    for k in done: data[k] = values[k]
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    p.chmod(0o600)
    changed.append(f"{p.relative_to(HOME)}: {', '.join(done)}")

def unit_env_files(unit):
    try:
        out = subprocess.run(["systemctl", "cat", unit], capture_output=True, text=True).stdout
    except Exception:
        return [], False
    files = [l.split("=", 1)[1].lstrip("-").strip() for l in out.splitlines() if l.strip().startswith("EnvironmentFile=")]
    inline = any(re.match(r'\s*Environment=.*(KEY|TOKEN|SECRET)', l) for l in out.splitlines())
    return files, inline

print("\n새 키를 붙여넣고 Enter 를 누르세요. 입력값은 화면에 보이지 않습니다.\n")

print("[1번 한투 라오어봇]  (한투 앱키는 그대로, 텔레그램만 교체)")
t1 = ask("새 텔레그램 봇 토큰")
set_env(HOME / ".env", {"TELEGRAM_TOKEN": t1})

print("\n[2번 토스 SOXS 스나이퍼]")
s2 = ask("새 토스 client secret")
t2 = ask("새 텔레그램 봇 토큰")
set_env(HOME / "toss_sniper" / ".env", {"TOSS_CLIENT_SECRET": s2, "TELEGRAM_BOT_TOKEN": t2})

print("\n[3번 토스 스마트적립]")
s3 = ask("새 토스 client secret", "2번과 같음" if s2 else None) or s2
t3 = ask("새 텔레그램 봇 토큰")
set_env(HOME / "toss_dca_bot" / ".env", {"TOSS_CLIENT_SECRET": s3, "TELEGRAM_BOT_TOKEN": t3})

print("\n[4번 빗썸 스마트적립]")
a4 = ask("새 빗썸 Access Key")
k4 = ask("새 빗썸 Secret Key")
t4 = ask("새 텔레그램 봇 토큰")
env4 = {"BITHUMB_ACCESS_KEY": a4, "BITHUMB_SECRET_KEY": k4, "TELEGRAM_BOT_TOKEN": t4}
unit_files, inline = unit_env_files("bithumb_bot.service")
targets = {str(HOME / "bithumb_laoeo_bot" / ".env_vars"), str(HOME / ".bashrc")} | set(unit_files)
for f in sorted(targets):
    set_env(f, env4)
set_json(HOME / "bithumb_laoeo_bot" / "config.json", {"BITHUMB_API_KEY": a4, "BITHUMB_SECRET_KEY": k4, "TELEGRAM_TOKEN": t4})

# 옛 토스 메모 파일 (옛 secret/토큰 기록) 정리
api_txt = HOME / "toss_sniper" / "API.txt"
if api_txt.exists() and (s2 or s3):
    api_txt.chmod(0o600)

print("\n결과")
for c in changed: print("  ✅", c)
if not changed: print("  바뀐 파일이 없습니다.")
if inline:
    print("  ⚠️ bithumb_bot.service 안에 키가 직접 적혀 있습니다(Environment=). 아래로 직접 수정이 필요합니다:")
    print("     sudo systemctl edit --full bithumb_bot.service")
print("\n봇 재시작:")
print("  sudo systemctl daemon-reload")
print("  sudo systemctl restart han4384tubot.service toss_sniper.service toss_dca.service bithumb_bot.service")
print("  systemctl is-active han4384tubot.service toss_sniper.service toss_dca.service bithumb_bot.service")
print("\n텔레그램 각 봇에서 /start 를 눌러 응답이 오는지 확인하세요.")
print("문제가 생기면 백업(*.bak_keys_" + STAMP + ")을 원래 이름으로 되돌리면 됩니다.")
