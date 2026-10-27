#!/usr/bin/env python3
"""GitHub 비밀키 유출 재발 방지 설정 (2026-10-21)

홈 폴더(~)가 통째로 Git 저장소라서 `git add -A` 한 번에 .bashrc, 빗썸 키, 토스 키가 올라갔습니다.
이 스크립트는 아래를 합니다. 커밋/푸시는 하지 않습니다(마지막에 명령어를 안내합니다).

  1) .gitignore 를 '화이트리스트' 방식으로 교체 — 기본 전부 제외, 코드(.py)와 문서만 허용
  2) 이미 올라간 비밀/서버 파일을 Git 추적에서 제거 (서버의 실제 파일은 지우지 않음)
  3) 커밋할 때마다 비밀키를 검사해 막는 pre-commit 훅 설치
  4) 키가 들어있는 파일 권한을 600(본인만 읽기)으로 변경
  5) 각 봇이 키를 어디서 읽는지 알려줌 (재발급 후 바꿔 넣을 위치)

사용법 (홈 폴더에서):  python3 secure_repo_20261021.py
"""
import os, re, stat, subprocess, sys
from pathlib import Path

HOME = Path(os.environ.get("REPO_DIR", str(Path.home())))
os.chdir(HOME)

def git(*a, check=True):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=check).stdout

try:
    top = git("rev-parse", "--show-toplevel").strip()
except Exception:
    sys.exit(f"{HOME} 는 Git 저장소가 아닙니다.")
if Path(top).resolve() != HOME.resolve():
    sys.exit(f"저장소 최상위가 {top} 입니다. 그 폴더에서 실행하거나 REPO_DIR={top} 로 지정하세요.")

GITIGNORE = """# ==========================================================
# 화이트리스트 방식 (2026-10-21): 기본은 전부 제외, 아래 '!' 로 허용한 것만 GitHub 에 올라갑니다.
# 새 폴더/파일을 올리려면 여기에 '!' 줄을 추가하세요. 키/설정/장부/로그는 절대 추가하지 마세요.
# ==========================================================
/*
!/.gitignore
!/.github/
!/README.md
!/CONTEXT.md
!/TODO.md
!/LICENSE
!/.env.example
!/*.py
!/*.md
!/*.sh
!/background.png
!/background.gif
!/프롬프트.txt
!/Vwap 연구.txt
!/리버스모드.txt
!/롤백 구조 봇.txt
!/차세대 avwap 프롬프트.txt
!/자가 업데이트 설치 가이드.txt
!/[[]긴급 실전 팁] KST(한국시간) 영구 고정 비기.txt

# 봇 폴더: 코드와 README 만
!/toss_dca_bot/
/toss_dca_bot/*
!/toss_dca_bot/*.py
!/toss_dca_bot/README.md

!/toss_sniper/
/toss_sniper/*
!/toss_sniper/*.py
!/toss_sniper/README.md
!/toss_sniper/LICENSE

!/bithumb_laoeo_bot/
/bithumb_laoeo_bot/*
!/bithumb_laoeo_bot/*.py
!/bithumb_laoeo_bot/README.md

# 허용 범위 안이라도 항상 제외
.env
.env.*
!.env.example
*.bak
*.save
*.log
__pycache__/
venv/
"""

HOOK = r"""#!/usr/bin/env python3
# pre-commit: 비밀키/서버 파일이 커밋되는 것을 막는다 (secure_repo_20261021.py 가 설치)
import re, subprocess, sys
BLOCK_PATH = re.compile(r'(^|/)(\.bash_history|\.bashrc|\.profile|\.ssh/|\.cache/|\.env(?!\.example$)|\.env_vars|API\.txt|auth\.json|token[^/]*\.dat|[^/]+\.save)', re.I)
PATTERNS = [
    ("텔레그램 봇 토큰", re.compile(r'\b\d{8,10}:[A-Za-z0-9_-]{35}\b')),
    ("JWT/액세스 토큰", re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}')),
    ("개인키", re.compile(r'-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ("GitHub 토큰", re.compile(r'\b(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})')),
    ("Google API 키", re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b')),
    ("키 값 직접 대입", re.compile(r'''(?i)(secret|api[_-]?key|access[_-]?key|client[_-]?secret|app[_-]?secret|password|passwd|token)["']?\s*[:=]\s*["']([A-Za-z0-9/+=_\-\.]{20,})["']''')),
]
files = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], capture_output=True, text=True).stdout.splitlines()
bad = []
for f in files:
    if BLOCK_PATH.search(f):
        bad.append(f"{f}: 올리면 안 되는 파일"); continue
    blob = subprocess.run(["git", "show", f":{f}"], capture_output=True).stdout
    if len(blob) > 5_000_000:
        bad.append(f"{f}: 5MB 초과 파일"); continue
    text = blob.decode("utf-8", "ignore")
    for name, pat in PATTERNS:
        m = pat.search(text)
        if m:
            line = text.count("\n", 0, m.start()) + 1
            bad.append(f"{f}:{line}: {name} 의심")
            break
if bad:
    print("\n🚫 커밋 차단: 비밀키 또는 서버 파일이 포함되어 있습니다.")
    for b in bad[:30]: print("   -", b)
    print("\n   해당 파일을 빼거나(git restore --staged <파일>) 키를 .env 로 옮긴 뒤 다시 커밋하세요.\n")
    sys.exit(1)
"""

