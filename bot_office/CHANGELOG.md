# 5번 사무실 비서 변경 기록

## v1.7.0 · 2026-11-12 21:10 (KST)
- 파일: fanding_fetch_server.py, test_fanding_fetch_server.py
- 내용: 팬딩 서버 수집기: SERVER_SETUP.md 고침 — 유닛 파일(.service/.timer) 내용을 heredoc으로 넣어 서버에서 직접 만들게 (업데이터 허용 목록 밖이라 저장소에 두지 않음)
- 브랜치: fanding-server-collect

## v1.6.9 · 2026-11-12 20:41 (KST)
- 파일: bot_updater.py
- 내용: 업데이터 enable 고침: 재시작 때 실행 중이면 enable도 같이 (사무실 vNEXT)
- 브랜치: updater-enable-fix

## v1.6.8 · 2026-11-12 15:00 (KST)
- 파일: live_board.py
- 내용: office: live_board writes sniper_snapshot (vNEXT)
- 브랜치: staging

## v1.6.7 · 2026-11-12 13:53 (KST)
- 파일: live_board.py
- 내용: live_board: 한국만 열림에도 시트 현금 갱신 + 한투 달러화 43행 포함 (사무실 vNEXT)
- 브랜치: staging

## v1.6.6 · 2026-11-12 13:20 (KST)
- 파일: office_briefing.py
- 내용: 메리츠 4번 need 브리핑 + 자동환전 (office_briefing vNEXT, meritz_dca v1.0.1)
- 브랜치: staging

## v1.6.5 · 2026-11-11 13:21 (KST)
- 파일: bot_updater.py, office_briefing.py
- 내용: Revert "상태 기록: need.json"
- 브랜치: staging

## v1.6.4 · 2026-11-11 10:42 (KST)
- 파일: fanding_trade.py
- 내용: 배수 맞추기 주단위 5일 + 나머지 하루 더 (fanding_trade v1.5.7)
- 브랜치: staging

## v1.6.3 · 2026-11-11 10:15 (KST)
- 파일: fanding_trade.py
- 내용: 자동환전 $10 단위 올림(ceiling) — 부족 남지 않게 (fanding_trade v1.5.6)
- 브랜치: staging

## v1.6.2 · 2026-11-11 05:40 (KST)
- 파일: live_board.py
- 내용: live_board 원장 파일(sniper_tiers.json) 5분마다 live-board 브랜치에 발행
- 브랜치: staging

## v1.6.1 · 2026-11-10 13:22 (KST)
- 파일: live_board.py
- 내용: 키움 수량 변경 live_board vNEXT (NAVER 21→14, TIGER 코리아휴머노이드 237→398, 에코프로비엠 49→67, 이수페타시스 60→82; 11-10 12:15 잔고 캡처 + 자동매매내역 2일치 기준)
- 브랜치: staging

## v1.6.0 · 2026-11-10 11:16 (KST)
- 파일: fanding_vr6.py, meritz_client.py, office_briefing.py
- 내용: VR6 need: 체결된 매수 줄 제외 — reserved_rows + remaining_need_usd (브리핑 남은 필요)
- 브랜치: staging

## v1.5.9 · 2026-11-10 11:12 (KST)
- 파일: live_board.py
- 내용: 시세 직접받기 한국(KRX) 확장 live_board vNEXT (종목명 정정: TIGER 미국S&P500, probe 32/32)
- 브랜치: staging

## v1.5.8 · 2026-11-10 11:05 (KST)
- 파일: live_board.py
- 내용: 시세 직접받기 한국(KRX) 확장 live_board vNEXT (토스 한국 시세 → krx 섹션 + E41 실시간 합계)
- 브랜치: staging

## v1.5.7 · 2026-11-10 10:46 (KST)
- 파일: meritz_client.py
- 내용: 메리츠 원화 조회 deposit 교체 meritz_client vNEXT (사무실 vNEXT)
- 브랜치: staging

## v1.5.6 · 2026-11-10 10:29 (KST)
- 파일: bot_updater.py
- 내용: 업데이트 비서 2번 스나이퍼 버전은 코드 머리말 버전으로 기록 (태그 카운터 대신)
- 브랜치: staging

## v1.5.5 · 2026-11-10 10:19 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 자동환전 원화 조회 중단 수정 fanding_trade vNEXT (사무실 vNEXT)
- 브랜치: staging

## v1.5.4 · 2026-11-10 10:12 (KST)
- 파일: live_board.py
- 내용: 시세 직접받기 서버 부분 (토스 시세 → live_board.json → live-board 고아 브랜치 1분 발행, 신규 vNEXT)
- 브랜치: staging

