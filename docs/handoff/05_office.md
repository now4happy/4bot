## 11. 비서 하단 메뉴 개편·브리핑 구분선 — 파일 작성·가짜 검사 완료, 서버 적용 미확인, 스나이퍼 달러 재계산 미완료 (2026-10-26)
- (10절 대체) `office_secretary.py`: `/start` 하단 메인 버튼 4개 — 📊 조회 · 💲 가격·비용 · ✍️ 수정 요청 · ❓ 도움말. 하위 메뉴도 채팅창 맨 아래 키보드로 바뀐다: 📊 조회(🗞 브리핑·💰 잔액·📋 현황), 💲 가격·비용(🔎 가격 목록·🔄 확인·📊 비교·➕ 등록·🔀 웹·앱 비교 등록, 🤖 Gemini 사용량·💵 잔액 입력·💲 단가 입력), ✍️ 수정 요청(🔧 1~4번 봇 선택·🤔 내용으로 찾기). 모든 하위 메뉴에 🏠 메인 메뉴. 입력 대기 중 다른 메뉴 버튼을 누르면 취소.
- 팬딩 제거: 📋 팬딩 버튼과 /가격표·/배수·/자동 글자 명령은 비서에서 삭제(5번 팬딩 봇에서 사용). 이미 보낸 옛 `fd:`/`fm:` 버튼을 위한 콜백 처리 코드는 남겨 둠. 상품별 ⏸중지/▶재개, 결재 승인·반려, 수정 요청 확인은 메시지에 딸린 선택이라 인라인 유지.
- `office_briefing.py`: 섹션 사이 빈 줄을 ━━━ 구분선으로 변경, 잔액·달러·빗썸·서버·사무실 줄에 이모티콘 추가, 빗썸을 별도 항목(🪙)으로 분리. 계산/주문/조회 로직은 건드리지 않음.
- 미완료: 2번 스나이퍼 필요 달러는 아직 옛 장부 AssassinLedger_SOXS.json의 budget×max_buy_count(기본 100×5) 계산. 02_sniper.md에 새 매매방식 수치가 없어 재계산하지 않았다. 새 전략/장부 파일 확인 후 수정.
- 검사: 가짜 텔레그램으로 메인→하위→입력대기→취소, 수정요청 접수, 옛 팬딩 명령 제거, 옛 fd: 콜백 응답 확인. 가짜 섹션으로 구분선 렌더링·청크 확인. 실제 텔레그램·서버·실계좌 조회는 실행하지 않음.
- 적용: Python 2개를 staging bot_office/에 업로드 → 6. Update 승인. 비서는 상시 서비스라 새 코드 로드(재시작) 확인 필요, 이후 7번 채팅에 /start 1회. 브리핑은 다음 실행 때 반영.

