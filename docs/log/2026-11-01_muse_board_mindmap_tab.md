# 2026-11-01 Muse — 상황판 마인드맵 탭 추가 (staging)

- 분류: 5번 사무실 비서(bot-office)만. 매매 봇(1~4번) 파일 변경 없음, 전략·종목·금액·enabled 변경 없음, API·주문 기능 변경 없음.
- 변경 파일 3개 + 기록 1개:
  - bot_office/board.html: 마인드맵 탭(버튼 data-t="mindmap") + 섹션 추가, iframe src="/thought-mindmap", 보기 전용 안내.
  - bot_office/server.py: GET /thought-mindmap 라우트 추가, 로그인 필요, SAMEORIGIN 프레임만 허용. 기존 라우트·인증 규칙 변경 없음(로그인 미인증 시 /thought-mindmap도 /login으로).
  - bot_office/thought_mindmap.html: 생각의 연결 마인드맵 v1.3 원본 그대로.
  - docs/log/2026-11-01_muse_board_mindmap_tab.md: 이 기록.
- 출처: board.html·server.py는 main 최신본에서만 고침. 마인드맵 v1.3은 다른 AI의 v1.2에 최신 정보(v3.3.4/v3.3.5, v2.4/v2.5, 신호 전환반복)를 추가한 Muse 업데이트본.
- 단계: staging 업로드까지만. 서버 적용은 텔레그램 6. Update 가장 마지막 알림 승인 뒤에 진행한다. main 직접 push·서버 직접 적용·재시작은 하지 않았다.