## v1.5.3 · 2026-11-10 09:58 (KST)
- 파일: sniper_upstream.py
- 내용: 업데이트 비서 원작 자동 알림 끄기 (매일 09:02 자동 확인 기본 OFF, 수동 원작 확인 유지)
- 브랜치: staging

## v1.5.2 · 2026-11-09 16:02 (KST)
- 파일: office_briefing.py
- 내용: 사무실 vNEXT: 토스 준비금 스나이퍼만 계산 — 3번 적립 합산 제외 (office_briefing vNEXT)
- 브랜치: staging

## v1.5.1 · 2026-11-09 13:45 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 배수 맞추기(따라잡기 매수) 추가 fanding_trade vNEXT (사무실 vNEXT)
- 브랜치: staging

## v1.5.0 · 2026-11-09 13:09 (KST)
- 파일: bot_updater.py, office_briefing.py, office_secretary.py
- 내용: 사무실 vNEXT: 비서 브리핑 텔레그램 중단 + need.json 발행 + 브리핑 버튼 제거 (A안 뮤즈 브리핑)
- 브랜치: staging

## v1.4.9 · 2026-11-09 11:53 (KST)
- 파일: office_briefing.py
- 내용: 사무실 vNEXT: 비서 브리핑 필요 금액 표 한투·메리츠·빗썸 계산 및 본문 표만 표시
- 브랜치: staging

## v1.4.8 · 2026-11-09 11:09 (KST)
- 파일: bot_updater.py
- 내용: 사무실 vNEXT: STATUS.md 기록 시 스나이퍼 층별 공개 JSON(sniper_tiers.json) 동시 생성·업로드
- 브랜치: staging

## v1.4.7 · 2026-11-08 05:25 (KST)
- 파일: bot_updater.py
- 내용: 업데이터: NAMES에 meritz_dca.service 추가 (메리츠 적립, 사무실 vNEXT)
- 브랜치: staging

## v1.4.6 · 2026-11-08 03:52 (KST)
- 파일: bot_updater.py
- 내용: meritz settings.example.json 제거 (구버전 업데이터가 .json을 거부해 묶음 적용이 막힘 — 서버 설정은 이미 /etc/meritz-laoer/settings.json으로 설치됨)
- 브랜치: staging

## v1.4.5 · 2026-11-07 13:46 (KST)
- 파일: office_briefing.py, office_secretary.py
- 내용: 브리핑 수동 --manual + 메뉴 사무실 주소 버튼 삭제 (office_briefing.py·office_secretary.py vNEXT)
- 브랜치: staging

## v1.4.4 · 2026-11-07 13:25 (KST)
- 파일: bot_updater.py, office_secretary.py
- 내용: 하단 메뉴 2개로 줄이기 (2번 v2.4.1·tg_ui v2.3.1·사무실 vNEXT)
- 브랜치: staging

## v1.4.3 · 2026-11-07 12:06 (KST)
- 파일: asset_board.py, board.html, office_board.py, test_asset_board.py
- 내용: 사무실 vNEXT: 현금 금액 표기 + 투자 종목 증권사별 색
- 브랜치: staging

## v1.4.2 · 2026-11-06 17:39 (KST)
- 파일: asset_board.py, board.html, office_board.py, test_asset_board.py
- 내용: 자산 현황 하이브리드: 도넛+막대+수익률 (사무실 vNEXT)
- 브랜치: staging

## v1.4.1 · 2026-11-06 17:13 (KST)
- 파일: board.html
- 내용: 자산 현황 도넛 2개 파이 지름 같게 (사무실 vNEXT)
- 브랜치: staging

## v1.4.0 · 2026-11-06 17:00 (KST)
- 파일: kiwoom_holdings.py, price_watch.py
- 내용: 파기 파일 삭제: bot_office/price_watch.py (가격·비용 메뉴 삭제)
- 브랜치: staging

## v1.3.9 · 2026-11-06 16:57 (KST)
- 파일: bot_updater.py, office_briefing.py, office_secretary.py
- 내용: 가격·비용 메뉴 삭제 + 파기 파일 2개 삭제 준비 (사무실 vNEXT)
- 브랜치: staging

## v1.3.8 · 2026-11-06 16:51 (KST)
- 파일: asset_board.py, test_asset_board.py
- 내용: 자산 구성 도넛 1% 미만 숨김 (사무실 vNEXT)
- 브랜치: staging

