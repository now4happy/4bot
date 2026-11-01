# alert-hub — 봇 알림 허브

매매봇 5개 + 업데이트봇이 각자 텔레그램으로 떠들던 것을 **한곳(허브)** 으로 모읍니다.

- 🔴 **긴급** → 즉시 텔레그램으로 알림
- 🟡 **경고** / 🟢 **일반** → 조용히 기록해 두었다가 **하루 한 번 브리핑**
- 봇이 **멈췄을 때**도 알려줍니다 (조용하다고 안전한 게 아니니까요)

## 왕초보용 비유

> 직원 6명이 사장님께 각자 전화하던 방식을 바꿉니다.
> 이제 직원들은 **비서실(허브)** 에만 보고합니다.
> 비서실은 **급한 건 바로 전화**, 나머지는 **쌓아뒀다가 퇴근 전에 한 번에 보고**합니다.
> 그리고 비서실은 "○○ 직원이 3시간째 연락이 없어요!" 도 챙겨줍니다.

```
매매봇1~5, 업데이트봇
      │  notify("봇이름", "등급", "내용")      heartbeat("봇이름")
      ▼
 ┌─────────── 허브 (data/hub.db) ───────────┐
 │ 🔴 긴급 ─────────► 즉시 텔레그램 (비서봇)  │
 │ 🟡🟢 경고/일반 ──► 기록만                   │
 └──────────────────────────────────────────┘
      ▲                         ▲
  watchdog (10분마다)       briefing (하루 1번)
  무소식 봇 찾기             건수 요약 + (선택) AI 요약
```

## 폴더 구성

| 파일 | 역할 |
|---|---|
| `alert_hub/notify.py` | 봇들이 부르는 `notify()`, `heartbeat()` |
| `alert_hub/briefing.py` | 하루 브리핑 만들기 (+ AI 요약) |
| `alert_hub/watchdog.py` | 멈춘 봇 감시, 밀린 알림 재전송 |
| `alert_hub/cli.py` | `python -m alert_hub ...` 명령들 |
| `.env.example` | 설정 견본 (복사해서 `.env` 로) |
| `crontab.example` | 자동 실행 등록 예시 |
| `examples/bot_example.py` | 봇에 붙이는 모양 예시 |
| `tests/` | 자체 점검 테스트 |

별도 설치 패키지는 **필요 없습니다** (파이썬 기본 기능만 사용, 파이썬 3.8 이상).

## 설치 (서버에서)

```bash
cd alert-hub
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
nano .env        # 아래 "설정하기" 참고
```

> `pip install` 이 안 되면: 봇 실행 환경에 `export PYTHONPATH=/home/USER/alert-hub` 를 넣어도 `import alert_hub` 가 됩니다.

### 설정하기 (`.env`)

반드시 채울 것 3가지:

1. `TELEGRAM_BOT_TOKEN` — **지금 쓰는 비서봇의 토큰** 을 그대로 쓰면 됩니다. 허브는 *보내기만* 하므로 기존 비서봇 동작과 충돌하지 않습니다.
2. `TELEGRAM_CHAT_ID` — 비서봇이 지금 브리핑을 보내는 **내 채팅 ID**, 그대로.
3. `HUB_BOT_NAMES` — 봇 이름들. **봇 코드의 `notify("이름", ...)` 와 글자 하나까지 같아야** 합니다.

그다음 확인:

```bash
.venv/bin/python -m alert_hub test      # 텔레그램에 ✅ 메시지가 오면 성공
```

## 봇 코드에 붙이기

봇 하나당 **import 3줄 + 호출 몇 줄** 이면 끝입니다. (`examples/bot_example.py` 참고)

```python
try:
    from alert_hub import notify, heartbeat
except Exception:                      # 허브에 문제가 있어도 매매는 계속!
    def notify(*a, **k): return False
    def heartbeat(*a, **k): return False

BOT = "매매봇1"

heartbeat(BOT)                                  # 메인 루프 안에서 (자주 불러도 30초에 한 번만 기록)
notify(BOT, "info", "BTC 매수 체결")             # 모아뒀다 브리핑
notify(BOT, "critical", "주문 실패: 잔고 부족")   # 즉시 텔레그램
```

