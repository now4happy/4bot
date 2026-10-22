#!/usr/bin/env python3
# ==========================================================
# FILE: /opt/bot-office/office_submit.py   (OFFICE_SUBMIT_V1)
# Claude가 만든 수정(git diff)을 사무실 결재함에 "결재 대기"로 등록
#   사용: (diff) | sudo python3 /opt/bot-office/office_submit.py <서비스명> "<제목>" "<쉬운 설명>"
#   - 봇 파일은 바꾸지 않습니다. 승인 후 기존 적용 담당이 적용 → 재시작 확인 → GitHub 업로드
# ==========================================================
import json, os, shutil, subprocess, sys, tempfile, uuid, fcntl
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import office_package  # noqa: E402
import office_pipeline as P  # noqa: E402


def main():
    if os.geteuid() != 0 and "OFFICE_ROOT" not in os.environ:
        raise SystemExit("🛑 sudo 로 실행해 주세요")
    if len(sys.argv) != 4:
        raise SystemExit("사용법: (diff) | sudo python3 office_submit.py <서비스명> <제목> <설명>")
    unit, title, reason = sys.argv[1], sys.argv[2].strip(), sys.argv[3].strip()
    if unit not in office_package.ALL_UNITS:
        raise SystemExit("🛑 허용되지 않은 봇: " + unit)
    t = office_package.targets().get(unit)
    if not t:
        raise SystemExit("🛑 대상 봇 정보(targets.json)가 없습니다")
    root = Path(t["root"])
    diff = sys.stdin.buffer.read()
    if not diff.strip() or len(diff) > 3_000_000:
        raise SystemExit("🛑 변경 내용(diff)을 읽지 못했습니다")
    r = subprocess.run(["git", "-c", "safe.directory=*", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    repo = Path(r.stdout.strip()) if r.returncode == 0 else root
    # diff 안의 파일 경로 → 봇 폴더 기준 파일 이름
    names = {}
    for line in diff.decode("utf-8", "replace").splitlines():
        if line.startswith("+++ b/"):
            rel = line[6:].strip()
            absp = (repo / rel).resolve()
            if absp.parent != root.resolve():
                raise SystemExit(f"🛑 이 봇 폴더 밖의 파일이 들어 있습니다: {rel}")
            names[rel] = absp.name
    if not names:
        raise SystemExit("🛑 diff 에서 바뀐 파일을 찾지 못했습니다")
    work = Path(tempfile.mkdtemp(prefix="office-submit-"))
    try:
        for rel in names:
            dst = work / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / rel, dst)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        (work / "change.diff").write_bytes(diff)
        chk = subprocess.run(["git", "-C", str(work), "apply", "--check", "change.diff"], capture_output=True, text=True)
        if chk.returncode:
            raise SystemExit("🛑 지금 서버 코드와 맞지 않아 등록하지 않았습니다 (코드가 그사이 바뀜). Claude에게 다시 맞춰 달라고 요청하세요.\n"
                             + (chk.stderr or chk.stdout).strip()[-300:])
        subprocess.run(["git", "-C", str(work), "apply", "change.diff"], check=True)
        changes = {names[rel]: (work / rel).read_bytes() for rel in names}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    total = 0
    for name, new in changes.items():
        old = (root / name).read_bytes().decode("utf-8-sig")
        problems, ch = P.verify(old, new.decode("utf-8-sig"), name, limit=0)
        problems = [p for p in problems if "위험 코드" not in p]   # Claude 수정은 대표님이 대화에서 검토한 내용
        if problems:
            raise SystemExit("🛑 검증 실패: " + " / ".join(problems)[:300])
        total += ch
    dep = office_package.register(unit, changes, "Claude · " + title, source="claude", reason=reason)
    # 업무 흐름판 안건으로 등록 (승인 → 적용 → GitHub 업로드를 기존 엔진이 추적)
    P.PIPE.mkdir(parents=True, exist_ok=True)
    with open(P.PIPE / "pipeline.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = P.load(P.PIPE / "cases.json", {})
        state.setdefault("cases", {})
        now = datetime.now(timezone.utc).isoformat()
        cid = uuid.uuid4().hex[:8]
        files = list(changes)
        case = {"id": cid, "unit": unit, "file": files[0], "files": files, "kind": "claude", "title": title[:80],
                "detail": reason[:1500], "line": 0, "func": "", "fingerprint": "claude-" + dep[:12], "auto": False,
                "why_manual": "", "created_at": now, "first_seen": now, "last_seen": now, "count": 1,
                "stage": "awaiting_approval", "note": f"Claude 수정 · {total}줄 변경 · 대표님 결재 대기",
                "history": [{"at": now, "stage": "awaiting_approval", "note": "Claude가 만든 수정 등록"}],
                "deploy_id": dep, "gemini_calls": 0, "commit": "", "reason": reason[:600], "changed_lines": total}
        state["cases"][cid] = case
        P.save(P.PIPE / "cases.json", state)
    P.notify_approval(case)
    print(f"✅ 결재함 등록 완료 · {P.UNIT_NAMES.get(unit, unit)} · {', '.join(files)} · {total}줄 변경")
    print("   텔레그램 사무실 비서의 [✅ 승인] 버튼이나 웹 결재함에서 승인해 주세요. (봇은 아직 바뀌지 않았습니다)")


if __name__ == "__main__":
    main()