## v1.3.7 · 2026-11-06 15:30 (KST)
- 파일: asset_board.py, board.html, office_board.py, test_asset_board.py
- 내용: 상황판 자산 현황 도넛 2개 (사무실 vNEXT)
- 브랜치: staging

## v1.3.6 · 2026-11-06 13:33 (KST)
- 파일: kiwoom_holdings.py
- 내용: 키움 보유 종목 서버 가져오기 신규 (사무실 vNEXT)
- 브랜치: staging

## v1.3.5 · 2026-11-06 13:28 (KST)
- 파일: fanding_vr6.py
- 내용: VR6 판독 날짜 기준 수정 fanding_vr6 2.6.1 (사무실 vNEXT)
- 브랜치: staging

## v1.3.4 · 2026-11-06 10:23 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 검산 오탐 + 주문 버튼 사라짐 수정 fanding_trade 1.14.4 (사무실 vNEXT)
- 브랜치: staging

## v1.3.3 · 2026-11-06 10:12 (KST)
- 파일: office_briefing.py, sniper_picture.html, sniper_picture.py
- 내용: 2번 스나이퍼 Case 91 이식 v2.3.0 (복리/단리 모드 + 무제한 시멘트추가 + 지하층 보존, 사무실 vNEXT)
- 브랜치: staging

## v1.3.2 · 2026-11-05 17:23 (KST)
- 파일: office_briefing.py
- 내용: 비서 브리핑 필요 금액 표 한투 USD 줄 추가 (사무실 vNEXT)
- 브랜치: staging

## v1.3.1 · 2026-11-05 15:24 (KST)
- 파일: export_past_sheet.py, fanding_trade.py, past_sheet_telegram.py
- 내용: 팬딩 과거자료 다운 버튼화 + 당일 표 누적 (추출기 1.1.1, fanding_trade 1.14.3, 텔레그램 모듈 1.1.0)
- 브랜치: staging

## v1.3.0 · 2026-11-05 14:50 (KST)
- 파일: export_past_sheet.py, fanding_trade.py, past_sheet_telegram.py
- 내용: 팬딩 past_sheet 자동 추출 + 텔레그램 전달 (추출기 1.1.0, fanding_trade 1.14.2, 텔레그램 모듈 1.0.0)
- 브랜치: staging

## v1.2.9 · 2026-11-05 14:17 (KST)
- 파일: export_past_sheet.py
- 내용: staging에서 백테스트 스크립트만 제외 (업데이터 허용 파일만 남김)
- 브랜치: staging

## v1.2.8 · 2026-11-05 09:58 (KST)
- 파일: sniper_picture.html, sniper_picture.py
- 내용: 사무실 현황판 지하층 시각 표시 (황금 칸·상단 지하 주수, 사무실 vNEXT)
- 브랜치: staging

## v1.2.7 · 2026-11-05 09:32 (KST)
- 파일: office_briefing.py, sniper_picture.html, sniper_picture.py
- 내용: 2번 스나이퍼 v2.2.0 원작 골든포켓 폐기 이식 + 지하층 보관 (사무실 vNEXT)
- 브랜치: staging

## v1.2.6 · 2026-11-04 22:13 (KST)
- 파일: sniper_picture.html, sniper_picture.py
- 내용: 사무실 vNEXT: 스나이퍼룸 층 영역에 골든포켓 줄 표시 (⭐ 80주 · 황금 칸 ×8, 1칸=10주 반올림)
- 브랜치: staging

## v1.2.5 · 2026-11-04 21:40 (KST)
- 파일: sniper_picture.html, sniper_picture.py
- 내용: 사무실 vNEXT: 스나이퍼룸 상단 카드에 골든포켓 주수 표시 (본 51·서브 0·골든 80, 합계 131)
- 브랜치: staging

## v1.2.4 · 2026-11-04 17:00 (KST)
- 파일: fanding_trade.py, fanding_vr6.py
- 내용: 팬딩 자동주문 시간 선택 + 토글 버튼 동작 표시 (fanding_trade 1.14.0, fanding_vr6 2.6.0)
- 브랜치: staging

## v1.2.3 · 2026-11-04 16:25 (KST)
- 파일: fanding_trade.py, fanding_vr6.py
- 내용: 메리츠 환전 순서 변경 + 원화 역자동환전 (fanding_trade 1.13.0, fanding_vr6 2.5.0)
- 브랜치: staging

## v1.2.2 · 2026-11-04 15:43 (KST)
- 파일: fanding_trade.py, fanding_vr6.py
- 내용: 메리츠 환전 직관화 + 부족금 자동환전 (fanding_trade 1.12.0, fanding_vr6 2.4.0)
- 브랜치: staging

