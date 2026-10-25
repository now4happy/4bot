# 서버·서비스·시간·운영 확인

갱신: 2026-10-26. 기존 기록을 분리한 문서이며 새 서버 적용의 증거가 아니다.
필수 작업 원칙은 저장소 루트 START.md를 따른다. 아래에서 이번 작업과 관련된 제목만 읽는다.

## 6. 서버 운영·마지막 확인 상태

### 6.1 환경과 스냅샷

과거 서버 스냅샷(실시간 상태 아님):
- 과거 24.04.5 판독은 정정됨. 2026-10-25 사용자 화면은 Ubuntu **22.04.5 LTS**, 커널 6.8.0-1070-gcp.
- 루트 사용률 80.8% / 약 9.51GB.
- 메모리 사용률 44%, 스왑 사용률 29%, 시스템 load 0.0, 프로세스 120 표시.
- 이는 그 순간의 로그인 화면 값이며 현재 상태가 아니다.

개별 서비스 마지막 확인:
- 1번: 이전 폴더 전환 점검에서 active/running, NRestarts=0, 새 main.py 실행 및 텔레그램 응답 확인. 정확한 현재 상태는 미확인.
- 2번: 원작자 연결 점검·거래 시간 확대는 사용자 완료 보고. 최신 서비스 상태·실제 주문 로그 미확인.
- 3번: QLD 상세·중지 화면 2026-10-24 약 10:41에 표시 확인. 신규 목록 개선 재시작 성공은 미확인.
- 4번: 이 대화 후반의 개별 active 확인 자료 없음.
- 5번: 브리핑 수정·unit 조회 이력 있음. 2026-10-24 업데이트 알림이 5번 v1.0.13 완료로 표시했으나 업데이트 비서 자체 변경을 포함하므로 사무실의 모든 기능 정상 증거는 아님.
- 6번: 2026-10-24 12:37 텔레그램 “업데이트 완료”, GitHub main 업로드 완료, 이어서 “업데이트 비서 새 버전 정상 작동 확인” 표시. 마지막으로 확인된 실제 정상 기동 증거.

### 6.2 하루 한 번 서버 관리

- 스크립트 `/usr/local/sbin/bot-server-care`.
- unit `/etc/systemd/system/bot-server-care.service`, `.timer`.
- 매일 08:55 Asia/Seoul, AccuracySec=1min, Persistent=false.
- Type=oneshot, Nice=19, IOSchedulingClass=idle, TimeoutStartSec=120.
- `journalctl --vacuum-time=14d --vacuum-size=200M`, `apt-get -o DPkg::Lock::Timeout=10 clean`.
- 디스크·메모리·실패한 서비스 조회 결과 출력.
- 봇 재시작, 거래기록 삭제, 자동 패키지 업그레이드는 포함하지 않음.
- 예약 enable과 다음 실행 시각 표시까지 실제 확인. 최초 정리 실행 성공 결과는 이 대화에서 최종 확인되지 않음.
- 기존 임시파일 정리·로그 순환 타이머가 있어 중복 대규모 작업은 피했다. 기존 타이머별 최신 상세는 미확인.

### 6.3 브리핑

- 실제 확인한 `bot-office-briefing.timer`: 한국시간 오전 09:00, 오후 16:30.
- 사용자는 오전 7시 제거를 요청했으나 실제 타이머에는 7시 예약이 없고 설명 문자열에 오래된 시간이 남아 있었음.
- 타이머 Description을 09:00/16:30 KST로 수정하는 명령을 제공했다. 설명 수정 자체의 최종 출력 확인은 제한적.
- `office_briefing.py`에 `section_server_care()`를 추가해 오전(`kst.hour < 12`) 브리핑 상단에 관리 결과, 마지막 시작 시각, 디스크, 가용 메모리/스왑, 실패 서비스 수 표시하도록 수정.
- 파일 저장·문법 검사·함수 출력은 확인.
- 미실행 서비스의 시작 시각 `n/a`가 성공으로 표시되는 문제를 발견해 “첫 실행 대기” 처리 수정 명령 제공. 그 마지막 수정의 별도 실행 증거와 실제 9시 전송 결과는 미확인.
- 07:00/19:00이라는 다른 파일 주석은 오래된 설명일 수 있음. 현재 확정 예약으로 되살리지 않는다.

### 6.4 로그와 알려진 운영 이슈

- systemd 로그는 `journalctl -u <unit>`로 조회했다. 앱별 자체 로그 파일 경로는 미확인.
- 서버에 `rg`가 없어 이전 SSH 조회가 실패한 적 있음. 서버에서는 설치 없이 grep/sed/python 대안 사용.
- 1번 로그의 숫자 409 한 번을 텔레그램 충돌로 단정하지 않았고, 후속 충돌/인증 단서 0·단일 프로세스·답장 정상 확인.
- 사무실 터널 과거 화면에 origin 접속 실패·EOF와 cloudflared 버전 경고가 있었으나 해결 여부 미확인. 이것을 이번 Git 업데이트 오류 원인으로 연결하지 않는다.

## 실행 확인에 필요한 경로만

- Google Cloud VM 1대, systemd. 과거 스냅샷은 실시간 건강 상태가 아니다.
- 1 han4384tubot.service, 2 toss_sniper.service, 3 toss_dca.service, 4 bithumb_bot.service. 실행 본문은 각각 01~04 문서에 있다.
- 사무실 /opt/bot-office; bot-office.service, bot-office-secretary.service, bot-office-briefing.service/.timer. 업데이트 bot-updater.service.
- /etc/bot-office/telegram.json은 token/chat_id를 읽는 위치이며 비밀 원문을 출력하지 않는다.
- updater 기본 U_REPO=/home/gieokkim, U_TARGETS=/var/lib/bot-office-deploy/targets.json, U_STATE=/var/lib/bot-updater/state.json, U_OFFICE=/opt/bot-office, U_EVERY=300, guard U_GRACE=120초.
- 원격 main에서 2026-10-25까지 브리핑 주말/휴장 처리 코드 반영 확인. 실제 다음 예약 전송 결과는 아직 미확인. 오래된 07:00/19:00 주석을 현재 타이머로 되살리지 않는다.
- 관련 서비스/시간 범위만 조회한다. 전체 환경변수·키 파일·전체 저널을 채팅에 덤프하지 않는다.
