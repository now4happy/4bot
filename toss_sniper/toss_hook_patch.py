# -*- coding: utf-8 -*-
"""
FILE: toss_sniper/toss_hook_patch.py  (v1.2.8 · 방: 2. 토스 스나이퍼 · 작업 toss-token-q5-auto-reapply)

원작 자동 동기화(plugin_updater._extract_upstream_files_sync)는 원작 toss_api.py 를 바이트 그대로
toss_sniper/ 에 덮어써서 '토스 토큰 공유 HOOK'(toss_token_share 로 3곳이 토큰 1개를 같이 씀)이 사라진다.
이 모듈은 동기화 직후 저장된 패치를 다시 적용해 훅을 되살린다.

 · PATCH_TEXT = 작업 toss-token-shared-restore 판 1 의 diff (기준 now4happy/4bot@cee85d2)
   기준 toss_api.py sha256  = PATCH_BASE_SHA256
   적용 후 toss_api.py sha256 = PATCH_RESULT_SHA256
 · 이 파일은 plugin_updater.UPSTREAM_SYNC_MODULES(원작 덮어쓰기 대상)에 들어 있지 않아 동기화 때 지워지지 않는다.
 · 외부 프로그램(patch/git apply)을 쓰지 않는 순수 파이썬 적용기다. 줄 번호가 밀려도 앞뒤 문맥이 같으면 찾아 붙인다.
 · 안 맞으면(원작이 그 부분을 바꿈) 원작 파일을 한 글자도 건드리지 않고 ("failed", 이유)를 돌려준다.
   예외는 밖으로 던지지 않는다 → 스나이퍼 동작·동기화 흐름을 멈추지 않는다.
 · 매매 로직은 건드리지 않는다. 비밀값·토큰 값 없음.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import tempfile
from typing import Iterable, List, Optional, Tuple

logger = logging.getLogger("toss_sniper.toss_hook_patch")

PATCH_TARGET = "toss_api.py"
PATCH_BASE_COMMIT = "cee85d2"
PATCH_BASE_SHA256 = "14587b693e30b02704b64990ee82ff925b6e0de7a72a711591a5d77d91a9ba6c"
PATCH_RESULT_SHA256 = "f5b341101cb89a688417e914d71a256968ef776790a10f40f5d7e1368635c330"

# 훅이 들어갔는지 보는 표시 (지시 4): 표지 문구 + _TTS 참조 + try_acquire 호출
HOOK_MARKER = "[🔗토스 토큰 공유 HOOK]"
HOOK_REQUIRED_TOKENS = ("_TTS", "try_acquire")

PATCH_TEXT = r'''--- a/toss_sniper/toss_api.py
+++ b/toss_sniper/toss_api.py
@@ -47,6 +47,11 @@
     httpx = None  # type: ignore
     _HTTPX_KEEPALIVE_OK = False

+try:  # [🔗토스 토큰 공유 HOOK] 2번 스나이퍼·live_board·브리핑이 같은 토큰 1개를 같이 씀 (없으면 원작 그대로 직접 발급)
+    import toss_token_share as _TTS
+except Exception:
+    _TTS = None
+
 from toss_api_core import (
     ALLOWED_SYMBOLS,
     AssassinLedger,
@@ -413,6 +418,7 @@

         self._access_token: str = ""
         self._token_expires_mono: float = 0.0
+        self._tts_bad_token: str = ""  # [🔗토스 토큰 공유 HOOK] 401 로 거절된 토큰 (공유 토큰 재발급 판단용)
         self._token_lock: asyncio.Lock = asyncio.Lock()

         self.account_seq: Optional[int] = None
@@ -603,18 +609,47 @@
                 "Accept": "application/json",
             }

-            status_code, payload = await asyncio.wait_for(
-                asyncio.to_thread(
-                    self._execute_http_sync,
-                    "POST",
-                    url,
-                    headers,
-                    form_data,
-                    "AUTH",
-                    10.0,
-                ),
-                timeout=12.0,
-            )
+            # [🔗토스 토큰 공유 HOOK] 직접 발급하면 다른 곳(live_board·브리핑)의 토큰이 취소(401)되므로
+            # 공유 토큰을 먼저 가져온다. 이미 다른 곳이 새로 받아 둔 토큰이면 그대로 쓰고,
+            # 거절된 바로 그 토큰이 아직 공유 토큰일 때만 새로 발급한다. 공유 불가(None)면 아래 원작 직접 발급으로 간다.
+            _bad = self._tts_bad_token or self._access_token
+            _sh = None
+            if _TTS is not None:
+                try:
+                    _sh = await asyncio.wait_for(
+                        asyncio.to_thread(
+                            _TTS.try_acquire,
+                            self.base_url,
+                            self.client_id,
+                            self.client_secret,
+                            bool(force_refresh or _bad),
+                            _bad,
+                            "2번 스나이퍼",
+                        ),
+                        timeout=15.0,
+                    )
+                except Exception:
+                    _sh = None
+            if _sh and _sh[0] == "ok":
+                self._access_token = _sh[1]
+                self._token_expires_mono = time.monotonic() + float(_sh[2])
+                self._tts_bad_token = ""
+                return self._access_token
+            if _sh and _sh[0] == "fail":
+                status_code, payload = _sh[1], _sh[2]
+            else:
+                status_code, payload = await asyncio.wait_for(
+                    asyncio.to_thread(
+                        self._execute_http_sync,
+                        "POST",
+                        url,
+                        headers,
+                        form_data,
+                        "AUTH",
+                        10.0,
+                    ),
+                    timeout=12.0,
+                )
             if status_code != 200 or not isinstance(payload, dict):
                 err_code = str(payload.get("error") or f"http-{status_code}")
                 err_desc = str(
@@ -633,6 +668,7 @@

             self._access_token = token
             self._token_expires_mono = time.monotonic() + float(expires_in)
+            self._tts_bad_token = ""
             return self._access_token

     async def ensure_account_seq(self) -> int:
@@ -835,6 +871,7 @@
                 )

                 if status_code == 401 and attempt < max_retries:
+                    self._tts_bad_token = token  # [🔗토스 토큰 공유 HOOK] 거절된 토큰 기억 (비우기 전에)
                     self._access_token = ""
                     force_token_refresh = True
                     last_exc = None
'''

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def hook_present(text: str) -> bool:
    """toss_api.py 소스에 공유 토큰 훅 표시가 모두 있는가."""
    return HOOK_MARKER in text and all(tok in text for tok in HOOK_REQUIRED_TOKENS)


def _parse_hunks(patch_text: str) -> List[dict]:
    hunks: List[dict] = []
    cur: Optional[dict] = None
    lines = patch_text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    for line in lines:
        m = _HUNK_RE.match(line)
        if m:
            cur = {"old_start": int(m.group(1)), "old": [], "new": []}
            hunks.append(cur)
            continue
        if cur is None or line.startswith("\\"):
            continue  # 파일 머리줄 / '\ No newline' 표시
        if line.startswith("-"):
            cur["old"].append(line[1:])
        elif line.startswith("+"):
            cur["new"].append(line[1:])
        elif line.startswith(" "):
            cur["old"].append(line[1:])
            cur["new"].append(line[1:])
        elif line == "":  # 빈 문맥줄의 공백이 잘린 경우
            cur["old"].append("")
            cur["new"].append("")
    return hunks


def _apply_hunks(
    src_lines: List[str], hunks: List[dict]
) -> Tuple[Optional[List[str]], List[int], List[int]]:
    """(결과 줄 목록 또는 None, 맞지 않은 조각 번호들, 조각별 줄 이동량)"""
    out: List[str] = []
    pos = 0
    failed: List[int] = []
    shifts: List[int] = []
    for idx, h in enumerate(hunks, 1):
        old = h["old"]
        n = len(old)
        expect = h["old_start"] - 1
        cands = [
            k
            for k in range(pos, len(src_lines) - n + 1)
            if src_lines[k] == old[0] and src_lines[k : k + n] == old
        ]
        if not cands:
            failed.append(idx)
            continue
        k = min(cands, key=lambda x: abs(x - expect))
        out.extend(src_lines[pos:k])
        out.extend(h["new"])
        pos = k + n
        shifts.append(k - expect)
    if failed:
        return None, failed, shifts
    out.extend(src_lines[pos:])
    return out, failed, shifts


def check_hook_installed(target_dir: str) -> Tuple[bool, str]:
    """디스크의 toss_api.py 에 훅이 들어 있는지 검사 (지시 4)."""
    fp = os.path.join(target_dir, PATCH_TARGET)
    try:
        with open(fp, "rb") as f:
            raw = f.read()
        text = raw.decode("utf-8")
    except Exception as exc:
        return False, f"{PATCH_TARGET} 읽기 실패: {exc}"
    if hook_present(text):
        return True, f"훅 확인됨 (sha {_sha256(raw)[:8]})"
    missing = [t for t in (HOOK_MARKER,) + HOOK_REQUIRED_TOKENS if t not in text]
    return False, f"훅 없음 (원작 그대로 · 없는 표시 {len(missing)}개 · sha {_sha256(raw)[:8]})"


def _write_atomic(fp: str, raw: bytes) -> None:
    d = os.path.dirname(fp) or "."
    fd, tmp = tempfile.mkstemp(prefix=".hookpatch.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        try:
            shutil.copymode(fp, tmp)
        except Exception:
            pass
        os.replace(tmp, fp)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise


def _fail_note(up_sha: str, why: str) -> str:
    # 지시 5: 원작 파일 sha 와 기준 sha 를 함께 남겨 기준에서 얼마나 멀어졌는지 알 수 있게
    exact = up_sha == PATCH_BASE_SHA256
    return (
        f"{why} · 원작 {PATCH_TARGET} sha {up_sha[:8]} "
        f"({'기준과 동일' if exact else '기준과 다름'}) · "
        f"기준 {PATCH_BASE_COMMIT} sha {PATCH_BASE_SHA256[:8]} · 원작 파일 그대로 둠"
    )


def _reapply(target_dir: str, synced_files: Optional[Iterable[str]]) -> Tuple[str, str]:
    if synced_files is not None and PATCH_TARGET not in set(synced_files):
        return "skip", f"{PATCH_TARGET}는 동기화 대상 아님 · 재적용 없음"

    fp = os.path.join(target_dir, PATCH_TARGET)
    with open(fp, "rb") as f:
        raw = f.read()
    up_sha = _sha256(raw)
    try:
        text = raw.decode("utf-8")
    except Exception as exc:
        return "failed", _fail_note(up_sha, f"원작 파일 UTF-8 해석 실패({exc})")

    if hook_present(text):
        return "already", f"원작본에 훅이 이미 있음 · 재적용 생략 (sha {up_sha[:8]})"

    crlf = "\r\n" in text
    work = text.replace("\r\n", "\n") if crlf else text
    hunks = _parse_hunks(PATCH_TEXT)
    if not hunks:
        return "failed", _fail_note(up_sha, "저장된 패치가 비어 있음")

    new_lines, failed, shifts = _apply_hunks(work.split("\n"), hunks)
    if new_lines is None:
        nums = ",".join(f"#{i}" for i in failed)
        return "failed", _fail_note(
            up_sha, f"패치 {len(failed)}/{len(hunks)}개 조각이 안 맞음({nums})"
        )

    new_text = "\n".join(new_lines)
    if crlf:
        new_text = new_text.replace("\n", "\r\n")
    try:
        compile(new_text, fp, "exec")
    except SyntaxError as exc:
        return "failed", _fail_note(up_sha, f"패치 적용본 컴파일 실패({exc.msg}, {exc.lineno}행)")
    if not hook_present(new_text):
        return "failed", _fail_note(up_sha, "패치 적용 뒤에도 훅 표시가 없음")

    new_raw = new_text.encode("utf-8")
    new_sha = _sha256(new_raw)
    exact = up_sha == PATCH_BASE_SHA256
    if exact and new_sha != PATCH_RESULT_SHA256:
        return "failed", _fail_note(
            up_sha, f"적용 결과 sha {new_sha[:8]} ≠ 기대 {PATCH_RESULT_SHA256[:8]}"
        )

    _write_atomic(fp, new_raw)

    ok, chk = check_hook_installed(target_dir)  # 지시 4: 디스크 재확인
    if not ok:
        try:  # 쓰기 결과가 이상하면 원작 바이트로 되돌린다
            _write_atomic(fp, raw)
        except Exception:
            pass
        return "failed", _fail_note(up_sha, f"적용 뒤 디스크 검사 실패({chk})")

    if exact:
        where = f"기준 {PATCH_BASE_COMMIT}과 같은 원작본 · 결과 sha {new_sha[:8]} 일치"
    else:
        where = (
            f"원작본이 기준과 다름(원작 {up_sha[:8]} · 기준 {PATCH_BASE_SHA256[:8]}) · "
            f"조각 줄 이동 {shifts} · 결과 sha {new_sha[:8]}"
        )
    return "applied", f"토큰 공유 훅 재적용 완료 · {where}"


def reapply_after_sync(
    target_dir: str, synced_files: Optional[Iterable[str]] = None
) -> Tuple[str, str]:
    """원작 동기화 직후 호출. 반환: (상태, 설명)
    상태: 'applied'(재적용함) · 'already'(이미 훅 있음) · 'skip'(toss_api.py 동기화 아님) · 'failed'(원작 그대로 둠).
    어떤 경우에도 예외를 던지지 않고, 실패하면 원작 파일을 바꾸지 않는다."""
    try:
        status, note = _reapply(target_dir, synced_files)
    except Exception as exc:
        status, note = "failed", f"훅 재적용 중 예외({exc!r}) · 원작 파일 그대로 둠"
    if status == "failed":
        logger.error("🚨 [토큰 공유 훅] %s", note)
    else:
        logger.info("🔗 [토큰 공유 훅] %s: %s", status, note)
    return status, note
