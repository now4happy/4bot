# 1번 한투 라오어 변경 기록

## v1.0.4 · 2026-11-19 (KST)
- 파일: kis_order_engine.py, order_executor.py, scheduler_regular.py
- 내용: fix: 감사 구멍 고침 — 보유 조회 실패 구분(빈 {}와 실패 구분, 실패면 주문 계획 안 짬), 타임아웃 재시도 전 미체결·체결·예약 원장 조회로 중복 주문 방지
- 브랜치: staging

## v1.0.3 · 2026-11-01 17:16 (KST)
- 파일: main.py, scheduler_regular.py
- 내용: feat: alert-hub 연동 3차 — 1번 한투 자율 알림
- 브랜치: staging

## v1.0.2 · 2026-11-01 14:47 (KST)
- 파일: scheduler_sniper.py
- 내용: feat: alert-hub 연동 1차 — 전 봇 하트비트 + 사무실·팬딩 자율 알림
- 브랜치: staging

## v1.0.1 · 2026-10-25 17:36 (KST)
- 파일: callback_config_handler.py, plugin_updater.py, telegram_commands.py
- 내용: 안내 문구 수정 2번봇
- 브랜치: staging

