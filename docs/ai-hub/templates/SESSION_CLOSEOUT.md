# 세션 종료·HANDOFF 양식 (SESSION_CLOSEOUT)

> 사용법: 작업 대화를 끝낼 때 **각 AI(ChatGPT·Claude·Gemini·DeepSeek)가 마지막 답변에 아래 HANDOFF 블록을 출력**한다. 사용자는 그 블록을 Muse에 붙여 넣는다.
> **이 양식은 대화를 닫지 않는다.** 창을 닫을지는 Muse가 4절 닫기 조건을 확인한 뒤 알린다.
> 규칙 원문: docs/ai-hub/README.md (대화 정리 3절·저장 용량 4절) · docs/ai-hub/TASK_ID.md (chat_cleanup 7절) · 결과 검수는 templates/RESULT_REVIEW.md
> 공개 저장소 양식이다. 이 파일에는 실제 작업 제목·내용·개인정보·계좌·비밀번호·API 키·쿠키·토큰·이메일을 넣지 않는다. 채운 블록은 Muse 작업공간 `ai-hub/tasks/<task_id>/`에만 둔다.

---

## 1. AI에게 붙일 요청 문장

> 이 대화를 끝낸다. 아래 HANDOFF 블록을 순서·항목 이름 그대로 채워서 마지막 답변으로 출력해라. 모르는 값은 "모름", 하지 않은 검사는 "안 함"이라고 쓰고 지어내지 마라. 비밀값·개인정보는 넣지 마라.

## 2. HANDOFF 블록 (이 순서만)

```text
=== HANDOFF ===
1) task_id: MUSE-YYYYMMDD-NNN
2) 산출물:
   - <파일명> · <버전 / 없음> · SHA-256 <앞 16자리 / 계산 못 함> · <크기 bytes>
3) 검증 결과: <통과 / 실패>
   - 실행한 검사: <예: 문법 검사 · 모의 입력 · 비밀값 검색 · 범위 밖 변경 확인 / 안 함>
4) 독립 검수 판정: <있음: 판정 통과·수정 필요·불가 / 지적 n건 요약 / 미확인 목록> 또는 <없음>
5) 미확인·남은 문제:
   - <항목 / 없음>
6) next_action: <다음에 누가(사용자/Muse/ChatGPT/Claude/Gemini/DeepSeek) 무엇을>
7) chat_cleanup: <not_needed / pending_delete / deleted_by_owner / kept>
--- 작업 정보 ---
chat_mode: <temporary / incognito / 사용자가 고른 모드>
storage: <server / minipc>
size: <__MB>
=== END ===
```

- 독립 검수가 없었으면 4)에 **없음**이라고 쓴다. 검수 없이 통과로 쓰지 않는다.
- 검증을 실행하지 않았으면 3)을 "통과"로 쓰지 않는다.

## 3. 저장 위치·용량 (Muse가 채움)

| 항목 | 값 |
|---|---|
| 저장 경로 | ai-hub/tasks/<task_id>/handoff.md |
| storage | server / minipc |
| size | <__MB> (작업 1건 또는 tasks/ 누적이 100MB 넘으면 minipc — README 4절) |
| 옮긴 날짜 | <YYYY-MM-DD KST / 옮기지 않음> |

옮기는 방법은 이 양식에서 정하지 않는다. 옮겼을 때 위 3칸만 기록한다.

## 4. 닫기 조건 (Muse가 확인)

1. HANDOFF 블록을 저장한다.
2. 저장한 파일을 **다시 읽는다(read-back)**. 내용·산출물 해시가 블록과 같은지 본다.
3. **task_id 일치**: HANDOFF 블록 · 대화 제목 또는 첫 줄 · 결과 파일의 task_id가 모두 같은지 본다.
4. 세 가지가 모두 맞으면 사용자에게 **"창 닫아도 됨"**을 알린다.

- **저장 실패 · 해시 불일치 · task_id 불일치** 중 하나라도 있으면 **"닫지 마세요"**로 멈추고 다시 저장한다.
- Muse가 "창 닫아도 됨"을 알리기 전에는 사용자가 창을 닫지 않는다.

| 확인 | 결과 |
|---|---|
| 저장 | <성공 / 실패> |
| read-back | <성공 / 실패> |
| task_id 일치 | <일치 / 불일치 (어디가 다른지)> |
| 알림 | <창 닫아도 됨 / 닫지 마세요> · <YYYY-MM-DD HH:MM KST> |

## 5. 대화 정리

| 대화 종류 | chat_cleanup | 할 일 |
|---|---|---|
| 임시 채팅(ChatGPT) · 시크릿 채팅(Claude) | not_needed | 기록에 남지 않아 지울 대상이 생기지 않는다. 창만 닫는다 |
| 일반 채팅 | pending_delete | 계정 주인이 **앱에서 직접** 지운다. 지운 뒤 deleted_by_owner로 바꾼다 |
| 대상 대화를 확실히 구별할 수 없음 | kept | 지우지 않고 보관한다 |

- **삭제 전 조건 (모두 충족)**: HANDOFF 저장 성공 + read-back 성공 + 대화 제목·첫 줄의 task_id 일치.
- **금지**: 자동 삭제 · 다른 사람 대화 삭제 · 계정 전체 대화 삭제.

## 6. 다음 세션

- 다음 세션은 이전 대화 원문이 아니라 이 HANDOFF와 승인된 파일 주소로 시작한다.
- 끝맺음 한 줄: `task_id · 닫기 알림(창 닫아도 됨 / 닫지 마세요) · next_action`