봇이 서로 **다른 파이썬 환경(venv)** 을 쓰면, 각 환경에서 한 번씩 `pip install -e /경로/alert-hub` 를 실행하세요.

### 등급 기준 (추천)

| 등급 | 이럴 때 | 동작 |
|---|---|---|
| 🔴 `critical` | 주문 실패, 에러/예외, 손절 발동, 잔고 부족, API 키/인증 오류, 봇 비정상 종료 | 즉시 전송 |
| 🟡 `warning` | 재시도 후 성공, 슬리피지 큼, 잔고 적어짐, 평소보다 느림 | 브리핑에서 강조 |
| 🟢 `info` | 정상 체결, 상태 보고, 업데이트 완료, 시작/종료 | 브리핑에서 요약 |

> 등급을 잘못 적으면(예: `"critcal"`) **놓치지 않도록 긴급으로 처리**합니다.

## 자동 실행 등록

`crontab.example` 를 보고 `crontab -e` 에 2줄을 붙여 넣으세요.
**서버 시간대가 UTC 일 수 있으니** 파일 안의 설명대로 시간을 맞춰야 합니다.

## 확인 명령 모음

```bash
.venv/bin/python -m alert_hub status                    # 봇별 마지막 하트비트, 24시간 건수
.venv/bin/python -m alert_hub briefing --no-send        # 브리핑 미리보기 (전송 안 함)
.venv/bin/python -m alert_hub briefing --no-send --hours 6   # 최근 6시간만 보기
.venv/bin/python -m alert_hub notify 매매봇1 critical "테스트"  # 수동 알림
.venv/bin/python -m unittest discover -s tests          # 자체 점검 (마지막 줄이 OK 면 정상)
```

## 안전장치 (알아두면 좋은 것)

- **봇을 절대 멈추지 않습니다.** `notify`/`heartbeat` 는 내부에서 에러가 나도 예외를 던지지 않고 그냥 `False` 를 돌려줍니다.
- **매매 루프가 느려지지 않습니다.** 긴급 전송은 백그라운드에서 합니다.
- **알림 폭탄 방지.** 같은 긴급 알림은 10분간 한 번만, 봇 하나가 10분에 5건을 넘기면 "폭주" 안내 1건 후 브리핑으로 모읍니다.
- **텔레그램이 잠깐 죽어도 안 잃어버립니다.** 못 보낸 긴급 알림은 10분마다 watchdog 이 다시 보냅니다.
- **브리핑 숫자는 AI가 아니라 코드가 계산**합니다. AI 요약은 그 아래 덧붙는 보너스이고, 실패해도 브리핑은 나갑니다.
- **AI 요약 비용:** `ANTHROPIC_API_KEY` 를 넣을 때만 켜지고, 하루 1번 호출이라 소액입니다. 더 아끼려면 `HUB_AI_MODEL=claude-haiku-5-5`.

## 기존 비서봇에 끼워 넣고 싶다면 (선택)

비서봇이 이미 자기 브리핑을 만들고 있다면, 이 한 줄로 허브 내용만 가져다 붙일 수 있습니다.

```python
from alert_hub.briefing import get_briefing_text
text = get_briefing_text(use_ai=False)   # 문자열만 돌려줌 (전송/기록 갱신 없음)
```

## 문제 해결

| 증상 | 확인 |
|---|---|
| `test` 에서 "전송 실패" | 토큰/채팅ID 오타, 서버가 인터넷에 연결돼 있는지, 비서봇과 대화를 시작(`/start`)했는지 |
| 봇이 계속 "무소식" 으로 뜸 | 봇 코드에 `heartbeat()` 가 있는지, `HUB_BOT_NAMES` 이름이 코드와 똑같은지 |
| 브리핑 시각이 이상함 | `timedatectl` 로 서버 시간대 확인 → `crontab.example` 설명대로 조정 |
| 브리핑이 안 옴 | `data/briefing.log` 확인 |
| `.env` 값이 안 먹음 | 값 뒤에 `# 주석`을 붙이지 않았는지 (주석은 줄 맨 앞에만) |