# 1) .gitignore
gi = HOME / ".gitignore"
if gi.exists():
    (HOME / ".gitignore.before_secure").write_text(gi.read_text(encoding="utf-8"), encoding="utf-8")
gi.write_text(GITIGNORE, encoding="utf-8")
print("1) .gitignore 화이트리스트로 교체 (이전 파일: .gitignore.before_secure)")

# 2) 추적 정리
before = set(git("ls-files").splitlines())
git("rm", "-r", "-q", "--cached", ".")
git("add", "-A")
after = set(git("ls-files").splitlines())
removed = sorted(before - after)
print(f"2) Git 추적에서 제거 {len(removed)}개 / 남은 파일 {len(after)}개 (서버의 실제 파일은 그대로)")
for p in [x for x in removed if re.search(r'(\.bash|\.ssh|\.env|config\.json|API\.txt|\.save)', x)][:15]:
    print("   - 제거:", p)

# 3) pre-commit 훅
hook = HOME / ".git" / "hooks" / "pre-commit"
hook.write_text(HOOK, encoding="utf-8")
hook.chmod(0o755)
print("3) pre-commit 비밀키 검사 훅 설치")
r = subprocess.run([sys.executable, str(hook)], capture_output=True, text=True)
if r.returncode != 0:
    print("   ⚠️ 현재 올라갈 파일 중 검사에 걸린 것이 있습니다 (커밋 전에 확인 필요):")
    print("\n".join("   " + l for l in r.stdout.strip().splitlines()[1:]))
else:
    print("   현재 올라갈 파일 검사 통과")

# 4) 권한 600
secret_files = [HOME / ".env", HOME / ".bashrc", HOME / "bithumb_laoeo_bot" / ".env_vars",
                HOME / "bithumb_laoeo_bot" / "config.json", HOME / "bithumb_laoeo_bot" / "config.json.save",
                HOME / "toss_sniper" / "API.txt"] + list(HOME.glob("*/.env"))
fixed = []
for p in secret_files:
    if p.exists() and p.is_file():
        if stat.S_IMODE(p.stat().st_mode) & 0o077:
            p.chmod(0o600); fixed.append(str(p.relative_to(HOME)))
print("4) 권한 600 적용:", ", ".join(fixed) if fixed else "변경 없음")

# 5) 키 위치 안내
print("\n5) 재발급한 키를 넣을 위치")
def svc_env(unit):
    try:
        out = subprocess.run(["systemctl", "cat", unit], capture_output=True, text=True).stdout
    except Exception:
        return []
    return [l.strip() for l in out.splitlines() if l.strip().startswith(("EnvironmentFile", "WorkingDirectory", "ExecStart"))] + \
           [re.sub(r'=.*', '=…(값 숨김)', l.strip()) for l in out.splitlines() if l.strip().startswith("Environment=")]
for unit, where in [("bithumb_bot.service", "빗썸: BITHUMB_ACCESS_KEY / BITHUMB_SECRET_KEY / TELEGRAM_BOT_TOKEN"),
                    ("toss_dca.service", "토스 적립: ~/toss_dca_bot/.env (TOSS_CLIENT_ID / TOSS_CLIENT_SECRET / TELEGRAM_BOT_TOKEN)"),
                    ("toss_sniper.service", "토스 스나이퍼: ~/toss_sniper/.env (같은 항목)")]:
    print(f"   [{unit}] {where}")
    for l in svc_env(unit): print("      ", l)
for p in [HOME / ".bashrc", HOME / "bithumb_laoeo_bot" / ".env_vars", HOME / "bithumb_laoeo_bot" / "config.json"]:
    if p.exists():
        keys = sorted(set(re.findall(r'(BITHUMB_[A-Z_]*KEY|TELEGRAM_[A-Z_]*TOKEN|TOSS_[A-Z_]*SECRET)', p.read_text(errors="ignore"))))
        if keys: print(f"   옛 키가 남아 있는 파일: {p.relative_to(HOME)} → {', '.join(keys)} (새 키로 교체 필요)")

print("\n다음 단계 (커밋·푸시):")
print('   git commit -m "보안: 비밀키·서버 파일 제거, 화이트리스트 .gitignore 적용"')
print("   git push")
