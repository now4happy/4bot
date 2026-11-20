#!/usr/bin/env python3
# 사무실 v1.9.5 (2026-11-20, audit-fix-v2 9-1·9-2): ① CHANGELOG 기록 실패가 커밋·태그·푸시를 막지 않고 보고만(write_changelog) ② main 푸시가 성공했을 때만 staging 을 맞춤(push_main_then_staging)
# 사무실 v1.9.4 (2026-11-20): 9번 브리핑(briefing/) 연결 — ① briefing/ 하위 폴더(sources/·systemd/)까지 9번 브리핑 소속으로 분류 (.py·.json·.service·.timer, tests/·test_* 제외) · 이름 '9번 브리핑'
#                       ② 재시작 목록에서 BRIEFING_KEY 제외 (briefing 은 서비스가 아니라 one-shot 이라, 재시작하면 텔레그램 브리핑이 의도치 않게 발송됨)
#                       ③ briefing/ 파일을 /opt/bot-office/briefing/ 으로 폴더 구조 그대로 복사 (briefing_deploy · 백업·되돌림은 사무실 파일과 같은 방식 · systemd/ 유닛은 복사 안 함=수동 설치) · CHANGELOG·태그는 briefing-vX.Y.Z · 전략·종목·금액·enabled 변경 없음
# 사무실 v1.9.3 (2026-11-19, 방 updater-redesign-sniper-separate 판 2): 업데이트 봇 재설계 1단계 — ① 2번 스나이퍼를 적용 대상에서 제외(classify 무시·두 전체 검사에서 경로 제외·병합 때 스나이퍼 파일 그대로 둠 · NAMES·원작 알림·매일 STATUS·sniper_tiers는 유지)
#                       ② A: 저장 안 된 변경 검사를 이번에 바뀌는 봇 폴더 + 공용 파일로 한정 ③ B: 서버에만 있는 수정과 겹치는 봇만 '앞섬, 사람 승인 필요'로 보류
#                       ④ D: 매매 중·일시중지 대기·앞섬인 봇만 보류하고 나머지는 적용 (보류 목록·경과일은 STATUS, 사유가 풀리면 자동 재시도)
#                       ⑤ 원작자 새 커밋 알림 때 2번 자동 업뎃(원작 직접 동기화만 · 재시작 항상 · 건강 확인 실패 시 자동 되돌림) — 본체는 sniper_upstream.py
#                       · 판 2 v2 고침: 전부 보류일 때도 보류 목록에 기록(적용은 안 함) · 2번 동기화 명령은 스나이퍼 자체 CLI(plugin_updater.py --base-dir) 기본값
#                       · 스위치 U_SCOPED_CHECKS=0 이면 ①~④ 전부 예전 동작(저장소 전체 검사·전체 중단)으로 복귀 · 9번 첫 화면(메뉴 3차)은 그대로
# 사무실 v1.9.1 (2026-11-19, 방 telegram-bot-menu-review 3차): 9번 첫 화면 4칸 [업데이트 확인 | 거래 상태 | 유지보수 | 도움말] — 충돌 정리·상태 기록·원작 확인은 유지보수 안 · 단순 이모티콘 제거(예전 키보드 글자도 같은 버튼으로 읽음) · 업데이트 적용·일시중지·재개 동작 불변
# 사무실 v1.9.0 (2026-11-17): live-board 브랜치를 업데이트 알림 대상에서 제외 — 보드용 고아 브랜치가 1분마다 커밋을 올려 매번 새 업데이트 알림이 뜨던 폭주 수정 (음수 refspec 가드와 별개로 코드에서도 제외)
# 사무실 v1.8.8 (2026-11-15): 한 달 무인 운영 대비 — ① 매일 06:10 STATUS 기록 때 대상 서비스·상시 서비스의 실행(is-active)·부팅 자동시작(is-enabled)을 확인해
#                       문제가 있으면 8번 방(alert-hub 긴급)으로 즉시 알림 ② STATUS 기록이 같은 이유로 이틀 연속 건너뛰어지면 하루 1번 긴급 알림
#                       ③ 서버가 GitHub main 보다 앞선 커밋이 2번 원작 자동 동기화(sniper: upstream … direct sync)뿐이고 staging 대기도 없으면 main·staging 에 그대로 올림(빨리감기만, 강제 없음)
#                       ④ alert-hub 설치 판정에서 폐기된 watchdog cron 조건 제거 · 설치 cron 에 watchdog 줄 안 씀 ⑤ captures/ 브랜치는 업데이트 알림 대상에서 제외
#                       · 전략·종목·금액·enabled·승인·적용 흐름 변경 없음
# 사무실 v1.8.7 (2026-11-14): 웹 사무실 완전 제거 — 웹 서비스 재시작·의도적 중단 건너뜀·웹 healthz 대리 신호·터널 상태 줄 삭제,
#                       bot_office/ 분류 뿌리는 서비스가 아닌 폴더 키 OFFICE_KEY('bot-office')로 유지 (태그·CHANGELOG·/opt/bot-office 복사 그대로,
#                       재시작 없음 · 비서·팬딩은 OFFICE_EXTRA 로만 재시작) · 8번 비서 표시 '8번 비서(SGOV)' · 전략·종목·금액·enabled 변경 없음
# 사무실 v1.8.6 (2026-11-14): 봇 이름·번호 새 1~9번 목록으로 표시 문자열만 정리 (전략·종목·금액·enabled 그대로)
# 사무실 v1.8.5 (2026-11-14): 웹 서버 끄기 준비 — ① 의도적 중단 표시 파일(/var/lib/bot-office/intentional_stop)이 있으면
#                       사무실 웹 서비스(bot-office.service)는 재시작·정상 확인(healthy)·enable 을 건너뜀 (로그 '의도적 중단, 재시작 건너뜀')
#                       · 건너뜀은 성공으로 셈 (되돌림 없음) · 완료 알림에 '의도적 중단 — 재시작 건너뜀' 줄 따로 표시
#                       · 'inactive' 상태만으로는 의도적 중단으로 보지 않음 (고장과 구별이 안 되므로) · 다른 서비스 재시작·enable 규칙은 그대로
#                       ② HUB_BOT_NAMES 에서 웹 사무실 항목 제거 (새로 설치할 때 .env 를 채우는 값 · 이미 있는 서버 .env 는 안 바꿈)
# 사무실 v1.8.1 (2026-11-13): 옛(리베이스 전) 브랜치 되풀이 알림·충돌 방지 — ① 알림에 '서버보다 N개 뒤처짐'·'지금 적용하면 충돌할 파일'(git merge-tree, 미리 보기만) 표시
#                       ② 같은 수정(제목+작성 시각 같음)이 이미 서버 HEAD나 다른 대기 브랜치에 있으면 '♻️ 옛 브랜치' 안내 + [🗑 옛 브랜치 지우기] 버튼
#                          (누를 때 다시 확인 · 백업 태그 updater-backup/superseded-… 와 삭제를 한 번에 · 자동 삭제 없음 · main·staging 은 못 지움)
#                       ③ '업데이트 확인'에서 알림을 다시 보냈는데도 '새로 올라온 수정이 없습니다'가 같이 뜨던 것 고침
#                       ④ NAMES 의 meritz_dca.service 중복 키 정리 — 뒤 항목 '메리츠 적립'이 '3번 메리츠 적립'을 덮어쓰던 것
#                       · 안전장치(버전 역전·되돌림 감지·dirty 검사·main 앞섬 검사·병합 실패 시 abort)는 그대로
# 사무실 v1.8.0 (2026-11-13): 3번 메리츠 적립 표시 및 서비스 연결 정리
# 사무실 v1.7.5 (2026-11-13): 배포에서 빠진 파일은 막지 않고 넘김 — classify()가 (units, skipped) 반환, 테스트·점파일 등은 알림에 '⏭️ 배포에서 빠진 파일'로만 표시 (✅·중지 버튼 항상 표시, apply·중지 요청 거부 안 함)
# 사무실 v1.7.2 (2026-11-13): 서버 미저장 변경 중단 안내에서 'Claude나 Gemini에게 확인을 요청해 주세요.' 문구 제거
# 사무실 v1.6.9 (2026-11-12): 재시작 때 실행 중인 서비스는 enable도 같이 함 — 재부팅 뒤에도 살아남게 (7번 비서 재발 방지)
# 사무실 v1.6.5 (2026-11-11): dirty 검사에서 생성 상태 파일(need.json·sniper_tiers.json) 제외 — 브리핑이 매번 다시 써서 업데이트가 멈추던 것 수정
# 사무실 v1.5.6 (2026-11-10): 2번 스나이퍼 버전은 코드 머리말 버전으로 기록 (태그 카운터 v1.2.3 대신 v2.5.2식) — 머리말 없으면 기존 next_tag 유지
# 사무실 v1.5.0 (2026-11-09): need.json 상태 업로드 경로 추가
# BOT_UPDATER_V2 — GitHub에 올라온 수정(main 이외의 브랜치)을 감지 → 텔레그램 [✅ 업데이트] 버튼 → 안전 확인 후 적용
#  · Gemini/Jules/딥시크 등 누가 올려도 main 이 아닌 브랜치면 감지 (main 은 서버가 적용한 결과만 올라가는 곳)
#  · 1~4번 봇 + 5번 사무실 비서(저장소 bot_office/ → 서버 /opt/bot-office) · 업데이트 비서 자신도 업데이트(실패 시 2분 뒤 자동 복구)
#  · 적용: 보유·매매시간 확인 → 병합 → 문법 검사 → 해당 봇만 재시작 → 실패 시 원래 코드로 자동 복구 → 버전 기록 → main 업로드
#  · 사무실 v1.0.43 (2026-10-28): 사무실에 새로 추가되는 파일은 server.py 와 같은 주인·그룹·권한으로 복사 (있던 파일은 원래 권한 유지)
#  · 사무실 v1.0.44 (2026-10-28): 되돌림 감지 — 올라온 파일이 최근 14일 안의 다른 수정을 지우거나 버전이 더 낮으면 알림에 경고
#  · 사무실 v1.0.46 (2026-10-28): 저장소 맨 위 STATUS.md 자동 작성 — 업데이트 적용 때마다 + 하루 1번(06:10 KST, 대기 중인 업로드 없을 때)
#                       봇별 버전·서비스 상태·최근 적용·대기 업데이트. 사람·AI 는 읽기만 (손으로 고치지 않음)
#                       · 버전 표기 통일: 이 파일의 변경 기록도 텔레그램·CHANGELOG 와 같은 '사무실 vX.Y.Z' 번호를 씀
#  · 사무실 v1.0.47 (2026-10-28): 버전 자동 기입 — 올린 파일에 'v'+'NEXT'(붙여 쓴 글자)를 적어 두면 승인 때 정해진 실제 번호(예: v1.0.48)로 바꿔 기록
#                       (승인 순서에 따라 번호가 밀려도 파일 머리말·CHANGELOG·텔레그램 번호가 항상 같음)
#  · 사무실 v1.0.48 (2026-10-28): office_url.py(사무실 주소 관리)가 바뀌면 7번 비서도 재시작
#  · 사무실 v1.0.49 (2026-10-28): ① 2번 원작자 새 버전 알림 다시 켬 (sniper_upstream.py · 알림 전용, 자동 합치기 없음)
#                       ② 버전 자동 기입 고침 — v1.0.48 적용 때 이 파일 속 표시 글자까지 바뀌어 기능이 꺼져 있었음
#                          (표시 글자를 코드에 직접 쓰지 않고 조립해서 다시는 안 바뀌게)
#                       ③ sniper_upstream.py 가 바뀌면 업데이트 비서만 재시작 (사무실 서비스는 재시작 안 함)
#  · 사무실 v1.0.54 (2026-10-28): ① 한글 파일명 문서가 '허용되지 않은 파일'로 거부되던 것 고침 (git 경로 따옴표·8진수 표기 끔)
#                       ② GitHub main 에 서버를 거치지 않은 수정이 있으면 알림 1번 + 그 수정이 빠진 브랜치는 적용 전에 멈춤
#                       ③ 충돌 정리 '서버 HEAD≠main' 안내를 main 앞섬/서버 앞섬/갈라짐으로 나눠 할 일까지 표시 (update_conflicts.py)
#  · 사무실 v1.0.55 (2026-10-28): ① 사무실 파일 읽기 권한 자동 정리 — 이미 있던 파일도 웹서버(server.py 와 같은 그룹)가 읽을 수 있게
#                          (pixel_office.html 이 관리자 전용 권한으로 남아 로그인 뒤 첫 화면이 끊김 · pc_monitor.py 502 와 같은 원인)
#                          주인은 바꾸지 않고, 그룹 쓰기 권한은 주지 않음 · 적용 때마다 /opt/bot-office 전체를 한 번 훑어 고침
#                       ② STATUS.md 를 쓸 때 사무실 상황판용 복사본 /var/lib/bot-office/status.md (읽기 전용 0644) 도 남김
#  · 사무실 v1.0.64 (2026-10-29): 7번 비서 재시작 목록에서 fanding_trade.py 제외 — 비서는 팬딩 코드를 쓰지 않음(10-26 V4에서 분리).
#                       팬딩 파일이 바뀌어도 비서를 괜히 다시 시작하지 않음 (5번 팬딩 서비스는 그대로 다시 시작)
#  · 사무실 v1.0.80 (2026-11-01): alert-hub/ 폴더 파일은 업데이터 적용 대상이 아니므로 classify에서 거부하지 않고 넘김
#                       (보관만, 실제 설치는 서버 직접 — 다른 봇 업데이트가 같이 막히지 않게 함)
#  · 사무실 v1.0.81 (2026-11-01): 업데이터 시작 때 alert-hub가 설치 안 돼 있으면 자동 설치 시도
#                       (venv·.env·테스트·cron, 기존 .env·cron은 건드리지 않음, 실패해도 봇 업데이트는 계속)
#  · 사무실 v1.0.82 (2026-11-01): hub 자동 설치의 unittest를 hub 폴더 안에서 실행하도록 고침
#                       (절대 경로 -s/-t 조합은 tests 폴더를 import할 수 없어 실패했음)
#  · 사무실 v1.1.0 (2026-11-01): alert-hub 연동 1차 — 전 봇 하트비트 + 사무실·팬딩 자율 알림 hub 복사 (기존 전송·매매 로직 무변경)
#  · 사무실 v1.0.82 (2026-11-01): 버전 숫자 최대 9 굴림 — 마지막 숫자가 9를 넘으면 중간을 올리고 마지막을 0으로
#                       (예: 1.0.81 다음은 1.1.0, 1.1.9 다음은 1.2.0, 1.9.9 다음은 2.0.0)
#  · 사무실 v1.1.1 (2026-11-01): watchdog 무소식 경고 대응 — ① 업데이터 시작 때마다(이미 설치돼 있어도) hub 데이터 폴더 0777,
#                       hub.db·hub.db-wal·hub.db-shm 0666 으로 정리 (다른 계정으로 도는 봇도 신호를 쓸 수 있게 · best-effort · 예외 없음)
#                       ② 8번 사무실 비서 대리 신호 — 사무실 웹(127.0.0.1:8765/healthz)이 200이면 60초에 1번 hub에 신호
#                          (bot-office.service 의 ProtectHome 보호로 server.py 가 hub 폴더를 못 볼 수 있어서 · 웹 코드·유닛 무변경)
#  · 사무실 v1.4.4 (2026-11-07): 하단 메뉴 2개 [🔄 업데이트 확인 | ☰ 메뉴] — 나머지 버튼은 ☰ 메뉴 안(menu_sub_keyboard) · ⬅ 처음 화면
#                       '메뉴'·'/menu' = 하위 메뉴 펼치기 · /start·/help·도움말·? = 사용법 + 처음 2개 (버튼 글자·명령 그대로)
#  · 사무실 v1.4.6 (2026-11-08): ① .gitignore·*.example.json은 저장소 전용 문서라 classify에서 거부하지 않고 넘김
#                       (alert-hub와 같은 방식 — 서버 적용 대상이 아님, 같이 묶인 다른 봇 업데이트가 막히지 않게 함)
#                       ② NAMES에 meritz_laoer.service 추가 (메리츠 SOXL 무매) — targets.json 등록 뒤 적용 가능
#  · 사무실 v1.4.7: NAMES에 meritz_dca.service 추가 (메리츠 적립) — targets.json 등록 뒤 적용 가능
#  · 사무실 v1.4.8 (2026-11-09): STATUS.md 기록 시 스나이퍼 층별 공개 JSON 동시 생성·업로드 (실패 격리)
#  · 2번 스나이퍼: 원작자 새 버전 하루 1번(09:02 KST) 확인 → 🔴 중요 알림 (sniper_upstream.py · 알림 전용) · 6. Update 에 '원작 확인'
import json, os, pwd, re, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# --- alert-hub: 기존 전송은 그대로, 자율 알림만 hub DB에 복사 (실패해도 봇은 계속) ---
try:
    import sys as _hub_sys
    _HUB_ROOT = "/home/gieokkim/alert-hub"
    if _HUB_ROOT not in _hub_sys.path:
        _hub_sys.path.insert(0, _HUB_ROOT)
    from alert_hub.notify import heartbeat as _hub_heartbeat, notify as _hub_notify
except Exception:
    _hub_heartbeat = None
    _hub_notify = None

def _hub_beat(bot):
    try:
        if _hub_heartbeat:
            _hub_heartbeat(bot)
    except Exception:
        pass

