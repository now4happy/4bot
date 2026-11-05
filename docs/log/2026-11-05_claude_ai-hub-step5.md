# 2026-11-05 Claude — MUSE-20261105-003 · ai-hub 5단계: Gemini 독립 검수 양식

- task_id: MUSE-20261105-003 · parent: MUSE-20261105-002 · project_id: muse_product · risk: R0 (문서만, .py 변경 없음)
- 기준 main: **21d72b0** (지시 기준과 같음, 작업 시점 main 앞섬 없음). main의 ai-hub 파일 7개 해시는 1·2·4단계 제출본과 일치.
- 읽은 주소 (사용자가 적은 순서, 9개):
  - 열림 8개: START.md · STATUS.md(갱신 2026-11-05 09:32 KST, 대기 업로드 없음) · README.md · TASK_ID.md · templates/TASK_INDEX.md · TASK_REQUEST.md · CHATGPT_BRIEF.md · CLAUDE_BRIEF.md
  - **안 열림 1개**: templates/DEEPSEEK_SEARCH.md raw 주소 — 읽기 도구가 "세션 허용 목록에 없음"으로 거부. 같은 파일은 git main 21d72b0에서 읽었고 해시 16ab8e3c6eba99fb(4단계 제출본과 같음).
  - 참고: raw로 연 TASK_ID.md는 표 마지막 행이 `general`로 보였으나, git main에는 `thought_connection` 행이 있음 (4단계 기록과 같은 현상). git main 기준으로 작업.

## 바꾼 파일

| # | 저장소 경로 | 종류 | 이유 |
|---|---|---|---|
| 1 | docs/ai-hub/templates/GEMINI_REVIEW.md | 새 파일 | Gemini 독립 검수 빈 양식 |
| 2 | docs/log/2026-11-05_claude_ai-hub-step5.md | 새 파일 | 이 기록 |

고치지 않음: TASK_ID.md · README.md · 기존 양식 5종 · STATUS.md · 그 밖의 모든 파일.

## 양식 내용

- 역할 고정: 이미지 판독·독립 검수 · 자기 결과 자기 검수 금지 — 만든 AI가 Gemini면 검수 시작 없이 "불가 — 자기 검수라 불가" 후 멈춤 · 검수는 승인·서버 적용·GitHub 변경이 아님.
- 검수 대상: task_id · project_id · 결과 파일·버전·해시·만든 AI · 원래 의뢰(목표·범위·제약) · 검수 기준 주소 · 첨부 유무.
- 검수 항목 6개: 목표·범위 일치 / 사실·숫자·날짜 출처 일치(URL·발행일·확인일 구분) / 범위 밖 변경 / 비밀값·개인정보 / 이미지·첨부 읽힘·안 읽힘 구분(추측 금지) / 미확인·추측의 단정.
- 반환 순서: 1) 판정(통과/수정 필요/불가+사유) 2) 지적 사항(항목·위치·이유·근거·고칠 수 있음 여부) 3) 통과한 항목 4) 미확인 목록 5) next_action. 지적 없는 통과 지어내기 금지, 고칠 수 없는 문제는 그렇다고 씀.
- 공통 자리표시자: chat_mode · chat_cleanup · storage(server/minipc) · size. chat_mode는 README 3절에 Gemini 고정값이 없어 `<사용자가 고른 대화 모드>`로만 둠.
- 끝맺음: `task_id · 판정 · next_action` 한 줄. SESSION_CLOSEOUT(7단계) 형식은 정하지 않음.

## 검증 (로컬, 서버 적용 아님)

- 기준 main 21d72b0 대비 `git status`: 새 파일 2개뿐, 수정·삭제 0, STATUS.md·.py 무변경.
- `docs/ai-hub/` 안 .md 아닌 파일 0개. 업데이트 비서 `classify()`: 거부 0, 재시작 대상 봇 없음.
- 비밀값 패턴(이메일·API 키·텔레그램 토큰·계좌 형식) 0건.
- 해시·크기는 제출 ZIP의 VERIFY.md 참고.

## 아직 하지 않은 것

- staging 업로드, 6. Update 승인, 서버 적용·재시작 — Muse 검토 뒤 사용자·Muse 담당.

## 남은 일

1. README.md 7절 파일 목록 표시(2·4·5단계 "예정")와 변경 기록 갱신 — 범위 밖. README를 고치는 작업 때 한꺼번에.
2. 3단계(공통 상태·기억 파일)는 Muse 작업공간 경로 보고가 아직 없어 대기.
3. 다음 양식: 6단계 RESULT_REVIEW.md.

## 다음 AI가 읽을 파일

START.md → STATUS.md → docs/ai-hub/README.md → docs/ai-hub/TASK_ID.md → docs/ai-hub/templates/GEMINI_REVIEW.md → 이 기록.