## v1.2.1 · 2026-11-04 10:34 (KST)
- 파일: sniper_picture.html, sniper_picture.py
- 내용: 사무실 현황판 Case 89 사이클 표시 (사무실 vNEXT)
- 브랜치: staging

## v1.2.0 · 2026-11-04 09:46 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 가격표 메시지 간결화: fanding_trade 1.11.2 (달러 숫자 먼저·정수 반올림, 참고 줄 삭제)
- 브랜치: staging

## v1.1.9 · 2026-11-04 09:18 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 PC 정상 노트 미전송: fanding_trade 1.11.1 (머리말·VERSION 일치, 기록 파일 미포함 — 받은 작업만으로 staging)
- 브랜치: staging

## v1.1.8 · 2026-11-04 03:30 (KST)
- 파일: office_briefing.py
- 내용: staging에서 업데이터 거부 파일 제거: docs/log 검증 스크립트(.py)는 서버 적용 대상이 아님, office_briefing.py + VERIFY.md만 남김
- 브랜치: staging

## v1.1.7 · 2026-11-03 17:32 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 미국 휴장일 반영: fanding_trade 1.11.0 (작업 기록 포함)
- 브랜치: staging

## v1.1.6 · 2026-11-03 16:25 (KST)
- 파일: sniper_picture.html, sniper_picture.py
- 내용: 사무실 현황판 v2.0.0 서브 그리드·수혈·골든포켓 표시
- 브랜치: staging

## v1.1.5 · 2026-11-03 16:18 (KST)
- 파일: office_briefing.py
- 내용: 사무실 vNEXT 토스 달러 확인 v2.0.0 매매법
- 브랜치: staging

## v1.1.4 · 2026-11-02 11:19 (KST)
- 파일: office_briefing.py
- 내용: 사무실 브리핑 토스 달러 확인 계산식 재작성 (vNEXT)
- 브랜치: staging

## v1.1.3 · 2026-11-01 22:54 (KST)
- 파일: board.html, office_board.py
- 내용: feat: 상황판 정리 — 마인드맵 탭 삭제·탭 순서·신호등 번호순·오늘 할 일 삭제 (사무실 v1.0.61)
- 브랜치: staging

## v1.1.2 · 2026-11-01 21:54 (KST)
- 파일: board.html, server.py, thought_mindmap.html
- 내용: feat: 상황판 마인드맵 탭 추가 (생각의 연결 v1.3, 보기 전용)
- 브랜치: staging

## v1.1.1 · 2026-11-01 18:38 (KST)
- 파일: bot_updater.py
- 내용: feat: watchdog 무소식 경고 대응 — 2번 신호 위치 + hub 권한 + 8번 대리 신호
- 브랜치: staging

## v1.1.0 · 2026-11-01 14:47 (KST)
- 파일: bot_updater.py, fanding_trade.py, office_secretary.py, pc_monitor.py, server.py
- 내용: feat: alert-hub 연동 1차 — 전 봇 하트비트 + 사무실·팬딩 자율 알림
- 브랜치: staging

## v1.0.82 · 2026-11-01 14:33 (KST)
- 파일: bot_updater.py
- 내용: feat: 버전 숫자 최대 9 굴림 + hub 테스트 고침
- 브랜치: staging

## v1.0.81 · 2026-11-01 14:27 (KST)
- 파일: bot_updater.py
- 내용: feat: 업데이터 시작 때 alert-hub 자동 설치 (승인만으로 설치)
- 브랜치: staging

## v1.0.80 · 2026-11-01 10:48 (KST)
- 파일: bot_updater.py
- 내용: feat: 업데이터 alert-hub 폴더 무시 처리 (다른 봇 업데이트 차단 방지)
- 브랜치: staging

## v1.0.79 · 2026-11-01 10:16 (KST)
- 파일: office_board.py
- 내용: feat: 상황판 5번 사무실 비서 → 8번 사무실 비서 표시 변경
- 브랜치: board-8-office

## v1.0.78 · 2026-10-31 20:38 (KST)
- 파일: board.html
- 내용: 텔레그램 매매 그림 표현을 현황판으로, 상황판 맨밑 보기 전용 링크 제거
- 브랜치: staging

## v1.0.77 · 2026-10-31 20:33 (KST)
- 파일: sniper_picture.html
- 내용: 스나이퍼 매매 그림 한 화면 v9: 바 16px, 층 옆 주수, 중복 잔글씨 제거
- 브랜치: staging

