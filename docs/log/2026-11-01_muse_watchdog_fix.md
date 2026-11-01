# watchdog 무소식 경고 대응 — Muse 검토·staging 기록 (2026-11-01)

- 기준: main = staging = 5b7d2fe (한투 v1.0.3 적용 후, 대기 없음)
- 초안: 다른 AI가 만든 2개 파일, 사용자 첨부로 전달됨
  - toss_sniper/main.py v1.1.2 예정 (파일명 main_v1.1.2)
  - bot_office/bot_updater.py 사무실 v1.1.1 예정 (파일명 bot_updater_v1.1.1)
- Muse 검토 결과: 통과
  - main 대비 의도된 변경만: 스나이퍼 +2줄, 업데이터 +59줄, 삭제 0줄
  - 스나이퍼: main_sniper_loop 맨 위(주말 체크 전)에 _hub_beat 1줄 + 주석 1줄, 폴백 루프 신호 그대로
  - 업데이터: hub_data_perm_repair (data 0777, hub.db/-wal/-shm 0666, 심볼릭 링크 건너뜀, 예외 없음),
    office_beat_proxy (127.0.0.1:8765/healthz 200일 때만 60초에 1번 8번 신호, 프록시 없이, 3초 제한),
    main 시작 때 권한 정리 + 루프에 대리 신호 호출
  - server.py, 유닛 파일, 매매·주문·전략·종목·금액·enabled 무변경
  - py_compile 통과 (두 파일 모두), 비밀 패턴 0건, healthz는 server.py에 200으로 있음
  - 버전: 스나이퍼 v1.1.1→v1.1.2, 사무실 v1.1.0→v1.1.1, 둘 다 마지막 자리 상승, 최대 9 규칙에 맞음
  - 주의: 8번 ProtectHome 값은 확인되지 않음 (ProtectSystem=strict만 2026-10-28 기록에 있음).
    이 초안은 유닛 보호 설정을 바꾸지 않고 대리 신호로 대응한다. 유닛 변경은 사용자 결정 사항으로 남김.
- 서버 적용: 사용자가 텔레그램 6. Update 마지막 알림으로 승인할 때만.
- 적용 뒤 확인: watchdog(10분마다)이 2번·8번 복구 메시지를 보내면 확인.
  복구 메시지가 안 오면, 초안 문서의 읽기 전용 확인 명령으로 별도 확인한다.
- 남은 일: Case 84·85·86 라이브 확인 (2026-11-02 월요일 EST, case-live-check-20261102.md 참조)
