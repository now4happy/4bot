# 작업 ID 표준 (task_id)

모든 프로젝트의 요청 → 결과 → 검수 → handoff → 대화 정리를 task_id 하나로 잇는다.

## 1. 형식

`MUSE-YYYYMMDD-NNN`

- 날짜: 요청을 받은 날, **한국시간(KST)** 기준. (사용자 현지 UTC+8, 서버 UTC와 헷갈리지 않게)
- NNN: 그날 001부터. Muse 작업공간 TASK_INDEX.md의 같은 날짜 마지막 번호 + 1.
- 한 번 쓴 번호는 취소돼도 다시 쓰지 않는다 (상태를 `blocked` + 사유 '취소'로 남김).
- 예: `MUSE-20261105-001`

## 2. 작업을 나누는 기준

- 한 작업 = 목표 1개 + 담당 AI 흐름 1개.
- **R3 작업은 반드시 별도 task_id**로 나눈다 (실거래·주문·계좌, CO₂ PLC 실제 출력·주소 변경, 병원 환자·직원 개인정보).
- 같은 파일을 두 AI가 동시에 고치는 작업 2개를 동시에 `in_progress`로 두지 않는다.
- 이어지는 작업은 새 task_id를 만들고 `parent`에 앞 작업 ID를 적는다.

## 3. project_id

| project_id | 범위 |
|---|---|
| trading_soxs | 토스 SOXS 스나이퍼 등 미국 레버리지 매매 |
| trading_korea | 한투·토스 적립 등 주식 매매 봇, 팬딩 가격표 매매 |
| crypto | 빗썸 적립 등 가상자산 |
| co2_control | CO₂ 예측 모델·센서·제어 로직 |
| hospital | WEHAGO·인사·회계·보고 |
| investment_signals | 5대 신호, 지표·뉴스·금리 |
| muse_product | Muse 자체: 기억·작업 관리·AI 전달·ai-hub |
| general | 문서·여행·구매·학습·디자인 등 일반 업무 |

목록에 없는 프로젝트는 가장 가까운 것을 쓰고 `title`에 프로젝트 이름을 적는다. 새 project_id는 사용자 승인 후에만 이 표에 추가한다.

## 4. 위험 등급 (risk)

| 등급 | 뜻 | 승인 |
|---|---|---|
| R0 | 문서·조사·기획 (코드·운영 영향 없음) | 결과 확인만 |
| R1 | 운영에 안 들어가는 코드·양식·테스트 | 사용자 확인 |
| R2 | 운영 코드·설정 (봇·사무실·서버) | staging → 6. Update ✅ |
| R3 | 실거래·주문·계좌·키 / PLC 실제 출력 / 개인정보 | **별도 task_id + 별도 명시 승인** + R2 절차 |

등급이 애매하면 높은 쪽으로 정한다.

## 5. 상태 (status)

`received → planned → in_progress → review → approval_pending → completed`
어느 단계에서든 → `blocked` (사유 필수)

| 상태 | 들어가는 조건 |
|---|---|
| received | Muse가 요청을 받아 ID를 붙임 |
| planned | 목표·담당 AI·위험 등급·산출물이 정해짐 |
| in_progress | 사용자가 담당 AI 앱에서 실행 시작 |
| review | 결과 파일이 `results/`에 저장되고 다시 읽기(read-back) 성공 |
| approval_pending | 검수 완료, 사용자 승인 또는 6. Update ✅ 대기 (R0·R1은 건너뛸 수 있음) |
| completed | 승인 끝 + 결과·근거·검수 상태 기록 + handoff 작성 + chat_cleanup 기록 |
| blocked | 막힘·취소·사용량 한도 등. 사유와 다시 시작 조건을 적음 |

**AI 응답만으로 completed 처리하지 않는다.** 결과 파일·근거·검수 상태가 있어야 한다.

## 6. 작업 카드 항목

| 항목 | 값 | 비고 |
|---|---|---|
| task_id | MUSE-YYYYMMDD-NNN | |
| parent | 앞 작업 ID 또는 `-` | |
| project_id | 3절 표 | |
| title | 한 줄 | 개인정보 넣지 않음 |
| objective | 완료 기준이 보이는 문장 | |
| agents | chatgpt / claude / gemini / deepseek 중 | 역할은 README 2절 고정 |
| risk | R0~R3 | |
| status | 5절 | |
| account_alias | 계정 **별칭**만 (예: GPT-공유1) | 이메일·비밀번호·토큰 금지 |
| usage_state | available / near_limit / limited / unknown | **사용자가 확인한 값만**. 자동 조회 안 함 |
| chat_mode | temporary / incognito / normal | 기본은 temporary(GPT)·incognito(Claude) |
| chat_cleanup | not_needed / pending_delete / deleted_by_owner / kept | 아래 7절 |
| storage | server / minipc | 100MB 규칙 (README 4절) |
| size | 예: 12MB | Muse가 확인한 값 |
| links | docs/log·docs/instructions·브랜치·commit SHA | 4bot 작업일 때 |
| next_action | 다음에 누가 무엇을 | |
| created / updated | YYYY-MM-DD HH:MM KST | |

## 7. 대화 정리 상태 (chat_cleanup)

| 값 | 뜻 |
|---|---|
| not_needed | 임시·시크릿 채팅이라 기록에 남지 않음 (기본) |
| pending_delete | 일반 채팅으로 진행됨. HANDOFF 저장 검증 후 계정 주인이 앱에서 직접 삭제할 차례 |
| deleted_by_owner | 계정 주인이 대화 제목의 task_id를 확인하고 직접 삭제함 |
| kept | 대상 대화를 확실히 구별할 수 없음 → 지우지 않고 보관 |

`pending_delete`로 바꾸기 전 조건: HANDOFF 저장 성공 + read-back 성공 + 대화 제목/첫 줄의 task_id 일치.
저장이 하나라도 실패하면 대화를 닫지도, 지우지도 않는다.

## 8. 금지

- 카드·목록에 비밀번호·API 키·쿠키·세션 토큰·이메일·계좌번호·환자/직원 실명을 적지 않는다.
- 사용량을 자동으로 조회하거나, 계정을 자동으로 바꾸거나, 대화를 자동으로 지우지 않는다.
