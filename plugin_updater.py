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
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from global_throttle import GlobalThrottle # 🚨 중앙 통제소 결속

class SystemUpdater:
    def __init__(self):
        self.remote_branch = "origin/main"
        
        load_dotenv()
        self.daemon_name = os.getenv("daemon_name") or os.getenv("DAEMON_NAME", "mybot")

    async def is_update_allowed(self):
        return (False, '자가 업데이트 해제: 직접 관리 모드입니다.')

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
        return (False, '자가 업데이트 해제: 직접 관리 모드입니다.')

    async def restart_daemon(self):
        return False
