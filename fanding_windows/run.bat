@echo off
REM 팬딩 가격표 가져오기 - 작업 스케줄러가 매일 오전에 실행 (FANDING_FETCH_V1.0.0)
cd /d %~dp0
py fanding_fetch.py run >> fetch_log.txt 2>&1