## v1.0.76 · 2026-10-31 20:18 (KST)
- 파일: server.py
- 내용: 스나이퍼룸 iframe 허용: 그림 페이지만 같은 주소 프레임 허용
- 브랜치: staging

## v1.0.75 · 2026-10-31 20:15 (KST)
- 파일: sniper_picture.py
- 내용: 스나이퍼 그림 현재가 스냅샷: 스나이퍼 폴더에 60초마다 쓰기 + 사무실 백엔드 확인
- 브랜치: staging

## v1.0.74 · 2026-10-31 20:13 (KST)
- 파일: board.html
- 내용: 상황판 스나이퍼룸 탭 추가: 그림 페이지를 iframe으로 표시
- 브랜치: staging

## v1.0.73 · 2026-10-31 20:08 (KST)
- 파일: sniper_picture.html
- 내용: 스나이퍼 매매 그림 상단 2열 v7: 누적 실현 금액 / 수익률, 칸 흰색
- 브랜치: staging

## v1.0.72 · 2026-10-31 19:47 (KST)
- 파일: sniper_picture.html
- 내용: 스나이퍼 매매 그림 계단식 v4: 바 길이=주수, 주수는 층 표시 밑, 맨 위 보유·손익
- 브랜치: staging

## v1.0.71 · 2026-10-31 17:50 (KST)
- 파일: board.html, server.py, sniper_picture.html, sniper_picture.py
- 내용: 스나이퍼 매매 그림: 텔레그램 메뉴 + 사무실 그림 페이지/API (상단 1개층 밤 잠김 수정 포함)
- 브랜치: staging

## v1.0.70 · 2026-10-31 13:13 (KST)
- 파일: fanding_vr6.py
- 내용: VR6 날짜 대조 강화 v2.3.0: 진행일=표 시작 정확 일치, 기간 10~12일, 2차 날짜 정정 (작업 기록 포함)
- 브랜치: staging

## v1.0.69 · 2026-10-30 11:02 (KST)
- 파일: fanding_fetch_win.py, fanding_trade.py
- 내용: 팬딩 사이트 재시도 중단 + 진단 + 09:00 1회: PC 1.5.4, 서버 1.10.3 (1.10.2 보존 병합)
- 브랜치: staging

## v1.0.68 · 2026-10-30 10:38 (KST)
- 파일: office_briefing.py
- 내용: 비서 브리핑 메리츠 P·VR6 2계좌 조회
- 브랜치: staging

## v1.0.67 · 2026-10-30 10:26 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 가격표 날짜 오독 교차 확인 + 반복 알림 1회: fanding_trade 1.10.2
- 브랜치: staging

## v1.0.66 · 2026-10-29 18:25 (KST)
- 파일: pc_monitor.py
- 내용: PC 연결 감시 기준 10분으로 변경: offline_seconds 180→600, 경고 문구 10분 (작업 기록 포함)
- 브랜치: staging

## v1.0.65 · 2026-10-29 14:30 (KST)
- 파일: fanding_trade.py, fanding_vr6.py
- 내용: 팬딩 VR6 버튼 글자에서 'VR6' 빼기: fanding_trade 1.10.1, fanding_vr6 2.2.1 (작업 기록 포함)
- 브랜치: staging

## v1.0.64 · 2026-10-29 14:17 (KST)
- 파일: bot_updater.py, fanding_trade.py, fanding_vr6.py
- 내용: 팬딩 메뉴 정리: fanding_trade 1.10.0, fanding_vr6 2.2.0, bot_updater 비서 재시작 목록에서 fanding 제외 (작업 기록 포함)
- 브랜치: staging

## v1.0.63 · 2026-10-29 13:34 (KST)
- 파일: fanding_trade.py, fanding_vr6.py
- 내용: VR6 환전·09:00 알림 + P·VR6 매도 수량 맞춤: fanding_trade 1.9.0, fanding_vr6 2.1.0 (작업 기록 포함)
- 브랜치: staging

## v1.0.62 · 2026-10-29 13:06 (KST)
- 파일: fanding_vr6_win.py
- 내용: VR6 수집기 1.1.0: 이미지 20장·글 끝까지 스크롤·run.bat 안내 수정 (작업 기록 개정 포함)
- 브랜치: staging

## v1.0.61 · 2026-10-29 12:48 (KST)
- 파일: fanding_vr6.py, fanding_vr6_win.py, meritz_client.py
- 내용: VR6 예약주문 2단계: fanding_vr6 2.0.0, meritz_client V1.5, fanding_vr6_win 1.0.1
- 브랜치: staging

