# 2번 토스 스나이퍼

갱신: 2026-10-26. 기존 기록을 분리한 문서이며 새 서버 적용의 증거가 아니다.
필수 작업 원칙은 저장소 루트 START.md를 따른다. 아래에서 이번 작업과 관련된 제목만 읽는다.

### 5.2 2번 토스 SOXS 스나이퍼

- 사용자 재코딩본: `now4happy/4bot`의 `toss_sniper`.
- 사용자 보고: 조건 충족 시 거래 시간 확대를 해결했다. 정확한 최신 거래 세션·주문 가능 시간은 코드 미확인.
- 물타기 기능·통합 이력이 있고 사용자 관심 사항이지만, 정확한 하락률/RSI/차수/금액/최대 횟수는 이 대화에서 확정되지 않았다.
- 업데이트 비서는 SOXS/SOXL 장부의 `sell_order_id`, `last_buy_price`, `target_sell_price`, 조건부 `buy_order_id`와 `entry_session`을 확인한다. 물타기 상태의 `order_id`가 있으면 업데이트를 막는다.
- 이 장부 확인은 배포 보호 규칙이지 중복 매수 방지의 전체 증거가 아니다.
- 24시간 내내 거래가 가능하다거나 손절·시장가/지정가가 확정됐다고 쓰지 않는다.

## 현재 소스와 실행 구분

- 경로 /home/gieokkim/toss_sniper, 서비스 toss_sniper.service. 사용자 확정 이름은 SOXS 스나이퍼지만 마지막 확인 c2bb1c2의 toss_api.REAL_ALLOWED_SYMBOLS는 SOXL 단독이다. 실제 전략 수치를 이름으로 추정하지 않는다.
- main.py가 여러 전략 모듈을 조립하고 주문은 toss_api.TossApiClient._request를 통한다. 현재 전체 전략/물타기 수치는 관련 작업에서 필요한 함수만 확인한다.
- 코드의 기본 .env 및 config.json/secrets.json/toss_config.json flat 인증 설정을 사용하며 키 원문은 출력하지 않는다.
- 신규 주문 중지 수정안: toss_sniper/deployment_gate.py, toss_api.py. 주문 생성/정정에 연결하고 기존 조회/취소는 유지한다. 실제 설치 미확인.
- 원작자 새 버전 알림: `bot_office/sniper_upstream.py` (사무실 v1.0.49, 2026-10-28 사용자 요청으로 **알림 전용**으로 다시 켬). 매일 09:02 KST·'원작 확인' 시 원작(pipios4006-boop/pipiosToss_bot) 최신과 '기준 원작'을 비교해 🔴 중요 알림. 자동 합치기·자동 업로드 없음.
- 기준 원작 = 2번 봇이 바탕으로 삼은 원작 커밋. 처음 값 `2e23df2` (10-24 11:54 KST, v1.0.7 이후 파일과 가장 비슷 — 내용 비교로 판단). 반영 후 알림의 ✅ 반영 완료로 갱신(↩️ 되돌리기 가능), 상태는 /var/lib/bot-updater/state.json `sniper_up`.
- 원작 새 버전 반영 방법: 원작 최신 위에 내 수정(데이장 매매·토스 토큰 공유 HOOK·plugin_updater 4bot 범위 제한)을 다시 붙여 staging 업로드 → 📦 ✅. 원작으로 그냥 덮지 않는다.
- 중지/재개 상세는 06_updater.md. 타 봇과 같은 계좌/같은 종목을 공유하면 API 수량을 봇별로 분리할 수 없다는 제한도 그 문서에 기록했다.
