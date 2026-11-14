#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================================================
# FILE: /opt/bot-office/fanding_direct_upload.py   (사무실 vNEXT · 2026-11-14)
# 팬딩 가격표 직접 넣기 — 웹 서버(/api/fanding/upload)를 거치지 않고 팬딩 INBOX 에 바로 넣는다
#  · 웹 서버(bot-office.service)를 끈 뒤에도 수동으로 가격표 이미지를 넣을 수 있게 하는 대체 경로
#  · 검사는 fanding_trade.http_upload() 과 같다:
#      업로드 토큰(서버 설정 fanding.json 의 upload_token 과 비교 · hmac.compare_digest · 20자 미만이면 거부)
#      크기(1000 < n <= 8_000_000) · 이미지 형식(JPEG/PNG/RIFF 머리 글자)
#    + 필요 종가일(expected) 검사: live 는 YYYY-MM-DD 이고 fanding_trade.last_session_date() 와 같아야 함
#  · INBOX 파일 형식도 같다: P = {name}.json + {name}.img + bridge_state()['last_received'] 갱신
#                            VR6 = fanding_vr6.http_upload() 과 같은 {name}.json(kind=vr6) + {name}.img, 끝에 {stamp}.vr6done
#  · 그 뒤 판독·주문은 상시 프로그램(bot-office-fanding.service)의 process_inbox() 가 그대로 한다 (그 코드는 안 바꿈)
#  · 토큰은 FANDING_UPLOAD_TOKEN 환경변수 또는 화면에 안 보이는 입력으로 받는다 · 어디에도 출력·저장하지 않는다
#
# 사용 (서버 SSH · 상시 프로그램과 같은 계정 root 로):
#   sudo python3 /opt/bot-office/fanding_direct_upload.py p  /tmp/표.jpg [--post 글주소] [--expected YYYY-MM-DD]
#   sudo python3 /opt/bot-office/fanding_direct_upload.py history /tmp/옛표.jpg [--post 글주소]
#   sudo python3 /opt/bot-office/fanding_direct_upload.py vr6 /tmp/v1.jpg /tmp/v2.jpg --post 글주소
#   sudo python3 /opt/bot-office/fanding_direct_upload.py check /tmp/표.jpg      (검사만 · INBOX 에 안 씀)
# 끝코드: 0 성공 · 1 검사 실패(아무것도 안 씀) · 2 사용법 오류 · 3 저장 실패
# ==========================================================
import argparse
import getpass
import hashlib
import hmac
import json
import os
import re
import sys
import time
import uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fanding_trade as ft

VERSION = "vNEXT"


class Reject(Exception):
    """검사 실패 — INBOX 에 아무것도 쓰지 않음"""


# ---------------------------------------------------------- 검사 (http_upload 과 같은 조건)
def check_token(given, token):
    if len(token) < 20 or not hmac.compare_digest(given.encode(), token.encode()):
        raise Reject("bad_token")


def check_image(data):
    if not 1000 < len(data) <= 8_000_000:
        raise Reject("bad_size")
    if not (data[:3] == b"\xff\xd8\xff" or data[:4] == b"\x89PNG" or data[:4] == b"RIFF"):
        raise Reject("not_image")


def check_expected(expected, mode, need=None):
    """live: YYYY-MM-DD 이고 지금 필요한 종가일(last_session_date)과 같아야 함 · history: 형식만 (빈 값 허용)"""
    if mode == "history" and not expected:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", expected or ""):
        raise Reject("bad_expected")
    try:
        date.fromisoformat(expected)
    except ValueError:
        raise Reject("bad_expected")
    if mode == "live":
        need = need or ft.last_session_date().isoformat()
        if expected != need:
            raise Reject(f"expected_mismatch (지금 필요한 종가일 {need})")
    return expected


# ---------------------------------------------------------- 쓰기 (원자적: 임시 이름에 쓰고 이름 바꿈 · *.img/*.json 로 미리 안 잡힘)
def _own_like_inbox(path):
    try:
        st = ft.INBOX.stat()
        os.chown(path, st.st_uid, st.st_gid)
    except (PermissionError, OSError):
        pass
    os.chmod(path, 0o644)


def _put(path, payload):
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex[:6]}.tmp")
    if isinstance(payload, bytes):
        tmp.write_bytes(payload)
    else:
        tmp.write_text(payload, encoding="utf-8")
    _own_like_inbox(tmp)
    os.replace(tmp, path)


