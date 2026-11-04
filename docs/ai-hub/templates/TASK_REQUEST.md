# 작업 카드 양식 (TASK.md)

> 사용법: 이 양식을 복사해 Muse 작업공간 `ai-hub/tasks/<task_id>/TASK.md`로 저장하고 빈칸을 채운다.
> 규칙: docs/ai-hub/TASK_ID.md · 비밀번호·API 키·쿠키·토큰·이메일·계좌번호·환자/직원 실명 금지.

---

## 기본

- task_id: MUSE-YYYYMMDD-NNN
- parent: -
- project_id:
- title:
- risk: R0 / R1 / R2 / R3
- status: received
- created: YYYY-MM-DD HH:MM KST
- updated: YYYY-MM-DD HH:MM KST

## 목표

- objective (완료 기준이 보이게):
- 산출물 (파일 이름·형식):
- 범위 밖 (하지 않을 것):

## 담당

| AI | 할 일 | account_alias | usage_state (사용자 확인) | chat_mode |
|---|---|---|---|---|
| | | | unknown | temporary / incognito |

- DeepSeek는 검색 전용 · Gemini는 독립 검수 · Claude는 개발 (README 2절).

## 입력

- 읽을 파일·주소 (승인된 것만):
- 사용자가 준 자료:
- 제약 (시간대·버전 규칙·금지 사항):

## 진행 기록 (한 줄씩 추가)

- YYYY-MM-DD HH:MM · 상태 → planned · (무엇을 정했나)

## 결과·검수

- 결과 파일: results/
- read-back: 성공 / 실패 · SHA-256 앞 16자리:
- 검수: 미실시 / Gemini 확인 n건·미확인 n건 / 사용자 확인
- GitHub (4bot 작업): 브랜치 · commit SHA · docs/log 경로
- 승인: 필요 없음(R0·R1) / 사용자 승인 일시 / 6. Update ✅ 일시

## 대화 정리

- chat_cleanup: not_needed / pending_delete / deleted_by_owner / kept
- 대화 제목(일반 채팅일 때): MUSE-YYYYMMDD-NNN · 제목
- HANDOFF 저장: 성공 / 실패 · 확인 일시:

## 저장

- storage: server / minipc
- size: __MB (100MB 넘으면 미니컴, README 4절)

## 다음

- next_action:
- 남은 문제:
