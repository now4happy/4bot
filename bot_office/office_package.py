#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_package.py   (OFFICE_PACKAGE_V2)
# 여러 파일을 한 번에 바꾸는 결재 변경안(패키지) 등록
#  - 패키지 폴더: /var/lib/bot-office-deploy/packages/<id>/{manifest.json, before/<파일>, after/<파일>}
#  - 공개 변경안: /var/lib/bot-office-deploy-public/<id>.json  (웹 결재함·텔레그램이 보는 내용, diff 포함)
#  - 적용은 기존과 같이 승인 후 deploy_worker → apply_deploy 가 담당 (중지 → 전부 교체 → 시작 확인 → 실패 시 전부 복구)
# ==========================================================
import ast, difflib, hashlib, json, os, tempfile, uuid
from datetime import datetime, timezone
from pathlib import Path

R = Path(os.environ.get("OFFICE_ROOT", "/"))
BASE = R / "var/lib/bot-office-deploy"
PUBLIC = R / "var/lib/bot-office-deploy-public"
ALL_UNITS = ("han4384tubot.service", "toss_sniper.service", "toss_dca.service", "bithumb_bot.service")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def targets():
    try:
        return json.loads((BASE / "targets.json").read_text()).get("targets", {})
    except (OSError, ValueError):
        return {}


def _publish(folder, m):
    diff = []
    for f in m["files"]:
        old = (folder / "before" / f["file"]).read_bytes().decode("utf-8-sig", "replace")
        new = (folder / "after" / f["file"]).read_bytes().decode("utf-8-sig", "replace")
        diff.append("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                 fromfile="변경 전/" + f["file"], tofile="변경 후/" + f["file"])))
    pub = dict(m)
    pub["diff"] = "\n".join(diff)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=PUBLIC)
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(pub, fh, ensure_ascii=False, indent=2)
        try:
            import grp
            os.chown(tmp, 0, grp.getgrnam("bot-office").gr_gid)
        except (KeyError, PermissionError):
            pass
        os.chmod(tmp, 0o640)
        os.replace(tmp, PUBLIC / (m["id"] + ".json"))
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return pub


def register(unit, changes, title, source="office", reason=""):
    """changes: {파일이름: 새 내용(bytes)}  → 패키지 번호(uuid) 반환"""
    if unit not in ALL_UNITS:
        raise ValueError("허용되지 않은 봇")
    t = targets().get(unit)
    if not isinstance(t, dict) or not t.get("root"):
        raise ValueError("대상 봇 정보(targets.json) 없음")
    root = Path(t["root"])
    if not changes or len(changes) > 12:
        raise ValueError("변경 파일 수 확인 필요(1~12개)")
    files = []
    for name, new in changes.items():
        if Path(name).name != name or name not in t.get("files", []):
            raise ValueError(f"등록된 대상 파일이 아님: {name}")
        cur = root / name
        if cur.is_symlink() or not cur.is_file() or cur.stat().st_size > 1_000_000 or len(new) > 1_000_000:
            raise ValueError(f"대상 파일 확인 필요: {name}")
        compile(new, name, "exec", ast.PyCF_ONLY_AST)
        old = cur.read_bytes()
        if old != new:
            files.append((name, old, new, cur.stat()))
    if not files:
        raise ValueError("변경 내용이 없습니다")
    os.umask(0o077)
    ident = str(uuid.uuid4())
    folder = BASE / "packages" / ident
    (folder / "before").mkdir(parents=True, mode=0o700)
    (folder / "after").mkdir(mode=0o700)
    for name, old, new, _ in files:
        (folder / "before" / name).write_bytes(old)
        (folder / "after" / name).write_bytes(new)
    first = files[0]
    m = {
        "id": ident, "version": 2, "unit": unit,
        "file": first[0] if len(files) == 1 else f"{first[0]} 외 {len(files) - 1}개",
        "files": [{"file": n, "before_sha256": sha(o), "after_sha256": sha(w)} for n, o, w, _ in files],
        "title": title.strip()[:200], "reason": reason.strip()[:600], "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "before_sha256": sha(first[1]), "after_sha256": sha(first[2]),
        "status": "승인 대기",
        "validation": "Python 문법 검사 통과 · 승인 후 봇 중지 → 전체 교체 → 시작 확인 (실패 시 전부 원래대로)",
    }
    (folder / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2))
    _publish(folder, m)
    return ident
