# 2026-11-05 Claude — AI 협업 허브(ai-hub) 1단계: task_id 표준

- 기준: now4happy/4bot main 25824dc (사무실 v1.2.6, STATUS 2026-11-04 22:13 KST). 기준 main에 `docs/ai-hub/` 없음 → 기존 파일 덮어쓰기 없음.
- 근거: MUSE AI 협업 시스템 최종 구현 작업 계획 v1.2 + 2026-11-05 07:28 KST 사용자 승인 3건 (임시·시크릿 채팅 / 100MB 초과 시 미니컴, 누적 포함 / 1단계 진행).
- 종류: 문서만 (docs-only). 봇·사무실·업데이터 코드 무변경 → 승인 시 재시작·버전 증가 없음.

## 바꾼 파일 (전부 새 파일)

| 파일 | 저장소 경로 | 이유 |
|---|---|---|
| README.md | docs/ai-hub/README.md | 허브 목적·역할·대화 정리 정책·100MB 규칙·기존 체계와의 관계 |
| TASK_ID.md | docs/ai-hub/TASK_ID.md | task_id 형식·project_id·위험 등급 R0~R3·상태·카드 항목·chat_cleanup |
| TASK_INDEX.md | docs/ai-hub/templates/TASK_INDEX.md | 작업 목록 빈 양식 (실제 목록은 Muse 작업공간) |
| TASK_REQUEST.md | docs/ai-hub/templates/TASK_REQUEST.md | 작업 카드 빈 양식 |
| 이 기록 | docs/log/2026-11-05_claude_ai-hub-step1.md | 작업 기록 |

## 계획서 v1.2와 달라진 점 (이유)

- `TASK_INDEX.md`를 GitHub에는 **양식**으로만 둠 (templates/). 4bot이 공개 저장소라 실제 작업 제목·내용은 Muse 작업공간에만 둔다.
- `tasks/`·`results/`·`review/`·`sources/` 빈 폴더를 만들지 않음. git은 빈 폴더를 못 올리고, `.gitkeep`은 업데이트 비서 classify가 '허용되지 않은 파일'로 거부한다.
- 대화 자동 삭제 대신 임시·시크릿 채팅 + HANDOFF + `pending_delete` (공식 읽기·삭제 API 없음 확인, 사용자 승인).
- 위치를 계획서의 `ai-hub/`(저장소 맨 위) 대신 **`docs/ai-hub/`**로 둠. 4bot `.gitignore`는 화이트리스트 방식(`/*` 전부 제외 후 `!`로 허용)이라 맨 위 `ai-hub/`는 무시된다. `.gitignore`를 고치지 않고(기존 파일 무변경) 이미 허용된 `docs/**/*.md` 안에 둔다. Muse 작업공간 쪽 이름은 그대로 `ai-hub/`.
- 새 항목: `chat_mode`, `chat_cleanup`, `storage`, `size`, `parent`, `links`.

## 검증 (로컬, 서버 적용 아님)

- 기준 main에 4개 파일을 넣고 `git status --porcelain`: 새 파일(??)만, 수정·삭제 없음.
- `docs/ai-hub/` 안 .md 아닌 파일: 0개.
- 업데이트 비서 `bot_updater.py`의 `classify()`를 그대로 떼어 실행: 5개 파일 모두 거부 없음, 재시작 대상 봇 없음 (문서만).
- 비밀·개인정보 검사(password·token·api key·cookie·이메일 패턴·계좌 형식 숫자): 실제 값 0건 (규칙 설명 속 단어만 있음).
- 확인하지 않은 것: 실제 staging 업로드·6. Update 알림·서버 적용 (사용자·Muse 담당).

## 남은 일

1. Muse 작업공간 실제 경로 확인 — 구글 서버 /home·/opt·/root 에서 MEMORY.md를 찾지 못함 (2026-11-05 07:27 사용자 SSH 결과). Muse에게 직접 경로 보고를 받아야 0단계 기준선(파일 목록·MEMORY·GOAL·cron)이 끝난다.
2. 서버(Muse 작업공간)에 `ai-hub/TASK_INDEX.md` 실제 파일과 `tasks/` 만들기 — 경로 확인 뒤 3단계와 묶어서.
3. 미니컴 이동 방법 (6단계).
4. project_id 표에 생각의 연결·스마트폰 비서를 따로 둘지 사용자 결정 (지금은 muse_product/general로 분류 가능).
5. 다음 단계: 2단계 AI별 전달 패키지 (CHATGPT_BRIEF·CLAUDE_BRIEF).

## 다음 AI가 읽을 파일

START.md → STATUS.md → docs/ai-hub/README.md → docs/ai-hub/TASK_ID.md → 이 기록.
