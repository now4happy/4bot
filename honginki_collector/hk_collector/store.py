"""append-only JSONL 저장. 경로: DATA_DIR/YYYYMMDD/<이름>.jsonl (KST 날짜)."""
import json
import os
import threading
import time
from collections import Counter
from datetime import datetime

from .config import KST


def now_kst():
    return datetime.now(KST)


class Store:
    def __init__(self, root):
        self.root = root
        self.day = None
        self.files = {}
        self.lock = threading.Lock()
        self.counts = Counter()

    def _file(self, name):
        day = now_kst().strftime("%Y%m%d")
        if day != self.day:
            self._close_all()
            self.day = day
            self.counts = Counter()
        f = self.files.get(name)
        if f is None:
            d = os.path.join(self.root, day)
            os.makedirs(d, exist_ok=True)
            f = open(os.path.join(d, name + ".jsonl"), "a", encoding="utf-8")
            self.files[name] = f
        return f

    def write(self, name, rec):
        row = {"recv_ts": now_kst().isoformat(timespec="milliseconds"),
               "recv_ns": time.time_ns(), **rec}
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        with self.lock:
            self._file(name).write(line + "\n")
            self.counts[name] += 1

    def event(self, ev, **kw):
        self.write("events", {"ev": ev, **kw})

    def write_summary(self, summary):
        with self.lock:
            day = self.day or now_kst().strftime("%Y%m%d")
            d = os.path.join(self.root, day)
            os.makedirs(d, exist_ok=True)
            tmp = os.path.join(d, "summary.json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=1)
            os.replace(tmp, os.path.join(d, "summary.json"))

    def flush(self):
        with self.lock:
            for f in self.files.values():
                f.flush()

    def _close_all(self):
        for f in self.files.values():
            f.close()
        self.files = {}

    def close(self):
        with self.lock:
            self._close_all()
