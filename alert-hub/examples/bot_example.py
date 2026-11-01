"""매매 봇에 alert_hub 를 붙이는 예시. 이 파일을 그대로 쓰는 게 아니라 '모양'을 참고하세요.

핵심 3가지
  1) import 는 try/except 로 감싼다  -> 허브에 문제가 생겨도 봇은 그대로 돈다
  2) 메인 루프에서 heartbeat() 를 부른다 -> 봇이 멈추면 watchdog 이 알려준다
  3) 기존 텔레그램 전송 자리에 notify(봇이름, 등급, 메시지) 를 쓴다
"""
import logging
import time

try:
    from alert_hub import HubLogHandler, heartbeat, notify
except Exception:  # alert_hub 가 설치 안 됐거나 문제가 있어도 매매는 계속한다
    def notify(*args, **kwargs):
        return False

    def heartbeat(*args, **kwargs):
        return False

    HubLogHandler = None

BOT_NAME = "매매봇1"  # .env 의 HUB_BOT_NAMES 에 적은 이름과 글자 하나까지 똑같이!

# (선택) 이미 logging 을 쓰는 봇이면 이 한 줄로 ERROR 는 긴급, WARNING 은 경고로 자동 연결
if HubLogHandler:
    logging.getLogger().addHandler(HubLogHandler(BOT_NAME))


def place_order():
    """기존 주문 코드 자리 (예시)"""
    return {"ok": True, "symbol": "BTC", "side": "buy"}


def main():
    notify(BOT_NAME, "info", "봇 시작")
    while True:
        heartbeat(BOT_NAME)  # 자주 불러도 30초에 한 번만 기록됨
        try:
            result = place_order()
            if result["ok"]:
                notify(BOT_NAME, "info", f"{result['symbol']} {result['side']} 체결")  # 모아뒀다 브리핑
            else:
                notify(BOT_NAME, "critical", "주문 실패!")  # 즉시 텔레그램
        except Exception as e:
            notify(BOT_NAME, "critical", f"예외 발생: {type(e).__name__}: {e}")
        time.sleep(60)


if __name__ == "__main__":
    main()
