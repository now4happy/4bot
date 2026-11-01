# 2026-11-01 Muse — 상황판 정리 (staging)

- 분류: 5번 사무실 비서(bot-office)만. 매매 봇(1~4번) 파일 변경 없음, 전략·종목·금액·enabled 변경 없음, API·주문 기능 변경 없음.
- 변경 파일 2개 + 기록 1개:
  - bot_office/board.html: 마인드맵 탭(버튼·섹션) 삭제, 탭 순서 상황판·스나이퍼룸·팬딩룸·서버실·기록실, 상황판 오늘 할 일 카드와 주문 안내 문구 삭제, 첫 줄 안내 문구 삭제. /api/board 내용 변경 없음.
  - bot_office/office_board.py: v1.0.60 → v1.0.61, 신호등 표시 순서 번호순(1·2·3·4·5·6·7·8, 터널은 board.html에서 제외). /api/board todo 필드는 그대로.
  - docs/log/2026-11-01_muse_board_cleanup.md: 이 기록.
- 출처: board.html·office_board.py는 main 최신본(23a76db, 사무실 v1.1.2)에서만 고침. 문법 검사: office_board.py py_compile 통과, board.html 스크립트 node --check 통과.
- 범위 밖: /thought-mindmap 주소와 thought_mindmap.html 파일은 이번에 안 건드림. 다른 탭 내용 변경 없음.
- 단계: staging 업로드까지만. 서버 적용은 텔레그램 6. Update 가장 마지막 알림 승인 뒤에 진행한다. main 직접 push·서버 직접 적용·재시작은 하지 않았다.