def write_p(data, meta):
    """http_upload 과 같은 이름·내용: {unix}_{sha10}.json → .img, 그다음 bridge last_received"""
    name = f"{int(time.time())}_{hashlib.sha256(data).hexdigest()[:10]}"
    ft.INBOX.mkdir(parents=True, exist_ok=True)
    _put(ft.INBOX / f"{name}.json", json.dumps(meta, ensure_ascii=False))
    _put(ft.INBOX / f"{name}.img", data)
    with ft.bridge_state() as b:
        b["last_received"] = {"at": ft.now_kst().isoformat(), "mode": meta["mode"]}
    return name


def write_vr6(data, meta):
    """fanding_vr6.http_upload(kind=vr6) 과 같은 이름·내용 (bridge 는 안 건드림 — 원래도 안 함)"""
    name = f"{int(time.time())}_{hashlib.sha256(data).hexdigest()[:10]}"
    ft.INBOX.mkdir(parents=True, exist_ok=True)
    _put(ft.INBOX / f"{name}.json", json.dumps(meta, ensure_ascii=False))
    _put(ft.INBOX / f"{name}.img", data)
    return name


def write_vr6_done(post, count):
    stamp = f"{int(time.time())}_{uuid.uuid4().hex[:6]}"
    meta = {"post": post[:300], "count": str(count)[:4], "at": time.time()}
    _put(ft.INBOX / f"{stamp}.vr6done", json.dumps(meta, ensure_ascii=False))
    return stamp


# ---------------------------------------------------------- 묶음 처리 (먼저 전부 검사 → 하나라도 실패면 아무것도 안 씀)
def upload(kind, images, given_token, post="", expected="", write=True, need=None):
    """kind: p | history | vr6. images: [(경로, bytes)]. 반환: 쓴 이름 목록"""
    check_token(given_token, ft.cfg().get("upload_token") or "")
    if not images:
        raise Reject("no_image")
    for _p, data in images:
        check_image(data)
    post = post[:300]
    names = []
    if kind == "vr6":
        if not write:
            return names
        n = len(images)
        for i, (_p, data) in enumerate(images):
            names.append(write_vr6(data, {"kind": "vr6", "post": post, "idx": str(i)[:4], "count": str(n)[:4]}))
        names.append(write_vr6_done(post, n))
        return names
    mode = "history" if kind == "history" else "live"
    if mode == "live" and not expected:
        expected = need or ft.last_session_date().isoformat()   # deliver()·request_scan() 과 같은 값
    expected = check_expected(expected, mode, need)
    if not write:
        return names
    seed = f"{post}|{expected}" if post else f"manual|{expected}|{time.time()}|{uuid.uuid4().hex}"
    batch = hashlib.sha256(seed.encode()).hexdigest()[:16]          # deliver() 와 같은 만들기 (글 주소가 있으면 같은 값)
    n = len(images)
    for i, (_p, data) in enumerate(images):
        meta = {"post": post, "at": ft.now_kst().isoformat(), "batch": batch,
                "idx": str(i), "count": str(n), "mode": mode, "request_id": "", "expected": expected[:10]}
        names.append(write_p(data, meta))
    return names


def _token():
    t = os.environ.get("FANDING_UPLOAD_TOKEN")
    if t is None:
        t = getpass.getpass("업로드 토큰 (입력해도 화면에 안 보임): ")
    return t.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=f"팬딩 가격표 직접 넣기 {VERSION} (웹 서버 없이)")
    ap.add_argument("kind", choices=("p", "history", "vr6", "check"))
    ap.add_argument("images", nargs="+")
    ap.add_argument("--post", default="", help="팬딩 글 주소 (있으면 같은 글 중복 알림 묶음에 씀)")
    ap.add_argument("--expected", default="", help="필요 종가일 YYYY-MM-DD (live 기본값 = 지금 필요한 종가일)")
    a = ap.parse_args(argv)
    images = []
    for p in a.images:
        try:
            with open(p, "rb") as fh:
                images.append((p, fh.read(8_000_001)))
        except OSError as e:
            print(f"⛔ 파일을 못 읽음: {p} ({type(e).__name__})")
            return 2
    kind = "p" if a.kind == "check" else a.kind
    try:
        names = upload(kind, images, _token(), a.post, a.expected, write=a.kind != "check")
    except Reject as e:
        print(f"⛔ 넣지 않았어요: {e}")
        return 1
    except OSError as e:
        print(f"⛔ 저장 실패: {type(e).__name__}")
        return 3
    if a.kind == "check":
        print(f"✅ 검사 통과 ({len(images)}장) · INBOX 에는 안 씀")
    else:
        print(f"✅ INBOX 에 넣었어요 ({kind} · 이미지 {len(images)}장) · 1~2분 안에 팬딩 봇이 판독해 알려 줘요")
        for nm in names:
            print("  ", nm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