def _hub_alert(bot, level, text):
    try:
        if _hub_notify:
            import re as _hub_re
            _hub_notify(bot, level, _hub_re.sub(r"<[^>]+>", "", str(text)))
    except Exception:
        pass
 
REPO = os.environ.get("U_REPO", "/home/gieokkim")
TG_CFG = os.environ.get("U_TG", "/etc/bot-office/telegram.json")
TARGETS = os.environ.get("U_TARGETS", "/var/lib/bot-office-deploy/targets.json")
STATE = os.environ.get("U_STATE", "/var/lib/bot-updater/state.json")
OFFICE_DIR = os.environ.get("U_OFFICE", "/opt/bot-office")
SELF_UNIT, SELF_FILE = "bot-updater.service", "bot_updater.py"
# v1.8.7: 저장소 bot_office/ ↔ 서버 /opt/bot-office 묶음의 키 — systemd 서비스가 아님 (웹 사무실 삭제). 재시작하지 않고
#   태그(bot-office-vX.Y.Z)·CHANGELOG(bot_office/CHANGELOG.md)·복사(office_deploy)에만 씀. 비서·팬딩·업데이터 재시작은 아래 OFFICE_EXTRA·SELF_FILE 로
OFFICE_KEY, OFFICE_NAME = "bot-office", "사무실 파일(bot_office)"
# 사무실 폴더(/opt/bot-office)에서 따로 도는 상시 서비스 — 그 파일이 바뀌면 이 서비스도 다시 시작해야 새 코드가 반영됨
SECRETARY_UNIT, FANDING_UNIT = "bot-office-secretary.service", "bot-office-fanding.service"
OFFICE_EXTRA = {SECRETARY_UNIT: ("office_secretary.py", "office_sgov.py", "gemini_usage.py", "meritz_client.py", "toss_token_share.py"),
                FANDING_UNIT: ("fanding_trade.py", "fanding_vr6.py", "meritz_client.py", "gemini_usage.py")}
OFFICE_EXT = (".py", ".html", ".css", ".js")
# 9번 브리핑(briefing/ 패키지, one-shot): 서비스 유닛이 없어 재시작 대상 없음. 키는 systemd 서비스 이름이 아니다
#   (briefing.service 는 타이머용 유닛이라, 키로 쓰면 '재시작'이 곧 텔레그램 발송이 된다).
BRIEFING_KEY, BRIEFING_EXT = "briefing", (".py", ".json", ".service", ".timer")
SYSTEMCTL = os.environ.get("U_SYSTEMCTL", "systemctl")
TG_API = os.environ.get("U_TG_API", "https://api.telegram.org")
CHECK_EVERY = int(os.environ.get("U_EVERY", "300"))
KST, ET = ZoneInfo("Asia/Seoul"), ZoneInfo("America/New_York")
NAMES = {"han4384tubot.service": "1번 한투 라오어", "toss_sniper.service": "2번 토스 스나이퍼",
         "meritz_dca.service": "6번 메리츠 적립", "bithumb_bot.service": "3번 빗썸 적립",
         "meritz_laoer.service": "7번 메리츠 속쓸 적립봇",
         BRIEFING_KEY: "9번 브리핑"}
SECRET_RE = re.compile(r"(\d{8,10}:[A-Za-z0-9_-]{30,}|ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|AIza[0-9A-Za-z_-]{30,}|-----BEGIN [A-Z ]*PRIVATE KEY|sk-[A-Za-z0-9]{20,})")
# --- 사무실 v1.9.3: 스나이퍼 제외 + 봇별 검사·보류 ---
SNIPER_UNIT, SNIPER_DIR = "toss_sniper.service", "toss_sniper"
SCOPED = os.environ.get("U_SCOPED_CHECKS", "1") != "0"   # 스위치 1개: 0 이면 스나이퍼 제외·A·B·D 전부 끄고 예전 동작(저장소 전체 검사·전체 중단)
HOLDS = os.environ.get("U_HOLDS", "/var/lib/bot-updater/holds.json")   # 보류 목록 (D)
HOLD_RETRY_MAX = 3   # 보류가 풀려 다시 적용했는데 연속 3번 실패하면 자동 재시도를 멈추고 사람 확인으로
# alert-hub 자동 설치 (승인만으로 설치되게 하기 위한, 업데이터 내장 설치 — 봇 코드가 아님)
HUB_DIR = os.path.join(REPO, "alert-hub")
HUB_VENV = os.path.join(HUB_DIR, ".venv")
HUB_PY = os.path.join(HUB_VENV, "bin", "python")
HUB_PIP = os.path.join(HUB_VENV, "bin", "pip")
HUB_BOT_NAMES = "1번 한투 라오어,2번 토스 스나이퍼,3번 빗썸 적립,4번 팬딩 가격표,6번 메리츠 적립,8번 비서,9번 업데이트 비서:1500"
OWNER = pwd.getpwuid(os.stat(REPO).st_uid)
try:   # 2번 스나이퍼 원작자 새 버전 알림 부품 (알림 전용 · 없어도 비서는 정상 작동)
    import sniper_upstream as SU
except Exception as _e:   # 파일이 없거나 오류면 알림만 끔
    print("원작 알림 부품 없음:", type(_e).__name__, _e, flush=True)
    SU = None

import deployment_control as DC
try:
    import update_conflicts as UC
except ImportError:
    UC = None

 
 