### 11-2. 2차 수정 (2026-10-26 오후) — 파일 작성·가짜 API 검사 완료, 서버 적용 미확인
- 메뉴: 📊 조회 = 🗞 브리핑·📋 현황·🏦 한국투자·🔷 토스·🏛 메리츠·🧾 전체 잔액(계좌별, 봇별 아님). `office_briefing.py --balances kis|toss|meritz|bithumb|all`. 메리츠는 조회 연결 대기(meritz_client.py 확인 필요, 추측 호출 안 함). 글자 명령 /잔액은 전체.
- 브리핑: 🏢 사무실 섹션·📝 오늘 할 일·읽기 전용 문구 제거. 시장분석실·Gemini 기록은 '마지막 정기 전송 때 보여 준 값'(`briefing-calendar/seen.json`)과 같으면 '변동 없음' 한 줄, 다르면 내용 표시. 수동 미리보기는 저장하지 않음, 정기 전송 성공 시에만 저장. Gemini는 report() 문자열 해시 비교라 문구에 날짜/시각이 들어 있으면 매번 '변동'으로 보일 수 있음(gemini_usage.py 미확인).
- 한국장: 정규장 '예정' 고정 문구 → 평일 개장일이면 시각별 시작 예정(09:00 전)/진행 중(09:00~15:30)/마감. 달력(KIS 휴장일 조회)+시계 기준이며 실시간 체결 상태 확인이 아님.
- 토스 401: 확정 원인 미확인. 화면은 계좌조회 성공 뒤 holdings에서 401 → 토큰 자체보다 토큰 만료·교체(다른 봇의 동시 토큰 발급 등) 가능성만 있음(미확정). 401이면 새 토큰으로 1회 재시도, 오류에 API 코드 앞 60자 표시(비밀값 제외). 적용 후에도 401이면 toss_api.py의 토큰 발급·캐시 방식 확인 필요.
- 스나이퍼 필요 달러(인피니트 스노우볼 v6.0 백서, issue #358 기준 SOXL 순수 롱): 코어자산=max(기준시드, 가용현금+투입원가−예비수혈금), 1회분=코어자산×8%, 예비수혈 최대 +6회분. '1회분만'=min(1회분, 가용현금), '장부 전액까지'=가용현금(추매는 10분 게이트·신저가 조건이라 하루 횟수 상한 없음). 가용현금<1회분의 30%면 시드고갈 표시. 원장은 toss_sniper의 *Ledger*.json 중 free_cash_usd/initial_seed_usd 있는 최신 파일을 자동 탐색 — 실제 파일명·항목 미검증, 없으면 '계산 보류'.

## 12. 상황판 첫 화면 · 사무실 접속 감시 · 파일 권한 자동 정리 (2026-10-28, 사무실 v1.0.55 예정 — 승인 순서에 따라 번호는 6. Update 알림 기준) — 파일 작성·가짜 환경 검사 완료, 서버 적용 미확인
- 첫 화면 `/` = 상황판 `board.html` (보기 전용). 방: 상황판(봇 신호등·오늘 할 일) / 매매방(1~4번 버전·켜진 시각·마지막 적용) / 팬딩방(가격표·하남 컴) / 서버실(디스크·메모리·접속 감시·사무실 서비스) / 기록실(대기 업로드·최근 적용) / 미팅룸·옛 화면 링크. 데이터 `/api/board` → `office_board.py`. 금액·잔고·수량·주소 원문은 넣지 않음.
- 옛 화면은 그대로: 픽셀 사무실 `/pixel-office`, 운영 화면 `/operations`. 기존 API·POST 기능은 바꾸지 않음(웹 결재는 원래 기록만 하고 실행하지 않음).
- 버전·최근 적용은 업데이트 비서가 STATUS.md 를 쓸 때 남기는 복사본 `/var/lib/bot-office/status.md`(0644)에서 읽음. 웹서버 계정은 journal 을 못 읽어 '마지막으로 일한 시각' 대신 '켜진 시각'을 보여 줌(한계).
- `office_url.py`: 터널 주소를 cloudflared 내부 창구(127.0.0.1:20241~20245 `/quicktunnel`)에 먼저 묻고 journal 은 보조. 5분마다 내부 `127.0.0.1:8765/healthz` + 바깥 `<주소>/login` 확인 → 2번 연속 실패면 7번 비서로 원인별 할 일 1번, 복구 때 1번. 결과 `/var/lib/bot-office/office_health.json`, 상태가 바뀔 때만 한 줄 JSON 기록(start.md 2절). `/주소` 에 마지막 접속 확인 표시.
- `bot_updater.py`: 사무실 파일 복사 때 주인은 그대로, 그룹·읽기 권한은 server.py 와 같게(그룹 쓰기는 주지 않음). 적용 때마다 /opt/bot-office 의 .py·.html·.css·.js 를 훑어 읽기 권한 빠진 파일을 고치고 완료 알림에 표시. 원인: pixel_office.html 관리자 전용 권한 → 로그인 뒤 첫 화면 끊김(2026-10-28).

## 13. 상황판 2차 수정 (2026-10-28, 사무실 v1.0.56 예정) — 파일 작성·가짜 환경 검사 완료, 서버 적용 미확인
- 탭: 상황판 · 팬딩룸 · 서버실 · 기록실 (매매방·미팅룸 탭 삭제, 미팅룸은 상황판 서비스 목록에서도 뺌. `/room`·`/pixel-office`·`/operations` 주소 자체는 그대로).
- 봇 신호등: 번호 대신 이름 + 켜진 시각 + 버전 (1~7번, 터널은 서버실에만).
- 팬딩룸: 모은 과거 가격표 수(`state.json` 의 past_count), 기록된 날짜 수·최근 날짜(`history.jsonl` 의 past_sheet 줄), 저장 폴더 `/var/lib/bot-office/fanding` · 파일 `history.jsonl`. 이미지는 판독 뒤 지우고 판독 결과만 남음.
- 서버실 '서버 정리 실행' 버튼: POST `/api/server-care`(로그인·같은 주소·`X-Bot-Office: care`, 10분 1번) → 요청 파일 `/var/lib/bot-office/care/request` 만 씀 → 서버의 `bot-server-care-request.path`(관리자 설치 1회)가 보고 기존 `bot-server-care.service`(매일 08:55 자동 정리와 같은 작업) 실행. 웹서버에 관리자 권한을 주지 않음.
- 디스크 80%·메모리 85%·스왑 50% 이상이거나 최근 정리 실패면 정리 카드 강조 + 오늘 할 일에 표시. 요청은 한 줄 JSON(user_event server_care_requested) 기록.

## 14. 비서 메뉴 정리 · 꺼진 기능 삭제 · 정리 버튼 오류 (2026-10-28, 사무실 v1.0.57 예정) — 파일 작성·가짜 환경 검사 완료, 서버 적용 미확인
- 7번 비서 하단 메뉴: 📊 조회 · 💲 가격·비용 · 🏢 사무실 · ❓ 도움말. 🏢 사무실 = 지금 주소(/etc/bot-office/office_url)를 여는 URL 버튼(/사무실).
- 📊 조회: 🗞 브리핑 · 💰 잔액(→ 다음 단계 인라인 버튼으로 한국투자·토스·메리츠·빗썸·전체, `bl:` 콜백) · 🖥 PC 상태 · 🔗 사무실 주소. 📋 현황 삭제.
- ✍️ 수정 요청·자유 문장 접수·결재(ap/apy/rj/df) 버튼 삭제. 예전 메시지의 그 버튼은 '기능 없어짐' 응답 후 버튼 제거. 코드 수정은 GitHub staging → 6. Update 만.
- 삭제한 파일(꺼져 있거나 지운 결재·수정 요청에만 쓰이던 것): ai_room.py, room.html, office_pipeline.py, office_pipeline_api.py, office_package.py, office_submit.py, draft_change.py, prepare_deploy.py, publish_deploy.py, install_v2.py, office_dev.py, deploy_worker.py, apply_deploy.py, test_deploy.py, office_deploy.py, risk_agent.py, optimization_agent.py, generate_ideas.py. server.py 의 /room·/api/deployments·/api/dev-requests·/api/pipeline 도 삭제.
- 서버에서 끈 것(유닛 파일은 /var/backups/bot-office-cleanup-<시각>/ 로 이동): ai-room(.service·-reload.path·-reload.service), bot-office-deploy(.timer·.service), bot-office-pipeline(.timer·.service). 자료 폴더(/var/lib/ai-room 등)는 지우지 않음.
- 남긴 것(켜져 있음): 픽셀 사무실(/pixel-office · pixel_office·office_tasks), 운영 화면(/operations · index.html·office_reviews·market_manual·collect_inventory + bot-office-inventory.timer), 브리핑 타이머, 서버 정리 타이머, backup_office.py(서버에만 있음, 용도 미확인).
- 정리 버튼 오류 원인: bot-office.service 가 ProtectSystem=strict + ReadWritePaths(fanding, market-manual)라 /var/lib/bot-office/care 에 쓸 수 없었음(OSError) → drop-in `bot-office.service.d/care.conf` 로 ReadWritePaths 추가.

## 15. 픽셀 사무실·운영 화면 삭제 · 수집기 유지 (2026-10-28, 사무실 v1.0.58 예정) — 파일 작성·diff·문법 검사 완료, 서버 적용 미확인
- 삭제 주소: /pixel-office, /operations, /api/pixel-office, /api/market-manual, /api/reviews, /api/office-export, /api/office-tasks (GET·POST 모두). 상황판 /, /board, /api/board, /api/server-care, /api/status, /api/idea-report는 그대로.
- 삭제 파일 6개: pixel_office.py, pixel_office.html, index.html, market_manual.py, office_reviews.py, office_tasks.py. 삭제 뒤 남은 파일 중 지운 모듈을 import하는 곳 없음(board.html은 /api/board·/api/server-care만 씀).
- 유지: collect_inventory.py와 bot-office-inventory 타이머. /api/status의 inventory.json 갱신이 계속됨.
- 자료: /var/lib/bot-office/pixel-office와 /var/lib/bot-office/market-manual(점수·결재·업무 기록)은 현용 위치에서 백업 폴더로 이동, 나중에 백업 폴더 삭제 시 완전 삭제. 픽셀 자료 삭제와 점수·결재 기록 삭제는 사용자 승인, 수집기 유지는 사용자 지시.
- 적용: server.py + 이 문서(15절) + 로그를 staging에 올리고, SSH로 자료 이동 뒤 연결로 6개 파일 삭제, 6. Update 마지막 알림 승인. SSH git push는 https 인증 프롬프트에서 멈춘 전례가 있어 이번에는 파일 삭제를 연결로 함.
