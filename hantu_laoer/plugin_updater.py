# ==========================================================
# FILE: plugin_updater.py
# ==========================================================
# 🚨 MODIFIED: [배포 락다운 타임라인 최적화 (Case 09 절대 사수)] 기존 04:00~16:10 EST의 과도한 락다운을 파기하고, 실제 V-REV 슬라이싱 타격 및 정산이 이루어지는 '장 마감 직전 핵심 교전 윈도우(15:26 ~ 16:10 EST)'로만 정밀 락온 완료. 이를 통해 비-교전 시간대에는 자유로운 업데이트를 보장하되, 실제 주문이 나가는 대참사 위험 구간만 100% 진공 격리함.
# 🚨 MODIFIED: [V44.53 제1헌법 및 16계명 절대 락온] 달력 API(mcal) 스캔을 비동기(to_thread) 래핑
# 🚨 MODIFIED: [Case 14 절대 헌법 준수] 달력 API 타임아웃 5.0초를 10.0초로 팩트 교정하여 타임아웃 헌법 일원화.
# 🚨 MODIFIED: [제1헌법 철저 준수] 낡은 time.sleep(0.06) 땜질 코드를 영구 소각하고 GlobalThrottle.wait_api_sync() 중앙 통제소 락온 결속.
# 🚨 MODIFIED: [제1헌법 교정] 서브프로세스 교착 방어를 위한 30초 타임아웃 족쇄 및 os.makedirs 비동기 래핑 전면 결속
# 🚨 NEW: [좀비 프로세스 방어] 서브프로세스 TimeoutError 발생 시 .kill() 직후 await .wait()를 강제 호출하여 OS 자원 누수(Zombie) 원천 차단
# ==========================================================
import logging
import asyncio
import subprocess
import os
import time
import datetime
import io
import re
import zipfile
import urllib.request
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from global_throttle import GlobalThrottle # 🚨 중앙 통제소 결속

# 🚨 NEW: 원작자(KIS) 저장소 비교 업데이트 설정
AUTHOR_ZIP_URL = "https://codeload.github.com/pipios4006-boop/KIS-API-Python-Trading-Bot-Example/zip/refs/heads/main"
# 직접 관리하는 파일: 원작자 버전과 달라도 비교·덮어쓰기에서 제외 (파일을 더 추가하려면 여기에 적는다)
# telegram_commands.py / callback_config_handler.py 는 '최신 버전' 안내(재시작 생략)를 위해 직접 수정한 파일이다.
MANAGED_FILES = ("plugin_updater.py", "telegram_commands.py", "callback_config_handler.py")


