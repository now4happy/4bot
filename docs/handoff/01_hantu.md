# 1번 한투 라오어

갱신: 2026-10-26. 기존 기록을 분리한 문서이며 새 서버 적용의 증거가 아니다.
필수 작업 원칙은 저장소 루트 START.md를 따른다. 아래에서 이번 작업과 관련된 제목만 읽는다.

### 5.1 1번 한투 라오어봇

- 역할·서비스·실행 경로는 확인됨.
- 실제 라오어 전략의 매수·매도 계산, 물타기, 손절, 투자 한도, 주문 유형, 중복 방지 상세는 최신 코드 미확인.
- 업데이트 비서는 미국 현지 평일 09:25~16:05에 1번 업데이트를 차단하는 코드가 있었다. 이것을 실제 주문 가능 시간으로 혼동하지 않는다.

### 7.1 1번 폴더 분리

- 목적: 홈 루트의 코드와 구분해 독립 관리.
- `90-hantu-folder.conf`로 ExecStart의 main.py 경로만 새 폴더로 변경.
- 이미 override가 있어 중복 생성 시 중단한 뒤 현재 설정·프로세스를 조회.
- 결과: 새 경로 실행·active/running·텔레그램 응답 확인.

### 7.7 1번 원작자 비교 업데이트 및 직접 관리 제외

- 사용자가 보낸 /update의 ‘자가 업데이트 해제: 직접 관리 모드’ 응답은 이전 plugin_updater의 하드코딩된 차단 문구였다. 이후 원작자 비교 방식으로 수정됐고 이번 최신 main에서 구현과 han4384tubot-v1.0.1 기록을 확인했다. 현재 서버 /update 실응답은 아직 새로 받지 않았다.
- 원작 https://github.com/pipios4006-boop/KIS-API-Python-Trading-Bot-Example . 앞선 비교 기준 8a39992(V97.40): 로컬 .py 중 기존 차단 updater만 차이가 있었고, 원작 전용 main2/mergy/rescue_bot/scheduler/scheduler_trade는 사용 import가 아니었다.
- 원작의 git reset --hard는 홈 전체 4bot에 영향을 주므로 사용하지 않는다. 원작 zip 최상위 .py 바이트 비교 → 다른 파일만 사전 컴파일 → stable_backup/임시파일+os.replace → 실패 원복. 새 원작 파일은 실제 import가 필요할 때만 추가. .env/장부/설정은 건드리지 않는다.
- telegram_commands.py/callback_config_handler.py는 같으면 ‘이미 최신’ 안내만 하고 재시작하지 않으며 변경이 있으면 기존 재가동 흐름을 따른다. 원작 보호구간 15:26~16:10 미국 현지 시간과 별도 6번 업데이트 비서 보호구간을 구분한다. 기존 UI의 ‘로컬 코드 초기화’ 설명은 오래된 문구다.
- 직접 관리 제외 목록 MANAGED_FILES는 기존 plugin_updater.py/telegram_commands.py/callback_config_handler.py 3개였다. 이번 주문 차단을 보존하려고 **deployment_gate.py와 kis_api_client.py도 제외에 추가**했다. 원작이 이 파일들을 바꾸면 로컬 차단 연결을 유지하며 수동 비교해야 한다. 다른 전략 파일을 임의 제외하지 않는다.
- 앞선 검증은 실제 원작 zip을 임시폴더에서 비교해 동일/변경/재실행/제외/문법실패/새 import/불필요 파일/보호시간을 검사한 이력이다. 이번에는 원작 파일을 새로 서버에 적용하거나 실주문하지 않았다.

## 실행 및 신규 주문 차단의 현재 상태

- 실행 `/home/gieokkim/hantu_laoer/main.py`, 서비스 han4384tubot.service. 홈 루트 중복 코드와 구분한다. 데이터/설정/venv를 전부 옮긴 것은 아니다.
- 원작자 비교 updater는 마지막 확인 main c2bb1c2에 반영. 현재 서버 /update 실응답은 새로 확인하지 않았다.
- 업데이트용 중지 부품은 로컬 작성/검증 단계이며 서버 적용 미확인. 전체 의미/설치 순서는 06_updater.md의 ‘확정 동작’·‘처음 설치하는 순서’를 필요한 경우만 읽는다.
- 첫 설치 파일3개: hantu_laoer/deployment_gate.py, kis_api_client.py, plugin_updater.py. 원작자 자동 비교 제외 목록에 gate와 kis_api_client를 보강한 것은 이 미배포 수정안이다.