def sh(*a, timeout=120):
    try:
        r = subprocess.run(list(a), capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, "시간 초과"
 
 
def git(*a, timeout=120):
    cmd = ["env", f"HOME={OWNER.pw_dir}", "GIT_TERMINAL_PROMPT=0", "git", "-c", "core.quotepath=false", "-C", REPO, *a]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    return sh(*cmd, timeout=timeout)
 
 
def git_raw(*a):
    cmd = ["env", f"HOME={OWNER.pw_dir}", "git", "-c", "core.quotepath=false", "-C", REPO, *a]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout
 
 
def _sniper_prefixes():
    """저장소 안 2번 스나이퍼 폴더 경로 접두사(끝에 /). 기본 toss_sniper/ + 서버 targets.json 에 적힌 스나이퍼 root (그 파일은 서버에만 있음)"""
    pre = {SNIPER_DIR}
    try:
        root = targets().get(SNIPER_UNIT)
        if root:
            rel = os.path.relpath(root, os.path.realpath(REPO))
            if rel not in (".", "") and not rel.startswith(".."):
                pre.add(rel)
    except Exception:
        pass
    return tuple(sorted(p.strip("/") + "/" for p in pre))


def _unit_roots_rel():
    """봇 폴더(저장소 상대 경로, 끝에 /) → 봇 키 (스나이퍼는 뺌). 사무실 폴더 bot_office/ 는 OFFICE_KEY"""
    base, out = os.path.realpath(REPO), {}
    for u, r in targets().items():
        if u == SNIPER_UNIT:
            continue
        rel = os.path.relpath(r, base)
        if rel in (".", "") or rel.startswith(".."):
            continue
        out[rel.strip("/") + "/"] = u
    return out


def _owner_unit(path, rel_roots):
    """이 파일이 속한 봇 (가장 깊은 폴더 기준). 어느 봇 폴더도 아니면 None = 공용 파일"""
    best = None
    for rel, u in rel_roots.items():
        if path.startswith(rel) and (best is None or len(rel) > len(best[0])):
            best = (rel, u)
    return best[1] if best else None


def _dirty_code_files(include_staged=False, scope=None):
    """저장 안 된 변경 중 실제 코드 변경만 반환한다.
    브리핑이 매번 다시 쓰는 생성 상태 파일(need.json·sniper_tiers.json)은 제외한다.
    include_staged=True면 스테이징된 변경도 포함한다.
    사무실 v1.9.3 (U_SCOPED_CHECKS 켜짐): ① 2번 스나이퍼 폴더(toss_sniper/) 변경은 제외한다 (임시 수정이 있어도 다른 봇 적용을 막지 않음)
      ② scope=(봇 목록, 이번에 바뀌는 파일들)을 주면 그 봇 폴더 + 공용 파일(어느 봇 폴더도 아닌 곳) + 이번에 바뀌는 파일에 겹치는 변경만 본다 (A)
      scope 없으면 저장소 전체(스나이퍼 제외). 스위치를 끄면 예전처럼 저장소 전체를 본다."""
    state = {NEED_FILE, SNIPER_TIERS_FILE}
    files = []
    out = git("status", "--porcelain", "--untracked-files=no")[1]
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[-1] not in state:
            files.append(parts[-1])
    if include_staged:
        staged = git("diff", "--cached", "--name-only")[1]
        for line in staged.splitlines():
            name = line.strip()
            if name and name not in state:
                files.append(name)
    if not SCOPED:
        return files
    pre = _sniper_prefixes()
    files = [f for f in files if not f.startswith(pre)]
    if scope is not None:
        units, touched = set(scope[0]), set(scope[1])
        rel_roots = _unit_roots_rel()
        files = [f for f in files if f in touched or _owner_unit(f, rel_roots) in units or _owner_unit(f, rel_roots) is None]
    return files


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d
 
 
def save(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
 
 
CFG = load(TG_CFG, {})
 
 
def tg(method, **params):
    data = json.dumps(params).encode()
    req = urllib.request.Request(f"{TG_API}/bot{CFG.get('token')}/{method}", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except Exception as e:
        print("텔레그램 오류:", type(e).__name__, flush=True)
        return {}
 
 
def say(text, rows=None, keyboard=None):
    p = {"chat_id": CFG.get("chat_id"), "text": text[:3900], "parse_mode": "HTML", "disable_web_page_preview": True}
    if rows:
        p["reply_markup"] = {"inline_keyboard": rows}
    elif keyboard:   # 채팅창 아래에 계속 떠 있는 버튼
        p["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True, "is_persistent": True}
    return tg("sendMessage", **p)
 
 
def uname(u):
    """표시 이름 — 봇 서비스는 NAMES, 사무실 폴더 키는 OFFICE_NAME"""
    return OFFICE_NAME if u == OFFICE_KEY else NAMES.get(u, u)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
 
 
# ---------------------------------------------------------------- 어떤 봇이 바뀌는지
def targets():
    t = load(TARGETS, {}).get("targets", {})
    office_root = os.path.realpath(os.path.join(REPO, "bot_office"))
    out = {u: os.path.realpath(v["root"]) for u, v in t.items() if isinstance(v, dict) and v.get("root")}
    out = {u: r for u, r in out.items() if r != office_root}   # v1.8.7: 서버 targets.json 에 옛 웹 서비스 항목이 남아 있어도 bot_office/ 는 폴더 키로만
    out[OFFICE_KEY] = office_root   # 저장소 bot_office/ ↔ 서버 /opt/bot-office (8번 비서·4번 팬딩·9번 업데이터 파일 · 서비스 아님)
    return out
 
 
def classify(files):
    """바뀐 파일 → (봇별 파일, 배포에서 빠진 파일)
    배포 규칙에 안 맞는 파일(테스트·점파일·폴더 안 파일·저장소 루트 파일·alert-hub·.gitignore·.example.json)은
    거부하지 않고 skipped 로 넘긴다 — 같이 묶인 다른 봇 업데이트가 막히지 않게."""
    roots, units, skipped = targets(), {}, []
    sniper_pre = _sniper_prefixes() if SCOPED else ()
    for f in files:
        if sniper_pre and f.startswith(sniper_pre):
            # 사무실 v1.9.3: 2번 스나이퍼 폴더는 업데이트 비서가 건드리지 않는다 (가져오기·덮어쓰기·삭제 전부 안 함 — 원작 직접 동기화로 따로 관리)
            skipped.append(f)
            continue
        if f == "alert-hub" or f.startswith("alert-hub/"):
            # alert-hub는 업데이터 적용 대상이 아님 (보관만, 서버 직접 설치).
            skipped.append(f)
            continue
        if f == ".gitignore" or f.endswith(".example.json"):
            # .gitignore·예시 설정은 저장소 전용 문서라 서버 적용 대상이 아님 (실제 설정은 서버에만 있음).
            skipped.append(f)
            continue
        absf = os.path.realpath(os.path.join(REPO, f)); d = os.path.dirname(absf); name = os.path.basename(f)
        unit = next((u for u, r in roots.items() if r == d), None)
        bdir = roots.get(BRIEFING_KEY)
        if unit is None and bdir and d.startswith(bdir + os.sep):   # briefing/ 하위 폴더(sources/·systemd/·tests/)도 9번 브리핑 소속
            unit = BRIEFING_KEY
        if name.endswith(".md"):
            if unit: units.setdefault(unit, [])
            continue
        if unit == OFFICE_KEY and name.endswith(OFFICE_EXT):   # 사무실 폴더: 예전과 같은 확장자 규칙 (삭제된 파일도 여기로 → /opt/bot-office 에서 지움)
            units.setdefault(unit, []).append(f)
        elif unit == BRIEFING_KEY:   # 9번 브리핑: .py·.json·.service·.timer 만 (tests/·__pycache__/·test_* 는 제외) — 재시작 대상 없음
            parts = os.path.relpath(absf, roots[BRIEFING_KEY]).split(os.sep)
            if name.endswith(BRIEFING_EXT) and not {"tests", "__pycache__"} & set(parts) and not name.startswith("test_"):
                units.setdefault(unit, []).append(f)
            else:
                skipped.append(f)
        elif unit and unit != OFFICE_KEY and name.endswith(".py") and not name.startswith(("bot_office_", "test_")):
            units.setdefault(unit, []).append(f)
        else:
            skipped.append(f)
    return units, skipped
 
 
# ---------------------------------------------------------------- 매매 중인지 확인
def sniper_orders_open():
    """2번 스나이퍼 장부에 매수·매도 주문이 걸려 있으면 보류 사유 문장, 없으면 ''.
    현 장부(인피니트 스노우볼 soxl_stratum_ledger*.json, {"SOXL": {...}}): 매수·매도 주문이 걸려 있으면 보류.
    (스노우볼은 원래 보유를 다음 날로 넘기는 전략이라 '보유 중'만으로는 막지 않음 · 재시작하면 장부·잔고로 이어서 관리)
    사무실 v1.9.3: busy_reason 에서 떼어 냄 — 스나이퍼는 이제 다른 봇 적용 판단에서 빠지고, 이 확인은 2번 자동 업뎃 조건에서 쓴다."""
    import glob
    root = targets().get(SNIPER_UNIT, "")
    for p in glob.glob(os.path.join(root, "soxl_stratum_ledger*.json")):
        d = load(p, {})
        L = d.get("SOXL", d) if isinstance(d, dict) else {}
        if isinstance(L, dict) and (str(L.get("buy_order_id") or "").strip() or str(L.get("sell_order_id") or "").strip()):
            return "스나이퍼(SOXL) 주문이 걸려 있음 (체결·취소 뒤 다시 눌러 주세요)"
    return ""


def sniper_pause_phase():
    """2번 스나이퍼의 업데이트용 일시중지 상태 값('running'·'waiting'·'paused'). 상태 파일이 없거나 읽을 수 없으면 ''"""
    root = targets().get(SNIPER_UNIT)
    try:
        if root and SNIPER_UNIT in DC.UNITS.values() and DC.state_path(root).exists():
            return str(DC.read(DC.state_path(root)).get("phase") or "")
    except Exception:
        return "unreadable"
    return ""


def sniper_dirty_files():
    """서버 스나이퍼 폴더의 저장 안 된 코드 변경 (장부 soxl_stratum_ledger* 와 생성 상태 파일은 제외) — 임시 수정이 남아 있는지 보는 용도"""
    pre = [p.rstrip("/") for p in _sniper_prefixes()]
    out = git("status", "--porcelain", "--untracked-files=no", "--", *pre)[1]
    names = [line.split()[-1] for line in out.splitlines() if line.split()]
    return [n for n in names if not os.path.basename(n).startswith("soxl_stratum_ledger") and n not in (NEED_FILE, SNIPER_TIERS_FILE)]


def busy_reason(unit, pause_verified=False):
    if pause_verified:
        return ""
    now_k, now_e = datetime.now(KST), datetime.now(ET)
    k, e = now_k.hour * 100 + now_k.minute, now_e.hour * 100 + now_e.minute
    if unit == SNIPER_UNIT:
        r = sniper_orders_open()
        if r:
            return r
    if unit == "bithumb_bot.service" and 1850 <= k <= 1925:
        return "4번 봇 19:00 정기 매수 시간"
    if unit == "han4384tubot.service" and 925 <= e <= 1605 and now_e.weekday() < 5:
        return "1번 봇 미국 정규장 시간"
    if unit == FANDING_UNIT and now_e.weekday() < 5 and 750 <= e <= 835:
        return "4번 팬딩 예약주문 마감 전후 (08:30 ET 전후)"
    return ""
 
 
def gate_installed(unit):
    """업데이트용 신규 주문 차단 부품(deployment_gate.py)이 그 봇 폴더에 있는지"""
    return os.path.isfile(os.path.join(targets().get(unit, ""), "deployment_gate.py"))


# ---------------------------------------------------------------- 새 업데이트 찾기
CAPTURE_PREFIX = "captures/"
# live-board: 사무실 보드용 live_board.json 전용 고아 브랜치 — 1분마다 커밋이 올라가므로 업데이트가 아님.
# 음수 refspec 가드와 별개로 코드에서도 제외 (refspec이 빠져도 알림 폭주 재발 방지 · 2026-11-17)
LIVE_BOARD_BRANCH = "live-board"


def scan(st, force=False):
    """새 업데이트 찾기 → 이번에 보낸 알림 개수 (GitHub 확인 실패면 None).
    v1.8.1: 대기 브랜치 목록을 먼저 다 모은 뒤 알림 — 옛 브랜치 안내(superseded)가 다른 대기 브랜치도 볼 수 있게. 감지 조건은 그대로."""
    rc, out = git("fetch", "-q", "--prune", "origin")
    if rc:
        if st.get("fetch_err") != out[:80]:
            st["fetch_err"] = out[:80]; say("<b>[업데이트 비서] GitHub 확인 실패</b>\n· " + esc(out[-200:]))
        return None
    st["fetch_err"] = ""
    main_ahead_notice(st)
    rc, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    live = {}   # 지금 GitHub에 실제로 있고 아직 반영 안 된 브랜치 → 최신 SHA
    for line in refs.splitlines():
        ref, sha = line.split()
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if br in ("main", "HEAD") or ref == "origin":
            continue
        if br.startswith(CAPTURE_PREFIX):
            continue   # 캡처·참고 파일 브랜치(AI 작업 보드 B안)는 업데이트가 아님 — 알림·옛 브랜치 판정에서 뺌
        if br == LIVE_BOARD_BRANCH:
            continue   # 보드용 고아 브랜치 — 1분마다 커밋이라 매번 새 업데이트로 보임 (알림 폭주 원인)
        if git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue   # 이미 반영된 브랜치
        live[br] = sha
    sent = 0
    seen = st.setdefault("seen", {})
    for br, sha in live.items():
        if seen.get(br) == sha and not force:
            continue
        seen[br] = sha
        offer(st, br, sha, live)
        sent += 1
    prune(st, live)
    return sent


def main_ahead_notice(st):
    """GitHub main 에 서버를 거치지 않은 수정(웹에서 main 에 바로 올림 등)이 있으면 같은 main 마다 1번만 알림.
    그대로 두면 서버 HEAD≠main 이라 충돌 정리·STATUS 기록이 멈추고, 다음 승인 때 main 업로드가 실패한다."""
    rc_m, main = git("rev-parse", "origin/main")
    if rc_m or not main or git("merge-base", "--is-ancestor", main, "HEAD")[0] == 0:
        st.pop("main_ahead", None)
        return
    if st.get("main_ahead") == main:
        return
    st["main_ahead"] = main
    _, subj = git("log", "--format=%s", "HEAD..origin/main", "-n", "3")
    _, fs = git("diff", "--name-only", "HEAD...origin/main")
    fs = [f for f in fs.splitlines() if f.strip()]
    say("<b>[업데이트 비서] GitHub main 에 서버를 거치지 않은 수정이 있습니다</b>\n"
        "· 수정: " + esc(" / ".join(subj.splitlines()) or "-") + "\n"
        "· 파일: " + esc(", ".join(fs[:6]) + (" 외" if len(fs) > 6 else "")) + "\n"
        "· 이대로면 충돌 정리·STATUS 기록이 멈춥니다.\n"
        "→ GitHub 에서 <b>main 기준 새 브랜치</b>를 만들면 업데이트 알림이 뜹니다. 그 알림을 승인하면 서버와 main 이 다시 같아집니다.")


def prune(st, live):
    """지난 알림 정리: 브랜치가 지워졌거나 새 커밋으로 바뀐(또는 이미 반영된) 알림·정리화면을 지운다.
    예전 알림 버튼을 누르면 '최신 업데이트 알림에서 다시 눌러 주세요'로 안내된다. 지운 개수 반환."""
    offers = st.setdefault("offers", {})
    removed = 0
    for k, o in list(offers.items()):
        if live.get(o.get("branch")) != o.get("sha"):
            offers.pop(k, None); removed += 1
    # 같은 브랜치·같은 SHA 알림이 여러 개면 가장 최근 것 하나만 남김
    keep = {}
    for k, o in sorted(offers.items(), key=lambda kv: kv[1].get("at", 0)):
        if o["branch"] in keep:
            offers.pop(keep[o["branch"]], None); removed += 1
        keep[o["branch"]] = k
    for br in list(st.get("seen", {})):
        if br not in live:
            st["seen"].pop(br, None)
    plans = st.get("conflict_plans", {})
    for t, pl in list(plans.items()):
        if pl.get("offer_key") not in offers:
            plans.pop(t, None)
    return removed


def live_branches():
    """GitHub에 지금 있고 아직 main에 반영 안 된 브랜치 → 최신 SHA. 확인 실패 시 None."""
    rc, out = git("fetch", "-q", "--prune", "origin")
    if rc:
        return None
    _, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    live = {}
    for line in refs.splitlines():
        ref, sha = line.split()
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if br in ("main", "HEAD") or ref == "origin" or br.startswith(CAPTURE_PREFIX) or br == LIVE_BOARD_BRANCH:
            continue
        if git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue
        live[br] = sha
    return live
 
 
REVERT_DAYS, REVERT_SKIP = 14, ("CHANGELOG.md",)
_VER_RES = (re.compile(r"""^\s*(?:BOT_|UPDATER_)?VERSION\s*=\s*["']v?(\d+(?:\.\d+)+)""", re.M),
            re.compile(r"_V(\d+(?:\.\d+)+)\)"))


def _ver(text):
    for rx in _VER_RES:
        m = rx.search(text or "")
        if m:
            return tuple(int(x) for x in m.group(1).split("."))
    return None


def revert_check(sha, files):
    """되돌림 감지: 이 업로드가 최근 main 수정을 지우는지 · 버전이 더 낮은지. 경고 문장 목록 (확인 실패는 조용히 넘어감)
    · 업로드 브랜치가 이미 가진 최근 커밋(C)이 추가한 줄이 지금 main 에는 있는데 업로드 파일에는 없으면 → 지워지는 것
      (브랜치가 C 를 모르면 병합이 C 를 지켜 주거나 충돌로 멈추므로 검사 안 함)"""
    out = []
    for f in files[:25]:
        if os.path.basename(f) in REVERT_SKIP or not f.endswith((".py", ".md", ".html", ".js", ".css", ".json", ".sh")):
            continue
        rc_h, head_txt = git("show", f"HEAD:{f}")
        if rc_h:
            continue                                   # main 에 없던 새 파일
        rc_n, new_txt = git("show", f"{sha}:{f}")
        if rc_n:
            out.append(f"<code>{esc(f)}</code> 파일을 지웁니다"); continue
        hv, nv = _ver(head_txt), _ver(new_txt)
        if hv and nv and nv < hv:
            out.append(f"<code>{esc(f)}</code> 버전이 더 낮아요: 지금 {'.'.join(map(str, hv))} → 올린 것 {'.'.join(map(str, nv))}")
        new_lines = {l.strip() for l in new_txt.splitlines()}
        head_lines = {l.strip() for l in head_txt.splitlines()}
        _, log = git("log", f"--since={REVERT_DAYS}.days", "--no-merges", "-n", "12", "--format=%H\t%ad\t%s",
                     "--date=format:%m/%d %H:%M", "HEAD", "--", f)
        for row in log.splitlines():
            parts = row.split("\t", 2)
            if len(parts) < 3 or parts[2].startswith("버전 기록"):
                continue
            c, when, subj = parts
            if git("merge-base", "--is-ancestor", c, sha)[0] != 0:
                continue
            _, patch = git("show", "--format=", "-U0", c, "--", f)
            added = {l[1:].strip() for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++")}
            added = {l for l in added if len(l) >= 8 and l in head_lines}     # 지금도 main 에 살아 있는 의미 있는 줄
            lost = [l for l in added if l not in new_lines]
            if added and len(lost) >= max(2, len(added) * 0.3):
                out.append(f"<code>{esc(f)}</code>: {esc(when)} 수정 '<b>{esc(subj[:40])}</b>'의 {len(lost)}/{len(added)}줄이 사라져요"
                           f"\n    예) <code>{esc(sorted(lost, key=len, reverse=True)[0][:70])}</code>")
    return out


# ---------------------------------------------------------------- 옛(리베이스 전) 브랜치 감지 (v1.8.1)
# 왜: scan 은 'main 이 아니고 서버 HEAD 의 조상이 아닌' 브랜치를 모두 새 수정으로 본다. 리베이스는 새 커밋을 만들 뿐
#     옛 커밋을 HEAD 의 조상으로 만들지 않으므로, 옛 커밋을 가리키는 브랜치가 GitHub 에 남으면 영원히 '미반영'으로 보이고
#     낡은 기준에서 같은 파일을 고친 것이라 병합 때마다 충돌한다. apply 의 자동 삭제는 적용한 브랜치 하나만 지운다.
_BRANCH_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")


def behind_count(sha):
    """서버 HEAD 에는 있고 이 브랜치에는 없는 커밋 수 (= 브랜치가 뒤처진 정도). 확인 실패 None."""
    rc, n = git("rev-list", "--count", f"{sha}..HEAD")
    return int(n) if rc == 0 and n.strip().isdigit() else None


def predict_conflicts(sha):
    """지금 HEAD 에 병합하면 충돌할 파일 목록 (미리 보기만 · 작업 폴더·인덱스·HEAD 는 건드리지 않음).
    [] = 충돌 없음, None = 확인 불가 (git 2.38 미만 등 — 그때는 예전처럼 적용 때 판정)."""
    rc, out = git("merge-tree", "--write-tree", "--name-only", "--no-messages", "HEAD", sha)
    if rc == 0:
        return []
    if rc != 1:
        return None
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    if not lines or not re.fullmatch(r"[0-9a-f]{40,64}", lines[0]):
        return None
    return lines[1:]


def _commit_keys(rng):
    """범위 안 병합 아닌 커밋 → [(작성 시각 원본, 제목, sha)]. 작성 시각(author date)은 리베이스·체리픽에서 그대로 남는다."""
    rc, out = git("log", "--no-merges", "--format=%H%x09%ad%x09%s", "--date=raw", rng)
    if rc:
        return None
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append((parts[1], parts[2], parts[0]))
    return rows


def superseded(sha, others=None):
    """이 브랜치의 수정이 전부(제목 + 작성 시각이 같은 커밋으로) 이미 서버 HEAD 나 다른 대기 브랜치에 들어 있는지.
    → {"where": "HEAD" 또는 브랜치 이름, "by": 새 커밋 sha, "subject": 제목, "count": 커밋 수} / 아니면 None.
    제목만 같은 것(예: GitHub 웹 기본 제목 'Update x.py')은 작성 시각이 달라 걸리지 않는다."""
    targets_ = [("HEAD", "HEAD")] + sorted((b, s) for b, s in (others or {}).items() if s != sha)
    for where, ref in targets_:
        mine = _commit_keys(f"{ref}..{sha}")
        theirs = _commit_keys(f"{sha}..{ref}")
        if not mine or not theirs:
            continue
        index = {(d, s): h for d, s, h in theirs}
        if all((d, s) in index for d, s, _h in mine):
            d, s, _h = mine[0]
            return {"where": where, "by": index[(d, s)], "subject": s, "count": len(mine)}
    return None


def _superseded_text(sup):
    if sup["where"] == "HEAD":
        return (f"<b>이미 서버에 반영된 옛 브랜치예요</b> — 같은 수정(제목·작성 시각 같음)이 다른 커밋 "
                f"<code>{esc(sup['by'][:8])}</code>로 이미 들어와 있어요 (리베이스 전 원본으로 보임)."
                "\n→ 업데이트 버튼·충돌 정리 말고 <b>옛 브랜치 지우기</b>를 눌러 주세요. 백업 태그를 남기고 지웁니다.")
    return (f"<b>같은 수정의 새 브랜치가 따로 있어요</b>: <code>{esc(sup['where'])}</code> "
            f"(<code>{esc(sup['by'][:8])}</code>, 리베이스본으로 보임)."
            "\n→ 이 옛 브랜치 말고 새 브랜치 알림을 승인하고, 이건 <b>옛 브랜치 지우기</b>로 정리해 주세요.")


def _drop_row(key):
    return [{"text": "옛 브랜치 지우기 (백업 남김)", "callback_data": f"rm:{key}"}]


def drop_superseded(st, key):
    """옛 브랜치 지우기 — 누를 때 다시 확인: GitHub 최신 SHA 같음 + 여전히 '이미 반영된 옛 브랜치'.
    백업 태그 만들기와 브랜치 삭제를 한 번에(--atomic), 그사이 브랜치가 바뀌었으면 거부(--force-with-lease).
    서버 작업 폴더·HEAD·main·staging 은 건드리지 않는다. Git 출력은 보여 주지 않는다(주소에 인증값이 있을 수 있음)."""
    o = st.get("offers", {}).get(key)
    if not o:
        return say("최신 업데이트 알림에서 다시 눌러 주세요.")
    br, sha = o["branch"], o["sha"]
    if br in ("main", "staging", "HEAD") or not _BRANCH_RE.fullmatch(br):
        return say("이 브랜치는 여기서 지울 수 없습니다.")
    if git("fetch", "-q", "--prune", "origin")[0]:
        return say("GitHub 확인에 실패했습니다. 잠시 후 다시 눌러 주세요. (아무것도 지우지 않았습니다)")
    rc, now_sha = git("rev-parse", f"origin/{br}")
    if rc or now_sha != sha:
        return say("그사이 브랜치가 바뀌었거나 사라졌습니다. 새 알림에서 다시 확인해 주세요. (아무것도 지우지 않았습니다)")
    live = live_branches() or {}
    sup = superseded(sha, live)
    if not sup:
        return say("이미 반영된 옛 브랜치로 확인되지 않아 지우지 않았습니다.")
    backup = "updater-backup/superseded-" + datetime.now(KST).strftime("%Y%m%d-%H%M%S") + "-" + sha[:8]
    rc, _out = git("push", "--atomic", f"--force-with-lease=refs/heads/{br}:{sha}", "origin",
                   f"{sha}:refs/tags/{backup}", f":refs/heads/{br}")
    if rc:
        return say(f"옛 브랜치를 지우지 못했습니다 (코드 {rc}). 브랜치·태그 모두 그대로입니다.")
    git("fetch", "-q", "--prune", "origin")
    for k, ofr in list(st.get("offers", {}).items()):
        if ofr.get("branch") == br:
            st["offers"].pop(k, None)
    st.setdefault("seen", {}).pop(br, None)
    say(f"옛 브랜치 <code>{esc(br)}</code> 를 지웠습니다.\n· 백업 태그: <code>{esc(backup)}</code> (필요하면 이 태그로 되살릴 수 있어요)"
        "\n· 서버 코드·main·staging 은 그대로입니다.")


def offer(st, br, sha, live=None):
    _, files = git("diff", "--name-only", f"HEAD...{sha}")
    files = [f for f in files.splitlines() if f.strip()]
    units, skipped = classify(files)
    _, log = git("log", "--format=%an · %s", f"HEAD..{sha}", "-n", "5")
    key = sha[:12]
    st.setdefault("offers", {})[key] = {"branch": br, "sha": sha, "at": time.time()}
    bots = ", ".join(uname(u) for u, fs in units.items() if fs) or "봇 코드 없음(문서만)"
    warn = ("\n<b>배포에서 빠진 파일</b>: " + esc(", ".join(skipped[:5])) + (" 외 " + str(len(skipped) - 5) + "개" if len(skipped) > 5 else "")
            + " (서버에 적용하지 않고 넘김 · 업데이트는 그대로 진행 가능)") if skipped else ""
    if SCOPED and any(f.startswith(_sniper_prefixes()) for f in skipped):
        warn += "\n2번 스나이퍼 폴더 파일은 이 업데이트로 적용되지 않아요 (원작 직접 동기화로 따로 관리)"
    try:
        pre = _sniper_prefixes() if SCOPED else ()
        reverts = revert_check(sha, [f for f in files if not f.startswith(pre)] if pre else files)   # 스나이퍼 파일은 적용 대상이 아니라 되돌림 감지도 안 함
    except Exception as e:
        print("되돌림 감지 실패:", type(e).__name__, e, flush=True); reverts = []
    if reverts:
        warn += ("\n\n<b>덮어쓰기 의심</b> (예전 파일을 기준으로 고친 것 같아요)\n" + "\n".join(reverts[:6])
                 + ("\n…외 " + str(len(reverts) - 6) + "건" if len(reverts) > 6 else "")
                 + "\n→ 최신 main 파일을 받아 다시 고쳐 올리는 걸 추천해요. 알고 올린 거면 그대로 승인해도 돼요.")
        st["offers"][key]["reverts"] = len(reverts)
    # v1.8.1: 낡은 정도 · 미리 본 충돌 · 옛 브랜치 안내 (모두 알림 정보만 — 적용 단계의 검사는 그대로)
    try:
        behind = behind_count(sha)
        conflicts = predict_conflicts(sha)
        sup = superseded(sha, live)
    except Exception as e:
        print("옛 브랜치 확인 실패:", type(e).__name__, e, flush=True); behind, conflicts, sup = None, None, None
    if behind:
        warn += f"\n\n기준: 서버보다 <b>{behind}개</b> 뒤처진 브랜치"
    if conflicts:
        warn += ("\n<b>지금 적용하면 충돌하는 파일</b>: " + esc(", ".join(conflicts[:6])) + (" 외" if len(conflicts) > 6 else "")
                 + ("" if sup else "\n→ 최신 main 기준으로 다시 올려(리베이스) 주세요. 이대로 업데이트를 누르면 충돌로 멈춥니다."))
        st["offers"][key]["conflicts"] = len(conflicts)
    if sup:
        warn += "\n\n" + _superseded_text(sup)
        st["offers"][key]["superseded"] = sup["where"]
    rows = [[{"text": "바뀐 내용 보기", "callback_data": f"df:{key}"}, {"text": "무시", "callback_data": f"ig:{key}"}]]
    if sup:
        rows.append(_drop_row(key))
    if UC:
        rows.append([{"text": "이전 변경·충돌 정리", "callback_data": "cp:" + key}])
    rows.insert(0, [{"text": "알고 있음 · 그래도 업데이트" if reverts else "업데이트", "callback_data": f"up:{key}"}])   # 빠진 파일이 있어도 항상 표시
    gated = {u for u in DC.UNITS.values() if units.get(u) and gate_installed(u)}   # 차단 부품이 설치된 봇만 일시중지 버튼
    if gated:
        rows.append([{'text':'이번 업데이트 대상 전체 중지 대기','callback_data':'pa:'+key},
                     {'text':'이번 대상 거래 재개','callback_data':'ra:'+key}])
    for number, unit in DC.UNITS.items():
        if unit in gated:
            rows.append([{ "text": "" + NAMES[unit] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + number}])
    say(f"<b>[업데이트 비서] 새 수정이 올라왔어요</b>\n· 대상: {esc(bots)}\n· 브랜치: <code>{esc(br)}</code>\n"
        f"· 파일: {esc(', '.join(files[:8]))}{' 외' if len(files) > 8 else ''}\n· 내용:\n{esc(log[:600])}{warn}\n\n"
        "업데이트 버튼을 누르면 매매 중인지 확인 → 적용 → 재시작 확인(실패 시 자동 복구) → 버전 기록 → GitHub main 업로드까지 진행합니다.", rows)
 
 
# ---------------------------------------------------------------- STATUS.md (자동 현재 상태)
STATUS_FILE = "STATUS.md"
SNIPER_TIERS_FILE = "sniper_tiers.json"
NEED_FILE = "need.json"
EXTRA_UNITS = {SECRETARY_UNIT: "8번 비서(SGOV)", FANDING_UNIT: "4번 팬딩 가격표", SELF_UNIT: "9번 업데이트 비서"}
_CL_RE = re.compile(r"^## (\S+) · ([\d-]+ [\d:]+) \(KST\)\n((?:- .*\n?)*)", re.M)


def _changelog(root, n=3):
    """봇 폴더 CHANGELOG.md 의 최근 n건 → [(버전, 시각, 파일, 내용)]"""
    try:
        text = open(os.path.join(root, "CHANGELOG.md"), encoding="utf-8").read()
    except OSError:
        return []
    out = []
    for m in _CL_RE.finditer(text):
        info = dict(re.findall(r"^- ([^:]+): (.*)$", m.group(3), re.M))
        out.append((m.group(1), m.group(2), info.get("파일", ""), info.get("내용", "")))
        if len(out) >= n:
            break
    return out


def _svc(unit):
    _, out = sh(SYSTEMCTL, "show", unit, "-p", "ActiveState", "-p", "ActiveEnterTimestamp", "--value")
    lines = (out.splitlines() + ["", ""])[:2]
    state, since = lines[0].strip(), lines[1].strip()
    m = re.search(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) (\w+)", since)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc) if m.group(2) == "UTC" else dt.replace(tzinfo=KST if m.group(2) == "KST" else None)
            since = dt.astimezone(KST).strftime("%m-%d %H:%M") if dt.tzinfo else dt.strftime("%m-%d %H:%M")
        except ValueError:
            since = m.group(1)[5:16]
    mark = "실행 중" if state == "active" else ("꺼짐" if state == "inactive" else f"상태 {state or '확인 불가'}")
    return mark, since


def _cell(s):
    return str(s).replace("|", "/").replace("\n", " ").strip()


def hold_status_lines():
    """STATUS 에 쓸 보류 목록 한 줄씩 (보류 경과일 포함)"""
    out = []
    try:
        items = load(HOLDS, {}).get("items", {})
        now = time.time()
        for key, e in sorted(items.items(), key=lambda kv: kv[1].get("since", 0)):
            days = int((now - e.get("since", now)) // 86400)
            since = datetime.fromtimestamp(e.get("since", now), KST).strftime("%m-%d %H:%M")
            for u, r in (e.get("units") or {}).items():
                tail = "사람 확인 필요" if e.get("stuck") or (e.get("kinds") or {}).get(u) == "ahead" else f"자동 재시도 {e.get('tries', 0)}회"
                out.append(f"- {_cell(uname(u))}: {_cell(r)[:90]} · 브랜치 `{_cell(e.get('branch', '-'))}` ({_cell(e.get('sha', '')[:7])}) · {since} KST부터 {days}일째 · {tail}")
    except Exception as ex:
        out.append("- 보류 목록을 읽지 못했습니다: " + type(ex).__name__)
    return out


def sniper_observe_lines():
    """STATUS 의 2번 스나이퍼 관찰 줄: 서버 스나이퍼 커밋 · 원작 기준 커밋 · 자동 업뎃 상태 (읽기만)"""
    out = []
    try:
        pre = _sniper_prefixes()
        rc, c = git("log", "-1", "--format=%h %s", "--", *[p.rstrip("/") for p in pre])
        out.append(f"- 서버 스나이퍼 최신 커밋: {_cell(c)[:100] if rc == 0 and c else '확인 불가'}")
        sl = load(STATE, {}).get("sniper_up", {}) if SU else {}
        base = (sl.get("base") or getattr(SU, "BASE_DEFAULT", "")) if SU else ""
        out.append(f"- 원작 기준 커밋: {base[:7] if base else '확인 불가'}")
        last = sl.get("auto_last") or {}
        if last:
            out.append("- 자동 업뎃: 마지막 " + _cell(last.get("result", "-")) + f" · 원작 {_cell(str(last.get('head', ''))[:7])} · {_cell(last.get('when', ''))}")
        else:
            out.append("- 자동 업뎃: 기록 없음")
        failed = sl.get("auto_failed") or {}
        if failed:
            out.append("- 자동 업뎃 중단(사람이 풀 때까지): " + ", ".join(_cell(h[:7]) for h in failed))
    except Exception as ex:
        out.append("- 관찰 줄을 만들지 못했습니다: " + type(ex).__name__)
    return out


def build_status(reason):
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    roots = targets()
    L = ["# STATUS — 서버가 자동으로 쓰는 현재 상태", "",
         "> 이 파일은 업데이트 비서가 자동으로 씁니다. **손으로 고치지 마세요** (고쳐도 다음 기록 때 덮어씀).",
         "> 규칙·설명은 START.md · docs/handoff/ · 작업 기록은 docs/log/ 에 새 파일로.", "",
         f"- 갱신: {now} (KST) · 계기: {_cell(reason)}", ""]
    L += ["## 봇별 현재 상태", "", "| 봇 | 서비스 | 상태 | 버전 | 마지막 적용 | 내용 |", "|---|---|---|---|---|---|"]
    recent = []
    for u, name in NAMES.items():
        mark, since = _svc(u)
        cl = _changelog(roots.get(u, ""), 10) if roots.get(u) else []
        ver, when, _, what = cl[0] if cl else ("-", "-", "", "-")
        L.append(f"| {name} | `{u.replace('.service', '')}` | {mark}{' (' + since + ' KST부터)' if since and mark == '실행 중' else ''} | {ver} | {when} | {_cell(what)[:60]} |")
        recent += [(w, name, v, f, t) for v, w, f, t in cl]
    cl = _changelog(roots.get(OFFICE_KEY, ""), 10) if roots.get(OFFICE_KEY) else []   # v1.8.7: 사무실 파일은 서비스가 없어 상태 칸 대신 '파일 묶음'
    ver, when, _, what = cl[0] if cl else ("-", "-", "", "-")
    L.append(f"| {OFFICE_NAME} | `{OFFICE_KEY}` (서비스 없음) | 파일 묶음 | {ver} | {when} | {_cell(what)[:60]} |")
    recent += [(w, OFFICE_NAME, v, f, t) for v, w, f, t in cl]
    L += ["", "## 사무실 상시 서비스", ""]
    for u, name in EXTRA_UNITS.items():
        mark, since = _svc(u)
        L.append(f"- {name} `{u.replace('.service', '')}`: {mark}{' (' + since + ' KST부터)' if since and mark == '실행 중' else ''}")
    _, failed = sh(SYSTEMCTL, "list-units", "--failed", "--plain", "--no-legend", "--no-pager")
    failed = [ln.split()[0] for ln in failed.splitlines() if ln.split()]
    L.append(f"- 실패 상태로 남은 서비스·타이머: {', '.join('`' + f + '`' for f in failed) if failed else '없음'}")
    try:
        du = shutil.disk_usage(REPO)
        L.append(f"- 디스크 사용: {du.used / du.total * 100:.0f}% (남은 {du.free / 1e9:.1f}GB)")
    except OSError:
        pass
    L += ["", "## 최근 적용 10건", ""]
    for w, name, v, f, t in sorted(recent, reverse=True)[:10]:
        L.append(f"- {w} · {name} {v} · {_cell(f)[:60]} · {_cell(t)[:60]}")
    L += ["", "## 대기 중인 업로드 (아직 승인 안 됨)", ""]
    _, refs = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    pend = []
    for line in refs.splitlines():
        ref, sha = (line.split() + [""])[:2]
        br = ref.split("/", 1)[1] if "/" in ref else ref
        if not sha or br in ("main", "HEAD") or ref == "origin" or br.startswith(CAPTURE_PREFIX) or br == LIVE_BOARD_BRANCH or git("merge-base", "--is-ancestor", sha, "HEAD")[0] == 0:
            continue
        _, fs = git("diff", "--name-only", f"HEAD...{sha}")
        fs = [x for x in fs.splitlines() if x.strip()]
        pend.append(f"- `{br}`: {', '.join(fs[:6])}{' 외' if len(fs) > 6 else ''}")
    L += pend or ["- 없음"]
    if SCOPED:   # 사무실 v1.9.3: 보류 목록(D) · 2번 스나이퍼 관찰 줄
        L += ["", "## 보류 중인 봇 업데이트 (매매 중·일시중지 대기는 풀리면 자동 재시도 · 앞섬은 사람 승인 필요)", ""]
        L += hold_status_lines() or ["- 없음"]
        L += ["", "## 2번 스나이퍼 (관찰 전용 — 업데이트 비서가 적용하지 않음)", ""]
        L += sniper_observe_lines()
    L += ["", "## AI·사람 작업 순서 (요약)", "",
          "1. 이 파일과 START.md 를 먼저 읽는다. 위 표가 서버의 실제 상태다 (다른 문서의 '현재 상태'보다 우선).",
          "2. 고칠 파일은 **main 의 최신본**을 받아서 고친다 (기억·예전 대화의 파일로 고치지 않는다).",
          "3. 고친 파일은 staging 에 올리고 9. Update 에서 승인한다. 예전 파일로 덮어쓰면 승인 알림에 경고가 뜬다.",
          "4. 작업 기록은 docs/log/날짜_AI이름_작업.md 새 파일로 남긴다 (공용 문서를 여럿이 고치지 않는다).", ""]
    return "\n".join(L)


STATUS_COPY = os.environ.get("U_STATUS_COPY", "/var/lib/bot-office/status.md")


def _status_copy(text):
    """사무실 상황판(웹서버 bot-office 계정)이 읽는 STATUS.md 복사본 · 모두 읽기 0644 (비밀값 없음 — STATUS.md 와 같은 내용)"""
    try:
        os.makedirs(os.path.dirname(STATUS_COPY), exist_ok=True)
        tmp = STATUS_COPY + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, STATUS_COPY)
    except OSError as e:
        print("상황판용 STATUS 복사 실패:", type(e).__name__, flush=True)


def write_sniper_tiers():
    """스나이퍼 원장 읽기 전용 공개 투영. 오류여도 실패 JSON을 원자적으로 기록한다."""
    stamp = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    result = {"ok": False, "error": "unknown", "as_of_kst": stamp}
    try:
        import importlib.util
        source = os.path.join(OFFICE_DIR, "sniper_picture.py")
        spec = importlib.util.spec_from_file_location("office_sniper_picture_export", source)
        if not spec or not spec.loader:
            raise RuntimeError("sniper_picture_unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        found, err = module._find_ledger()
        if not found:
            raise RuntimeError(str(err or "ledger_unavailable"))
        _, state = found
        live, note = module._snapshot_price(time.time())
        data = module.build(state, live_price=live, price_note=note)
        if not data.get("ok"):
            raise RuntimeError(str(data.get("error") or "build_failed"))
        holding = data.get("holding") or {}
        result = {
            "ok": True, "as_of_kst": stamp, "symbol": "SOXL",
            "live_price": (data.get("price") or {}).get("live"),
            "price_note": (data.get("price") or {}).get("note", ""),
            "tiers": data.get("tiers") or [], "targets": data.get("targets") or [],
            "sub_tiers": data.get("sub_tiers") or [], "sub_targets": data.get("sub_targets") or [],
            "holding": {k: holding.get(k, 0) for k in ("shares", "sub_shares", "basement_shares", "total_shares")},
            "basement": data.get("basement"),
        }
    except Exception as exc:
        result = {"ok": False, "error": str(exc)[:160], "as_of_kst": stamp}
    path = os.path.join(REPO, SNIPER_TIERS_FILE)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=REPO,
                                         prefix=".sniper_tiers_", suffix=".tmp", delete=False) as out:
            tmp = out.name
            json.dump(result, out, ensure_ascii=False, allow_nan=False, indent=2)
            out.write("\n")
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
        tmp = None
        try:
            os.chown(path, OWNER.pw_uid, OWNER.pw_gid)
        except OSError:
            pass
        return True
    except Exception as exc:
        print("sniper_tiers.json 기록 실패:", type(exc).__name__, str(exc)[:120], flush=True)
        return False
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def write_status(reason):
    """STATUS.md 를 쓰고, '갱신' 줄 말고 실제 내용이 바뀌었으면 True"""
    path = os.path.join(REPO, STATUS_FILE)
    new = build_status(reason)
    _status_copy(new)
    strip = lambda t: re.sub(r"^- 갱신: .*$", "", t, flags=re.M)
    try:
        old = open(path, encoding="utf-8").read()
    except OSError:
        old = ""
    if strip(old) == strip(new):
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    try:
        os.chown(path, OWNER.pw_uid, OWNER.pw_gid)
    except OSError:
        pass
    return True


HEALTH_OK_ENABLED = ("enabled", "enabled-runtime", "static", "generated", "indirect", "alias")
SYNC_SUBJ_RE = re.compile(r"^sniper: upstream [0-9a-f]{7,40} direct sync$")   # 2번 plugin_updater 가 남기는 커밋 제목


def health_units():
    """매일 점검할 서비스: 대상 봇 서비스(사무실 폴더 키·9번 브리핑 제외 — 타이머 구동 one-shot 이라 평소 inactive) + 사무실 상시 서비스"""
    return [u for u in targets() if u not in (OFFICE_KEY, BRIEFING_KEY)] + [u for u in EXTRA_UNITS if u not in targets()]


def health_check(st, today):
    """실행·부팅 자동시작 확인 → 문제 목록. 문제가 있으면 8번 방(alert-hub 긴급)·9번 방으로 알림 (같은 날 같은 내용은 1번)"""
    bad = []
    for u in health_units():
        a = sh(SYSTEMCTL, "is-active", u)[1].strip()
        e = sh(SYSTEMCTL, "is-enabled", u)[1].strip()
        name = EXTRA_UNITS.get(u) or uname(u)
        if a != "active":
            bad.append(f"{name} ({u}): 실행 상태 {a or '확인 불가'}")
        if e not in HEALTH_OK_ENABLED:
            bad.append(f"{name} ({u}): 부팅 자동시작 {e or '확인 불가'}")
    sig = today + "|" + "|".join(bad)
    if bad and st.get("health_sig") != sig:
        st["health_sig"] = sig
        text = "[9번 업데이트 비서] 매일 점검 — 서비스 확인 필요\n" + "\n".join("· " + b for b in bad)
        _hub_alert("9번 업데이트 비서", "critical", text)
        say(esc(text))
    if not bad:
        st.pop("health_sig", None)
    return bad


def _only_sync_ahead(main, head):
    """서버 HEAD 가 origin/main 의 빨리감기이고, 앞선 커밋이 전부 2번 원작 자동 동기화 커밋이면 True"""
    if not main or main == head or git("merge-base", "--is-ancestor", main, head)[0] != 0:
        return False
    rc, subj = git("log", "--format=%s", main + ".." + head)
    lines = [x for x in subj.splitlines() if x.strip()]
    return rc == 0 and bool(lines) and all(SYNC_SUBJ_RE.match(x.strip()) for x in lines)


def _sniper_only_ahead(main, head):
    """사무실 v1.9.3: 서버 HEAD 가 origin/main 의 빨리감기이고 앞선 커밋이 전부 2번 스나이퍼 폴더만 건드리면 True (서버 앞섬 검사에서 스나이퍼 제외).
    올릴 내용에 비밀키로 보이는 값이 있으면 False. 스위치가 꺼져 있으면 항상 False(예전 동작)."""
    if not SCOPED or not main or main == head or git("merge-base", "--is-ancestor", main, head)[0] != 0:
        return False
    rc, out = git("rev-list", f"{main}..{head}", "--", ".", *[":(exclude)" + p for p in _sniper_prefixes()])
    if rc != 0 or out.strip():
        return False
    rc, d = git("diff", f"{main}..{head}")
    return rc == 0 and not SECRET_RE.search("\n".join(l for l in d.splitlines() if l.startswith("+")))


def status_skip_watch(st, today, result):
    """STATUS 기록을 건너뛴 이유가 이틀 연속 같으면 하루 1번 긴급 알림 (무인 기간에 STATUS 가 조용히 멈추지 않게)"""
    if not (isinstance(result, str) and result.endswith("건너뜀")):
        st.pop("status_skip", None)
        return False
    sk = st.get("status_skip") or {}
    if sk.get("reason") != result:
        st["status_skip"] = {"reason": result, "since": today}
        return False
    if sk.get("since", today) >= today or sk.get("alerted") == today:
        return False
    sk["alerted"] = today
    st["status_skip"] = sk
    text = ("[9번 업데이트 비서] STATUS.md 기록이 " + sk["since"] + " 부터 멈춰 있습니다\n"
            "· 이유: " + result + "\n· 봇 매매와는 별개입니다. 서버·GitHub 상태 확인이 필요합니다.")
    _hub_alert("9번 업데이트 비서", "critical", text)
    say(esc(text))
    return True


def status_daily(st, force=False):
    """하루 1번(06:10 KST 이후) STATUS.md 갱신 → main·staging 업로드. 대기 중인 업로드가 있으면 다음 날로 (staging 을 건드리지 않음)
    + 매일 서비스 점검(health_check)과 기록 건너뜀 감시(status_skip_watch) — 수동 기록(force)에서는 하지 않음"""
    now = datetime.now(KST)
    today = now.strftime("%Y-%m-%d")
    if not force and (now.hour * 100 + now.minute < 610 or st.get("status_day") == today):
        return None
    st["status_day"] = today
    if not force:
        try:
            health_check(st, today)
        except Exception as e:
            print("매일 점검 오류:", type(e).__name__, e, flush=True)
    r = _status_daily_write(st, force)
    if not force:
        try:
            status_skip_watch(st, today, r)
        except Exception as e:
            print("기록 건너뜀 감시 오류:", type(e).__name__, e, flush=True)
    return r


def _status_daily_write(st, force=False):
    if _dirty_code_files():
        return "서버에 저장 안 된 변경이 있어 건너뜀"
    _, head = git("rev-parse", "HEAD")
    rc_m, main = git("rev-parse", "origin/main")
    rc_s, stg = git("rev-parse", "origin/staging")
    if rc_m == 0 and main != head and (rc_s != 0 or stg == main) and (_only_sync_ahead(main, head) or _sniper_only_ahead(main, head)):
        # 2번 원작 자동 동기화 커밋만(또는 2번 스나이퍼 폴더만 바꾼 커밋만) 앞서 있음 → 빨리감기로 main·staging 에 올림 (강제 없음 · 실패하면 아래에서 건너뜀으로 끝남)
        rc_p, out_p = git("push", "-q", "origin", "HEAD:main", "HEAD:staging")
        if rc_p == 0:
            git("fetch", "-q", "origin")
            rc_m, main = git("rev-parse", "origin/main")
            rc_s, stg = git("rev-parse", "origin/staging")
        else:
            print("원작 동기화 커밋 업로드 실패:", SECRET_RE.sub("***", out_p[-160:]), flush=True)
    if rc_m or main != head:
        return "서버와 GitHub main 이 달라 건너뜀"
    if rc_s == 0 and stg != head:
        return "staging 에 대기 중인 업로드가 있어 건너뜀"
    changed = write_status("매일 점검" if not force else "수동 기록")
    tiers_written = write_sniper_tiers()
    need_exists = os.path.exists(os.path.join(REPO, NEED_FILE))
    if not changed and not tiers_written and not need_exists:
        return "바뀐 내용 없음"
    git("add", "-f", "--", *([STATUS_FILE] if changed else []), *([SNIPER_TIERS_FILE] if tiers_written else []),
        *([NEED_FILE] if need_exists else []))
    if not git("diff", "--cached", "--name-only")[1].strip():
        return "바뀐 내용 없음"
    git("commit", "-qm", "상태 기록: STATUS.md")
    rc, out = git("push", "-q", "origin", "HEAD:main", "HEAD:staging")
    if rc:
        return "GitHub 업로드 실패: " + out[-120:]
    return "STATUS.md 갱신·업로드 완료"


# ---------------------------------------------------------------- 적용
def _office_perm(existing):
    """복사할 파일의 주인·그룹·권한. 주인은 그대로, 그룹·읽기 권한은 office_secretary.py 와 같게 (비서 계정이 읽을 수 있게)
    (예전엔 새 파일을 root 전용 640 으로 만들어 pc_monitor.py 502, 있던 파일은 권한을 그대로 둬서 pixel_office.html 첫 화면 끊김)"""
    try:
        ref = os.stat(os.path.join(OFFICE_DIR, "office_secretary.py"))
    except OSError:
        ref = None
    try:
        st = os.stat(existing) if existing else None
    except OSError:
        st = None
    if not ref and not st:
        return 0, 0, 0o644
    base = st or ref
    uid, gid, mode = base.st_uid, base.st_gid, base.st_mode & 0o777
    if not st:
        mode &= ~0o111                        # 새 파일엔 실행 권한은 빼고
    if ref:
        if gid != ref.st_gid:                 # 그룹을 웹서버 그룹으로 바꿀 땐 그룹 쓰기 권한은 주지 않음
            gid = ref.st_gid
            mode &= ~0o020
        mode |= ref.st_mode & 0o044           # office_secretary.py 가 그룹·모두에게 읽기를 열어 둔 만큼 똑같이
    return uid, gid, mode | 0o400             # 주인은 항상 읽을 수 있게


def office_perm_repair():
    """/opt/bot-office 의 .py·.html·.css·.js 중 office_secretary.py 기준 읽기 권한이 빠진 파일만 고침 → 고친 파일 이름 목록"""
    fixed = []
    try:
        names = sorted(os.listdir(OFFICE_DIR))
    except OSError:
        return fixed
    for name in names:
        p = os.path.join(OFFICE_DIR, name)
        if not name.endswith(OFFICE_EXT) or not os.path.isfile(p) or os.path.islink(p):
            continue
        try:
            st = os.stat(p)
            uid, gid, mode = _office_perm(p)
            if (st.st_gid, st.st_mode & 0o777) != (gid, mode):
                os.chown(p, uid, gid); os.chmod(p, mode); fixed.append(name)
        except OSError as e:
            print("사무실 파일 권한 정리 실패:", name, type(e).__name__, flush=True)
    if fixed:
        print("사무실 파일 읽기 권한 고침:", ", ".join(fixed), flush=True)
    return fixed


def office_deploy(files):
    """저장소 bot_office/ 의 바뀐 파일을 서버 /opt/bot-office 로 복사 (덮어쓰기 전 파일은 백업) → 백업 목록 반환"""
    bk_dir = os.path.join(OFFICE_DIR, "_backups", "updater_" + datetime.now(KST).strftime("%Y%m%d_%H%M%S"))
    os.makedirs(bk_dir, exist_ok=True)
    saved = []
    for f in files:
        name = os.path.basename(f); src = os.path.join(REPO, f); dst = os.path.join(OFFICE_DIR, name)
        existed = os.path.exists(dst)
        if existed:
            subprocess.run(["cp", "-p", dst, os.path.join(bk_dir, name)], check=True)
            if name == SELF_FILE:
                subprocess.run(["cp", "-p", dst, os.path.join(OFFICE_DIR, "bot_updater.prev.py")], check=True)
        saved.append((dst, os.path.join(bk_dir, name) if existed else None))
        if os.path.exists(src):
            uid, gid, mode = _office_perm(dst if existed else None)
            tmp = dst + ".updtmp"
            subprocess.run(["cp", src, tmp], check=True); os.chmod(tmp, mode); os.chown(tmp, uid, gid); os.replace(tmp, dst)
        elif existed:
            os.remove(dst)
    return saved
 
 
def office_restore(saved):
    for dst, bk in saved:
        if bk:
            subprocess.run(["cp", "-p", bk, dst])
        elif os.path.exists(dst):
            os.remove(dst)
 
 
def briefing_deploy(files):
    """9번 브리핑: 저장소 bot_office/briefing/ 의 바뀐 파일을 서버 /opt/bot-office/briefing/ 으로 폴더 구조(sources/ 등) 그대로 복사 → 백업 목록 반환(office_restore 로 되돌림).
    systemd/ 유닛은 /etc/systemd/system 에 수동 설치하는 파일이라 복사하지 않는다. 재시작 없음 (one-shot 이라 다음 실행부터 새 코드)."""
    root = targets().get(BRIEFING_KEY)
    if not root or not files:
        return []
    bk_dir = os.path.join(OFFICE_DIR, "_backups", "updater_briefing_" + datetime.now(KST).strftime("%Y%m%d_%H%M%S"))
    base, saved = os.path.join(OFFICE_DIR, "briefing"), []
    for f in files:
        src = os.path.join(REPO, f)
        rel = os.path.relpath(os.path.realpath(src), root)
        if rel.startswith("..") or rel.split(os.sep)[0] == "systemd":
            continue
        dst = os.path.join(base, rel)
        existed = os.path.exists(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        bk = None
        if existed:
            bk = os.path.join(bk_dir, rel); os.makedirs(os.path.dirname(bk), exist_ok=True)
            subprocess.run(["cp", "-p", dst, bk], check=True)
        saved.append((dst, bk))
        if os.path.exists(src):
            uid, gid, mode = _office_perm(dst if existed else None)
            tmp = dst + ".updtmp"
            subprocess.run(["cp", src, tmp], check=True); os.chmod(tmp, mode); os.chown(tmp, uid, gid); os.replace(tmp, dst)
        elif existed:
            os.remove(dst)
    return saved


def header_version(files):
    """올린 파일 머리말의 코드 자체 버전 (# 4bot N번 vX.Y.Z, 숫자만 · v1.5.6 제외).
    main.py 머리말을 우선, 없으면 바뀐 파일 중 처음 찾은 것. 없으면 None (기존 방식 유지)."""
    ordered = sorted(files, key=lambda f: (os.path.basename(f) != "main.py", f))
    for f in ordered:
        try:
            with open(os.path.join(REPO, f), encoding="utf-8") as fh:
                head = "".join(fh.readline() for _ in range(40))
        except OSError:
            continue
        m = re.search(r"#\s*4bot\s+\d+번\s+v(\d+)\.(\d+)\.(\d+)", head)
        if m:
            return f"v{m.group(1)}.{m.group(2)}.{m.group(3)}"
    return None


def bump_versions(units, old_head):
    """3·4번처럼 BOT_VERSION 이 있는 봇은 이번 수정에서 안 올렸으면 자동으로 한 칸 (v4.3 → v4.3.1)"""
    out = {}
    roots = targets()
    for u in units:
        root = roots.get(u, "")
        for f in sorted(os.listdir(root)) if root else []:
            if not (f.endswith("_core.py") or f == "averaging_plugin.py"):   # 2번 스나이퍼 버전은 averaging_plugin.py
                continue
            p = os.path.join(root, f); src = open(p, encoding="utf-8").read()
            m = re.search(r"""^(BOT_VERSION\s*=\s*["'])v?(\d+)\.(\d+)(?:\.(\d+))?(["'])""", src, re.M)
            if not m:
                continue
            rel = os.path.relpath(p, REPO)
            rc, old = git("show", f"{old_head}:{rel}")
            om = re.search(r"""BOT_VERSION\s*=\s*["']([^"']+)""", old) if rc == 0 else None
            cur = f"v{m.group(2)}.{m.group(3)}" + (f".{m.group(4)}" if m.group(4) else "")
            if om and om.group(1) == cur:
                _x, _y, _z = int(m.group(2)), int(m.group(3)), int(m.group(4) or 0)
                if _z < 9:
                    _x, _y, _z = _x, _y, _z + 1
                elif _y < 9:
                    _x, _y, _z = _x, _y + 1, 0
                else:
                    _x, _y, _z = _x + 1, 0, 0
                cur = f"v{_x}.{_y}.{_z}"
                open(p, "w", encoding="utf-8").write(src[:m.start()] + m.group(1) + cur + m.group(5) + src[m.end():])
            out[u] = cur
    return out
 
 
VNEXT = "v" + "NEXT"   # 버전 자동 기입 표시 글자 (코드에 붙여 쓰면 적용 때 이 줄까지 바뀌므로 조립)


def fill_vnext(files, ver, office=False):
    """올린 파일 속 VNEXT 표시 글자 → 이번에 정해진 버전 (저장소 파일 + 사무실이면 /opt/bot-office 복사본도). 실패해도 업데이트는 계속"""
    for f in files:
        paths = [os.path.join(REPO, f)] + ([os.path.join(OFFICE_DIR, os.path.basename(f))] if office else [])
        for p in paths:
            try:
                with open(p, encoding="utf-8") as fh:
                    src = fh.read()
                if VNEXT not in src:
                    continue
                st = os.stat(p)
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(re.sub(r"\b" + VNEXT + r"\b", ver, src))
                os.chown(p, st.st_uid, st.st_gid)
            except Exception as e:
                print("버전 자동 기입 실패:", p, type(e).__name__, flush=True)


def next_tag(prefix):
    """버전 숫자 최대 9 굴림: 마지막이 9를 넘으면 중간을 올리고 마지막을 0으로, 중간도 9를 넘으면 앞을 올림."""
    _, tags = git("tag", "-l", f"{prefix}-v*")
    nums = [tuple(map(int, m.groups())) for t in tags.split() if (m := re.fullmatch(re.escape(prefix) + r"-v(\d+)\.(\d+)\.(\d+)", t))]
    x, y, z = max(nums, default=(1, 0, 0))
    if z < 9:
        return f"v{x}.{y}.{z + 1}"
    if y < 9:
        return f"v{x}.{y + 1}.0"
    return f"v{x + 1}.0.0"
 
 
def healthy(unit):
    _, n0 = sh(SYSTEMCTL, "show", unit, "-p", "NRestarts", "--value")
    for _ in range(4):
        time.sleep(float(os.environ.get("U_WAIT", "4")))
        if sh(SYSTEMCTL, "is-active", unit)[1] != "active":
            return False
    return sh(SYSTEMCTL, "show", unit, "-p", "NRestarts", "--value")[1] == n0
 
 
def restart_service(unit, active=None):
    """재시작. active(업데이트 전 is-active 스냅샷)가 참일 때만 enable 먼저 — 재부팅 뒤에도 살아남게.
    active 를 안 넘기면 지금 한 번 판정. 정지돼 있던 서비스는 enable 안 함. enable 실패는 로그만 남기고 재시작은 계속."""
    if active is None:
        active = sh(SYSTEMCTL, "is-active", unit)[1].strip() == "active"
    if active:
        rc, out = sh(SYSTEMCTL, "enable", unit)
        if rc:
            print("enable 실패(재시작은 계속):", unit, SECRET_RE.sub("***", out)[-200:], flush=True)
    sh(SYSTEMCTL, "restart", unit)
    return active


# ---------------------------------------------------------------- 사무실 v1.9.3: 봇별 보류(D) · 병합에서 파일 빼기 · 보류 재시도
def git_env(extra, *a, timeout=120):
    """git() 과 같되 환경변수를 더 줌 (임시 인덱스 파일 등)"""
    cmd = ["env", f"HOME={OWNER.pw_dir}", "GIT_TERMINAL_PROMPT=0", *[f"{k}={v}" for k, v in extra.items()],
           "git", "-c", "core.quotepath=false", "-C", REPO, *a]
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    return sh(*cmd, timeout=timeout)


def _unit_dir_files(unit, files):
    """바뀐 파일 중 이 봇 폴더 바로 아래 파일 (classify 가 봇 파일로 보는 것과 같은 기준 · .md 포함)"""
    root = targets().get(unit, "")
    return [f for f in files if root and os.path.dirname(os.path.realpath(os.path.join(REPO, f))) == root]


def _blob(ref, f):
    rc, b = git("rev-parse", "-q", "--verify", f"{ref}:{f}")
    return b if rc == 0 else ""


def _ahead_reason(unit, sha, unit_files):
    """B: 서버에만 있는 커밋(origin/main 에도, 이 브랜치에도 없음)이 이번에 바뀌는 이 봇 파일을 이미 고쳐 놓았으면 사유 문장.
    그 파일을 브랜치 것으로 덮으면 서버 로컬 수정이 사라지므로 이 봇만 보류한다. 스위치 꺼짐·스나이퍼는 ''."""
    if not SCOPED or unit == SNIPER_UNIT or not unit_files:
        return ""
    root = targets().get(unit, "")
    if not root or git("rev-parse", "-q", "--verify", "origin/main")[0]:
        return ""
    rel = os.path.relpath(root, os.path.realpath(REPO))
    rc, out = git("log", "--format=", "--name-only", "HEAD", "^origin/main", "^" + sha, "--", rel)
    if rc:
        return ""
    both = sorted({x.strip() for x in out.splitlines() if x.strip()} & set(unit_files))
    if both:
        return "서버에만 있는 수정과 겹침 — 앞섬, 사람 승인 필요 (" + ", ".join(os.path.basename(x) for x in both[:4]) + ")"
    return ""


def _unit_hold_reason(unit, sha, unit_files, verified=None):
    """봇 하나를 지금 적용하면 안 되는 이유 → (종류, 문장). 종류: 'ahead' 사람 승인 필요 · 'busy' 풀리면 자동 재시도 · '' 적용 가능.
    verified: 일시중지(DC) 확인이 끝난 봇이면 True/False 로 넘김(apply 안). None 이면 여기서 확인."""
    r = _ahead_reason(unit, sha, unit_files)
    if r:
        return "ahead", r
    if verified is None:
        verified = False
        root = targets().get(unit)
        if unit in DC.UNITS.values() and root and DC.state_path(root).exists():
            try:
                state = DC.read(DC.state_path(root))
            except Exception:
                return "busy", "중지 상태 파일을 확인할 수 없음"
            if state.get("phase") in ("waiting", "paused"):
                if not DC.ready(sys.modules[__name__], unit):
                    return "busy", uname(unit) + " 보유/미체결 또는 실행 차단 확인 대기 중"
                verified = True
    r = busy_reason(unit, verified)
    if not r and unit == OFFICE_KEY and {os.path.basename(f) for f in unit_files} & set(OFFICE_EXTRA[FANDING_UNIT]):
        r = busy_reason(FANDING_UNIT)
        r = ("4번 팬딩: " + r) if r else ""
    return ("busy", r) if r else ("", "")


def _restore_paths(old_head, files):
    """files 를 old_head 때 모습으로 되돌림 (그때 있던 파일은 복원, 병합이 새로 만든 파일은 삭제)"""
    keep, drop = [], []
    for f in files:
        (keep if git("cat-file", "-e", f"{old_head}:{f}")[0] == 0 else drop).append(f)
    if keep:
        git("checkout", old_head, "--", *keep)
    if drop:
        git("rm", "-f", "-q", "--ignore-unmatch", "--", *drop)


def _merge_excluding(br, sha, old_head, excluded):
    """병합하되 excluded 파일(스나이퍼 파일·보류한 봇 파일)은 병합 전 모습 그대로 둔다 — 가져오기·덮어쓰기·삭제 전부 안 함.
    충돌이 excluded 파일에서만 나면 그 파일은 서버 것으로 정리하고 계속, 다른 파일 충돌이면 병합을 취소. → (성공 여부, git 출력)"""
    ex = set(excluded)
    rc, out = git("merge", "--no-ff", "--no-commit", sha)
    merging = git("rev-parse", "-q", "--verify", "MERGE_HEAD")[0] == 0
    if rc:
        if not merging:
            return False, out   # 시작도 못 함 (서버 저장 안 된 변경과 겹침 등)
        bad = [f for f in git("diff", "--name-only", "--diff-filter=U")[1].splitlines() if f.strip() and f not in ex]
        if bad:
            git("merge", "--abort")
            return False, out
    if merging:
        _restore_paths(old_head, sorted(ex))
        if git("diff", "--name-only", "--diff-filter=U")[1].strip():
            git("merge", "--abort")
            return False, out
        rc2, out2 = git("commit", "-q", "-m", f"update: {br}")
        if rc2:
            git("merge", "--abort")
            return False, out2
    return True, out


def _record_holds(br, sha, old_head, held, kinds, files):
    """보류한 봇을 보류 목록에 적음 (같은 커밋이면 갱신). 재시도 때 서버가 그 파일을 그사이 안 바꿨는지 보려고 보류 시점 파일 해시도 적어 둠"""
    data = load(HOLDS, {})
    items = data.setdefault("items", {})
    key = sha[:12]
    unit_files, blobs = {}, {}
    for u in held:
        fs = _unit_dir_files(u, files)
        unit_files[u] = fs
        for f in fs:
            blobs[f] = _blob(old_head, f)
    _, subj = git("log", "-1", "--format=%s", sha)
    e = items.get(key) or {"since": time.time(), "tries": 0}
    e.update({"branch": br, "sha": sha, "subject": subj, "units": dict(held), "kinds": dict(kinds), "files": unit_files, "blobs": blobs,
              "stuck": all(k == "ahead" for k in kinds.values())})
    items[key] = e
    save(HOLDS, data)


def _hold_commit(sha, files, subject):
    """지금 HEAD 위에, files 만 sha(원래 브랜치) 모습으로 바꾼 커밋을 만들어 sha 반환 (HEAD·작업 폴더는 안 건드림). 실패하면 None"""
    fd, idx = tempfile.mkstemp(prefix="updater_idx_")
    os.close(fd)
    os.unlink(idx)
    env = {"GIT_INDEX_FILE": idx}
    try:
        if git_env(env, "read-tree", "HEAD")[0]:
            return None
        for f in files:
            rc, ls = git("ls-tree", sha, "--", f)
            if rc:
                return None
            if ls.strip():
                meta, _, _path = ls.partition("\t")
                mode, _typ, h = meta.split()
                if git_env(env, "update-index", "--add", "--cacheinfo", f"{mode},{h},{f}")[0]:
                    return None
            else:
                git_env(env, "update-index", "--force-remove", "--", f)
        rc, tree = git_env(env, "write-tree")
        if rc:
            return None
        rc, commit = git_env(env, "commit-tree", tree, "-p", "HEAD", "-m", subject)
        return commit if rc == 0 and re.fullmatch(r"[0-9a-f]{40,64}", commit or "") else None
    finally:
        try:
            os.unlink(idx)
        except OSError:
            pass


def retry_holds(st):
    """보류 목록 재시도 (확인 주기마다 호출). 매매 중·일시중지 대기가 풀린 봇만 다시 적용하고, 아직이면 조용히 기다린다.
    앞섬 보류는 자동으로 적용하지 않는다 (서버 로컬 수정을 덮어쓸 수 있음) — 사람이 서버와 브랜치를 맞추면(파일이 같아지면) 목록에서 빠진다.
    보류 시점 이후 서버가 그 파일을 바꿨거나 연속 HOLD_RETRY_MAX 번 실패하면 멈추고 사람 확인으로 알린다."""
    if not SCOPED:
        return
    data = load(HOLDS, {})
    items = data.get("items", {})
    if not items:
        return
    dirty_flag = False
    for key, e in list(items.items()):
        sha, ufiles = e.get("sha", ""), e.get("files") or {}
        for u in list(e.get("units", {})):   # 사람이 이미 서버를 브랜치와 같게 맞춘 봇은 목록에서 뺌
            fs = ufiles.get(u, [])
            if fs and all(_blob("HEAD", f) == _blob(sha, f) for f in fs):
                e["units"].pop(u, None); e.get("kinds", {}).pop(u, None); dirty_flag = True
        if not e.get("units"):
            items.pop(key, None); dirty_flag = True
            continue
        ready = []
        for u in list(e["units"]):
            if e.get("kinds", {}).get(u) == "ahead":
                continue
            kind, why = _unit_hold_reason(u, sha, ufiles.get(u, []))
            if kind == "ahead":   # 보류 뒤 서버에 겹치는 수정이 생김 → 사람 승인으로
                e.setdefault("kinds", {})[u] = "ahead"; e["units"][u] = why; e["stuck"] = True; dirty_flag = True
            elif kind == "busy":
                if e["units"].get(u) != why:
                    e["units"][u] = why; dirty_flag = True
            else:
                ready.append(u)
        if e.get("stuck") or not ready:
            continue
        files = [f for u in ready for f in ufiles.get(u, [])]
        moved = [f for f in files if _blob("HEAD", f) != e.get("blobs", {}).get(f, "")]
        if moved:   # 보류 뒤 서버에서 그 파일이 바뀜 → 자동으로 덮어쓰지 않음
            e["stuck"] = True; dirty_flag = True
            say("<b>[업데이트 비서] 보류한 업데이트를 자동으로 적용하지 않았습니다</b>\n· 대상: " + esc(", ".join(uname(u) for u in ready))
                + "\n· 보류한 뒤 서버에서 같은 파일이 바뀌었어요: " + esc(", ".join(os.path.basename(f) for f in moved[:4]))
                + "\n→ 사람이 서버와 브랜치 <code>" + esc(e.get("branch", "-")) + "</code> 를 확인해 주세요.")
            continue
        if _dirty_code_files(include_staged=True, scope=(ready, files)):
            continue   # 서버에 저장 안 된 변경이 있으면 풀릴 때까지 조용히 기다림
        commit = _hold_commit(sha, files, (e.get("subject") or e.get("branch", "update")) + " (보류 반영)")
        e["tries"] = e.get("tries", 0) + 1; dirty_flag = True
        applied = False
        if commit:
            hk = "hold" + key[:8]
            st.setdefault("offers", {})[hk] = {"branch": "hold/" + key, "sha": commit, "at": time.time(), "local": True}
            say("보류했던 업데이트를 다시 적용합니다… (" + esc(", ".join(uname(u) for u in ready)) + ")")
            try:
                apply(st, hk)
            finally:
                st["offers"].pop(hk, None)
            applied = git("merge-base", "--is-ancestor", commit, "HEAD")[0] == 0
        if applied:
            for u in ready:
                e["units"].pop(u, None); e.get("kinds", {}).pop(u, None)
            e["tries"] = 0
            if not e["units"]:
                items.pop(key, None)
                br = e.get("branch", "")
                if br and br != "staging" and not br.startswith("hold/") and _blob_ref_sha(br) == sha:
                    git("push", "-q", "origin", "--delete", br)   # 보류가 다 풀려 끝났으니 옛 브랜치 정리 (그사이 바뀌었으면 안 지움)
        elif e["tries"] >= HOLD_RETRY_MAX:
            e["stuck"] = True
            say("<b>[업데이트 비서] 보류한 업데이트를 " + str(HOLD_RETRY_MAX) + "번 다시 적용했지만 실패했습니다</b>\n· 대상: "
                + esc(", ".join(uname(u) for u in ready)) + "\n→ 자동 재시도를 멈췄습니다. 사람이 확인해 주세요.")
    if dirty_flag:
        save(HOLDS, data)


def _blob_ref_sha(br):
    rc, s = git("rev-parse", "-q", "--verify", f"origin/{br}")
    return s if rc == 0 else ""


def write_changelog(root, name, ver, now, files, msgs, br):
    """audit-fix 9-1: 봇 폴더 CHANGELOG.md 맨 위에 한 건 추가 → 성공 None, 실패 '오류 글자'. 어떤 오류도 밖으로 안 던짐 (기록 실패가 커밋·태그·푸시를 막지 않게).
    임시 파일에 쓴 뒤 바꿔치기 → 쓰다 실패해도 기존 CHANGELOG 가 잘리지 않음"""
    tmp = None
    try:
        log = os.path.join(root, "CHANGELOG.md"); head = f"# {name} 변경 기록\n\n"
        old = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
        m_head = re.match(r"# [^\n]*변경 기록\n\n", old)   # v1.8.7: 이름이 바뀐 옛 제목 줄도 한 줄만 남게 (예: '# 5번 사무실 비서 변경 기록')
        body = old[m_head.end():] if m_head else old
        fl = ", ".join(os.path.basename(f) for f in files) or "문서"
        tmp = log + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(head + f"## {ver} · {now} (KST)\n- 파일: {fl}\n- 내용: {msgs.splitlines()[0] if msgs else br}\n- 브랜치: {br}\n\n" + body)
        os.chown(tmp, OWNER.pw_uid, OWNER.pw_gid)
        os.replace(tmp, log); tmp = None
        return None
    except Exception as e:
        print("CHANGELOG 기록 실패:", type(e).__name__, e, flush=True)
        return f"{type(e).__name__}: {str(e)[:80]}"
    finally:
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass


def push_main_then_staging(tags, br, local, held, git_fn=None):
    """audit-fix 9-2: main 푸시 → 성공했을 때만 (필요하면 옛 브랜치 삭제 +) staging 을 최신 main 기준으로 맞춤. → (rc, out, staging 밀었는지)
    main 푸시가 실패하면 staging 은 건드리지 않음 (예전엔 실패해도 강제 푸시로 staging 을 덮었음)"""
    g = git_fn or git
    rc, out = g("push", "-q", "origin", "HEAD:main", *tags)
    if rc != 0:
        return rc, out, False
    if br != "staging" and not local and not held:   # 보류한 봇이 남아 있으면 브랜치를 지우지 않음 (보류가 다 풀리면 정리)
        g("push", "-q", "origin", "--delete", br)
    g("push", "-q", "-f", "origin", "HEAD:staging")   # 다음 수정은 항상 최신 main 기준 staging 에서
    return rc, out, True


def apply(st, key):
    o = st.get("offers", {}).get(key)
    if not o:
        return say("이 업데이트 정보를 찾지 못했습니다. GitHub에 다시 올리면 새로 알려 드려요.")
    br, sha = o["branch"], o["sha"]
    if not o.get("local"):   # local: 보류 재시도용 서버 안 커밋 (GitHub 브랜치가 아님)
        git("fetch", "-q", "origin")
        rc, now_sha = git("rev-parse", f"origin/{br}")
        if rc or now_sha != sha:
            return say("그사이 브랜치가 바뀌었거나 사라졌습니다. 새 알림의 버튼을 눌러 주세요.")
    _, files = git("diff", "--name-only", f"HEAD...{sha}")
    files = [f for f in files.splitlines() if f.strip()]
    units, skipped = classify(files)
    if skipped:   # 막지 않고 기록만 — 무엇을 빼고 적용했는지 나중에 보이게
        print("배포에서 빠진 파일(적용 안 함):", key, ", ".join(skipped), flush=True)
    units = {u: fs for u, fs in units.items() if fs}   # 문서(.md)만 바뀐 봇은 재시작·버전 기록 안 함
    _, added = git("diff", f"HEAD...{sha}")
    if SECRET_RE.search("\n".join(l for l in added.splitlines() if l.startswith("+"))):
        return say("바뀐 내용에 비밀키로 보이는 값이 있어 적용하지 않았습니다. GitHub에서 그 내용을 지우고 키는 새로 발급해 주세요.")
    pause_verified = set()
    held, held_kind, dc_rows = {}, {}, []   # 사무실 v1.9.3(D): 이번에 적용하지 않고 보류할 봇 → 사유 · 종류('busy' 자동 재시도 / 'ahead' 사람 승인) · 재개 버튼
    for unit in units:
        root = targets().get(unit)
        if unit in DC.UNITS.values() and DC.state_path(root).exists():
            try:
                state = DC.read(DC.state_path(root))
            except Exception:
                return say("중지 상태 파일을 확인할 수 없습니다. 적용하지 않았습니다.")
            if state.get('phase') == 'paused':
                transport = 'kis_api_client.py' if unit == DC.UNITS['1'] else 'b_core.py' if unit == DC.UNITS['4'] else 'toss_api.py'
                relative = os.path.relpath(root, REPO)
                marker = 'with gate():' if unit == DC.UNITS['4'] else '@__import__("deployment_gate").transport'
                rc, source = git('show', sha + ':' + relative + '/' + transport)
                rc_gate, gate_source = git('show', sha + ':' + relative + '/deployment_gate.py')
                if rc or rc_gate or marker not in source or 'VERSION = 1' not in gate_source:
                    return say('업데이트 코드에 신규 주문 차단 연결이 없습니다. 차단 부품을 보존한 수정본이 필요합니다.')
            if state.get('phase') not in ('running','waiting','paused'):
                return say('일시중지 상태 값이 잘못돼 적용하지 않았습니다.')
            if state.get('phase') in ('waiting','paused'):
                if not DC.ready(sys.modules[__name__],unit):
                    if SCOPED:   # D: 이 봇만 보류, 나머지는 계속
                        held[unit], held_kind[unit] = NAMES.get(unit, unit) + " 보유/미체결 또는 실행 차단 확인 대기 중", "busy"
                        dc_rows.extend(DC.resume_rows(unit))
                        continue
                    return say("" + NAMES[unit] + " 보유/미체결 또는 실행 차단 확인 대기 중입니다. 적용하지 않았습니다.", DC.resume_rows(unit))
                pause_verified.add(unit)
    all_files = list(files)   # 보류·스나이퍼 때문에 병합에서 뺄 파일을 정하기 전의 전체 목록
    if SCOPED:
        # D(봇별 보류) + B(서버 앞섬): 지금 적용하면 안 되는 봇만 보류하고 나머지는 진행한다
        for u in units:
            if u in held:
                continue
            kind, why = _unit_hold_reason(u, sha, _unit_dir_files(u, all_files), verified=(u in pause_verified))
            if kind:
                held[u], held_kind[u] = why, kind
        if held and set(held) >= set(units):   # 전부 보류면 아무것도 적용하지 않음 (예전 안내와 같은 모양) — 보류 목록에는 기록함 (v2: 쌓인 보류가 잊히지 않게)
            if not o.get("local"):   # 보류 재시도(retry_holds)가 부른 apply 는 이미 목록에 있는 항목이므로 새로 적지 않음
                try:
                    _record_holds(br, sha, git("rev-parse", "HEAD")[1], held, held_kind, all_files)
                except Exception as e:
                    print("보류 목록 기록 실패:", type(e).__name__, e, flush=True)
            return say("<b>지금은 적용하지 않았습니다</b>\n· " + "\n· ".join(esc(uname(u) + ": " + r) for u, r in held.items())
                       + ("\n· 앞섬은 사람 승인이 필요합니다 (서버 수정을 브랜치에 합쳐 다시 올려 주세요)." if "ahead" in held_kind.values() else "\n· 나중에 같은 알림의 업데이트 버튼을 다시 눌러 주세요."),
                       [[{"text": "다시 시도", "callback_data": f"up:{key}"}]] + dc_rows +
                       [[{"text": "" + NAMES[u] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + n}] for n,u in DC.UNITS.items() if u in units and gate_installed(u)])
    else:
        busy = [f"{uname(u)}: {r}" for u in units if (r := busy_reason(u, u in pause_verified))]
        if {os.path.basename(f) for f in units.get(OFFICE_KEY, [])} & set(OFFICE_EXTRA[FANDING_UNIT]) and (r := busy_reason(FANDING_UNIT)):
            busy.append("4번 팬딩: " + r)
        if busy:
            return say("<b>지금은 적용하지 않았습니다</b>\n· " + "\n· ".join(esc(b) for b in busy) + "\n· 나중에 같은 알림의 업데이트 버튼을 다시 눌러 주세요.",
                       [[{"text": "다시 시도", "callback_data": f"up:{key}"}]] +
                       [[{"text": "" + NAMES[u] + " 비울 때 일시중지", "callback_data": "ps:" + key + ":" + n}] for n,u in DC.UNITS.items() if u in units and gate_installed(u)])
    # A: 저장 안 된 변경 검사 — 이번에 적용할 봇 폴더 + 공용 파일 + 이번에 바뀌는 파일에 겹치는 것만 (스나이퍼 폴더는 제외). 스위치를 끄면 저장소 전체
    dirty = _dirty_code_files(include_staged=True, scope=([u for u in units if u not in held], all_files) if SCOPED else None)
    if dirty:
        return say("서버에 저장 안 된 변경이 있어 멈췄습니다." + ("\n· " + esc(", ".join(dirty[:6]) + (" 외" if len(dirty) > 6 else "")) if SCOPED else ""))
    rc_m, main_sha = git("rev-parse", "origin/main")
    if SCOPED and rc_m == 0:   # 서버 앞섬 검사에서 스나이퍼 폴더만 바꾼 main 수정은 제외 (main 에만 있고 서버·이 브랜치에 없는 수정이 있는지)
        main_only = git("rev-list", main_sha, "^HEAD", "^" + sha, "--", ".", *[":(exclude)" + p for p in _sniper_prefixes()])[1].strip()
        main_blocked = bool(main_only)
    else:
        main_blocked = rc_m == 0 and git("merge-base", "--is-ancestor", main_sha, "HEAD")[0] and git("merge-base", "--is-ancestor", main_sha, sha)[0]
    if main_blocked:
        return say("GitHub main 에 서버를 거치지 않은 수정이 있고, 이 브랜치는 그 수정을 포함하지 않아 적용하지 않았습니다.\n"
                   "· 그대로 적용하면 main 업로드가 실패하고 서버·main 이 더 어긋납니다.\n"
                   "→ main 기준 새 브랜치로 먼저 승인하거나, 이 브랜치를 최신 main 기준으로 다시 올려 주세요.")
    _, old_head = git("rev-parse", "HEAD")
    units = {u: fs for u, fs in units.items() if u not in held}   # 보류한 봇은 이번에 적용하지 않음 (재시작·버전 기록도 안 함)
    held_note = ""
    if held:
        held_note = "\n· 보류: " + "; ".join(uname(u) + " — " + r for u, r in held.items())
    say(f"업데이트 적용 중… ({esc(', '.join(uname(u) for u in units) or '문서')})" + esc(held_note))
    # 병합에서 뺄 파일: 2번 스나이퍼 폴더(가져오기·덮어쓰기·삭제 안 함) + 보류한 봇 폴더 파일
    excluded = []
    if SCOPED:
        sniper_pre = _sniper_prefixes()
        excluded = sorted({f for f in all_files if f.startswith(sniper_pre)} | {f for u in held for f in _unit_dir_files(u, all_files)})
    if excluded:
        ok_merge, out = _merge_excluding(br, sha, old_head, excluded)
        rc = 0 if ok_merge else 1
    else:
        rc, out = git("merge", "--no-edit", "-m", f"update: {br}", sha)
        if rc:
            git("merge", "--abort")
    if rc:
        try:   # v1.8.1: 옛(리베이스 전) 브랜치면 충돌 정리가 아니라 지우기를 안내 (안내만 · 병합 중단은 위와 같음)
            sup = superseded(sha, live_branches())
        except Exception:
            sup = None
        rows = ([_drop_row(key)] if sup else []) + ([[{"text": "이전 변경·충돌 정리", "callback_data": "cp:" + key}]] if UC else [])
        return say("서버 코드와 업데이트 브랜치가 충돌해 적용하지 않았습니다. 이미 처리한 이전 변경만 선택해 정리한 뒤 새 알림으로 승인하세요."
                   + ("\n\n· 서버에 저장 안 된 변경과 겹쳐 병합을 시작하지 못했습니다 — 겹치는 파일을 브랜치에서 빼거나 서버 변경을 정리해 주세요." if SCOPED and "overwritten" in (out or "") else "")
                   + ("\n\n" + _superseded_text(sup) if sup else ""), rows or None)
    # 되돌릴 때 --hard 는 서버에 저장 안 된 변경(예: 스나이퍼 임시 수정)까지 지우므로, 스위치가 켜져 있으면 --keep (그 변경은 그대로 두고 병합 결과만 되돌림)
    reset_mode = "--keep" if SCOPED else "--hard"
    foreign_staged = set(git("diff", "--cached", "--name-only")[1].split()) if SCOPED else set()   # 병합 직후 이미 스테이징돼 있던 남의 변경 (이번 버전 기록 커밋에 섞지 않음)
    bad_py = [f for fs in units.values() for f in fs if f.endswith(".py") and os.path.exists(os.path.join(REPO, f)) and sh(sys.executable, "-m", "py_compile", os.path.join(REPO, f))[0]]
    if bad_py:
        git("reset", "-q", reset_mode, old_head)
        return say("문법 오류가 있어 원래대로 되돌렸습니다: " + esc(", ".join(bad_py)))
    vers = bump_versions([u for u in units if u != OFFICE_KEY], old_head)
    office_files = units.get(OFFICE_KEY, [])
    saved = office_deploy(office_files) if office_files else []
    saved += briefing_deploy(units.get(BRIEFING_KEY, []))   # 9번 브리핑: /opt/bot-office/briefing/ 로 복사 (실패 시 아래 되돌림에 같이 포함)
    perm_fixed = office_perm_repair() if office_files else []
    self_update = any(os.path.basename(f) in (SELF_FILE, "update_conflicts.py", "sniper_upstream.py") for f in office_files)
    restart = [u for u in units if u not in (OFFICE_KEY, BRIEFING_KEY)]   # v1.8.7: 사무실 폴더 키는 서비스가 아니라 재시작하지 않음 (웹 사무실 삭제) · v1.9.4: 브리핑 키도 제외 (one-shot 재시작=텔레그램 발송)
    names_changed = {os.path.basename(f) for f in office_files}
    for xu, xfiles in OFFICE_EXTRA.items():   # 비서·팬딩 상시 서비스도 관련 파일이 바뀌었으면 재시작 (설치돼 있을 때만)
        if names_changed & set(xfiles) and sh(SYSTEMCTL, "is-active", xu)[1].strip() == "active":   # 지금 실행 중인 것만 (비서는 disabled 지만 실행 중)
            restart.append(xu)
    # 업데이트 전 실행 상태 스냅샷 — 첫 재시작 직전에 한 번만 판정, 되돌림 때도 이 값을 다시 씀 (정지돼 있던 서비스는 끝까지 enable 안 함)
    was_active = {u: sh(SYSTEMCTL, "is-active", u)[1].strip() == "active" for u in restart}
    failed = []
    for u in restart:
        restart_service(u, was_active[u])
        if not healthy(u):
            failed.append(u)
    if failed:
        git("reset", "-q", reset_mode, old_head)
        office_restore(saved)
        for u in restart:
            restart_service(u, was_active[u])
        return say("<b>업데이트 후 봇이 정상 실행되지 않아 원래 코드로 되돌렸습니다</b>\n· " + esc(", ".join(uname(u) for u in failed)) + "\n· 봇은 이전 버전으로 다시 켜졌습니다.")
    # 버전 기록 (봇 폴더 CHANGELOG.md) → 커밋 → 태그 → main 업로드
    _, msgs = git("log", "--format=%s", f"{old_head}..{sha}", "-n", "8")
    tags, roots, now = [], targets(), datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    changelog_failed = []
    for u in units:
        prefix = u.replace(".service", "")
        # 2번 스나이퍼: BOT_VERSION이 없어 태그 카운터(v1.2.3식)가 붙던 것을 코드 머리말 버전(v2.5.2식)으로 기록. 머리말 없으면 기존 방식 유지.
        ver = vers.get(u) or (header_version(units[u]) if prefix == "toss_sniper" else None) or next_tag(prefix)
        if not ver.count(".") == 2:
            ver = next_tag(prefix)
        if git("rev-parse", "-q", "--verify", f"refs/tags/{prefix}-{ver}")[0] == 0:
            ver = next_tag(prefix)
        fill_vnext(units[u], ver, u == OFFICE_KEY)   # bot_office/ 파일은 /opt/bot-office 복사본에도 버전 채움 (office=True 유지)
        err_cl = write_changelog(roots[u], uname(u), ver, now, units[u], msgs, br)   # audit-fix 9-1: 기록 실패는 배포(커밋·태그·푸시)를 막지 않고 보고만
        if err_cl:
            changelog_failed.append(f"{uname(u)}: {err_cl}")
        tags.append(f"{prefix}-{ver}")
    if units:   # 적용 전 작업 폴더가 깨끗했으므로, 바뀐 건 이번 수정·버전 올림·CHANGELOG 뿐
        git("add", "-u", "--", *{os.path.relpath(roots[u], REPO) for u in units})
        git("add", "-f", "--", *{os.path.join(os.path.relpath(roots[u], REPO), "CHANGELOG.md") for u in units})
    try:   # 현재 상태 파일도 같은 기록에 함께 (실패해도 업데이트는 계속)
        if write_status(f"업데이트 적용 ({br}: {msgs.splitlines()[0] if msgs else ''})"):
            git("add", "-f", "--", STATUS_FILE)
        if write_sniper_tiers():
            git("add", "-f", "--", SNIPER_TIERS_FILE)
        if os.path.exists(os.path.join(REPO, NEED_FILE)):
            git("add", "-f", "--", NEED_FILE)
    except Exception as e:
        print("STATUS.md 작성 실패:", type(e).__name__, e, flush=True)
    staged_now = git("diff", "--cached", "--name-only")[1].split()
    if staged_now:
        msg_c = ("버전 기록: " + ", ".join(tags)) if tags else "상태 기록: STATUS.md"
        mine = [n for n in staged_now if n not in foreign_staged]
        if foreign_staged and mine:
            git("commit", "-qm", msg_c, "--", *mine)   # 남이 스테이징해 둔 변경(예: 스나이퍼 임시 수정)은 이 기록에 안 섞음
        elif not foreign_staged:
            git("commit", "-qm", msg_c)
    for t in tags:
        git("tag", t)
    rc, out, staging_pushed = push_main_then_staging(tags, br, bool(o.get("local")), bool(held))   # audit-fix 9-2: main 푸시가 성공했을 때만 staging 을 맞춤
    st.setdefault("seen", {}).pop(br, None)
    if held:   # D: 적용하지 않은 봇을 보류 목록에 적음 (staging 을 main 으로 맞춰도 내용은 서버에 남음)
        try:
            _record_holds(br, sha, old_head, held, held_kind, all_files)
        except Exception as e:
            print("보류 목록 기록 실패:", type(e).__name__, e, flush=True)
    done = ", ".join(uname(u) + " " + t.rsplit("-", 1)[-1] for u, t in zip(units, tags)) or "문서만 반영"
    held_msg = ""
    if held:
        held_msg = ("\n· <b>보류</b>: " + esc("; ".join(uname(u) + " — " + r for u, r in held.items()))
                    + "\n· 매매 중·일시중지 대기는 풀리면 자동으로 다시 적용하고, 앞섬은 사람 승인이 필요합니다 (보류 목록은 STATUS.md)")
    say(f"<b>업데이트 완료</b>\n· {esc(done)}\n"
        + (f"· 사무실 파일 읽기 권한 고침: {esc(', '.join(perm_fixed))}\n" if perm_fixed else "")
        + f"· 재시작 정상 확인 · GitHub main {'업로드 완료' if rc == 0 else '업로드 실패(봇은 새 코드로 정상 실행 중): ' + esc(out[-150:])}"
        + ("" if staging_pushed else "\n· staging 은 건드리지 않았습니다 (main 업로드가 안 돼서) — main 업로드를 다시 해결한 뒤 맞춰야 합니다")
        + (("\n· <b>CHANGELOG 기록 실패</b> (배포는 계속했음): " + esc("; ".join(changelog_failed))) if changelog_failed else "")
        + held_msg
        + ("\n· 업데이트 비서 자신도 바뀌어 지금 새 버전으로 다시 시작합니다. (2분 안에 정상 신호가 없으면 자동으로 이전 버전 복구)" if self_update else ""))
    for unit in units:
        root = targets().get(unit)
        if unit in DC.UNITS.values() and DC.state_path(root).exists() and DC.read(DC.state_path(root)).get('phase') == 'paused':
            say("" + NAMES[unit] + " 업데이트용 차단은 유지 중입니다. 준비되면 재개하세요.", DC.resume_rows(unit))
    if self_update:
        st["self_pending"] = {"since": time.time()}
        save(STATE, st)
        restart_service(SELF_UNIT)
 
 
def show_diff(st, key):
    o = st.get("offers", {}).get(key)
    if not o:
        return say("이 업데이트 정보를 찾지 못했습니다.")
    _, stat = git("diff", "--stat", f"HEAD...{o['sha']}")
    _, d = git("diff", "-U1", f"HEAD...{o['sha']}", "--", "*.py")
    lines = [l for l in d.splitlines() if l.startswith(("+", "-", "@@")) and not l.startswith(("+++", "---"))]
    say(f"<b>바뀐 내용</b> (<code>{esc(o['branch'])}</code>)\n<pre>{esc(stat[-800:])}</pre>\n<pre>{esc(chr(10).join(lines)[:2600])}</pre>",
        [[{"text": "업데이트", "callback_data": f"up:{key}"}, {"text": "무시", "callback_data": f"ig:{key}"}]])
 
 
# ---------------------------------------------------------------- 하단 버튼 메뉴 (/start 로 뜸)
# 버튼은 기존 글자 명령과 똑같이 처리된다. 승인·코드 보기·무시·일시중지·재개는 업데이트 알림 안의 버튼으로 이미 처리한다.
MENU_ALIAS = {"업데이트 확인": "업데이트 확인", "거래 상태": "거래 상태", "원작 확인": "원작 확인", "도움말": "/help", "충돌 정리": "충돌 정리",
              "메뉴": "메뉴", "유지보수": "메뉴", "처음 화면": "처음 화면", "상태 기록": "상태 기록"}   # 예전 "메뉴" 글자도 유지보수로
_EMOJI_RE = re.compile("(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u25A0-\u25FF\u2300-\u23FF\u2900-\u297F\u2139\u21A9\uFE0F\u200D])+ ?")


def _plain(t):
    """예전 하단 키보드(이모티콘 글자)가 폰에 남아 있어도 같은 버튼으로 읽도록 이모티콘만 뺀다"""
    return _EMOJI_RE.sub("", t or "").strip()

HELP_TEXT = ("<b>업데이트 비서 사용법</b>\n"
             "· 첫 화면 버튼 4개: <b>업데이트 확인</b> · <b>거래 상태</b> · <b>유지보수</b> · <b>도움말</b> (유지보수 안에 충돌 정리·상태 기록·원작 확인, 처음 화면으로 돌아감)\n"
             "· <b>업데이트 확인</b> : GitHub에 올라온 수정 확인 → 새 알림의 버튼(적용 · 코드 보기 · 무시)\n"
             "· <b>충돌 정리</b> : 이전 변경 파일 선택 → 확인 → 원래 브랜치를 백업 후 정리 → 별도 업데이트 승인\n"
             "· <b>거래 상태</b> : 업데이트용 일시중지·대기 중인 봇 보기 → 재개 버튼\n"
             "· <b>원작 확인</b> : 2번 스나이퍼 원작자 새 버전 지금 확인 (평소엔 매일 09:02 자동 · 알림 전용)\n"
             "· <b>상태 기록</b> (유지보수 안) : 저장소 STATUS.md 를 지금 갱신 (평소엔 적용 때·매일 06:10 자동)\n"
             "· 일시중지·재개·승인은 업데이트 알림 아래 버튼으로 진행합니다.")


def menu_keyboard():
    """처음 화면: 4칸 (업데이트 확인 / 거래 상태 / 유지보수 / 도움말). 충돌 정리·상태 기록·원작 확인은 유지보수 안."""
    return [[{"text": "업데이트 확인"}, {"text": "거래 상태"}], [{"text": "유지보수"}, {"text": "도움말"}]]


def menu_sub_keyboard():
    """유지보수 안: 충돌 정리(UC 있을 때만) · 상태 기록 · 원작 확인(SU 있을 때만 — 예전과 같은 조건) + 처음 화면."""
    rows = [["충돌 정리", "상태 기록"] if UC else ["상태 기록"],
            ["원작 확인"] if SU else [],
            ["처음 화면"]]
    rows = [r for r in rows if r]
    return [[{"text": t} for t in r] for r in rows]


# ---------------------------------------------------------------- 텔레그램 버튼 받기
def handle(st, upd):
    cb = upd.get("callback_query")
    msg = upd.get("message")
    if cb:
        if str(cb.get("message", {}).get("chat", {}).get("id")) != str(CFG.get("chat_id")):
            return
        tg("answerCallbackQuery", callback_query_id=cb["id"])
        act, _, key = (cb.get("data") or "").partition(":")
        if act == "cp" and UC:
            o = st.get("offers", {}).get(key)
            if o and o.get("superseded"):   # v1.8.1: 옛 브랜치면 정리보다 지우기가 맞다고 먼저 안내 (정리 화면도 그대로 열림)
                say("이 브랜치는 이미 반영된 옛 브랜치로 보여요. 충돌 정리보다 지우기가 맞습니다.", [_drop_row(key)])
            return UC.preview(sys.modules[__name__], st, key)
        elif act == "rm":   # v1.8.1: 옛 브랜치 지우기
            return drop_superseded(st, key)
        elif act in ("ct", "cc", "cr", "cx") and UC:
            return UC.handle(sys.modules[__name__], st, act, key)
        elif act == "pa":
            offer_data = st.get('offers',{}).get(key)
            if not offer_data:
                return say('최신 업데이트 알림에서 다시 눌러 주세요.')
            git('fetch','-q','origin')
            rc, sha = git('rev-parse','origin/'+offer_data['branch'])
            if rc or sha != offer_data['sha']:
                return say('브랜치가 바뀌었습니다. 새 알림에서 눌러 주세요.')
            _, files = git('diff','--name-only','HEAD...'+sha)
            units, _skipped = classify(files.splitlines())   # 빠진 파일 때문에 중지 요청을 거부하지 않음
            for unit in DC.UNITS.values():
                if units.get(unit):
                    DC.request(sys.modules[__name__],unit,key)
        elif act == 'ra':
            for unit, root in targets().items():
                if unit not in DC.UNITS.values() or not DC.state_path(root).exists():
                    continue
                state = DC.read(DC.state_path(root))
                if state.get('offer_key') == key and state.get('phase') in ('waiting','paused'):
                    DC.resume(sys.modules[__name__],unit)
        elif act == "ps":
            offer_key, _, number = key.partition(":")
            unit = DC.UNITS.get(number)
            offer_data = st.get("offers", {}).get(offer_key)
            if not unit or not offer_data:
                return say("최신 업데이트 알림에서 다시 눌러 주세요.")
            git("fetch", "-q", "origin")
            rc, sha = git("rev-parse", "origin/" + offer_data['branch'])
            if rc or sha != offer_data['sha']:
                return say("브랜치가 바뀌었습니다. 업데이트 확인 후 새 버튼을 눌러 주세요.")
            _, files = git("diff", "--name-only", "HEAD..." + sha)
            units, _skipped = classify(files.splitlines())
            if not units.get(unit):
                return say("해당 업데이트 대상 봇만 중지할 수 있습니다.")
            DC.request(sys.modules[__name__], unit, offer_key)
        elif act == "rs":
            if key in DC.UNITS:
                DC.resume(sys.modules[__name__], DC.UNITS[key])
        elif act == "up":
            apply(st, key)
        elif act == "df":
            show_diff(st, key)
        elif act == "ig":
            st.get("offers", {}).pop(key, None); say("이 업데이트는 무시했습니다. (봇 그대로)")
        elif act in ("um", "ud", "ui", "ub", "ur") and SU:   # 2번 스나이퍼 원작 새 버전 (합치기 / 보기 / 무시 / 자동 업뎃 되돌리기 / 자동 업뎃 다시 켜기)
            {"um": SU.merge, "ud": SU.show, "ui": SU.ignore, "ub": SU.rollback, "ur": SU.release}[act](sys.modules[__name__], st, key)
    elif msg and str(msg.get("chat", {}).get("id")) == str(CFG.get("chat_id")):
        txt = _plain(msg.get("text") or "")
        txt = MENU_ALIAS.get(txt, txt)   # 하단 버튼 글자 → 같은 명령
        if txt in ("/start", "/help", "도움말", "?"):
            say(HELP_TEXT, keyboard=menu_keyboard())
        elif txt in ("메뉴", "/menu"):   # 메뉴 → 하위 메뉴 펼치기
            say("<b>유지보수</b> — 가끔 쓰는 기능", keyboard=menu_sub_keyboard())
        elif txt == "처음 화면":   # 처음 화면 → 처음 2개로 돌아가기
            say("처음 화면입니다.", keyboard=menu_keyboard())
        elif txt in ("충돌 정리", "/conflicts") and UC:
            live = live_branches()
            if live is None:
                return say('GitHub 확인에 실패했습니다. 잠시 후 다시 눌러 주세요. (아무것도 지우지 않았습니다)')
            removed = prune(st, live)
            offers = st.setdefault('offers', {})
            missing = [b for b in live if b not in {o['branch'] for o in offers.values()}]
            if missing:   # 최신 알림이 지워졌거나 없던 브랜치는 새 알림을 다시 만든다
                for b in missing:
                    st.setdefault('seen', {})[b] = live[b]
                    offer(st, b, live[b], live)
            head = ('반영 안 된 지난 알림 ' + str(removed) + '개를 지웠습니다.\n') if removed else ''
            if not offers:
                return say(head + '정리할 업데이트가 없습니다. (GitHub에 대기 중인 수정 없음)')
            rows = [[{'text': '' + o['branch'] + ' (' + o['sha'][:7] + ')', 'callback_data': 'cp:' + k}]
                    for k, o in offers.items()]
            return say(head + '현재 대기 중인 업데이트입니다. 정리할 브랜치를 선택하세요. 아직 파일은 변경하지 않습니다.', rows)
        elif txt in ("상태 기록", "상태기록", "/status"):
            say("STATUS.md: " + esc(status_daily(st, force=True) or "확인 안 함"))
        elif txt in ("원작 확인", "원작 업데이트", "원작업데이트", "/upstream") and SU:
            say("원작 스나이퍼 저장소를 확인합니다…")
            SU.check(sys.modules[__name__], st, force=True)
        elif txt in ("원작 자동 재개", "/upstream_resume") and SU:   # 사무실 v1.9.3: 자동 업뎃 실패로 멈춘 원작 커밋을 사람이 풀어 줌
            SU.release(sys.modules[__name__], st, "all")
        elif txt in ("거래 상태", "일시중지 상태", "/pause_status"):
            found = False
            for unit, root in targets().items():
                if unit not in DC.UNITS.values() or not DC.state_path(root).exists():
                    continue
                try:
                    state = DC.read(DC.state_path(root))
                except Exception:
                    say("" + NAMES[unit] + " 중지 상태 파일 확인 필요")
                    continue
                if state.get('phase') in ('waiting', 'paused'):
                    found = True
                    say("" + NAMES[unit] + ": " + ('일시중지' if state['phase']=='paused' else '잔고 0 대기') + "\n" + esc(state.get('reason','확인 중')), DC.resume_rows(unit))
            if not found:
                say("업데이트용 일시중지/대기 중인 봇이 없습니다.")
        elif txt in ("업데이트", "업데이트 확인", "/update"):
            say("GitHub를 확인합니다…")
            sent = scan(st, force=True)   # v1.8.1: 보낸 알림 수로 판단 (예전엔 같은 알림을 다시 보내고도 '없습니다'가 같이 떴음)
            if sent == 0:
                say("새로 올라온 수정이 없습니다.")
            elif sent is None:
                say("GitHub 확인에 실패했습니다. 잠시 후 다시 눌러 주세요.")
 
 
def _run_as_owner(*a, timeout=120):
    cmd = list(a)
    if os.geteuid() == 0 and OWNER.pw_uid != 0:
        cmd = ["runuser", "-u", OWNER.pw_name, "--"] + cmd
    return sh(*cmd, timeout=timeout)


def _hub_cron_present():
    try:
        if os.path.exists("/etc/cron.d/alert-hub"):
            return "alert_hub watchdog" in open("/etc/cron.d/alert-hub", encoding="utf-8").read()
    except Exception:
        pass
    return False


def _hub_installed():
    # v1.8.8: watchdog 폐기(2026-11-13) 뒤로는 cron 의 watchdog 줄을 설치 조건으로 보지 않는다
    #        (예전 조건이면 cron 을 지운 서버에서 업데이터가 시작할 때마다 재설치·테스트 메시지·watchdog 줄 재생성)
    return (os.path.isfile(HUB_PY)
            and os.path.isfile(os.path.join(HUB_DIR, ".env")))


def hub_install():
    """alert-hub가 아직 설치 안 돼 있으면 한 번만 설치 시도. 이미 설치됐거나 폴더가 없으면 None.
    실패해도 예외를 밖으로 던지지 않고 실패 문장을 반환한다. 비밀값은 반환 문장에 넣지 않는다."""
    try:
        if not os.path.isfile(os.path.join(HUB_DIR, "alert_hub", "__init__.py")):
            return None
        if _hub_installed():
            return None
        if not CFG.get("token") or not CFG.get("chat_id"):
            return "alert-hub 설치 실패: 서버 텔레그램 설정(token/chat_id)이 없어 .env를 만들지 않았습니다"
        if not os.path.isfile(HUB_PY):
            rc, out = _run_as_owner("python3", "-m", "venv", HUB_VENV, timeout=300)
            if rc != 0 or not os.path.isfile(HUB_PY):
                return "alert-hub 설치 실패: venv 만들기 실패 (" + out[-200:] + ")"
        rc, out = _run_as_owner(HUB_PIP, "install", "-e", HUB_DIR, timeout=300)
        if rc != 0:
            return "alert-hub 설치 실패: pip install 실패 (" + out[-200:] + ")"
        env_path = os.path.join(HUB_DIR, ".env")
        if not os.path.isfile(env_path):
            try:
                tpl = open(os.path.join(HUB_DIR, ".env.example"), encoding="utf-8").read()
            except Exception as e:
                return "alert-hub 설치 실패: .env.example 읽기 실패 (" + type(e).__name__ + ")"
            lines = []
            for line in tpl.splitlines():
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    lines.append("TELEGRAM_BOT_TOKEN=" + str(CFG.get("token")))
                elif line.startswith("TELEGRAM_CHAT_ID="):
                    lines.append("TELEGRAM_CHAT_ID=" + str(CFG.get("chat_id")))
                elif line.startswith("HUB_BOT_NAMES="):
                    lines.append("HUB_BOT_NAMES=" + HUB_BOT_NAMES)
                else:
                    lines.append(line)
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            try:
                os.chmod(env_path, 0o600)
                if os.geteuid() == 0:
                    os.chown(env_path, OWNER.pw_uid, OWNER.pw_gid)
            except Exception:
                pass
        rc, out = _run_as_owner("sh", "-c", "cd " + HUB_DIR + " && " + HUB_PY + " -m unittest discover -s tests", timeout=300)
        if rc != 0:
            return "alert-hub 설치 실패: 테스트 실패 (cron을 넣지 않았습니다) (" + out[-200:] + ")"
        rc, out = _run_as_owner(HUB_PY, "-m", "alert_hub", "test", timeout=120)
        if rc != 0:
            return "alert-hub 설치 실패: 테스트 메시지 전송 실패 (cron을 넣지 않았습니다) (" + out[-200:] + ")"
        _, tz_out = sh("timedatectl", timeout=30)
        if "Asia/Seoul" in tz_out:
            briefing = "0 8 * * *"
        elif "UTC" in tz_out:
            briefing = "0 23 * * *"
        else:
            briefing = None
        cron_lines = ["# alert-hub — watchdog 줄 없음 (2026-11-13 폐기, v1.8.8)"]
        if briefing:
            cron_lines.append(briefing + " " + OWNER.pw_name + " cd " + HUB_DIR + " && .venv/bin/python -m alert_hub briefing >> data/briefing.log 2>&1")
        try:
            with open("/etc/cron.d/alert-hub", "w", encoding="utf-8") as fh:
                fh.write("\n".join(cron_lines) + "\n")
            os.chmod("/etc/cron.d/alert-hub", 0o644)
        except Exception as e:
            return "alert-hub 설치 실패: cron 파일 쓰기 실패 (" + type(e).__name__ + ")"
        extra = "" if briefing else " (서버 시간대를 몰라 브리핑 cron은 넣지 않았습니다)"
        return "alert-hub 설치 완료: venv·.env·테스트·cron" + extra
    except Exception as e:
        return "alert-hub 설치 실패: " + type(e).__name__ + " (" + str(e)[:200] + ")"


def hub_data_perm_repair():
    """hub 데이터 폴더 0777, hub.db(+ -wal·-shm) 0666 으로 정리. 시작할 때마다, 이미 설치돼 있어도 실행.
    봇마다 다른 계정으로 돌 수 있는데, sqlite(WAL)는 DB 파일과 폴더 둘 다 쓸 수 있어야 신호를 기록한다.
    HUB_DIR/data 안의 이 세 파일만 다룬다 (심볼릭 링크는 건드리지 않음). 예외를 밖으로 던지지 않고, 비밀값은 다루지 않는다.
    반환: 결과 한 줄 (폴더가 없으면 None)"""
    try:
        data_dir = os.path.join(HUB_DIR, "data")
        if not os.path.isdir(data_dir) or os.path.islink(data_dir):
            return None
        changed, failed = [], []
        targets_ = [(data_dir, 0o777)] + [(os.path.join(data_dir, n), 0o666) for n in ("hub.db", "hub.db-wal", "hub.db-shm")]
        for p, mode in targets_:
            try:
                if not os.path.exists(p) or os.path.islink(p):
                    continue
                if (os.stat(p).st_mode & 0o777) != mode:
                    os.chmod(p, mode)
                    changed.append(os.path.basename(p) + "=" + oct(mode)[2:])
            except Exception as e:
                failed.append(os.path.basename(p) + ":" + type(e).__name__)
        return ("hub 권한 정리: " + (", ".join(changed) if changed else "바꿀 것 없음")
                + (" · 실패 " + ", ".join(failed) if failed else ""))
    except Exception as e:
        return "hub 권한 정리 오류: " + type(e).__name__


def main():
    st = load(STATE, {})
    if git("rev-parse", "-q", "--verify", "refs/remotes/origin/staging")[0]:
        git("push", "-q", "origin", "HEAD:staging")   # 처음 한 번: staging 브랜치 만들기
    DC.monitor(sys.modules[__name__])
    try:
        hub_result = hub_install()
        if hub_result:
            print("alert-hub 자동 설치:", hub_result, flush=True)
            say("<b>alert-hub 자동 설치</b>\n· " + esc(hub_result))
    except Exception as e:
        print("alert-hub 자동 설치 오류:", type(e).__name__, e, flush=True)
    try:   # 설치 여부와 상관없이 시작할 때마다 (설치 직후 만들어진 DB 도 포함)
        perm_result = hub_data_perm_repair()
        if perm_result:
            print(perm_result, flush=True)
    except Exception as e:
        print("hub 권한 정리 오류:", type(e).__name__, flush=True)
    last = 0.0
    offset = st.get("offset")
    while True:
        _hub_beat('9번 업데이트 비서')
        if time.time() - last >= CHECK_EVERY:
            last = time.time()
            try:
                scan(st)
            except Exception as e:
                print("확인 오류:", e, flush=True)
            try:   # 사무실 v1.9.3(D): 보류한 봇 재시도 — 사유가 풀린 것만 (아직이면 조용히 기다림)
                retry_holds(st)
            except Exception as e:
                print("보류 재시도 오류:", type(e).__name__, e, flush=True)
            try:
                r = status_daily(st)
                if r:
                    print("STATUS.md:", r, flush=True)
            except Exception as e:
                print("STATUS.md 오류:", type(e).__name__, e, flush=True)
            if SU:
                try:
                    SU.check(sys.modules[__name__], st)   # 하루 1번(09:02 KST) 원작 스나이퍼 새 버전 확인
                except Exception as e:
                    print("원작 확인 오류:", e, flush=True)
            save(STATE, st)
        r = tg("getUpdates", timeout=25, offset=offset, allowed_updates=["message", "callback_query"]) if offset else tg("getUpdates", timeout=25, allowed_updates=["message", "callback_query"])
        if not r.get("ok"):
            time.sleep(10); continue
        if st.pop("self_pending", None):
            cl = _changelog(os.path.join(REPO, "bot_office"), 1)
            save(STATE, st); say(f"업데이트 비서 새 버전{' (사무실 ' + cl[0][0] + ')' if cl else ''} 정상 작동 확인", keyboard=menu_keyboard())
        for upd in r.get("result", []):
            offset = upd["update_id"] + 1; st["offset"] = offset
            try:
                handle(st, upd)
            except Exception as e:
                print("처리 오류:", e, flush=True); say("업데이트 비서 처리 오류: " + esc(str(e)[:200]))
            save(STATE, st)
        if os.environ.get("U_ONCE"):
            break
 
 
if __name__ == "__main__":
    main()
