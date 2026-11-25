# briefing/tg_send.py — 텔레그램 전송. 어느 봇·방으로 보낼지는 send(text, cfg_path) 의 설정 파일 경로가 정한다.
#   포트폴리오 브리핑 = config.json paths.telegram_cfg (/etc/bot-office/telegram.json, 9번 봇·업데이트 방 — 그대로).
#   필요 달러(부족 금액) 브리핑 = paths.telegram_need_cfg (/etc/bot-office/telegram_briefing9.json, 새 봇·새 전용 방).
# 설정 파일 모양: {"token": "...", "chat_id": ...}. 토큰·chat_id 는 코드·설정(config.json)·제출물에 적지 않는다.
# parse_mode=HTML. bot_updater.say() 는 본문을 3900자로 '절단'하므로 재사용하지 않고 직접 보낸다(분할 전송).
# 수동 도구 (토큰·chat_id 값은 출력하지 않는다, 방 목록의 chat_id 만 예외):
#   python3 -m briefing.tg_send fingerprint <설정파일>...  토큰 해시 앞 8자리 (9번 토큰과 새 토큰이 다른지 확인)
#   python3 -m briefing.tg_send chat-ids <설정파일>        새 방 chat_id 찾기 (token 만 있으면 됨)
#   python3 -m briefing.tg_send ping <설정파일>            그 설정의 방에 시험 한 줄 보내기
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request

LIMIT = 3800          # say() 의 3900 절단보다 약간 낮게 잡아 태그 여유를 둔다
RETRY_DELAYS = (2, 5, 10)


def load_cfg(path):
    with open(path, "r", encoding="utf-8") as f:
        c = json.load(f)
    token = c.get("token")
    chat_id = c.get("chat_id")
    if not token or chat_id in (None, ""):
        raise ValueError("telegram 설정에 token/chat_id 없음")
    return token, chat_id


def split_message(text, limit=LIMIT):
    """줄 경계로 분할. <pre> 블록이 갈라지면 각 조각에서 닫고 다시 연다."""
    if len(text) <= limit:
        return [text]
    parts, cur, size, in_pre = [], [], 0, False
    for line in text.split("\n"):
        add = len(line) + 1
        if cur and size + add + len("</pre>") + 1 > limit:
            parts.append("\n".join(cur + (["</pre>"] if in_pre else [])))
            cur = ["<pre>"] if in_pre else []
            size = sum(len(x) + 1 for x in cur)
        cur.append(line)
        size += add
        if "<pre>" in line and "</pre>" not in line:
            in_pre = True
        elif "</pre>" in line and "<pre>" not in line:
            in_pre = False
    parts.append("\n".join(cur))
    return parts


def _post(token, chat_id, text, opener=None):
    url = "https://api.telegram.org/bot%s/sendMessage" % token
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    op = opener or urllib.request.urlopen
    with op(req, timeout=20) as r:
        body = json.loads(r.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError("telegram ok=false")
    return True


def send(text, cfg_path, opener=None, sleep=time.sleep):
    """성공 True / 3회 재시도(2·5·10초) 모두 실패 False. 예외는 던지지 않는다."""
    try:
        token, chat_id = load_cfg(cfg_path)
    except Exception:
        return False
    for part in split_message(text):
        ok = False
        for i in range(len(RETRY_DELAYS) + 1):
            try:
                ok = _post(token, chat_id, part, opener)
                break
            except Exception:
                if i < len(RETRY_DELAYS):
                    sleep(RETRY_DELAYS[i])
        if not ok:
            return False
    return True


def same_bot_or_room(cfg_a, cfg_b):
    """두 설정 파일이 같은 봇 토큰이거나 같은 그룹 방이면 이유 문자열, 아니면 None (섞임 방지).
    개인 채팅의 chat_id(양수)는 사용자 번호라 어느 봇이든 같다 → 토큰이 다르면 다른 채팅이므로 막지 않는다.
    양수 숫자가 아닌 chat_id(음수 그룹, @이름)가 같으면 막는다.
    값은 출력하지 않는다. 한쪽이라도 못 읽으면 비교할 수 없으니 None (못 읽는 설정으로는 어차피 못 보낸다)."""
    try:
        ta, ca = load_cfg(cfg_a)
        tb, cb = load_cfg(cfg_b)
    except Exception:
        return None
    if hashlib.sha256(str(ta).encode("utf-8")).digest() == hashlib.sha256(str(tb).encode("utf-8")).digest():
        return "같은 봇 토큰"
    if str(ca) == str(cb) and not str(ca).isdigit():
        return "같은 방(chat_id)"
    return None


def token_fingerprint(cfg_path):
    """토큰 해시 앞 8자리만 (확인용). 못 읽으면 None."""
    try:
        token, _ = load_cfg(cfg_path)
    except Exception:
        return None
    return hashlib.sha256(str(token).encode("utf-8")).hexdigest()[:8]


def chat_ids(cfg_path, opener=None):
    """getUpdates 로 봇이 본 방 목록 [(chat_id, type, title)] — 새 방 chat_id 확보용. 토큰은 반환하지 않는다.
    봇을 방에 초대한 뒤 방에서 아무 메시지나 한 번 보내야 목록에 나온다."""
    with open(cfg_path, "r", encoding="utf-8") as f:
        token = json.load(f).get("token")           # chat_id 를 찾는 중이라 chat_id 는 아직 없어도 된다
    if not token:
        raise ValueError("telegram 설정에 token 없음")
    url = "https://api.telegram.org/bot%s/getUpdates" % token
    op = opener or urllib.request.urlopen
    with op(urllib.request.Request(url), timeout=20) as r:
        body = json.loads(r.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError("telegram ok=false")
    seen, out = set(), []
    for u in body.get("result", []):
        m = u.get("message") or u.get("channel_post") or u.get("my_chat_member") or {}
        c = m.get("chat") or {}
        if c.get("id") is None or c["id"] in seen:
            continue
        seen.add(c["id"])
        out.append((c["id"], c.get("type"), c.get("title") or c.get("username") or ""))
    return out


def _cli(argv):
    if len(argv) >= 3 and argv[1] == "fingerprint":
        for p in argv[2:]:
            print("%s\t%s" % (p, token_fingerprint(p) or "읽기 실패"))
        return 0
    if len(argv) == 3 and argv[1] == "chat-ids":
        try:
            for cid, typ, title in chat_ids(argv[2]):
                print("%s\t%s\t%s" % (cid, typ, title))
        except Exception as e:
            print("실패: %s" % type(e).__name__, file=sys.stderr)
            return 1
        return 0
    if len(argv) == 3 and argv[1] == "ping":
        ok = send("브리핑 연결 시험 (이 메시지는 시험입니다)", argv[2])
        print("전송 성공" if ok else "전송 실패")
        return 0 if ok else 1
    print("사용법: python3 -m briefing.tg_send fingerprint|chat-ids|ping <설정파일>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
