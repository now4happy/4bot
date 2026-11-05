# 2026-11-05 Claude — MUSE-20261105-004 · ai-hub 6단계: 결과 수집·검수 양식

- **새 기준 main: 862df95** — 지시 기준 21d72b0보다 앞섬. 그 사이 변경은 5단계 2개 파일(GEMINI_REVIEW.md·step5 기록) 추가뿐이고 staging도 862df95로 main과 같음 → 5단계가 이미 main 적용 완료라 6단계 파일이 5단계 6. Update 알림에 섞일 일 없음.
- task_id: MUSE-20261105-004 · parent: MUSE-20261105-003 · project_id: muse_product · risk: R0 (문서만, .py 변경 없음)
- main의 ai-hub 파일 8개 해시는 1·2·4·5단계 제출본과 일치.
- 읽은 주소 (사용자가 적은 순서, 10개):
  - 열림 8개: START.md · STATUS.md(갱신 2026-11-05 09:32 KST, 대기 업로드 없음) · README.md · TASK_ID.md · templates/TASK_INDEX.md · TASK_REQUEST.md · CHATGPT_BRIEF.md · CLAUDE_BRIEF.md
  - **안 열림 2개** (읽기 도구가 "세션 허용 목록에 없음"으로 거부): main/templates/DEEPSEEK_SEARCH.md · staging/templates/GEMINI_REVIEW.md. 둘 다 git에서 읽음 — 해시 16ab8e3c6eba99fb · f39b50dabd371a89 (제출본과 같음). GEMINI_REVIEW는 참고만, 고치지 않았고 제출에 넣지 않음.

## 바꾼 파일

| # | 저장소 경로 | 종류 | 이유 |
|---|---|---|---|
| 1 | docs/ai-hub/templates/RESULT_REVIEW.md | 새 파일 | Muse용 결과 수집·검수 빈 양식 |
| 2 | docs/log/2026-11-05_claude_ai-hub-step6.md | 새 파일 | 이 기록 |

고치지 않음: TASK_ID.md · README.md · 기존 양식 6종(GEMINI_REVIEW 포함) · STATUS.md · 그 밖의 모든 파일.

## 양식 내용

- 사용 주체: Muse (다른 AI에 붙여 넣지 않음) · "양식이 검수를 대신하지 않는다", 확인 안 한 칸은 "미확인" 명시.
- 수집: task_id · project_id · risk · 결과 파일 경로·버전·SHA-256 앞 16·크기(VERIFY.md 값 대조) · 만든 AI · 제출 ZIP 파일명 · results/ 저장 위치 · storage·size · chat_mode.
- 확인 7개: read-back · task_id 일치(대화 제목·첫 줄·결과 파일) · objective·범위 일치 · 범위 밖 파일 변경 · 비밀값·개인정보(위치만) · GEMINI_REVIEW 판정 기록(없으면 "없음", 지어내기 금지, 같은 AI 검수는 독립 아님) · chat_cleanup.
- 판정: 통과 / 수정 필요 / blocked(사유 필수). 상태 전이: AI 응답만으로 completed 금지 · R2는 staging → 6. Update ✅ 뒤 · R3는 별도 task_id + 별도 명시 승인 + R2 절차 · 저장 실패 시 대화 닫기·삭제 금지.
- 끝맺음: `task_id · 검수 결과 · next_action` 한 줄. SESSION_CLOSEOUT(7단계) 형식은 정하지 않음.

## 검증 (로컬, 서버 적용 아님)

- 기준 main 862df95 대비 `git status`: 새 파일 2개뿐, 수정·삭제 0, STATUS.md·.py 무변경.
- `docs/ai-hub/` 안 .md 아닌 파일 0개. 업데이트 비서 `classify()`: 거부 0, 재시작 대상 봇 없음.
- 비밀값 패턴(이메일·API 키·텔레그램 토큰·계좌 형식) 0건.
- 해시·크기는 제출 ZIP의 VERIFY.md 참고.

## 아직 하지 않은 것

- staging 업로드, 6. Update 승인, 서버 적용·재시작 — Muse 검토 뒤 사용자·Muse 담당.

## 남은 일

1. README.md 7절 파일 목록 표시(2·4·5·6단계 "예정")와 변경 기록 갱신 — 범위 밖. README를 고치는 작업 때 한꺼번에.
2. 3단계(공통 상태·기억 파일)는 Muse 작업공간 경로 보고가 아직 없어 대기.
3. 다음 양식: 7단계 SESSION_CLOSEOUT.md.

## 다음 AI가 읽을 파일

START.md → STATUS.md → docs/ai-hub/README.md → docs/ai-hub/TASK_ID.md → docs/ai-hub/templates/RESULT_REVIEW.md → 이 기록.
