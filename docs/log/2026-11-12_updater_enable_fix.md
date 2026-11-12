# 2026-11-12 · 업데이터 enable 고침 (Claude)

상태: 파일 작성·가짜 systemctl 검증 완료 / GitHub 업로드·승인·서버 적용·실제 재부팅 확인은 아직 안 함.

## 왜
- 7번 비서(bot-office-secretary.service)가 2026-10-21 설치 때 enable 없이 start만 됐고, 2026-11-12 커널 재부팅 때 멈춘 뒤 다시 돌아오지 않았다.
- 업데이터는 재시작만 하고 enable은 하지 않으므로 같은 일이 다시 생길 수 있었다. 7번 비서는 수동 enable+start로 이미 정상이다. 이번 고침은 재발 방지다.

## 바꾼 것 — `bot_office/bot_updater.py` 1개 (기준: 4bot origin/main 584eca3, 사무실 v1.6.5, 1347줄)
- 새 헬퍼 `restart_service(unit, active=None)`: active면 `systemctl enable` 후 restart, active가 아니면 기존처럼 restart만 한다.
  판정 방식은 기존과 같은 `sh(SYSTEMCTL, "is-active", unit)[1].strip() == "active"`다 (is-enabled는 쓰지 않음).
- `apply()`의 재시작 세 군데가 모두 이 헬퍼를 쓴다: (a) 일반 재시작, (b) 되돌림 재시작, (c) 업데이터 자신(self_update) 재시작.
- **스냅샷 규칙 (사용자 결정, 2026-11-12):** is-active 판정은 첫 재시작 직전에 `was_active`로 한 번만 한다. 되돌림 때는 다시 판정하지 않고 그 값을 그대로 쓴다.
  그래서 원래 정지돼 있던 서비스(toss_dca 등)는 메인 재시작으로 잠깐 active가 됐다가 되돌림이 돌아도 enable되지 않는다.
  self_update(c)는 따로 스냅샷이 없으므로 그 자리에서 한 번 판정한다.
- enable이 실패해도 업데이트를 멈추지 않는다. `print()` 로그만 남기고(SECRET_RE로 가림), 텔레그램 알림은 보내지 않는다. restart·healthy 검사는 기존 그대로 진행한다.
- 머리말 맨 위에 버전 자동 기입 표시('v'+'NEXT') 기록 1줄을 추가했다 (파일 안 그 표시는 이 1번뿐).
- 바꾸지 않은 것: healthy(), OFFICE_EXTRA의 is-active 게이트, next_tag, 되돌림 감지, 시간 보호, 그 밖의 모든 동작. 유닛을 새로 설치하는 경로는 없어서 만들지 않았다.

## toss_dca
- 이 고침은 toss_dca를 enable·start하는 코드를 추가하지 않는다. 정지(inactive) 서비스는 enable 대상이 아니고, 되돌림 때도 스냅샷 덕분에 enable되지 않는다 (검증 e).
- ⚠️ **기존 동작(이번에 바꾸지 않음):** 업데이트에 toss_dca 폴더 코드가 들어 있으면 업데이터는 원래대로 toss_dca를 restart한다. restart는 정지된 서비스를 켠다.
  toss_dca를 계속 꺼 두려면 toss_dca 코드는 staging에 올리지 말 것. (enable은 안 되므로 재부팅하면 다시 꺼진다.)

## 검증 (전부 직접 실행)
1. `python3 -m py_compile bot_office/bot_updater.py` 통과
2. 가짜 systemctl harness `test_restart_enable.py` 19/19 통과 — (a) active+disabled→enabled, (b) inactive+disabled→enable 0번, (c) 이미 enabled 유지, (d) enable 실패해도 restart+로그, (e) apply() 되돌림 때 원래 inactive였던 toss_dca enable 0번
3. `apply()` 안의 `sh(SYSTEMCTL, "restart", …)` 직접 호출 0건. 파일 전체에서는 헬퍼 안의 1건뿐
4. `git diff --check` 통과. 바뀐 파일은 bot_updater.py와 이 기록 파일뿐
5. 비밀 스캔(SECRET_RE, 추가된 줄): 0건

## 남은 일·주의
- 이번 고침을 승인할 때 그 승인을 처리하는 것은 서버의 **기존 v1.6.5 코드**다. 그래서 그 승인으로 일어나는 업데이터 자신의 재시작에서는 아직 enable이 되지 않는다. 새 규칙은 그다음 재시작부터 적용된다. bot-updater.service가 enabled인지는 서버에서 따로 확인이 필요하다 (`systemctl is-enabled bot-updater.service`).
- 930번대 기존 주석 "비서는 disabled 지만 실행 중"은 지금 사실과 다르지만(비서는 수동 enable됨), 최소 diff 원칙에 따라 그대로 뒀다.
- 실제 systemd·재부팅은 검증하지 않았다. 다음 재부팅 뒤 7번 비서가 자동으로 뜨는지 확인할 것.
- 참조용 `deployment_control.py`(사용자 첨부, sha256 f4ce0c67…a2a8, 374줄)는 import 검증에만 썼고 고치지 않았다. 584eca3과 같은 파일인지는 MANIFEST에 해시가 없어서 대조하지 못했다.

## 다음 AI가 읽을 파일
- START.md → docs/handoff/06_updater.md → 이 파일
