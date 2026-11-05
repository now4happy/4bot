# 2026-11-05 Claude — MUSE-20261105-001 · ai-hub 2단계: AI별 전달 패키지 양식

- task_id: MUSE-20261105-001 · project_id: muse_product · risk: R0 (문서만, .py 변경 없음)
- 지시 기준: main 5a311e1 (ai-hub 1단계 적용). 작업 시점 main은 ae44f3c로 앞서 있음 (5a311e1 뒤 커밋 4개: 3번 토스 적립 v4.3.8, 2번 스나이퍼 v2.2.0 이식, 버전 기록 2건). 그 사이 `docs/ai-hub/` 변경 없음 → **실제 기준 main ae44f3c**로 작성.
- 읽은 주소 (사용자가 적은 순서): START.md · STATUS.md(갱신 2026-11-05 09:32 KST, 대기 업로드 없음) · docs/ai-hub/README.md · TASK_ID.md · templates/TASK_INDEX.md · templates/TASK_REQUEST.md — 6개 모두 열림. main의 ai-hub 1단계 파일 5개는 1단계 제출 해시와 일치.

## 바꾼 파일

| # | 저장소 경로 | 종류 | 이유 |
|---|---|---|---|
| 1 | docs/ai-hub/templates/CHATGPT_BRIEF.md | 새 파일 | ChatGPT용 전달 패키지 빈 양식 (기획·설계·분석만, 운영 코드 확정·GitHub 쓰기 금지) |
| 2 | docs/ai-hub/templates/CLAUDE_BRIEF.md | 새 파일 | Claude용 전달 패키지 빈 양식 (개발·코딩·테스트, staging·main 업로드·서버 적용·재시작 금지) |
| 3 | docs/ai-hub/TASK_ID.md | 1행 추가 | project_id 표에 `thought_connection` 추가 (사용자 승인 2026-11-05). 다른 행 무변경 |
| 4 | docs/log/2026-11-05_claude_ai-hub-step2.md | 새 파일 | 이 기록 |

## 양식 공통 항목 (두 양식 모두)

task_id · project_id · title · objective(완료 기준) · risk · agents·역할(README 2절 고정) · account_alias · usage_state · 입력 파일·주소 · 제약 · 산출물 · chat_mode(GPT temporary / Claude incognito 기본) · chat_cleanup · storage(server/minipc) · size · next_action.
- 자리표시자(`<…>`)만 있고 실제 작업 제목·내용·개인정보·비밀값 없음.
- thought_connection 산출물 파일명 규칙(`생각의연결_` 접두 + 버전, main 루트 index.html 예외)을 두 양식의 산출물 절에 넣음. ai-hub 양식 파일 이름 자체에는 적용하지 않음.
- 반환 형식은 계획서 v1.2 8절 기준: ChatGPT=설계안·선택지·위험·테스트 기준 / Claude=최종본 목록·diff·테스트 결과·보안·미해결·롤백.

## 검증 (로컬, 서버 적용 아님)

- 기준 main ae44f3c 대비 `git status`: 새 파일 3개 + 수정 1개(TASK_ID.md)뿐. STATUS.md·.py·다른 파일 무변경.
- TASK_ID.md diff: `+` 1줄(thought_connection 행), `-` 0줄.
- `docs/ai-hub/` 안 .md 아닌 파일 0개. 업데이트 비서 `classify()` 실행 결과 거부 0, 재시작 대상 봇 없음.
- 비밀값 패턴(이메일·API 키·텔레그램 토큰·계좌 형식) 0건. 파기된 프로젝트는 표·예시 어디에도 넣지 않음 (양식 2개·TASK_ID 검색 0건).
- 해시·크기는 제출 ZIP의 VERIFY.md 참고.

## 아직 하지 않은 것

- staging 업로드, 6. Update 승인, 서버 적용·재시작 — Muse 검토 뒤 사용자·Muse 담당.

## 남은 일

1. README.md 7절 파일 목록의 CHATGPT_BRIEF·CLAUDE_BRIEF 표시가 아직 "2 (예정)"이고 변경 기록에 ai-hub v1.1.0 줄이 없음 — 이번 범위 밖이라 안 고침. 다음 단계(3단계) 문서 작업 때 함께 갱신.
2. 3단계: Muse 작업공간 경로 확인 뒤 공통 상태·기억 파일(GOAL.md 연결) + 서버 TASK_INDEX·tasks/ 생성.

## 다음 AI가 읽을 파일

START.md → STATUS.md → docs/ai-hub/README.md → docs/ai-hub/TASK_ID.md → docs/ai-hub/templates/CHATGPT_BRIEF.md · CLAUDE_BRIEF.md → 이 기록.
