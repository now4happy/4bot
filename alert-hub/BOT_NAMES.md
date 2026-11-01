# 봇 이름 정리 — Muse가 찾기 쉽게 (2026-11-01 기준)

기준: 4bot main 1e661fb, 상황판 2026-11-01 09:37 KST, 코드 bot_office/office_board.py 29-32행, bot_office/bot_updater.py 39-48행.
이름은 상황판 그대로 쓴다. 특히 7번은 괄호를 빼고 "7번 비서"만 쓴다.

| 상황판 이름 (notify()에 쓸 이름) | 서비스 | 저장소 폴더 / 주 파일 |
|---|---|---|
| 1번 한투 라오어 | han4384tubot.service | hantu_laoer/ |
| 2번 토스 스나이퍼 | toss_sniper.service | toss_sniper/ |
| 3번 토스 적립 | toss_dca.service | toss_dca_bot/ |
| 4번 빗썸 적립 | bithumb_bot.service | bithumb_laoeo_bot/ |
| 8번 사무실 비서 | bot-office.service | bot_office/server.py (웹 상황판) |
| 5번 팬딩 가격표 | bot-office-fanding.service | bot_office/fanding_trade.py, fanding_vr6.py |
| 6번 업데이트 비서 | bot-updater.service | bot_office/bot_updater.py |
| 7번 비서 | bot-office-secretary.service | bot_office/office_secretary.py, office_briefing.py, pc_monitor.py |

## 최종 알림 설계 — 7번 비서 한 곳에서만

- alert-hub의 최종 텔레그램 전송은 7번 비서 한 곳에서만 한다. .env의 토큰·채팅ID는 7번 비서 것으로 채운다.
- 다른 봇들은 notify()/heartbeat()로 허브 DB에만 기록하고, 허브 최종 알림을 직접 보내지 않는다. 그래서 허브 발신자가 여러 개가 돼서 생기는 중복·충돌 오류가 없다.
- 기존 봇 텔레그램 코드는 1~2주 병행 기간에는 그대로 둔다. 그 병행은 허브 발신자가 여러 개라는 뜻이 아니라, 옛날 방식과 허브 방식이 잠시 같이 가는 것이다. 정리는 사용자가 "정리해줘"라고 할 때만 한다.

## 8번 vs 7번 — 같은 거 아니다 (코드 확인 결과)

| 구분 | 8번 사무실 비서 | 5번 팬딩 가격표 | 7번 비서 |
|---|---|---|---|
| 서비스 | bot-office.service | bot-office-fanding.service | bot-office-secretary.service |
| 주 파일 | bot_office/server.py, board.html | bot_office/fanding_trade.py | bot_office/office_secretary.py |
| 하는 일 | 웹 상황판 서버 | 팬딩 가격표 판독·주문 버튼 | 브리핑·PC감시·사무실 주소, 텔레그램 대화 |
| 재시작 | bot-office만 | bot-office-fanding만 | bot-office-secretary만 |

같은 점: 저장소 폴더는 셋 다 bot_office/이고, 상황판에서 "사무실" 그룹으로 같이 보인다. 기본 텔레그램 설정도 /etc/bot-office/telegram.json을 같이 쓰는 경우가 많다.
다른 점: 서비스·주 파일·재시작 단위가 완전히 다르다. 특히 팬딩은 2026-10-26 V4에서 비서에서 분리됐고, 업데이터도 "팬딩 파일이 바뀌어도 비서를 다시 시작하지 않는다"고 적어 둔다. 팬딩 전용 텔레그램 설정(/etc/bot-office/telegram_fanding.json)이 있으면 팬딩은 그 봇을 쓴다.
결론: 8번·5번 팬딩·7번 비서는 같은 봇이 아니므로, 허브 이름도 따로 쓴다. (업데이터 알림 이름은 5번 그대로, 허브 이름은 상황판 8번을 따른다.)

## alert-hub 범위

- 범위: 자율 알림만. 버튼·명령 답장은 허브에 넣지 않는다.
- 등급: critical=주문실패/예외/손절/잔고부족/인증오류, warning=재시도성공/슬리피지/잔고적음, info=정상체결/상태/시작종료
- 저장 위치: 별도 alert-hub 저장소가 아니라, 4bot 저장소 안 alert-hub/ 폴더에 저장한다.
- 주의: 업데이터 분류상, alert-hub/ 하위 폴더의 .py 파일은 기존 봇 대상 폴더가 아니라서 6. Update 적용 대상으로 분류되지 않는다. 그래서 4bot에 저장하는 것은 코드 보관용이고, 서버 설치는 6. Update가 아니라 서버에서 직접 가져오는 방식으로 해야 한다. 이 부분은 서버 설치 때 다시 확인한다.