def _fetch_author_py_sync():
    req = urllib.request.Request(AUTHOR_ZIP_URL, headers={"User-Agent": "hantu-laoer-updater"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            parts = n.split("/", 1)
            if len(parts) < 2 or "/" in parts[1] or not parts[1].endswith(".py"):
                continue
            files[parts[1]] = z.read(n)
    if not files:
        raise RuntimeError("원작자 저장소에서 .py 파일을 찾지 못했습니다")
    return files


def _plan_author_update_sync(base_dir, author):
    """(변경할 {파일명: 바이트}, 오류문자열) 반환. 실제 파일은 건드리지 않는다."""
    plan = {}
    for name, new_bytes in author.items():
        if name in MANAGED_FILES:
            continue
        path = os.path.join(base_dir, name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                if f.read() != new_bytes:
                    plan[name] = new_bytes
    # 로컬에 없는 원작자 파일은, 적용될 코드가 import 할 때만 추가 (미사용 레거시 파일 방지)
    local_names = {n for n in os.listdir(base_dir) if n.endswith(".py")}
    texts = []
    for n in local_names:
        if n in plan:
            texts.append(plan[n].decode("utf-8", "replace"))
        else:
            with open(os.path.join(base_dir, n), "rb") as f:
                texts.append(f.read().decode("utf-8", "replace"))
    for name, new_bytes in author.items():
        if name in MANAGED_FILES or name in local_names:
            continue
        mod = re.escape(name[:-3])
        if any(re.search(rf"^\s*(?:import|from)\s+{mod}\b", t, re.M) for t in texts):
            plan[name] = new_bytes
    for name, b in plan.items():
        try:
            compile(b.decode("utf-8"), name, "exec")
        except Exception as e:
            return {}, f"원작자 {name} 문법 검증 실패, 아무것도 적용하지 않았습니다: {e}"
    return plan, ""


def _apply_author_update_sync(base_dir, plan):
    originals = {}
    try:
        for name, b in plan.items():
            path = os.path.join(base_dir, name)
            originals[name] = open(path, "rb").read() if os.path.exists(path) else None
            tmp = path + ".upd.tmp"
            with open(tmp, "wb") as f:
                f.write(b)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
    except Exception:
        for name, old in originals.items():
            path = os.path.join(base_dir, name)
            if old is None:
                try: os.remove(path)
                except OSError: pass
            else:
                with open(path, "wb") as f:
                    f.write(old)
        raise


class SystemUpdater:
    def __init__(self):
        self.remote_branch = "origin/main"
        self.changed = False
        
        load_dotenv()
        self.daemon_name = os.getenv("daemon_name") or os.getenv("DAEMON_NAME", "mybot")

    async def is_update_allowed(self):
        est = ZoneInfo('America/New_York')
        now_est = datetime.datetime.now(est)
        
        if now_est.weekday() >= 5:
            return True, ""

        def _check_holiday():
            GlobalThrottle.wait_api_sync()
            import pandas_market_calendars as mcal
            nyse = mcal.get_calendar('NYSE')
            schedule = nyse.schedule(start_date=now_est.date(), end_date=now_est.date())
            return schedule.empty

        is_holiday = False
        for attempt in range(3):
            try:
                is_holiday = await asyncio.wait_for(asyncio.to_thread(_check_holiday), timeout=10.0)
                break
            except asyncio.TimeoutError:
                if attempt == 2:
                    logging.error("⚠️ [Updater] 달력 API 타임아웃. Fail-Open 평일 강제 검사 진행.")
                else:
                    await asyncio.sleep(1.0 * (2 ** attempt))
            except Exception as e:
                if attempt == 2:
                    logging.debug(f"업데이트 락다운 달력 스캔 에러 (무시하고 시간 검사 진행): {e}")
                else:
                    await asyncio.sleep(1.0 * (2 ** attempt))

        if is_holiday:
            return True, ""

        curr_time = now_est.time()
        
        # 🚨 MODIFIED: [배포 락다운 정밀 캡핑] 실제 매매가 발생하는 15:26 ~ 16:10 EST 구간만 업데이트 전면 통제
        start_lock = datetime.time(15, 26)
        end_lock = datetime.time(16, 10)
        
        if start_lock <= curr_time <= end_lock:
            return False, "⚠️ <b>[배포 금지]</b> 실제 주문이 집행되는 핵심 교전 윈도우(15:26~16:10 EST) 중에는 핫픽스 롤백 방지를 위해 자동 업데이트를 강제 차단합니다."
        return True, ""

    async def _create_safety_backup(self):
        try:
            backup_dir = "stable_backup"
            await asyncio.to_thread(os.makedirs, backup_dir, exist_ok=True)
            
            proc = await asyncio.create_subprocess_shell(
                f"cp -p *.py {backup_dir}/ 2>/dev/null || true",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=30.0)
                logging.info("🛡️ [Updater] 롤백 봇을 위한 안전띠(stable_backup) 결속 완료")
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait() 
                logging.error("🚨 [Updater] 안전띠 결속 서브프로세스 통신 타임아웃 (30초 초과). 백업을 건너뜁니다.")
        except Exception as e:
            logging.error(f"🚨 [Updater] 안전띠 결속 중 에러 발생 (업데이트는 계속 진행): {e}")

    async def pull_latest_code(self):
        # 🚨 NEW: [원작자 버전 비교 업데이트] git reset --hard(전체 덮어쓰기)를 쓰지 않는다.
        #   원작자 저장소와 현재 폴더의 .py를 비교해 '다른 파일만' 적용하고, 같으면 "이미 최신"으로 끝낸다(재시작 없음).
        #   MANAGED_FILES(직접 관리)는 비교·덮어쓰기에서 제외. 모든 변경 파일은 컴파일 검증 후에만 쓴다.
        self.changed = False
        allowed, msg = await self.is_update_allowed()
        if not allowed:
            logging.warning(f"🛑 [Updater] 원작자 동기화 차단 (레드존): {msg}")
            return False, msg

        try:
            author = await asyncio.wait_for(asyncio.to_thread(_fetch_author_py_sync), timeout=40.0)
        except Exception as e:
            logging.error(f"🚨 [Updater] 원작자 저장소 조회 실패: {e}")
            return False, f"원작자 저장소 조회 실패: {e}"

        base_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            plan, err = await asyncio.to_thread(_plan_author_update_sync, base_dir, author)
        except Exception as e:
            return False, f"업데이트 비교 중 예외: {e}"
        if err:
            return False, err
        if not plan:
            return True, "이미 최신 버전입니다 · 적용할 원작자 업데이트 없음 (재시작 안 함)"

        await self._create_safety_backup()
        try:
            await asyncio.to_thread(_apply_author_update_sync, base_dir, plan)
        except Exception as e:
            logging.error(f"🚨 [Updater] 원작자 업데이트 적용 실패(원복 시도됨): {e}")
            return False, f"원작자 업데이트 적용 실패(원복됨): {e}"

        self.changed = True
        names = ", ".join(sorted(plan))
        logging.info(f"✅ [Updater] 원작자 업데이트 {len(plan)}개 파일 적용: {names}")
        return True, f"원작자 업데이트 {len(plan)}개 파일 적용: {names}"


    async def restart_daemon(self):
        allowed, _ = await self.is_update_allowed()
        if not allowed:
            logging.error("❌ 레드존 시간대 데몬 재가동 시도가 감지되어 OS 강제 차단했습니다.")
            return False

        try:
            logging.info(f"🔄 [Updater] 좀비 셧다운 방어를 위해 파이썬 프로세스를 즉시 자폭(Hard Kill)시킵니다. (systemd가 부활시킴)")
            os._exit(0)
            return True
        except Exception as e:
            logging.error(f"🚨 [Updater] 데몬 자폭 명령 하달 실패: {e}")
            return False
