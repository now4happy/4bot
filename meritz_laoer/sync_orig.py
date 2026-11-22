# ==========================================================
# FILE: meritz_laoer/sync_orig.py   (MERITZ_LAOER v2.9.0 — 판 29 3단계: 원작 업뎃 적용 도구)
# 원작 저장소(pipios4006-boop/pipiosToss_bot) 업뎃을 orig_sniper/ 에 반영하고, 뭐가 바뀌었는지 알려 준다. 서버·브로커·주문과 무관 (파일 복사·비교만).
#   python sync_orig.py --check                       복사본이 ORIGIN.json 해시와 같은지 + shim 이 원작이 가져다 쓰는 이름을 다 내보내는지
#   python sync_orig.py --from <원작 clone 폴더>        원작과 비교만 (복사 안 함): 복사 대상 3개 same/changed, 안 복사하는 파일(watch) 변경 알림
#   python sync_orig.py --from <폴더> --apply          복사 대상 3개를 원작 그대로 덮어쓰고 ORIGIN.json 갱신 → --check 자동 실행
# 끝에 항상 test_hybrid_v290.py 를 돌리라고 알려 준다 (원작 업뎃이 어댑터를 깨면 거기서 잡힘).
# ==========================================================
import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OD = os.path.join(HERE, "orig_sniper")
MANIFEST = os.path.join(OD, "ORIGIN.json")


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


def check():
    m, bad = load(), 0
    for f, h in m["files"].items():
        ok = os.path.exists(os.path.join(OD, f)) and sha(os.path.join(OD, f)) == h
        print(("OK   " if ok else "DIFF ") + f)
        bad += 0 if ok else 1
    code = ("import sys; sys.path.insert(0, %r); import quant_engine_core, quant_engine, toss_api, sniper_exit_plugin; print('import OK')" % OD)
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    print((r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr).strip() else "import 결과 없음")
    if r.returncode != 0:
        bad += 1
        print("→ 원작이 새 이름을 가져다 쓰는데 shim(orig_sniper/toss_api.py)이 못 내보냄. toss_api_core.py 에 그 이름이 있는지 확인.")
    return bad


def compare(src):
    m, changed = load(), []
    for f, h in m["files"].items():
        p = os.path.join(src, f)
        if not os.path.exists(p):
            print("MISSING  %s (원작에 없음 — 이름이 바뀌었는지 확인)" % f)
            changed.append(f)
            continue
        if sha(p) == h:
            print("same     " + f)
            continue
        changed.append(f)
        a = open(os.path.join(OD, f), encoding="utf-8").read().splitlines()
        b = open(p, encoding="utf-8").read().splitlines()
        d = [x for x in difflib.unified_diff(a, b, lineterm="", n=0) if x[:1] in "+-" and x[:3] not in ("+++", "---")]
        print("changed  %s (+%d −%d 줄)" % (f, sum(1 for x in d if x[0] == "+"), sum(1 for x in d if x[0] == "-")))
    w = []
    for f, h in (m.get("watch") or {}).items():
        p = os.path.join(src, f)
        if os.path.exists(p) and sha(p) != h:
            w.append(f)
    if w:
        print("watch 변경 (복사 안 하는 원작 파일 — 어댑터·하이브리드 실행부에 영향 있는지 사람이 확인): " + ", ".join(w))
    else:
        print("watch 변경 없음")
    return changed, w


def apply(src, changed):
    m = load()
    for f in changed:
        p = os.path.join(src, f)
        if os.path.exists(p):
            with open(p, "rb") as a, open(os.path.join(OD, f), "wb") as b:
                b.write(a.read())
            m["files"][f] = sha(os.path.join(OD, f))
    try:
        m["commit"] = subprocess.check_output(["git", "-C", src, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        m["commit"] = m.get("commit", "") + " (새 커밋 미확인)"
    for f in list(m.get("watch") or {}):
        p = os.path.join(src, f)
        if os.path.exists(p):
            m["watch"][f] = sha(p)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=1, ensure_ascii=False)
    print("복사·ORIGIN.json 갱신 완료: " + (", ".join(changed) or "바뀐 파일 없음"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--from", dest="src")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.src:
        ch, _w = compare(a.src)
        if a.apply:
            apply(a.src, ch)
            a.check = True
    if a.check or not a.src:
        sys.exit(1 if check() else 0)
    print("다음: test_hybrid_v290.py 실행")


if __name__ == "__main__":
    main()
