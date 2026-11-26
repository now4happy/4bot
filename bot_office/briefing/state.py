# briefing/state.py — 상태·sent 마커·latest.json 원자적 저장 (포트폴리오 스냅샷은 2026-11-26에 삭제됨)
import json
import os
import re
import tempfile

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def expand(path):
    return os.path.expanduser(path)


def atomic_write_json(path, obj, mode=0o644):
    """임시 파일 → fsync → rename. 중간에 죽어도 옛 파일이 남는다."""
    path = expand(path)
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_json(path, default=None):
    try:
        with open(expand(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


class State:
    def __init__(self, root):
        self.root = expand(root)
        self.hist_dir = os.path.join(self.root, "history")
        self.sent_dir = os.path.join(self.root, "sent")
        self.latest_path = os.path.join(self.root, "briefing_latest.json")
        self.state_path = os.path.join(self.root, "state.json")

    def ensure(self):
        for d in (self.root, self.hist_dir, self.sent_dir):
            os.makedirs(d, exist_ok=True)

    # latest / history
    def read_latest(self):
        return read_json(self.latest_path, None)

    def save_latest(self, obj, date):
        self.ensure()
        atomic_write_json(self.hist_dir + "/%s.json" % date, obj)
        atomic_write_json(self.latest_path, obj)

    # sent 마커
    def _marker(self, date, kind):
        return os.path.join(self.sent_dir, "%s.%s" % (date, kind))

    def is_sent(self, date, kind):
        return os.path.exists(self._marker(date, kind))

    def mark_sent(self, date, kind):
        self.ensure()
        with open(self._marker(date, kind), "w") as f:
            f.write("sent\n")

    # 상태 (null_reissue_streak)
    def load_state(self):
        s = read_json(self.state_path, None) or {}
        s.setdefault("null_reissue_streak", 0)  # 초기값 0 (Q6)
        s.setdefault("streak_alerted", False)
        s.setdefault("last_streak_date", None)
        return s

    def save_state(self, s):
        self.ensure()
        atomic_write_json(self.state_path, s)

    # 보관 기간 정리
    def prune(self, today, days):
        import datetime as dt
        limit = (dt.date.fromisoformat(today) - dt.timedelta(days=days)).isoformat()
        removed = 0
        for d, ext in ((self.hist_dir, ".json"),):
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for n in names:
                stem = n[:10]
                if _DATE_RE.match(stem) and stem < limit:
                    try:
                        os.unlink(os.path.join(d, n))
                        removed += 1
                    except OSError:
                        pass
        try:
            for n in os.listdir(self.sent_dir):
                stem = n[:10]
                if _DATE_RE.match(stem) and stem < limit:
                    os.unlink(os.path.join(self.sent_dir, n))
        except OSError:
            pass
        return removed
