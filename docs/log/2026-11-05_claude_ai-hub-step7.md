# 2026-11-05 Claude — MUSE-20261105-005 · ai-hub 7단계: 세션 종료·HANDOFF 양식

- 기준 main: **31b6f34** (지시 기준과 같음, 작업 시점 main 앞섬 없음, staging=main). main의 ai-hub 파일 9개 해시는 1·2·4·5·6단계 제출본과 일치.
- task_id: MUSE-20261105-005 · parent: MUSE-20261105-004 · project_id: muse_product · risk: R0 (문서만, .py 변경 없음) · ai-hub 양식 마지막 단계.
- 읽은 주소 (사용자가 적은 순서, 11개):
  - 열림 8개: START.md · STATUS.md(갱신 2026-11-05 09:32 KST, 대기 업로드 없음) · README.md · TASK_ID.md · templates/TASK_INDEX.md · TASK_REQUEST.md · CHATGPT_BRIEF.md · CLAUDE_BRIEF.md
  - **안 열림 3개** (읽기 도구가 "세션 허용 목록에 없음"으로 거부): templates/DEEPSEEK_SEARCH.md · GEMINI_REVIEW.md · RESULT_REVIEW.md. 셋 다 git main에서 읽음 — 해시 16ab8e3c6eba99fb · f39b50dabd371a89 · e223315f8f459306 (제출본과 같음).

## 바꾼 파일

| # | 저장소 경로 | 종류 | 이유 |
|---|---|---|---|
| 1 | docs/ai-hub/templates/SESSION_CLOSEOUT.md | 새 파일 | 세션 종료·HANDOFF 빈 양식 |
| 2 | docs/log/2026-11-05_claude_ai-hub-step7.md | 새 파일 | 이 기록 |

고치지 않음: TASK_ID.md · README.md · 기존 양식 7종 · STATUS.md · 그 밖의 모든 파일.

## 양식 내용

- 성격: 각 AI가 작업 대화를 끝낼 때 출력하는 HANDOFF 블록. "양식이 대화를 닫지 않는다" 명시. AI에게 붙일 요청 문장 포함.
- HANDOFF 블록 순서: 1) task_id 2) 산출물 파일명·버전·SHA-256 앞 16·크기 3) 검증 결과(통과/실패, 실행한 검사) 4) 독립 검수 판정(없으면 없음) 5) 미확인·남은 문제 6) next_action 7) chat_cleanup + 작업 정보(chat_mode·storage·size).
- 닫기 조건: Muse 저장 → read-back → task_id 일치(블록·대화 제목/첫 줄·결과 파일) 확인 뒤 "창 닫아도 됨". 저장 실패·해시 불일치·task_id 불일치 시 "닫지 마세요" 후 다시 저장.
- 대화 정리: 임시·시크릿 = not_needed · 일반 채팅 = pending_delete → 계정 주인이 앱에서 직접 삭제 → deleted_by_owner · 구별 불가 = kept. 삭제 전 조건 3개. 자동 삭제·타인 대화 삭제·계정 전체 삭제 금지.
- 저장 이동: storage·size·옮긴 날짜 자리표시자만. 이동 방법은 정하지 않음.
  - 용어 참고: 지시문은 "하남컴", README 4절·TASK_ID.md는 `minipc`(미니컴)로 적혀 있음. 기존 규칙 값 `minipc`를 그대로 썼고, 둘이 같은 기기인지는 이 작업에서 정하지 않음.
- 끝맺음: `task_id · 닫기 알림 · next_action` 한 줄.

## 검증 (로컬, 서버 적용 아님)

- 기준 main 31b6f34 대비 `git status`: 새 파일 2개뿐, 수정·삭제 0, STATUS.md·.py 무변경.
- `docs/ai-hub/` 안 .md 아닌 파일 0개. 업데이트 비서 `classify()`: 거부 0, 재시작 대상 봇 없음.
- 비밀값 패턴(이메일·API 키·텔레그램 토큰·계좌 형식) 0건.
- 해시·크기는 제출 ZIP의 VERIFY.md 참고.

## 아직 하지 않은 것

- staging 업로드, 6. Update 승인, 서버 적용·재시작 — Muse 검토 뒤 사용자·Muse 담당.

## 남은 일

1. README.md 7절 파일 목록(2·4·5·6·7단계 "예정" 표시)과 변경 기록 갱신 — 양식 7종이 다 갖춰졌으므로 README 정리 작업 1건으로 묶어서 진행 권장.
2. 3단계(공통 상태·기억 파일, Muse 작업공간 TASK_INDEX·tasks/ 생성)는 Muse 작업공간 경로 보고가 아직 없어 대기.
3. "하남컴"과 `minipc`가 같은 기기인지 사용자 확인 필요 (README 4절 용어 정리와 함께).
4. 계획서 8단계(GitHub staging 테스트)·9단계(시범 운영) 남음.

## 다음 AI가 읽을 파일

START.md → STATUS.md → docs/ai-hub/README.md → docs/ai-hub/TASK_ID.md → docs/ai-hub/templates/SESSION_CLOSEOUT.md → 이 기록.
