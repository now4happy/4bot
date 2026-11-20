# briefing/tg_send.py — 9번 봇 토큰·방으로 전송 (새 봇·새 토큰 없음)
# 설정: /etc/bot-office/telegram.json 의 token / chat_id (Q2 답변). parse_mode=HTML.
# bot_updater.say() 는 본문을 3900자로 '절단'하므로 재사용하지 않고, 같은 설정을 읽어 직접 보낸다(분할 전송).
import json
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
