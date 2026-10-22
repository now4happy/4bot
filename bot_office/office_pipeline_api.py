# OFFICE_PIPELINE_API_V1 — server.py(bot-office 사용자)가 쓰는 업무 흐름 조회/요청 모듈
# 실제 작업은 root 타이머(office_pipeline.py)가 하고, 여기서는 요청만 기록한다.
import json, os, re, tempfile, threading, uuid
from pathlib import Path
from datetime import datetime, timezone

R = Path(os.environ.get("OFFICE_ROOT", "/"))
PUBLIC = R / "var/lib/bot-office-pipeline-public/state.json"
REQUESTS = R / "var/lib/bot-office/market-manual/pipeline-requests.json"
LOCK = threading.Lock()


def _load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return default


def read():
    state = _load(PUBLIC, None)
    reqs = [{k: v for k, v in r.items() if k != "body"} for r in _load(REQUESTS, {}).get("items", [])]
    if state is None:
        return {"ready": False, "requests": reqs[-10:]}
    return {"ready": True, **state, "requests": reqs[-10:]}


def save(d):
    if not isinstance(d, dict):
        raise ValueError("잘못된 요청")
    action = d.get("action")
    if action not in ("scan", "retry", "dismiss", "request"):
        raise ValueError("허용하지 않는 요청")
    case = str(d.get("case", ""))
    extra = {}
    if action == "request":
        # 직접 수정 요청: 대상 봇/파일은 엔진이 공개한 목록 안에서만 허용
        targets = (_load(PUBLIC, {}) or {}).get("targets", {})
        unit, name = d.get("unit"), d.get("file")
        title, body = str(d.get("title", "")).strip(), str(d.get("body", "")).strip()
        if unit not in targets or (name != "auto" and name not in targets[unit].get("files", [])):
            raise ValueError("대상 봇/파일 확인 필요")
        if not 2 <= len(title) <= 80 or not 5 <= len(body) <= 1500:
            raise ValueError("제목 2~80자, 내용 5~1500자로 입력하세요")
        extra = {"unit": unit, "file": name, "title": title, "body": body}
    elif action != "scan" and not re.fullmatch(r"[0-9a-f]{8}", case):
        raise ValueError("안건 번호 확인 필요")
    with LOCK:
        data = _load(REQUESTS, {})
        items = data.get("items", []) if isinstance(data, dict) else []
        item = {"id": uuid.uuid4().hex, "action": action, "case": case, "at": datetime.now(timezone.utc).isoformat(), **extra}
        items = (items + [item])[-50:]
        REQUESTS.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=REQUESTS.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"items": items}, f, ensure_ascii=False, indent=2)
            os.chmod(tmp, 0o600)
            os.replace(tmp, REQUESTS)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return {"ok": True, "request": item}