## v1.0.60 · 2026-10-29 11:03 (KST)
- 파일: fanding_fetch_win.py
- 내용: 팬딩 PC 수집기 1.5.3: 하루 30개·미전송 우선·완료 후 건너뛰기
- 브랜치: staging

## v1.0.59 · 2026-10-29 10:43 (KST)
- 파일: board.html, fanding_trade.py, office_board.py
- 내용: 팬딩 아침 알림 정리 + 상황판 가격표 모음 매일 포함 (사무실 v1.0.59 예정)
- 브랜치: staging

## v1.0.58 · 2026-10-28 13:55 (KST)
- 파일: index.html, market_manual.py, office_reviews.py, office_tasks.py, pixel_office.html, pixel_office.py, server.py
- 내용: 픽셀·운영 삭제: office_tasks.py
- 브랜치: staging

## v1.0.57 · 2026-10-28 13:10 (KST)
- 파일: ai_room.py, apply_deploy.py, deploy_worker.py, draft_change.py, generate_ideas.py, install_v2.py, office_deploy.py, office_dev.py, office_package.py, office_pipeline.py, office_pipeline_api.py, office_secretary.py, office_submit.py, optimization_agent.py, prepare_deploy.py, publish_deploy.py, risk_agent.py, room.html, server.py, test_deploy.py
- 내용: 꺼진 기능 파일 삭제: generate_ideas.py
- 브랜치: staging

## v1.0.56 · 2026-10-28 12:33 (KST)
- 파일: board.html, office_board.py, server.py
- 내용: 사무실 상황판 2차 수정 (staging, 사무실 vNEXT)
- 브랜치: staging

## v1.0.55 · 2026-10-28 12:13 (KST)
- 파일: board.html, bot_updater.py, office_board.py, office_url.py, server.py
- 내용: 사무실 상황판 · 접속 감시 · 파일 권한 자동 정리 (staging, 사무실 vNEXT)
- 브랜치: staging

## v1.0.54 · 2026-10-28 11:12 (KST)
- 파일: bot_updater.py, update_conflicts.py
- 내용: 6. Update 오류 정리: main 앞섬 알림·한글 파일명 인식·충돌 안내 (start.md 파일명 규칙 추가, 로그 영문 파일명)
- 브랜치: fix-sync-20261028

## v1.0.53 · 2026-10-28 10:49 (KST)
- 파일: fanding_trade.py, meritz_client.py
- 내용: docs/log 한글 파일명 삭제 (영문 파일명으로 대체, 내용 동일)
- 브랜치: fanding-fx-button-20261028

## v1.0.52 · 2026-10-28 10:03 (KST)
- 파일: fanding_trade.py, meritz_client.py
- 내용: 팬딩 매수 자금 추정 기준 표시 + 환전 API 초안 (버튼 미연결)
- 브랜치: fanding-est-fx-20261028

## v1.0.51 · 2026-10-28 09:19 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 진단 이상 즉시 알람 (v4)
- 브랜치: fanding-diag-v4

## v1.0.50 · 2026-10-28 08:38 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 알림 시간
- 브랜치: staging

## v1.0.49 · 2026-10-28 07:52 (KST)
- 파일: bot_updater.py, sniper_upstream.py
- 내용: update: main 기준으로 선택한 이전 변경 정리
- 브랜치: staging

## v1.0.48 · 2026-10-28 07:30 (KST)
- 파일: bot_updater.py, office_secretary.py, office_url.py
- 내용: 사무실 주소 관리 · PC 감시 복구
- 브랜치: staging

## v1.0.47 · 2026-10-28 07:04 (KST)
- 파일: bot_updater.py, fanding_trade.py, gbuts_watch.py, office_briefing.py
- 내용: 묶음B
- 브랜치: staging

## v1.0.46 · 2026-10-28 06:33 (KST)
- 파일: bot_updater.py
- 내용: STATUS 자동 기록 · 버전 통일
- 브랜치: staging

## v1.0.45 · 2026-10-28 06:27 (KST)
- 파일: bot_updater.py
- 내용: md문서 관련
- 브랜치: staging

## v1.0.44 · 2026-10-28 06:21 (KST)
- 파일: bot_updater.py
- 내용: 2.2
- 브랜치: staging

## v1.0.43 · 2026-10-28 06:14 (KST)
- 파일: bot_updater.py
- 내용: 비서봇 오류 패치
- 브랜치: staging

