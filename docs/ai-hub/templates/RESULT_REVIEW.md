# 결과 수집·검수 양식 (RESULT_REVIEW)

> 사용법: **Muse**가 다른 AI의 결과를 받을 때마다 이 양식을 복사해 Muse 작업공간 `ai-hub/tasks/<task_id>/review/RESULT_REVIEW.md`로 저장하고 채운다. 다른 AI에게 붙여 넣는 양식이 아니다.
> **이 양식은 검수를 대신하지 않는다.** 칸을 채우는 것은 실제로 파일을 열고, 다시 읽고, 대조한 결과를 적는 일이다. 확인하지 않은 칸은 "미확인"으로 남긴다.
> 규칙 원문: docs/ai-hub/README.md (역할 2절·대화 정리 3절·저장 용량 4절) · docs/ai-hub/TASK_ID.md (상태 5절·위험 등급 4절·chat_cleanup 7절)
> 공개 저장소 양식이다. 이 파일에는 실제 작업 제목·내용·개인정보·계좌·비밀번호·API 키·쿠키·토큰·이메일을 넣지 않는다.

---

## 1. 수집

| 항목 | 값 |
|---|---|
| task_id | MUSE-YYYYMMDD-NNN |
| project_id | <TASK_ID.md 3절 표의 값> |
| risk | <R0 / R1 / R2 / R3> |
| 만든 AI | <chatgpt / claude / gemini / deepseek / 사용자> |
| 제출 ZIP 파일명 | <파일명 / 없음 (채팅 답변만)> |
| results/ 저장 위치 | ai-hub/tasks/<task_id>/results/<파일명> |
| storage | server / minipc |
| size | <__MB> — 작업 1건 또는 tasks/ 누적이 100MB 넘으면 미니컴 (README 4절) |
| chat_mode | <temporary / incognito / 사용자가 고른 모드> |
| 수집 일시 | YYYY-MM-DD HH:MM KST |

결과 파일 (파일마다 1줄):

| # | 결과 파일 경로 | 버전 | SHA-256 앞 16 | 크기(bytes) | 제출 VERIFY.md 값과 같음 |
|---|---|---|---|---|---|
| 1 | <경로> | <머리말 버전 / 없음> | <16자리> | <크기> | <같음 / 다름 / VERIFY 없음> |

## 2. 확인 (전부 본다)

| # | 확인 항목 | 결과 | 근거·위치 |
|---|---|---|---|
| 1 | 저장 뒤 다시 읽기(read-back) | <성공 / 실패 / 미확인> | <다시 읽은 해시가 위 표와 같은지> |
| 2 | task_id 일치 — 대화 제목·첫 줄·결과 파일 | <일치 / 불일치 / 미확인> | <각각 어디서 본 task_id인지> |
| 3 | 원래 objective·범위 대비 결과 일치 | <일치 / 일부 / 불일치 / 미확인> | <TASK.md objective와 비교한 내용> |
| 4 | 범위 밖 파일 변경·추가·삭제 | <없음 / 있음 / 미확인> | <기준 커밋 대비 파일 목록 비교 결과> |
| 5 | 비밀값·개인정보 포함 | <없음 / 있음 / 미확인> | <발견하면 **위치만**. 값은 옮겨 적지 않는다> |
| 6 | 독립 검수(GEMINI_REVIEW) 판정 기록 | <있음 / 없음> | 아래 6-1 |
| 7 | chat_cleanup (TASK_ID.md 7절) | <not_needed / pending_delete / deleted_by_owner / kept> | <임시·시크릿 여부, 삭제 대기 조건 충족 여부> |

### 6-1. 독립 검수 기록

- 판정이 있으면: 판정 <통과 / 수정 필요 / 불가> · 지적 <n건, 번호와 한 줄 요약> · 미확인 <목록> · 검수한 AI <이름> · 일시 <KST>
- 판정이 없으면: **없음**이라고 쓴다. 검수가 없는데 통과로 지어내지 않는다.
- 검수한 AI가 결과를 만든 AI와 같으면 그 검수는 독립 검수가 아니다 (README 2절).

## 3. 판정과 상태 전이

### 검수 결과 (하나만)

- <통과 / 수정 필요 / blocked> — blocked면 사유와 다시 시작 조건을 적는다.
- 수정 필요면: 누가 무엇을 고칠지 (2절 번호 기준).

### 상태 전이 규칙 (TASK_ID.md 5절)

- **AI 응답만으로 completed 처리하지 않는다.** 결과 파일(1절) · 근거(2절) · 검수 상태(6-1)가 모두 있어야 completed로 간다.
- 저장 뒤 read-back 성공 → `review`. 검수 결과 통과 → R0·R1은 사용자 확인 뒤 `completed`, R2·R3는 `approval_pending`.
- **R2**: staging → 텔레그램 6. Update ✅ 뒤에만 `completed`.
- **R3**: 별도 task_id + 별도 명시 승인 + R2 절차를 모두 거친 뒤에만 `completed`.
- 수정 필요 → `in_progress`로 되돌리고 next_action에 담당 AI를 적는다. blocked → `blocked` + 사유.

| 항목 | 값 |
|---|---|
| 상태 (이전 → 이후) | <예: review → approval_pending> |
| 승인 | <필요 없음(R0·R1) / 사용자 승인 일시 / 6. Update ✅ 일시 · commit SHA> |
| TASK_INDEX 갱신 | <했음 / 안 함> |

### 저장 실패 시

- read-back이 실패하거나 해시가 다르면 **대화를 닫지도, 지우지도 않는다.** 사용자에게 "닫지 마세요"를 알리고 다시 저장한다 (README 3절).

## 4. 남은 문제

- <미확인 항목 / 고칠 수 없는 문제 / 다음 작업으로 넘길 것>

## 5. 끝맺음

- 한 줄: `task_id · 검수 결과 · next_action`
- next_action: <다음에 누가 무엇을>
