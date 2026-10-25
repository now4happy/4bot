# 4번 빗썸 스마트적립

갱신: 2026-10-26. 기존 기록을 분리한 문서이며 새 서버 적용의 증거가 아니다.
필수 작업 원칙은 저장소 루트 START.md를 따른다. 아래에서 이번 작업과 관련된 제목만 읽는다.

### 5.4 4번 빗썸 스마트적립

- 상세 매매 조건·물타기·투자금·손절·익절·주문 방식 미확인.
- 업데이트 코드에는 한국시간 18:50~19:25를 “19:00 정기 매수 시간”으로 보호하는 조건이 있었다. 실제 최신 scheduler 확인은 별도 필요.

## 파일·설정·업데이트용 중지

- 기본 경로 /home/gieokkim/bithumb_laoeo_bot, 서비스 bithumb_bot.service. main.py/b_core.py/b_ui.py. 서비스의 현재 ExecStart는 필요한 작업 때 확인한다.
- b_core의 bot_config.json에 power/coins, bot_state.json에 실행·사이클 상태. 실제 투자금/설정 원문을 문서에 복제하거나 추정하지 않는다.
- 신규 주문은 b_core.place_order에서 API /v1/orders로 나간다. 새 deployment_gate가 이 함수를 감싸며 (성공여부, 결과) 반환 형식을 유지한다.
- 미배포 부품2개: bithumb_laoeo_bot/deployment_gate.py, b_core.py. 관리 코인 balance+locked와 대기 주문이 없을 때만 차단 전환한다. 코인 미세잔고도 0으로 반올림하지 않는다.
- 중지 의미·처음 설치·재개는 06_updater.md. 서버 적용/실계좌 차단 확인은 아직 안 했다.
