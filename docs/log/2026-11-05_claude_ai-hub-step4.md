# 2026-11-05 Claude — MUSE-20261105-002 · ai-hub 4단계: DeepSeek 검색 의뢰·반환 양식

- task_id: MUSE-20261105-002 · parent: MUSE-20261105-001 · project_id: muse_product · risk: R0 (문서만, .py 변경 없음)
- 기준 main: **9b94ea3** (지시 기준과 같음, 작업 시점 main 앞섬 없음). main의 ai-hub 파일 6개 해시는 1·2단계 제출본과 일치.
- 읽은 주소 (사용자가 적은 순서): START.md · STATUS.md(갱신 2026-11-05 09:32 KST, 대기 업로드 없음) · docs/ai-hub/README.md · TASK_ID.md · templates/TASK_INDEX.md · TASK_REQUEST.md · CHATGPT_BRIEF.md · CLAUDE_BRIEF.md — 8개 모두 열림.
  - 참고: raw 주소로 연 TASK_ID.md는 표 마지막 행이 `general`로 보였음 (raw 캐시 지연 또는 읽기 도구 요약 차이로 추정). git main 9b94ea3에는 33행 `thought_connection`이 있음 → git main 기준으로 작업.

## 바꾼 파일

| # | 저장소 경로 | 종류 | 이유 |
|---|---|---|---|
| 1 | docs/ai-hub/templates/DEEPSEEK_SEARCH.md | 새 파일 | DeepSeek 검색 의뢰·반환 빈 양식 |
| 2 | docs/log/2026-11-05_claude_ai-hub-step4.md | 새 파일 | 이 기록 |

고치지 않음: TASK_ID.md · README.md · 기존 양식 4종 · STATUS.md · 그 밖의 모든 파일.

## 양식 내용

- 역할 고정: 검색·자료 조사 전용 · 코딩·수정·GitHub 변경·최종 승인·운영 명령 금지 · 반환에 코드가 있어도 채택하지 않음 명시.
- 의뢰: task_id · project_id · 질문 · 범위 · 날짜 범위 · 언어 · 포함할/제외할 출처 · 찾지 말 것(개인정보·계좌·비밀번호·API 키·쿠키·토큰·이메일).
- 반환 순서: 1) 요약 2) 출처별(제목·URL·발행일·확인일 KST·확인하는 것·확인하지 못하는 것 + 오래됨 여부) 3) 미확인 목록 4) next_action.
- 발행일 모름은 "모름", 발행일≠확인일, 못 찾음은 "찾지 못함", 오래된 출처는 "오래됨" 표시.
- 공통 자리표시자: chat_mode · chat_cleanup · storage(server/minipc) · size.
  - chat_mode는 README 3절에 DeepSeek 고정값이 없어 `<사용자가 고른 대화 모드>`로만 둠 (규칙 새로 만들지 않음).
- 끝맺음: `task_id · 산출물 · next_action` 한 줄. SESSION_CLOSEOUT(7단계) 형식은 정하지 않음.

## 검증 (로컬, 서버 적용 아님)

- 기준 main 9b94ea3 대비 `git status`: 새 파일 2개뿐, 수정·삭제 0, STATUS.md·.py 무변경.
- `docs/ai-hub/` 안 .md 아닌 파일 0개. 업데이트 비서 `classify()`: 거부 0, 재시작 대상 봇 없음.
- 비밀값 패턴(이메일·API 키·텔레그램 토큰·계좌 형식) 0건.
- 해시·크기는 제출 ZIP의 VERIFY.md 참고.

## 아직 하지 않은 것

- staging 업로드, 6. Update 승인, 서버 적용·재시작 — Muse 검토 뒤 사용자·Muse 담당.

## 남은 일

1. README.md 7절 파일 목록 표시(2·4단계 "예정")와 변경 기록 갱신 — 이번에도 범위 밖. README를 고치는 작업 때 한꺼번에.
2. 3단계(공통 상태·기억 파일)는 Muse 작업공간 경로 보고가 아직 없어 대기.
3. 다음 양식: 5단계 GEMINI_REVIEW.md.

## 다음 AI가 읽을 파일

START.md → STATUS.md → docs/ai-hub/README.md → docs/ai-hub/TASK_ID.md → docs/ai-hub/templates/DEEPSEEK_SEARCH.md → 이 기록.
