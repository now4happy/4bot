# START — 새 채팅은 이 파일부터
갱신: 2026-10-28 · 저장소: https://github.com/now4happy/4bot (공개)
원문 주소: https://raw.githubusercontent.com/now4happy/4bot/main/<경로> (예: …/main/STATUS.md)

## 읽는 순서
1. **STATUS.md** — 서버가 자동으로 쓰는 현재 상태(봇별 버전·서비스·최근 적용·대기 업로드). 다른 문서의 '현재 상태'보다 우선한다.
2. 이 파일의 필수 원칙.
3. 이번 작업에 해당하는 docs/handoff/ 문서 1개 (아래 표).
4. 이어지는 작업이면 docs/log/ 의 최근 기록 (파일 이름이 날짜순).

## 필수 원칙
- **고칠 파일은 반드시 main 최신본을 받아서 고친다.** 기억·예전 대화·옛 첨부 파일로 고치지 않는다. 옛 파일로 덮어쓰면 6. Update 승인 알림에 🚨 덮어쓰기 경고가 뜬다.
- 사용자가 직접 staging 에 업로드 → 6. Update 새 알림 ✅ 승인. 지시 없는 push/서버 적용 금지.
- 기존 전략·종목·금액·enabled 보존. 실주문/강제매도/자동환전으로 테스트하지 않는다. 1·2번 봇은 원작자 버전 그대로(최소한의 표시된 연결만).
- 비밀키/토큰 원문 출력 금지. 미기록 변경 보존, 강제 reset/push로 해결하지 않는다.
- 코드를 고치면 파일 머리말 버전도 올린다. 봇 폴더 버전(CHANGELOG·태그·텔레그램 표시)은 업데이트 비서가 자동으로 매기며, bot_office 파일 머리말의 변경 기록은 그 번호('사무실 vX.Y.Z')를 쓴다.
- 서버 명령은 폰에서 한 번에 붙여넣을 수 있는 한 덩어리(20KB 미만)로 준다. 사용자는 초보자 기준으로 자세히 안내.
- 시간: 봇 일정 KST, 미국장 America/New_York, 서버 UTC, 사용자 현지 UTC+8. 과거 로그를 현재 상태로 단정하지 않는다.

## 문서 3종 — 누가 무엇을 고치나
| 종류 | 위치 | 고치는 쪽 |
|---|---|---|
| 현재 상태 | STATUS.md | 업데이트 비서만 (손으로 고치지 않음) |
| 규칙·구성 | START.md · docs/handoff/*.md | 규칙·구성이 바뀔 때 해당 항목만 |
| 작업 기록 | docs/log/날짜_AI_작업.md | 작업마다 **새 파일** (남의 기록은 고치지 않음) |
- 과거 자료는 docs/archive/ (예전 Total rule.md·메모 txt). 필요할 때 검색만 하고 새 내용을 더하지 않는다.
- 문서도 staging 에 올리고 승인한다 (문서만 바뀌면 봇 재시작 없음).

## 필요한 문서만 선택
| 이번 작업 | 상세 경로 |
|---|---|
| 공통 규칙·업로드·문서관리 | docs/handoff/00_rules.md |
| 1 한투 라오어 | docs/handoff/01_hantu.md |
| 2 토스 스나이퍼 | docs/handoff/02_sniper.md |
| 3 토스 스마트적립 | docs/handoff/03_toss_dca.md |
| 4 빗썸 스마트적립 | docs/handoff/04_bithumb.md |
| 사무실·잔액·브리핑·PC 감시 | docs/handoff/05_office.md |
| 업데이트·일시중지·STATUS | docs/handoff/06_updater.md |
| 서버·서비스·시간 | docs/handoff/07_server.md |
| Gemini 판독·비용 | docs/handoff/08_gemini.md |
| 가격·지역 비교·Gbuts | docs/handoff/09_prices.md |
| 팬딩 자동주문·5번 버튼 메뉴 | docs/handoff/10_fanding.md |

## 읽기 방법
- 상세 문서는 제목/키워드 검색 → 관련 범위만 읽는다. 관련 없으면 전체 저장소 점검 금지.
- 문서와 STATUS.md 가 다르면 STATUS.md(서버 실제 상태)를 믿고, 다른 점을 docs/log 기록에 남긴다.
- 검사 통과를 서버 배포 완료로 바꾸어 쓰지 않는다 (파일 작성 / 업로드 / 승인·적용 / 실제 확인을 구분).
