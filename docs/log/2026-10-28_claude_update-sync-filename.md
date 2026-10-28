# 6. Update 오류 정리 — 서버 HEAD≠main · 한글 파일명 거부
- 상태: **완료(파일 작성·로컬 검사까지)** — 시작 2026-10-28 10:16 KST (01:16 UTC) · 완료 10:34 KST (01:34 UTC)
- 업로드·승인·서버 적용·실제 확인: 아직 (사용자 진행)
- AI / 기기: Claude / 사용자 폰
- 기준: main 5be76b6. 읽은 문서: START.md, start.md(0절), STATUS.md(10:03 KST), 최근 docs/log 2건
- 범위: bot_office/bot_updater.py, bot_office/update_conflicts.py, 이 기록. 1~4번 봇·팬딩·전략·금액·enabled 는 건드리지 않음.
- 다른 AI 진행중 작업: docs/log 에 '진행중' 없음. 같은 파일을 고치는 대기 브랜치 없음.

## 원인 (캡처 2가지)
1. "서버 HEAD와 GitHub main이 다릅니다": 커밋 5be76b6(3·4번 재생 로그)이 staging·승인을 거치지 않고 main 에 바로 올라감.
   서버 HEAD 는 ad3d93b(사무실 v1.0.52) 그대로 → 충돌 정리·STATUS 매일 기록이 멈춤.
   이 상태로 다른 브랜치를 승인하면 main 업로드가 실패하고 staging 만 서버 기준으로 강제 덮어써져 더 어긋남.
2. "이 업데이트는 적용할 수 없습니다"(docs-20261028-fanding): git 이 한글 파일명을 "\355…" 따옴표 표기로 출력 →
   이름이 .md 로 끝나지 않아 '허용되지 않은 파일'로 분류. 실제로는 문서 1개, main 과 충돌 없음.

## 바꾼 것 (사무실 vNEXT → 승인 때 실제 번호)
- bot_updater.py: git 호출에 core.quotepath=false (한글 파일명 정상 인식) ·
  main 이 서버보다 앞서면 텔레그램 알림 1번(같은 main 은 반복 안 함) ·
  적용 직전, 병합 결과에 main 이 안 들어가면 멈춤(main 업로드 실패·staging 덮어쓰기 방지).
- update_conflicts.py: 'HEAD≠main' 안내를 main 앞섬 / 서버 앞섬 / 갈라짐 으로 나눠 할 일까지 표시.

## 검증 (로컬 복제본, 실제 서버·텔레그램·주문 없음)
- 지금 상황(서버 ad3d93b, main 5be76b6) 재현: 원본 코드는 캡처와 같은 문구·문서 브랜치 거부 그대로 나옴.
- 수정본: 한글 파일명 인식·거부 없음 / main 앞섬 알림 1회만 / 충돌 정리 문구 'main이 서버보다 앞섬' / 문서 브랜치는 적용 전 멈춤.
- main 기준 새 브랜치 병합 시뮬레이션: main 업로드 fast-forward 성공 → 알림 해제 → 문서 브랜치 충돌 0, 적용 가능.
- 비밀값 검사 통과, Python 문법 검사 통과.

## 남은 일
- 사용자: main 기준 새 브랜치(fix-sync-20261028)에 두 파일·이 기록 업로드 → 6. Update ✅ 승인.
  이 승인에는 3번 v4.3.5·4번 v4.0.4 재생 로그 적용(3·4번 재시작)이 함께 들어감.
- 그다음 docs-20261028-fanding 알림 승인(문서만, 재시작 없음).
- fanding-fx-button-20261028 브랜치는 다른 작업용 이름 → 승인하지 말 것(승인하면 비서가 그 브랜치를 지움).
- 원칙 재확인: main 에는 직접 올리지 않는다(staging 또는 main 기준 새 브랜치).

## 다음 AI가 읽을 파일
- STATUS.md, docs/handoff/06_updater.md, 이 기록.
