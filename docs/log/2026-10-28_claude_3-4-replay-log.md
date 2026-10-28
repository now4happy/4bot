# 3·4번 봇 재생 로그 (start.md 규칙 적용 · 묶음 L1)
- 상태: **완료(파일 작성·로컬 검사까지)** — 시작 2026-10-28 09:50 KST (00:50 UTC) · 완료 09:57 KST (00:57 UTC)
- 업로드·승인·서버 적용·실제 로그 확인: 아직 (사용자 진행)
- AI / 기기: Claude / 사용자 태블릿
- 기준: main 9af5614 (start.md 추가 직후). 읽은 문서: START.md, start.md, STATUS.md(09:19 KST), docs/handoff/03_toss_dca.md
- 범위: toss_dca_bot/, bithumb_laoeo_bot/ 만. 다른 폴더·팬딩·1·2번 봇은 건드리지 않음.
- 다른 AI 진행중 작업: docs/log 에 '진행중' 표시 없음. 3번 마지막 변경 10-27, 4번 10-22 → 같은 파일 겹침 없음.

## 바꾼 파일
- `toss_dca_bot/replay_log.py` (새 파일), `toss_dca_bot/t_core.py` (BOT_VERSION v4.3.5), `toss_dca_bot/main.py`
- `bithumb_laoeo_bot/replay_log.py` (새 파일, 3번과 같은 내용), `bithumb_laoeo_bot/b_core.py` (BOT_VERSION v4.0.4), `bithumb_laoeo_bot/main.py`
- `docs/handoff/03_toss_dca.md`, `docs/handoff/04_bithumb.md` — '재생 로그' 절 추가

## 무엇을 바꿨나 (start.md 2·3·4절)
- 5종 이벤트를 한 줄 JSON 으로: user_event(버튼·메시지) / decision(매매 판단·건너뜀 이유) / external_call(주문·API 실패) / state_change(설정·일차 변경, 시작·종료) / user_visible(보낸·고친 메시지, 실패 코드).
- 시간은 ts_utc 저장 + ts_kst 표시. correlation_id 로 버튼 → 판단 → 주문 → 보낸 메시지 연결.
- 금액·종목·수량·주문 응답·메시지 본문은 감사 로그(권한 600)에만, 일반 로그엔 참조값과 audit_ref.
- 반복 성공은 10분 요약, 같은 오류는 1시간 전문 1번 + 횟수 요약, 건너뜀 이유는 하루 1번.
- 매매 조건·주문 순서·금액·종목·enabled 는 바꾸지 않음 (기록 줄만 추가). 1·2번 봇, 사무실, 팬딩은 건드리지 않음.

## 검증 (로컬, 실제 주문·네트워크 없음)
- 원본(main) vs 수정본을 가짜 토스·빗썸·텔레그램으로 같은 상황에 돌려 비교:
  3번 12종목 시나리오(익절·매수·분할매도·정지·결정대기·달러부족·주문 응답 없음·주문 거절·보유 0 제거 + 버튼·입력 7건) → 주문 9건·설정 파일·실패 사유·보낸 메시지 **동일**(버전 표시만 다름).
  4번 5코인 시나리오(익절·매수·원화부족·주문 400·응답 없음 + 버튼·입력 8건) → 주문 5건·설정·상태(시각 제외)·거래내역·보낸 메시지 **동일**(버전 표시만 다름).
- start.md 5절 재생: 시나리오 1(버튼 → 주문 → 사용자에게 보임)을 `replay_log.py tg-903`, 시나리오 2(스케줄러 건너뜀 이유)를 `sch-kr-…-2` 로 로그만으로 재생 → 통과.
- `replay_log.py --scan`(토큰·긴 숫자·내부 경로) 두 봇 통과. 감사 로그 권한 600 확인. 종료 신호 → service_stop 기록 후 바로 종료(코드 0) 확인. Python 3.11 문법 검사 통과.

## 남은 일
- 체결 확인(fill)·취소 확인은 봇이 하지 않음 → 주문 체인은 '발주'까지만 재생 가능 (start.md P0-4 일부 남음).
- 토스 주문 응답의 주문 식별자 키 이름 미확정 → 실제 첫 주문 뒤 `broker_id_found` 값 확인 필요.
- 4번 b_core.py 에 텔레그램 채팅 식별자 기본값이 코드에 적혀 있음 (start.md 4절 위반 소지). 서버 환경변수 확인 뒤 빼는 것을 별도 작업으로.
- 이 작업 전 기록 `2026-10-28_claude_로깅계획-로그분석.md` 는 95d1717 '이전 변경 정리' 때 main 에서 빠졌음 (내용은 start.md 6절에 대부분 반영됨).

## 다음 AI가 읽을 파일
- start.md 0·2·4·5절, docs/handoff/03_toss_dca.md·04_bithumb.md '재생 로그' 절, 이 기록.