## v1.0.42 · 2026-10-27 22:17 (KST)
- 파일: office_briefing.py
- 내용: Add files via upload
- 브랜치: staging

## v1.0.41 · 2026-10-27 22:00 (KST)
- 파일: office_briefing.py, office_secretary.py
- 내용: 메리츠 잔액 표시
- 브랜치: staging

## v1.0.40 · 2026-10-27 17:31 (KST)
- 파일: bot_updater.py, office_briefing.py, toss_token_share.py
- 내용: Add files via upload
- 브랜치: staging

## v1.0.39 · 2026-10-27 17:22 (KST)
- 파일: bot_updater.py
- 내용: 업데이트 시간
- 브랜치: staging

## v1.0.38 · 2026-10-27 16:31 (KST)
- 파일: office_secretary.py, pc_monitor.py, server.py
- 내용: Pc와 스플릿 감시
- 브랜치: staging

## v1.0.37 · 2026-10-27 12:28 (KST)
- 파일: fanding_trade.py
- 내용: 알림 시간 9시로
- 브랜치: staging

## v1.0.36 · 2026-10-27 11:44 (KST)
- 파일: office_briefing.py, office_secretary.py
- 내용: 프리핑 파일 누락 재업
- 브랜치: staging

## v1.0.35 · 2026-10-27 08:17 (KST)
- 파일: fanding_fetch_win.py, fanding_trade.py, server.py
- 내용: 팬딩 패치
- 브랜치: staging

## v1.0.34 · 2026-10-27 07:40 (KST)
- 파일: bot_updater.py, update_conflicts.py
- 내용: 업데이트봇 수정
- 브랜치: staging

## v1.0.31 · 2026-10-26 15:45 (KST)
- 파일: fanding_trade.py, fanding_vr6.py, fanding_vr6_win.py
- 내용: 팬딩 vr6 추가
- 브랜치: staging

## v1.0.30 · 2026-10-26 13:36 (KST)
- 파일: office_briefing.py, office_secretary.py
- 내용: 브리핑 개선
- 브랜치: staging

## v1.0.29 · 2026-10-26 13:07 (KST)
- 파일: office_briefing.py, office_secretary.py
- 내용: 봇 ui 개선
- 브랜치: staging

## v1.0.28 · 2026-10-26 11:25 (KST)
- 파일: fanding_trade.py, office_secretary.py
- 내용: Add files via upload
- 브랜치: staging

## v1.0.27 · 2026-10-26 11:12 (KST)
- 파일: bot_updater.py
- 내용: 봇 버튼
- 브랜치: staging

## v1.0.26 · 2026-10-26 10:47 (KST)
- 파일: pixel_office.html, pixel_office.py, server.py
- 내용: 사무실 구조 변경
- 브랜치: staging

## v1.0.25 · 2026-10-26 10:36 (KST)
- 파일: fanding_fetch_win.py, fanding_trade.py, meritz_client.py
- 내용: 팬딩 달러 표기
- 브랜치: staging

## v1.0.24 · 2026-10-26 09:47 (KST)
- 파일: fanding_fetch_win.py, fanding_trade.py, server.py
- 내용: 팬딩
- 브랜치: staging

## v1.0.23 · 2026-10-26 09:28 (KST)
- 파일: fanding_trade.py, office_briefing.py
- 내용: 누락된 팬딩 봇 처리
- 브랜치: staging

## v1.0.22 · 2026-10-25 22:25 (KST)
- 파일: bot_updater.py, deployment_control.py
- 내용: 업데이트중 거래괸련
- 브랜치: staging

## v1.0.21 · 2026-10-25 20:43 (KST)
- 파일: gbuts_watch.py
- 내용: Update API response handling in gbuts_watch.py
- 브랜치: staging

## v1.0.20 · 2026-10-25 20:24 (KST)
- 파일: gbuts_watch.py, test_gbuts_watch.py
- 내용: Implement Gbuts public product monitoring feature
- 브랜치: staging

## v1.0.19 · 2026-10-25 14:47 (KST)
- 파일: office_briefing.py
- 내용: 주말 브리핑 중지·휴장 알림 코드
- 브랜치: staging

## v1.0.18 · 2026-10-25 11:44 (KST)
- 파일: gemini_usage.py, office_secretary.py, price_watch.py
- 내용: 가격비교 등록
- 브랜치: staging

## v1.0.17 · 2026-10-25 11:02 (KST)
- 파일: office_briefing.py, office_secretary.py, price_watch.py
- 내용: 가격 알림
- 브랜치: staging

## v1.0.16 · 2026-10-25 10:19 (KST)
- 파일: office_briefing.py, office_secretary.py
- 내용: 잔액 조회
- 브랜치: staging

## v1.0.15 · 2026-10-25 10:08 (KST)
- 파일: fanding_trade.py, gemini_usage.py, office_briefing.py, office_secretary.py
- 내용: 팬딩 이미지 수정 1차25일
- 브랜치: staging

## v1.0.14 · 2026-10-24 13:43 (KST)
- 파일: sniper_keep_addbuy.py, sniper_upstream.py
- 내용: Delete bot_office/sniper_keep_addbuy.py
- 브랜치: staging

## v1.0.13 · 2026-10-24 13:37 (KST)
- 파일: bot_updater.py
- 내용: 주말 예외 봇 수정
- 브랜치: updater-weekend-fix

## v1.0.12 · 2026-10-23 22:08 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 1.6.2: 월요일에 금요일 가격표 받기 · 재예약 보완
- 브랜치: staging

## v1.0.11 · 2026-10-23 19:34 (KST)
- 파일: fanding_trade.py, meritz_client.py
- 내용: 팬딩 1.6.1: 앱 취소 예약 건너뛰기 · 재예약강제
- 브랜치: staging

## v1.0.10 · 2026-10-23 19:19 (KST)
- 파일: fanding_trade.py, meritz_client.py
- 내용: 팬딩 1.6.0: 장마감 30분 전 발주 · 재예약
- 브랜치: staging

## v1.0.9 · 2026-10-23 19:12 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 1.5.2: DeepSeek 우선 · 형식 재요청
- 브랜치: staging

## v1.0.8 · 2026-10-23 19:00 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 1.5.1: 판독 형식 오류 수정
- 브랜치: staging

## v1.0.7 · 2026-10-23 18:50 (KST)
- 파일: fanding_trade.py
- 내용: 팬딩 1.5.0 가격표 판별, 이미지 자동 삭제
- 브랜치: staging

## v1.0.6 · 2026-10-23 18:32 (KST)
- 파일: fanding_trade.py
- 내용: 딥시크 분석 추가
- 브랜치: staging

## v1.0.5 · 2026-10-23 18:18 (KST)
- 파일: fanding_fetch_win.py, fanding_trade.py
- 내용: 팬딩 1.3.0: 전용 봇 · Gemini 재시도 · 과거 가격표 수집
- 브랜치: staging

## v1.0.4 · 2026-10-23 17:55 (KST)
- 파일: fanding_fetch_win.py
- 내용: 팬딩 윈도우 1.2.0: 시리즈의 가장 최근 글 가져오기
- 브랜치: staging

## v1.0.3 · 2026-10-23 17:44 (KST)
- 파일: fanding_fetch_win.py, fanding_trade.py
- 내용: 팬딩 1.1.0: 이미지 여러 장 중 가격표 자동 선택
- 브랜치: staging

## v1.0.2 · 2026-10-23 16:44 (KST)
- 파일: bot_updater.py, sniper_upstream.py
- 내용: 2번 스나이퍼 v1.0.5 + 원작 자동 합치기
- 브랜치: staging

## v1.1.1 · 2026-10-23 (KST)
- 파일: fanding_trade.py (FANDING_TRADE 1.0.1)
- 내용: 윈도우 PC 알림을 상시 프로그램이 전송하도록 변경(웹서버 계정 권한 문제) · 설정 저장 시 권한 유지
- 브랜치: staging

## v1.1.0 · 2026-10-23 (KST)
- 파일: fanding_trade.py(신규), meritz_client.py(신규), office_secretary.py(V2), server.py, ../fanding_windows/(신규)
- 내용: 팬딩 가격표 → Gemini 2회 판독·안전점검 → 비서 봇 [✅ 주문] → 메리츠 Limit VWAP 예약주문 · 마감 30분 전 알림 · 10분 전 자동주문(점검 통과 시) · /배수 /자동 /가격표
- 브랜치: staging

## v1.0.1 · 2026-10-22 14:26 (KST)
- 파일: ai_room.py, room.html, server.py
- 내용: office: AI 협업방 room-1.0.0 · 방(프로젝트)별 채팅 · 직접(API)/간접(아이디) AI 입장 · /room 연결 [ai_room.py 외 2개]
- 브랜치: staging

## v1.0.0 · 처음 등록
- 서버 /opt/bot-office 의 프로그램 파일을 GitHub에 등록 (이후 업데이트는 텔레그램 업데이트 비서로)

