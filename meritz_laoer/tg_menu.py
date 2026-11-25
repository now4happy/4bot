# ==========================================================
# FILE: meritz_laoer/tg_menu.py   (MERITZ_LAOER v2.7.0 · 판 39 v2.12.0)
# v2.12.0 수정 1차 (2026-11-24, 판 39 수정 1차): 설정값 줄의 '첫 기준가: 안 정함' 표시 삭제 (첫 매수는 가격 조건 없음)
# v2.15.0 (2026-11-25, 판 41 할 일 5): 바벨 삭제 — [바벨 관제보드] 버튼·화면(barbell_text)·B_BBBOARD·BOOL_NAME 바벨 항목 제거, 매수 비율 모드는 복리↔단리 2순환(PM_NEXT·PM_CHANGES 에서 바벨 제거)
# v2.10.0 (2026-11-23, 판 36 Case 113): '돌파 매수% 변경' 버튼·설정 표시·도움말 삭제, 눌림 매수% 기본 10(바벨 15), 1층 익절 기본 1.0, 다음 매수 타점 표시를 원작 판정과 같은 값(기준가=min(직전 매도가, 가장 낮은 F 평단), 15:00 신규 진입 차단·개장 7분 쉴드)으로 맞춤. 레이더 설정 버튼 5개(눌림·버킷 시드 / 1층 익절·상단 익절 / 첫 기준가)
# v2.9.0 6차 (2026-11-22, 판 33): 전술 제어반에 [탑쌓기 매매 시작]/[스나이퍼 매매로 돌아가기] 버튼 + 확인 메시지([네, 바꿀게요] 를 눌러야만 바뀜) · '매수 간격 변경'(1~10) 설정 추가
# v2.12.0 (2026-11-24, 판 39): 레이더 하위 메뉴를 원작 전술 제어반으로 교체 — [스나이퍼 켜기/끄기] [매수 비율 모드(복리 8·단리 10·바벨 15, 3순환)] [바벨 관제보드]. 눌림 매수%·첫 기준가·1층/상단 익절·남은 시드 설정·버튼 삭제, 스나이퍼 설정(snset) 화면 삭제, 바벨 켜기/끄기 별도 버튼은 모드 버튼에 흡수. 시드(F 완성 기준 금액·버킷 시드)는 잔고 동기화 화면으로 이동
# v2.7.0 (2026-11-21, 판 27): 층 간격 설정·버튼 제거 — MEANS '층 간격 변경'(tower_gap_usd)·MEANS 설명·TACT_SET·TOWER_DEFAULTS·설정 표시 '층 간격'·계획 '새 층 가격' 줄 삭제. 간격은 내부 고정값 GAP_USD=5로만 씀 (tower_strategy.params).
# v2.6.0 (2026-11-21, 판 26): '눌림 매수% 변경' 버튼(sniper_portion_pct, MEANS·TACT_SET·TOWER_DEFAULTS 8.0) · 설정 표시의 '눌림 8%' 고정 글자를 설정 비율로 · '돌파 매수% 변경' 예시 글자 · 층 줄 밑에 버킷별 목표 줄
# v2.4.0 (2026-11-21, 판 24): 스나이퍼 가격 선택 버튼(callback 'pk:<층 평단>:s|t') 처리 · 층 줄에 '잠금·탑 매도'·지하층(빈 층) 표시.
# v2.3.0 (2026-11-21, 판 23 하이브리드): 메뉴를 스나이퍼 봇(tg_ui_plugin) 형식으로 새로 만듦. 첫 화면(reply keyboard) 2행 4개: [🔫 스나이퍼 레이더][🔄 잔고 동기화] / [⚙️ 전술 제어반][💱 환전]. 모드 버튼·🚀 시스템 업데이트·자금/전술/현상태/기타 첫 화면 버튼 삭제 (기능은 아래 화면 인라인 버튼 안으로).
#   레이더(굵은 제목·F마다 한 줄·상태 완성/탑업 중/재매수 대기·채움률·다음 매수 타점·구분선·기준 시각, 오늘 체결 실시간 반영) · 잔고 동기화(잔고=장부일 때만 F를 장부에 맞추고 F 상태를 같은 메시지에 보여줌) · 전술 제어반(가로 전체 인라인 버튼: F 완성 기준 금액·스나이퍼 익절 1층/상단·탑쌓기 매도%·매도 비중·하루 매수/매도 F 수·봇 켜기/끄기 — 누르면 값 입력 → 이전→새 값 확인) · 환전(오늘 환전액·남은 한도·자동환전 켜기/끄기·하루 상한·여유%).
#   인라인 버튼은 callback_query 로 받음(getUpdates allowed_updates 에 callback_query 추가, answerCallbackQuery). 층 수·시드(total_krw)·1층 시작가 변경 버튼 삭제, 총 한도 표시 삭제. B8: 오늘 계획·자금 현황·레이더가 오늘 체결을 메모리에서 더한 층 상태로 계산, '잔고≠장부' 비교도 16:10 동기화 전엔 오늘 체결 반영 수량으로 비교, 영어 설정 이름 대신 한국어.
# v2.2.20 (2026-11-21, 판 22 듀얼 모드): ① 첫 메뉴 맨 위에 [스나이퍼 모드] [탑쌓기 모드] 버튼 — 누르면 설정 trading_mode 가 바로 바뀜 (다음 매매 판단부터 적용, 이미 낸 주문·층은 그대로. 설정 검사가 막으면 이유를 보여 줌). 첫 화면 글자에 지금 모드 표시
#   ② 상황판(현상태)을 스나이퍼 봇 형식 HTML 로 새로 씀 — 굵은 제목·이모티콘, 층마다 한 줄 ⚡ [N층: X주·$Y] $평단 ➔ $목표가 (+P%), 시드 배분 게이지(🟦🟨🟩), 구분선. 장부 파일뿐 아니라 오늘 체결(조회만, 메모리에서만 반영)까지 실시간으로 섞음. 스나이퍼 모드의 층 번호는 평단 낮은 층이 1층, 탑쌓기 모드는 예전 번호(평단 높은 층이 1층)
#   ③ 설정 메뉴에 '스나이퍼 1층 익절 변경'(sniper_tp_l1_pct, 기본 1.0)·'스나이퍼 상단층 익절 변경'(sniper_tp_upper_pct, 기본 1.0). 탑쌓기 설정은 그대로. send 에 html 옵션 추가 (일반 알림·다른 화면은 예전처럼 글자만)
# v2.2.18 (2026-11-20, 판 21 거래 내역·봇 상태 버튼 오류 고침): _local 이 4개(pos·halt·avg·tgt)를 돌려주는데 ledger_text·power_text 가 5개로 풀어서 ValueError 가 나던 것을 4개로 고침. 매매 로직·문구 변경 없음
# v2.2.17 (2026-11-20, 판 20 하루 매수·매도 층 수 설정): 설정 메뉴에 "하루 매수 F 수 변경"(tower_max_buy_layers_per_day)·"하루 매도 F 수 변경"(tower_max_sell_layers_per_day) 버튼 추가 — 1~3 정수, 없으면 1 (TOWER_DEFAULTS). MEANS 설명 2개, 설정 화면 SET_ROWS 와 상황판 설정값 줄에 현재 값 표시. 다른 설정 버튼은 그대로
# v2.2.14 (2026-11-20, 판 17 시초가 상한): 상황판 오늘 계획 미리보기가 저장된 시초가(main.load_open_price, 읽기만)를 build_plan 에 넘김 — 시초가가 아직 없으면 0 → 계획 배정 그대로. 메뉴·문구는 그대로
# v2.2.12 (2026-11-20, audit-fix-v2 r4): 표시 문구 '당일 시드' → '한층 금액' (상황판·자금 화면 2곳 + 주석). 금액 형식·다른 문구는 그대로
# v2.2.11 (2026-11-20, 7번 이름 변경): 표시 이름 '7번 메리츠 속쓸 적립봇' → '7번 메리츠 SOXL 탑쌓기' (HEAD·상황판 제목). 동작 변경 없음
# v2.2.9 (2026-11-20, 3차 — 풀이님 결정 10:06·10:14): 설정 메뉴를 탑쌓기 전용으로 개편 — 추가: 탑쌓기 간격 변경(tower_gap_usd, 1 이상 정수)·층 금액 변경(tower_floor_usd)·층 수 변경(tower_floors). 삭제: 회차·사다리 시작가·사다리 간격·재매수 하락폭·하루 최대 회차 버튼, '차감'(--credit) 입력, 사다리 채운 회차 경고(fill_warn). 상황판 전략 줄은 항상 탑쌓기. 시드·목표 이익률·매도 비중·1층 시작가·환전·봇 켜기/끄기는 그대로
# v2.2.6 (2026-11-20, 판 16 본격): 상황판 장부 줄의 매도 목표가 탑쌓기면 '가장 낮은 층 기준'(층별 매도라 전체 평단 목표는 의미 없음) 1곳만 고침. 층 표시(반칸·미완성 글자)는 tower_strategy.view_lines, 장중 확인 간격 표시(30초마다)는 기존 intraday_text 가 설정값을 그대로 보여 줌. 매매 동작 변경 없음
# v2.2.5 (2026-11-20, 판 16 1층 채우기 매수): 버전 표기만 올림 (1층 채우기 매수 로직은 tower_strategy.py)
# v2.2.4 (2026-11-19, 1층 시작가 메뉴): 설정 메뉴에 "1층 시작가 변경" 추가 (기본값 0 = 안 정함, 평단 기준)
# v2.2.3 (2026-11-19, 판 14 색상 고침): 버전 표기만 올림 (층 색상은 tower_strategy.py)
# v2.2.2 (2026-11-19, 판 14): 현상태(상황판)에 탑쌓기 층 시각화 추가 — tower_lines (채워진 층 칸 + N/10층 + 층별 상세 줄). 층 상태 파일(tower_state.json)을 읽기만 함. 전략이 사다리면 안 보임. 기존 상황판 줄은 그대로
# v2.2.0 (2026-11-19, 판 13): 상황판·자금 현황에 현재 전략(사다리/탑쌓기) 표시 추가 — 탑쌓기면 상황판에 '채운 회차' 대신 층 수. 전략 이름은 한글로만 보임 (영어 변수 이름 금지 규칙). 메뉴 토글 버튼은 이번 판에 안 만듦. 매매 동작 변경 없음
# v2.1.0 (2026-11-19, 방 telegram-bot-menu-review 3차 v3): 텔레그램 메뉴 문구 정리를 v2.0.9(판 11) 기준 위에 다시 적용 — 이모티콘 제거(예전 이모티콘 키보드 글자도 같은 버튼으로 읽음)·값 설명(넣을 수 있는 값·뜻·바꾸면)·주식 넣기 확인 단계. 판 11 변경은 그대로 둠, 매매 동작 변경 없음
# v2.0.9 (2026-11-19, 판 11): 버전 표기만 올림 (usd_cash 고침은 meritz_api.py·main.py). 이전 v2.0.8 (2026-11-19, 판 10): 자동환전 창이 '한국시간 09:00~주문 시간(실시간 환전 시간 안에서만)'으로 바뀐 데 맞춰 안내 글자 3곳만 고침 (💰 자금의 '신청은 …' · 💱 화면 설명 · 켜기 확인 문구). 로직 변경 없음
# v2.0.7 (2026-11-19, 판 9): 자동환전 시간이 한국시간 오전 9시로 바뀐 데 맞춰 안내 글자 3곳만 고침 (💰 자금의 '신청은 주문 시간에만' · 💱 화면 설명 · 켜기 확인 문구). 로직 변경 없음
# v2.0.6 (2026-11-19, 판 8): 버전 표기만 올림 — staging 에 빠진 v2.0.4 파일(notifier·tg_menu·accum_strategy)을 v2.0.5 main·meritz_api 와 한 묶음으로 맞춤 (ImportError 해소). 코드 로직 변경 없음
# v2.0.4 (2026-11-19): 💰 자금 화면에 '현금 부족 → 부분 매수'(몇 회차 몇 주만, 원래 몇 주) 표시. 판 5 보완(메뉴가 멈추거나 메시지를 버리는 이유를 로그에 남김·오래된 메시지 안내) 포함
# v2.0.3 (2026-11-18): 지시 2026-11-18 — 자동환전 여유%·하루 상한은 사용자가 💱 안·⚙️ 설정 안에서 직접 입력(값은 클로드가 안 정함) → 그 뒤에 💱 켜기.
#   값 없이 켜면 '여유%와 하루 상한을 먼저 입력해 주세요' 만 알림. 시드는 '2억'·F 완성 기준 금액은 '2,000만원'만 표시. 속쓸 가격만 소수점, 달러 금액·환율은 정수.
#   화면의 영어 변수 이름·옵션 이름·오류 문구는 한국말만(notifier.to_korean 이 보내기 직전에 정리). 글자를 짧고 쉽게, 버튼 이름 정리
#   (💸 매도 목표 퍼센트 변경 → 💸 매도 비중 변경 · ⚙️ 봇 상태 → 🤖 봇 상태(⚙️ 설정과 아이콘이 같아 헷갈림)). 상황판에 당일 매도 확인 표시. 매매 로직은 이 파일에서 안 바뀜
# v2.0.1 (2026-11-18): 메뉴 개편 — 맨밑 4개(💰 자금·📋 전술·📈 현상태·🛠 기타)가 메인, ☰ 메뉴·🏠·❓ 없앰. 이름 변경(거래 내역·봇 상태·주식 넣기·키 확인).
#   ⚙️ 설정(시드·회차·목표 이익률·매도 비중·사다리 시작가/간격·재매수 하락폭·하루 최대 회차·봇 켜기/끄기)과 💱 자동환전(켜기/끄기·여유%·하루 상한)은
#   설정 파일(config.update_settings) 값만 바꿈 — 입력 → 이전→새 값 확인 → [✅ 변경 확인]. 끄기(봇·자동환전)는 바로. 🛑 매매 정지 추가(정지 표시 켬). 상황판에 설정값 표시. 매매 로직 그대로
# v2.0.0 (2026-11-18): 적립봇 전환 — 표시 이름 '7번 메리츠 속쓸 적립봇', 상황판·계획·자금 표시를 새 계획(plan dict)에 맞춤,
#   ➕ 직접 산 주식 반영에 세 번째 글자 '차감' 추가 (예: 63 61.50 차감 = --add-shares --credit). 주문·설정 변경 기능은 그대로 없음
# 메리츠 무매 SOXL 텔레그램 메뉴: 📈 상황판 · ☰ 메뉴 · 🛠 도구 (맨밑 키보드만, 인라인 버튼 없음)
# v1.0.4 (2026-11-14): 봇 번호 정리 — 표시 이름 '메리츠 무매 SOXL' → '7번 메리츠 무매' (머리글·도움말·상황판)
# v1.0.3 (2026-11-14): 첫 버전.
#   - 토큰: 설정 telegram_file (notifier.py 와 같은 파일, 새 토큰 없음). 토큰 원문은 어디에도 출력·기록하지 않음 (지문 token_fp 만)
#   - check_identity() 가 '텔레그램 토큰이 다른 봇과 같음' 이면 폴링하지 않음 (forbid_telegram_files 검사 그대로)
#   - 등록된 chat_id 가 아닌 방의 글자·버튼은 조용히 무시 (알림 없음)
#   - 직렬화: main.idle() 안에서만 돎 = loop() 와 같은 스레드에서 순서대로. 별도 스레드·프로세스 없음.
#     장부·설정 쓰기는 기존 함수(cmd_add_shares → ConfigManager.add_shares, cmd_inject_start → inject_start,
#     clear_halt)만 부르며, 기존 GlobalThrottle.get_file_lock() 잠금을 그대로 씀
#   - 메뉴 동작은 기존 함수만 부름: cmd_check · build_plan+fmt_orders+plan_head · sell_target ·
#     cmd_add_shares · ConfigManager.clear_halt · cmd_inject_start(= --inject-start) · key_fingerprint
#   - 처음 시작 때 쌓여 있던 예전 업데이트는 건너뜀 (재시작으로 옛 버튼이 다시 실행되지 않게) · 2분 넘은 메시지 무시
# ==========================================================
import contextlib
import copy
import html as _html
import io
import json
import logging
import math
import os
import re
import time
import urllib.request

from config import update_settings
import tower_strategy as _TW
import sniper_mode as _SN
from global_throttle import GlobalThrottle
from notifier import Notifier, to_korean

# ---- v2.3.0 메뉴: 스나이퍼 봇 형식. 첫 화면(reply keyboard) 2행 4개 — 글자 앞 이모티콘은 handle 이 떼고 읽음 (예전 이모티콘 키보드와 같은 방식)
B_RADAR, B_SYNC, B_TOWER, B_FX = "스나이퍼 레이더", "잔고 동기화", "탑쌓기 매매", "환전"      # 판 35: 전술 제어반(⚙️) 없앰 → 탑쌓기 매매 화면
MAIN_ROWS = [["🔫 " + B_RADAR, "🏛️ " + B_TOWER], ["🔄 " + B_SYNC, "💱 " + B_FX]]      # 판 35 첫 화면 최종 형태
BACK = "뒤로"
R_REFRESH, T_TOOLS = "새로고침", "도구"
I_FUNDS, I_PLAN, I_LEDGER, I_POWER = "자금 현황", "오늘 계획", "거래 내역", "봇 상태"
T_CHECK, T_ADD, T_HALT, T_INJECT, T_FP = "점검", "주식 넣기", "정지 해제", "장부 시작", "키 확인"
T_STOP = "매매 정지"                               # 정지 표시를 켬 (정지 해제의 짝)
TOOLS_INLINE = [[T_CHECK, T_ADD], [T_STOP, T_HALT], [T_INJECT, T_FP], [BACK]]
HALT_OK, INJECT_OK, INJECT_OVER = "정지 해제 확인", "장부 시작 확인", "장부 덮어쓰기 확인"
CHG_OK = "변경 확인"
ADD_OK = "주식 넣기 확인"                            # 장부가 바뀌므로 수량·평단을 보여 준 뒤 확인
BOT_ON, BOT_OFF = "봇 켜기", "봇 끄기"
FX_ON, FX_OFF = "자동환전 켜기", "자동환전 끄기"
T_MODE_TOWER, T_MODE_SNIPER, MODE_OK = "탑쌓기 매매 시작", "스나이퍼 매매로 돌아가기", "네, 바꿀게요"      # v2.9.0 6차 판 33: 매매 모드 바꾸기 (누르면 확인 메시지 → [네, 바꿀게요] 를 눌러야만 바뀜)

# 설정 변경 버튼 → 설정 키·이름·단위·종류. kind: krw(원, 억·만 가능) | int | num(소수 가능). lo/hi: 허용 범위 (lo_incl/hi_incl 로 경계 포함 여부)
SET_ITEMS = {
    "탑쌓기 매도% 변경": dict(key="sell_profit_pct", name="탑쌓기 매도%", unit="%", kind="num", lo=0, lo_incl=False, hi=500, ex="예: 10 (완성 F 평단보다 10% 오르면 매도)"),
    "매도 비중 변경": dict(key="sell_fraction_pct", name="매도 비중", unit="%", kind="num", lo=0, lo_incl=False, hi=100, hi_incl=False, ex="예: 50 (보유의 절반을 매도)"),
    "버킷 시드 변경": dict(key="tower_box_seed_usd", name="버킷 시드", unit="$", kind="int", lo=0, lo_incl=False, ex="예: 15000 (버킷 시드. 매수 1번 = 이 금액 × 모드 비율 — 복리 8%·단리 10%)"),
    "매수 간격 변경": dict(key="tower_buy_gap_usd", name="매수 간격", unit="$", kind="int", lo=1, hi=10, ex="예: 5 (탑쌓기 매매 모드에서 시초가 가까운 칸부터 $1씩 아래로 5칸에 시드를 균등 분산. 1~10)"),
    "F 완성 기준 금액 변경": dict(key="tower_floor_usd", name="F 완성 기준 금액", unit="$", kind="int", lo=0, lo_incl=False, ex="예: 15000 (한 F에 쌓을 달러, 정수)"),
    "하루 매수 F 수 변경": dict(key="tower_max_buy_layers_per_day", name="하루 매수 F 수", unit="F", kind="int", lo=1, hi=3, ex="예: 2"),
    "하루 매도 F 수 변경": dict(key="tower_max_sell_layers_per_day", name="하루 매도 F 수", unit="F", kind="int", lo=1, hi=3, ex="예: 2"),
    "환전 여유% 변경": dict(key="auto_fx_buffer_pct", name="환전 여유%", unit="%", kind="num", lo=0, hi=100, ex="예: 3 (모자란 달러보다 3% 더 환전)"),
    "환전 하루 상한 변경": dict(key="auto_fx_max_usd_per_day", name="환전 하루 상한", unit="$", kind="int", lo=0, lo_incl=False, ex="예: 5000 (달러, 정수)"),
}
KEY_ITEM = {i["key"]: i for i in SET_ITEMS.values()}
# v2.1.0 (2026-11-19): 값 바꾸기 화면에 '넣을 수 있는 값 · 무슨 뜻 · 바꾸면' 설명 추가 (값 범위·검사·확인 단계는 그대로, 어려운 말은 시드·평단·분할매도·자동환전·장부만 씀)
MEANS = {
    "sell_profit_pct": ("완성 F를 파는 기준이에요. 그 F 평단보다 이 %만큼 오르면 매도해요 (탑쌓기 매도).", "다음 판단부터 완성 F 파는 시점이 달라져요"),
    "sell_fraction_pct": ("탑쌓기 매도가 일어날 때 그 F 보유 중 파는 비중이에요 (정수 주 내림, 1주는 남김).", "다음 탑쌓기 매도부터 파는 양이 달라져요"),
    "tower_box_seed_usd": ("버킷 하나의 시드(달러)예요. 매수 신호 1번에 이 금액의 모드 비율(복리 8%·단리 10%, 서브 신호는 4%)을 사요. 마지막 회차는 버킷에 남은 시드만큼 사요. 안 정하면 15000이에요.", "다음 매수부터 한 번에 사는 금액과 새 버킷 크기가 달라져요 (이미 있는 F는 안 바뀜)"),
    "tower_buy_gap_usd": ("탑쌓기 매매 모드에서 F 완성 기준 금액을 나눠 사는 칸 수예요 (시초가와 가장 가까운 칸부터 $1씩 아래로 이 칸 수만큼, 칸마다 같은 금액). 1~10 정수, 안 정하면 5예요. 스나이퍼 모드에서는 안 써요.", "탑쌓기 매매 모드의 다음 매수 계획부터 칸 수가 달라져요"),
    "tower_floor_usd": ("한 F의 시드(달러)예요. F 원가가 이 금액에 닿으면 그 F는 완성이에요. 총 시드·F 수 한도는 없어요. 안 정하면 15000이에요.", "새 F·남은 몫 매수 금액과 F 완성 기준이 달라져요"),
    "tower_max_buy_layers_per_day": ("하루에 채울 F 수예요 (아침 환전 금액 = F 완성 기준 금액 × 이 값). 1~3 정수만 돼요. 안 정하면 1이에요.", "아침 환전액이 달라져요"),
    "tower_max_sell_layers_per_day": ("하루에 최대 몇 F까지 팔지예요. 1~3 정수만 돼요. 안 정하면 1이에요 (지금처럼 하루에 한 F). 같은 때 여러 F가 목표에 닿으면 번호가 큰 F(맨 위 F)부터 팔아요.", "다음 매도 확인부터 하루에 파는 F 수가 달라져요 (목표 이익률·매도 비중은 그대로)"),
    "auto_fx_buffer_pct": ("자동환전 때 부족분에 더해 환전하는 여유 비율이에요.", "다음 자동환전 금액이 달라져요"),
    "auto_fx_max_usd_per_day": ("자동환전을 하루에 최대 얼마까지 할지 정한 상한이에요.", "하루 환전 한도가 달라져요"),
}
_EMOJI_RE = re.compile("(?:[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u25A0-\u25FF\u2300-\u23FF\u2900-\u297F\u2139\uFE0F\u200D])+ ?")   # 예전 이모티콘 키보드 글자를 새 버튼으로 읽는 데 씀
BOOL_NAME = {"compound_enabled": "복리 모드", "enabled": "봇", "auto_fx_enabled": "자동환전"}
T_ASSN, ASSN_OK = "암살자 승격", "네, 암살자 바꿀게요"      # v2.13.0 판 40 할 일 2: 암살자 승격·복귀 (눌러도 바로 안 바뀌고 확인부터 — 원작은 한 번 누름. 실돈이라 확인 단계 추가)
T_PMODE, PM_OK = "매수 비율 모드 바꾸기", "네, 모드 바꿀게요"      # v2.15.0 판 41 할 일 5: 복리↔단리 2순환 (바벨 삭제)
PM_KO = {"compound": "복리 8%", "simple": "단리 10%"}
PM_NEXT = {"compound": "simple", "simple": "compound"}
PM_CHANGES = {"compound": {"compound_enabled": True}, "simple": {"compound_enabled": False}}
MODE_KO = {"sniper": "하이브리드 스나이퍼 매매", "tower": "탑쌓기 매매"}
FX_NEED = "여유%와 하루 상한을 먼저 입력해 주세요"          # 값 없이 켜기를 눌렀을 때 이 글자만
SET_POWER = "봇 켜기/끄기"
TOWER_SET = ["매수 간격 변경", "탑쌓기 매도% 변경", "매도 비중 변경", "하루 매수 F 수 변경", "하루 매도 F 수 변경"]      # 판 35: 탑쌓기 매매 화면 (판 39: F 완성 기준 금액은 잔고 동기화로 이동, 남은 시드 삭제)
SYNC_SET = ["F 완성 기준 금액 변경", "버킷 시드 변경"]      # 판 39 할 일 3: 시드 설정 = 잔고 동기화 화면
TACT_SET = TOWER_SET + SYNC_SET
FX_SET = ["환전 하루 상한 변경", "환전 여유% 변경"]
TOWER_DEFAULTS = {"tower_buy_gap_usd": _TW.GAP_USD, "tower_floor_usd": int(_TW.FLOOR_USD), "tower_box_seed_usd": int(_TW.BOX_SEED_USD), 
                  "tower_max_buy_layers_per_day": 1, "tower_max_sell_layers_per_day": 1,
                  "sniper_tp_l1_pct": _SN.TP_L1_DEFAULT, "sniper_tp_upper_pct": _SN.TP_UPPER_DEFAULT}   # 설정에 없으면 쓰는 기본값 (표시용)


def _f0(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def cur_val(s, key):
    """설정값, 없으면 탑쌓기 기본값 (표시용)"""
    v = (s or {}).get(key)
    return TOWER_DEFAULTS.get(key) if v is None else v
PARENT = {"tools": "tower"}
CONFIRM_SEC = 60            # 제안값: 확인 버튼 유효 시간
WAIT_SEC = 300              # 제안값: 수량·평단 입력 기다림
MSG_MAX_AGE = 120           # 이보다 오래된 메시지는 처리하지 않음
HEAD = "7번 메리츠 SOXL 하이브리드"
ALL_LABELS = ({B_RADAR, B_SYNC, B_TOWER, B_FX, BACK, R_REFRESH, T_TOOLS, I_FUNDS, I_PLAN, I_LEDGER, I_POWER, T_CHECK, T_ADD, T_HALT, T_INJECT,
               T_FP, T_STOP, HALT_OK, INJECT_OK, INJECT_OVER, CHG_OK, ADD_OK, BOT_ON, BOT_OFF, FX_ON, FX_OFF, T_MODE_TOWER, T_MODE_SNIPER, MODE_OK, T_PMODE, PM_OK, T_ASSN, ASSN_OK} | set(SET_ITEMS))
LABEL_LIST = sorted(ALL_LABELS)
LABEL_IDX = {x: i for i, x in enumerate(LABEL_LIST)}      # 인라인 버튼 callback_data = "c:<번호>" (64바이트 제한 때문에 글자 대신 번호 — 같은 버전 안에서는 항상 같은 번호)


def fmt_krw(n):
    """원 금액을 짧게: 200000000 → '2억' · 20000000 → '2,000만원' · 150000000 → '1억 5,000만원' · 9500 → '9,500원' (앞에 긴 숫자 안 붙임)"""
    n = int(round(float(n)))
    if n < 10**4:
        return f"{n:,}원"
    e, m = divmod(int(round(n / 10**4)), 10**4)
    if e and not m:
        return f"{e:,}억"
    return (f"{e:,}억 " if e else "") + f"{m:,}만원"


def fmt_val(item, v, none="미정"):
    if v is None:
        return none
    if item["kind"] == "krw":
        return fmt_krw(v)
    if item["unit"] == "$":
        return f"${v:,}" if item["kind"] == "int" else f"${float(v):,.2f}"    # 달러 설정 중 소수 허용 항목(맨 위 F 시작가 등)은 소수 2자리
    return f"{v:g}{item['unit']}"


def _num(v):
    try:
        return None if v is None or isinstance(v, bool) else float(str(v).replace(",", ""))
    except ValueError:
        return None


def fx_values_ready(s):
    """자동환전 여유%(0 이상)·하루 상한(0 초과)을 사용자가 입력했는지 (config.validate_settings 와 같은 조건)"""
    b, m = _num(s.get("auto_fx_buffer_pct")), _num(s.get("auto_fx_max_usd_per_day"))
    return b is not None and b >= 0 and m is not None and m > 0


def parse_value(item, text):
    """입력 글자 → (값, 오류 글자). 오류가 있으면 값은 None"""
    t = re.sub(r"[,\s$%원회]", "", text)
    if item["kind"] == "krw":
        m = re.fullmatch(r"(?:(\d+(?:\.\d+)?)억)?(?:(\d+(?:\.\d+)?)만)?(\d+)?", t)
        if not t or not m or not any(m.groups()):
            return None, "숫자로 보내 주세요. " + item["ex"]
        x = float(m.group(1) or 0) * 10**8 + float(m.group(2) or 0) * 10**4 + float(m.group(3) or 0)
        if abs(x - round(x)) > 1e-6:
            return None, "원 단위 정수로 환산되지 않아요. " + item["ex"]
        v = int(round(x))
    elif item["kind"] == "int":
        if not re.fullmatch(r"\d+", t):
            return None, "정수로 보내 주세요. " + item["ex"]
        v = int(t)
    else:
        if not re.fullmatch(r"\d+(?:\.\d+)?", t):
            return None, "숫자로 보내 주세요. " + item["ex"]
        x = float(t)
        v = int(x) if x == int(x) else x
    lo, hi = item.get("lo"), item.get("hi")
    if lo is not None and not (v >= lo if item.get("lo_incl", True) else v > lo):
        return None, (f"{lo} 이상이어야 해요" if item.get("lo_incl", True) else f"{lo}보다 커야 해요")
    if hi is not None and not (v <= hi if item.get("hi_incl", True) else v < hi):
        return None, (f"{hi} 이하여야 해요" if item.get("hi_incl", True) else f"{hi} 미만이어야 해요")
    return v, None


def kb(rows):
    return {"keyboard": [[{"text": t} for t in r] for r in rows], "resize_keyboard": True, "is_persistent": True}


def ikb(rows):
    """인라인 버튼줄. 칸은 글자(= 그 글자가 곧 버튼 이름) 또는 (보이는 글자, 버튼 이름) — 버튼 이름은 ALL_LABELS 안의 것"""
    out = []
    for r in rows:
        line = []
        for b in r:
            txt, lab = (b, b) if isinstance(b, str) else b
            line.append({"text": txt, "callback_data": f"c:{LABEL_IDX[lab]}"})
        out.append(line)
    return {"inline_keyboard": out}


class MenuBot:
    @staticmethod
    def range_text(it):
        """값 설명 화면의 '넣을 수 있는 값' 글자 (범위·단위는 SET_ITEMS 의 lo/hi/unit 그대로)"""
        lo, hi = it.get("lo"), it.get("hi")
        u = {"krw": "원 (억·만 표기 가능)", "int": it["unit"] + " 정수", "num": it["unit"]}[it["kind"]]
        if it["unit"] == "$" and it["kind"] == "num":
            u = "달러"
        a = "" if lo is None else (f"{lo} 이상" if it.get("lo_incl", True) else f"{lo} 초과")
        b = "" if hi is None else (f"{hi} 이하" if it.get("hi_incl", True) else f"{hi} 미만")
        return (a + (" ~ " if a and b else "") + b + " · " if (a or b) else "") + u

    def __init__(self, ops):
        self.o = ops                 # meritz_laoer/main.py 모듈 (기존 함수를 그대로 부름)
        self.offset = None
        self.primed = False
        self.wait = None             # {"kind": "add"|"set", "ts", "label"}
        self.pending = None          # 변경 확인 대기: {"changes", "desc", "ts"}
        self.in_prompt = False       # 입력·확인 화면이 떠 있는 동안 True (뒤로 = 그 화면 취소하고 같은 메뉴로)
        self.nav = "main"            # 지금 보이는 화면 (main|fund|tact|stat|etc|settings|fx) — 뒤로 와 기본 버튼줄이 따라감
        self.confirm = {}            # 확인 버튼 글자 → 누를 수 있는 마지막 시각
        self._cred = (0.0, None)     # (확인 시각, (토큰, chat_id) 또는 None) — 60초마다 다시 확인
        self._warn_at = {}           # 판 5 보완: 조용히 무시하던 이유별 마지막 로그 시각 (같은 이유는 10분에 한 번만)

    # ---------------------------------------------------------- 텔레그램
    def creds(self, s):
        """notifier 와 같은 telegram_file. check_identity 가 '다른 봇 토큰과 같음'이면 None (폴링 안 함)"""
        now = time.time()
        if now - self._cred[0] > 60:
            c = None
            n = Notifier(s.get("telegram_file") or "")
            if not n.ok:
                self._why("nocred", "메뉴 멈춤: 텔레그램 파일에 토큰 또는 chat_id 가 없음")
            elif any("텔레그램 토큰이 다른 봇과 같음" in b for b in self.o.check_identity(s)[0]):
                self._why("dup", "메뉴 멈춤: 텔레그램 토큰이 다른 봇과 같음 (forbid_telegram_files)")
            else:
                c = (n.token, n.chat_id)
            self._cred = (now, c)
        return self._cred[1]

    def _why(self, key, text, every=600):
        """메뉴가 메시지를 조용히 버리거나 멈추는 이유를 로그에 남김 (같은 이유는 every 초에 한 번)"""
        now = time.time()
        if now - self._warn_at.get(key, 0.0) > every:
            self._warn_at[key] = now
            logging.warning("텔레그램 " + text)

    def _call(self, tok, method, payload, timeout):
        req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)

    def send(self, c, text, rows=None, dry=True, html=False, inline=None):
        """html=True 면 text 를 텔레그램 HTML(굵게 등)로 보냄 — 이미 이스케이프한 글자여야 함. inline 을 주면 그 인라인 버튼줄을 붙임 (맨밑 키보드는 그대로 남음), 아니면 맨밑 키보드(rows, 기본 첫 화면 4개)"""
        tok, chat = c
        if html:
            msg = (("[모의] " if dry else "") + HEAD + "\n" + text).replace(tok, "***")[:3900]
        else:
            msg = (("[모의] " if dry else "") + HEAD + "\n" + to_korean(text)).replace(tok, "***")[:3900]
        markup = ikb(inline) if inline else kb(rows or MAIN_ROWS)
        try:
            self._call(tok, "sendMessage", dict({"chat_id": chat, "text": msg, "reply_markup": markup}, **({"parse_mode": "HTML"} if html else {})), 15)
        except Exception as e:
            logging.warning(f"텔레그램 메뉴 전송 실패: {type(e).__name__}")

    def idle(self, s, t_end, once=False):
        """t_end 까지 getUpdates → 받은 것을 순서대로 처리 (이 스레드에서만).
        v2.13.0 판 40: once=True 면 기다리지 않고 한 번만 확인 (getUpdates timeout 0) 하고 돌아옴 — 1.5초 스나이퍼 틱 사이에 부름 (바쁜 대기 방지)"""
        c = self.creds(s)
        if not c:
            return
        tok, chat = c
        if not self.primed:          # 쌓인 옛 업데이트 건너뜀
            r = self._call(tok, "getUpdates", {"offset": -1, "timeout": 0}, 10)
            res = r.get("result") or []
            self.offset = (res[-1]["update_id"] + 1) if res else None
            self.primed = True
        while True:
            left = t_end - time.time()
            if left < 1 and not once:
                return
            q = {"timeout": 0 if once else int(min(25, max(0, left - 1))), "allowed_updates": ["message", "callback_query"]}
            if self.offset is not None:
                q["offset"] = self.offset
            r = self._call(tok, "getUpdates", q, q["timeout"] + 10)
            stale = False
            for upd in r.get("result") or []:
                self.offset = upd["update_id"] + 1
                m = upd.get("message")
                cq = upd.get("callback_query")
                if isinstance(cq, dict):          # v2.3.0 인라인 버튼: 누른 버튼 이름을 글자처럼 handle 에 넘김 (등록된 방의 버튼만)
                    cm = cq.get("message") or {}
                    try:
                        self._call(tok, "answerCallbackQuery", {"callback_query_id": cq.get("id")}, 10)
                    except Exception:
                        pass
                    if str((cm.get("chat") or {}).get("id", "")).strip() != str(chat):
                        self._why("chat", "메뉴: 등록된 방이 아닌 곳의 버튼 누름은 무시 — telegram 파일 chat_id 확인", 60)
                        continue
                    data = str(cq.get("data") or "")
                    if data.startswith("pk:"):          # v2.4.0 스나이퍼 가격 선택 버튼 ('pk:<층 평단>:s|t')
                        try:
                            parts = data.split(":")
                            try:
                                s = self.o.load_settings()
                            except Exception:
                                pass
                            self.send(c, self.o.apply_pick(s, parts[1], parts[2]) if len(parts) == 3 else "알 수 없는 버튼이에요", dry=s.get("dry_run", True))
                        except Exception as e:
                            logging.warning(f"텔레그램 선택 처리 실패: {type(e).__name__}")
                            self.send(c, "선택을 처리하지 못했어요. 다시 눌러 주세요.", dry=s.get("dry_run", True))
                        continue
                    lab = LABEL_LIST[int(data[2:])] if data.startswith("c:") and data[2:].isdigit() and int(data[2:]) < len(LABEL_LIST) else ""
                    if not lab:
                        continue
                    try:
                        try:
                            s = self.o.load_settings()
                        except Exception:
                            pass
                        self.handle(s, c, lab)
                    except Exception as e:
                        logging.warning(f"텔레그램 메뉴 처리 실패: {type(e).__name__}")
                        self.send(c, "처리 중 오류가 났어요. 다시 눌러 주세요.", dry=s.get("dry_run", True))
                    continue
                if not isinstance(m, dict):
                    continue
                if str((m.get("chat") or {}).get("id", "")).strip() != str(chat):
                    self._why("chat", f"메뉴: 등록된 방이 아닌 곳({(m.get('chat') or {}).get('type')})의 메시지는 무시 — telegram 파일 chat_id 확인", 60)
                    continue          # 다른 방은 무시 (이유는 로그에만)
                age = time.time() - float(m.get("date") or 0)
                if age > MSG_MAX_AGE:
                    self._why("stale", f"메뉴: {int(age)}초 지난 메시지는 처리 안 함 (서버 시계 어긋남이나 긴 대기 확인)", 60)
                    stale = True
                    continue
                try:
                    try:
                        s = self.o.load_settings()
                    except Exception:
                        pass                      # 못 읽으면 직전 값으로
                    self.handle(s, c, (m.get("text") or "").strip())
                except Exception as e:
                    logging.warning(f"텔레그램 메뉴 처리 실패: {type(e).__name__}")
                    self.send(c, "처리 중 오류가 났어요. 다시 눌러 주세요.", dry=s.get("dry_run", True))
            if stale:                 # 오래된 메시지를 말없이 버리지 않고 한 번 알림
                self.send(c, "메시지가 늦게 도착해서(2분 넘음) 처리하지 않았어요. 버튼을 다시 눌러 주세요.", dry=s.get("dry_run", True))
            if once:
                return

    # ---------------------------------------------------------- 기존 함수 부르기
    def _out(self, fn, *a, **k):
        """기존 CLI 함수(print 출력)를 그대로 부르고 출력만 받아 옴 → (반환값, 출력 글자)"""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = fn(*a, **k)
        return rc, buf.getvalue().strip()

    def _api(self, s):
        o = self.o
        return o.MeritzApi(s["key_file"], os.path.join(s["state_dir"], "data", "meritz_token.json"))

    def _local(self, s):
        o = self.o
        os.makedirs(os.path.join(s["state_dir"], "data"), exist_ok=True)
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            pos, halt = cfg.get_position(), cfg.get_halt()
            avg = cfg.avg_price(pos) if pos else 0.0
            tgt = o.sell_target(s, cfg, pos) if pos else None
        return pos, halt, avg, tgt

    def _api_ok(self, s):
        """cmd_check 와 같은 조건: 설정 문제·키 파일 없음·키 형식 오류면 메리츠 조회 안 함 → 문제 목록"""
        bad = self.o.validate_settings(s)
        idb, _ = self.o.check_identity(s)
        return bad + [b for b in idb if b in ("새 메리츠 키 파일 없음 (key_file)", "키 파일 형식 오류 (app_key/app_secret)")]

    def board(self, s):
        """상황판 값 (조회만 — 주문·장부·설정을 바꾸지 않음). cmd_check 와 같은 입력으로 오늘 계획 미리보기. v2.3.0 B8: 층 상태는 오늘 체결을 메모리에서 더한 값(d["tst"]) 으로 계산하고, 잔고와 비교하는 장부 수량(d["live_qty"])도 그 값"""
        o = self.o
        d = {"pos": None, "halt": None, "avg": 0.0, "target": None, "api_bad": [], "hold": None, "sellable": None,
             "price": None, "prev": None, "fx": None, "cash": None, "plan": None, "orders": [], "notes": [], "plan_err": None,
             "tst": None, "live_note": "", "live_qty": None}
        d["pos"], d["halt"], d["avg"], d["target"] = self._local(s)
        d["api_bad"] = self._api_ok(s)
        d["tst"], d["live_note"] = self.live_state(s, d)
        tq = sum(int(f.get("qty") or 0) for f in (d["tst"] or {}).get("floors") or [])
        d["live_qty"] = tq if tq > 0 else (int(d["pos"]["qty"]) if d["pos"] else None)
        if d["api_bad"]:
            return d
        api = self._api(s)
        d["hold"], d["sellable"], _ = api.holding(s["symbol"])
        d["price"], d["prev"], d["fx"] = o.market_inputs(s, api)
        d["cash"] = api.usd_cash()
        try:
            pos, st = d["pos"], s["start"]
            q = int(pos["qty"]) if pos else int(float(st["qty"]))
            principal = float(pos["principal"]) if pos else float(st["principal_usd"])
            with o.in_dir(s["state_dir"]):
                d["plan"] = o.build_plan(s, o.ConfigManager(s), d["price"], d["fx"], d["cash"], q, principal, d["sellable"], tst=copy.deepcopy(d["tst"]))
            d["orders"], d["notes"] = d["plan"]["orders"], d["plan"]["notes"]
        except Exception as e:
            d["plan_err"] = type(e).__name__
        return d

    def plan_lines(self, s, d):
        if d["api_bad"]:
            return ["오늘 계획: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")"]
        if d["plan"] is None:
            return [f"오늘 계획: 미확인 ({d['plan_err']})"]
        return ["오늘 계획 (미리보기 · 주문 안 냄)", self.o.plan_head(d["plan"], s), self.o.fmt_orders(d["orders"])] + \
               ["· " + n for n in d["notes"]]

    def mode_line(self, s, halt):
        return (f"· 봇 {'켜짐' if s.get('enabled') else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'}\n"
                f"· 정지 표시: {(halt or {}).get('reason') if halt else '없음'}")

    def strategy_text(self, s):
        """현재 전략 글자 — 7번은 탑쌓기만 씀 (v2.2.9)"""
        return self.o.strategy_ko(s)

    def tower_lines(self, s, d):
        """v2.2.2 (판 14): F 시각화 줄 (F 칸 + N/최대F + F별 상세). F 상태 파일을 읽기만 함 — 파일이 없으면 지금 장부를 1F로 본 값(저장 안 함)"""
        o, pos = self.o, d.get("pos")
        try:
            with o.in_dir(s["state_dir"]):
                tst, _ = o.tower_state_for(o.ConfigManager(s), int(pos["qty"]) if pos else 0, float(pos["principal"]) if pos else 0.0, s)
            return o.TW.view_lines(tst, s)
        except Exception:
            return ["탑: F 상태 미확인"]

    def intraday_text(self, s):
        """당일 매도 확인 상태 글자"""
        sec = _num(s.get("intraday_sell_check_sec")) or 0
        if sec <= 0:
            return "꺼짐"
        if s.get("order_type") != "LIMIT":
            return "꺼짐 (지정가 주문일 때만 켜져요)"
        return f"{int(sec // 60)}분마다" if sec % 60 == 0 else f"{int(sec)}초마다"

    def live_state(self, s, d):
        """v2.2.20 실시간 F 상태 → (F 상태, 안내 글자). 장부 파일(tower_state.json)에 오늘 체결을 메모리에서만 더함 (조회만 — 파일·장부·주문 안 건드림).
        체결을 못 읽으면(키·조회 오류 등) 장부 기준 그대로 + 안내"""
        o, pos = self.o, d.get("pos")
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            tst, _had = o.tower_state_for(cfg, int(pos["qty"]) if pos else 0, float(pos["principal"]) if pos else 0.0, s)
            day = o.now_et().strftime("%Y-%m-%d")
            m = cfg._load_json(f"data/{'dry_' if s.get('dry_run', True) else ''}orders_{day}.json", None)
        tst = copy.deepcopy(tst)
        if not (isinstance(m, dict) and (m.get("orders") or [])) or s.get("dry_run", True):
            return tst, ""
        if d.get("api_bad"):
            return tst, "오늘 체결은 못 읽어서 장부 기준이에요"
        try:
            rows = o.fill_rows_for(self._api(s), s, day)
            items = o.fill_items(m, rows)
            with o.in_dir(s["state_dir"]):
                o.apply_tower_fills(s, o.ConfigManager(s), day, items, tst, persist=False)
            return tst, ("오늘 체결 반영됨 (조회만)" if items else "")
        except Exception as e:
            return tst, f"오늘 체결 조회 실패 ({type(e).__name__}) — 장부 기준이에요"

    def floor_lines(self, s, st, px, esc=_html.escape):
        """F마다 한 줄 (레이더·잔고 동기화 공용, HTML) → (줄 목록, 채우는 F 줄). F 번호 = 평단 낮은 F가 1 (스나이퍼 번호).
        상태: 완성 = 탑 매도 대상(평단 +탑쌓기 매도%) · 재매수 대기 / 탑업 중 = 스나이퍼 매도 대상(1층 +1.0% · 상단 +1.0%, 전량). 채움률 = 원가 ÷ F 완성 기준 금액"""
        rows = sorted(_SN.sell_rows(st, s, px), key=lambda r: r["no"])
        pct_t = float(s.get("sell_profit_pct") or 0)
        out, fill = [], None
        for r in rows:
            g = r["gain_pct"]
            ratio = (r["cost"] / r["tgt_usd"]) if r["tgt_usd"] else 0.0
            if r["complete"]:
                tg, state, prog = _TW.ceil2(r["avg"] * (1 + pct_t / 100.0)), ("잠금·탑 매도" if r.get("locked") else "완성·탑 매도"), ""
            else:
                tg = r["target"]
                state = "재매수 대기" if r["rebuy"] else "탑업 중"
                prog = f" ◧{int(round(ratio * 100))}%"
                fill = fill or (r["no"], ratio, r["cost"], r["tgt_usd"], state)
            out.append(f"⚡ <b>[{esc(r['label'])}: {r['qty']}주·${r['cost']:,.0f}]</b> <b>${r['avg']:.2f}</b> ➔ <b>${tg:.2f}</b> ({'+' if (g or 0) >= 0 else ''}{(g or 0):.2f}%) {esc(state)}{prog}")
            if not r["complete"]:                      # v2.6.0 버킷별 매도: 버킷마다 자기 평단·목표 (공격 버킷 +1.0% · 나머지 +1.0%)
                for b in (r.get("boxes") or [])[:4]:
                    out.append(f"   ▫ 버킷 ${b['avg']:.2f} · {b['qty']}주 ➔ ${b['target']:.2f} (+{b['pct']:g}%{' · 공격' if b['role'] == 'L1' else ''}{' · 졸업 매도' if b.get('kind') == 'grad' else ''})")
                if len(r.get("boxes") or []) > 4:
                    out.append(f"   ▫ 그 위 {len(r['boxes']) - 4}개 버킷은 같은 규칙")
        for e in (st.get("empty") or []):          # v2.4.0 빈 F (공사중 · 스나이퍼 선택 새 F) — 0주·$0, 번호는 채워진 뒤 평단 순으로 붙음
            if isinstance(e, dict):
                out.append("⚪ <b>[" + ("공사중" if e.get("kind") == "basement" else "새 버킷") + ": 0주·$0]</b>" + (f" 기준가 ${float(e.get('ref_px') or 0):.2f}" if float(e.get("ref_px") or 0) > 0 else " 스나이퍼 매수가 여기서 시작"))
        return out, fill

    def board_text(self, s):
        """스나이퍼 레이더 (텔레그램 HTML). 스나이퍼 봇 형식: 굵은 제목·이모티콘 · F마다 한 줄 · 다음 매수 타점 · 구분선 · 기준 시각. 오늘 체결은 메모리에서 더해 실시간으로 보여줌. 조회만"""
        esc = _html.escape
        d = self.board(s)
        dry = s.get("dry_run", True)
        o = self.o
        st, live_note = d["tst"], d["live_note"]
        px = float(d["price"]) if d.get("price") else 0.0
        fu, _nfl, _gap = _TW.params(s)
        div = "──────────────"
        with o.in_dir(s["state_dir"]):
            ss = _SN.load_state(o.ConfigManager(s))
        rsi = _SN.rsi_from_state(ss, time.time())[0]
        lines = [f"📡 <b>[메리츠 SOXL 레이더]</b> (⚡하이브리드 · {'모의' if dry else '실거래'} · {'봇 켜짐' if s.get('enabled') else '봇 꺼짐'} · {esc(o.BOT_VERSION)})"]
        lines.append((f"🐂 <b>SOXL</b> 현재가 <b>${px:.2f}</b>" + (f" · RSI <b>{rsi:.1f}</b>" if rsi is not None else " · RSI 모으는 중")) if px else "🐂 <b>SOXL</b> 시세 미확인")
        if d.get("halt"):
            lines.append(f"🛑 정지 표시: {esc(str((d['halt'] or {}).get('reason') or ''))[:80]}")
        lines.append(div)
        fl = _SN.active_floors(st)
        tq, tc = _TW.totals(st)
        floor_rows, fill = self.floor_lines(s, st, px)
        lines.append(f"🏛️ <b>[보유 F : {len(fl)}F · 총 {tq}주]</b> (원가 ${tc:,.0f})")
        if fill:
            n = max(0, min(10, int(round(fill[1] * 10))))
            lines.append("🟨" * n + "⬜" * (10 - n) + f" {fill[0]}F {esc(fill[4])} · 채움 {fill[1] * 100:.0f}% (${fill[2]:,.0f} / F 완성 기준 금액 ${fill[3]:,.0f})")
        elif fl:
            lines.append("🟦" * 10 + " 모든 F 완성 · 다음 매수는 새 F")
        if not fl:
            lines.append("⚪ <b>[보유 F: 0주]</b> 첫 매수는 가격 조건 없이 현재가로 사요 (15:00 전 · 개장 7분 · 1분봉 검문 통과 시)")
        lines += floor_rows
        if fl:
            lines.append(f"▫️ 완성 F: 탑 매도 평단 +{float(s.get('sell_profit_pct') or 0):g}% → 보유의 {float(s.get('sell_fraction_pct') or 0):g}% · 미완성 F: 스나이퍼 1층 +{_SN.tp_pcts(s)[0]:g}% · 상단층 +{_SN.tp_pcts(s)[1]:g}% 전량")
        lines.append(div)
        if d["api_bad"]:
            lines.append("🎯 메리츠 조회 미확인: " + esc("; ".join(d["api_bad"][:3])))
        else:
            lines.append("🎯 <b>[다음 매수 타점]</b>")
            anchor, kind = _SN.anchor_info(st, ss, s)
            cap = _SN.lowest_layer_avg(fl)
            late = _SN.is_late_cutoff(o.now_et())
            sig = (_SN.first_buy_signal(px, o.now_et(), None) if not fl else _SN.timed_signal(px, anchor, kind, cap, _SN.depth_layers(ss, _SN.layer_count(fl)), rsi, o.now_et(), _SN.layer_count(fl)))      # 판 39: 보유 0개는 첫 매수 검문 (레이더는 1분봉을 안 읽으므로 HA 칸은 '준비 전'으로 보임)
            if not fl:      # v2.12.0 판 39: 보유 0개 = 원작 분기 A — 눌림·기준가 안 봄 (신호 칸이 검문 결과를 보여 줌)
                lines.append(f"▫️ 첫 매수: 가격 조건 없이 현재가 ${_SN.exec_price(px):.2f} (소수 2자리 내림) · 한 번에 버킷 시드의 {_TW.portion_pct(s):g}% (${_TW.portion_usd(s):,.0f})")
            elif anchor > 0:
                gate = "신규 진입 차단(15:00~)" if (late and not fl) else ("개장 7분 쉴드(09:30~09:36)" if sig["signal_type"] == "HOLD_REG_OPEN_7M_VWAP_SHIELD" else "")
                lines.append(f"▫️ 눌림 <b>${sig['pullback_price']:.2f}</b> ({sig['drop_pct']:+.1f}%) 도달 시 매수" + (f" · {gate}" if gate else ""))
                lines.append(f"▫️ 기준 ${anchor:.2f}({esc(o.ANCHOR_KO.get(kind, kind))}) 대비 {sig['chg_pct']:+.2f}%" + (f" · 상한 ${cap:.2f}" if cap > 0 else "") + (f" · 원작 기준가 ${sig['ref_anchor']:.2f}(직전 매도가·가장 낮은 F 평단 중 낮은 값)" if sig.get("ref_anchor") else ""))
            else:
                lines.append("▫️ 눌림 기준가가 아직 없어요 (첫 매수 체결 뒤에 생겨요)")
            inc = next((f for f in fl if not _TW.is_complete(f)), None)
            nxt = (f"{_SN.sniper_numbers(st).get(int(inc['id']), inc['id'])}F 남은 몫 ${max(0.0, float(inc.get('target') or fu) - float(inc.get('cost') or 0)):,.0f}" if inc is not None
                   else f"새 시드 ${fu:,.0f}")
            lines.append(f"▫️ 신호: {esc(_SN.SIGNAL_KO.get(sig['signal_type'], sig['signal_type']))} · 다음 매수 {esc(nxt)} · 60초마다 확인")
        lines.append(div)
        if not d["api_bad"]:
            lq = d.get("live_qty")
            lines.append(f"💵 달러 예수금 <b>${d['cash']:,.0f}</b> · 메리츠 잔고 {d['hold']}주 (장부·오늘 체결 반영 {lq if lq is not None else '시작 전'}주)" + (" · ⚠️잔고≠장부" if lq is not None and d["hold"] != lq else ""))
        lines.append(f"⚙️ F 완성 기준 금액 ${fu:,.0f} · 하루 매수 {_TW.buy_layers(s)}F · 당일 확인 {esc(self.intraday_text(s))}")
        if live_note:
            lines.append("ℹ️ " + esc(live_note))
        lines.append(f"🕒 {o.now_et().strftime('%m-%d %H:%M:%S ET')}")
        return "\n".join(lines)

    def sync_text(self, s):
        """잔고 동기화 (텔레그램 HTML) — 메리츠 잔고를 읽어 장부와 비교. 같을 때만, 오늘 체결 반영 전 주문이 없을 때만 F 합계를 장부에 맞춤(16:10 동기화와 같은 TW.reconcile) → F 상태를 같은 메시지에 보여줌.
        다르면 아무것도 안 바꾸고 알림 (장부=잔고 정지 규칙·주문·설정 그대로)"""
        esc = _html.escape
        o = self.o
        d = self.board(s)
        lines = ["🔄 <b>[잔고 동기화]</b>", "──────────────"]
        note = ""
        if d["api_bad"]:
            lines.append("메리츠 조회 미확인: " + esc("; ".join(d["api_bad"][:3])))
        else:
            pos = d["pos"]
            lq = int(pos["qty"]) if pos else None
            if lq is None:
                note = "장부 시작 전이라 동기화할 것이 없어요 (채팅에 '장부 시작'이라고 보내면 돼요)"
            elif d["hold"] != lq:
                note = f"⚠️ 메리츠 잔고 {d['hold']}주 ≠ 장부 {lq}주 — F는 안 바꿨어요. 원인을 확인해 주세요 (직접 산 주식은 채팅에 '주식 넣기'라고 보내면 돼요)"
            else:
                with o.in_dir(s["state_dir"]):
                    cfg = o.ConfigManager(s)
                    pend = [mp for mp in o.pending_syncs(s["state_dir"]) if (lambda m: isinstance(m, dict) and (m.get("orders") or m.get("attempts")) and not m.get("synced", True))(cfg._load_json(mp, {}))]
                    tst, had = o.tower_state_for(cfg, lq, float(pos["principal"]), s)
                    fq = sum(int(f.get("qty") or 0) for f in tst.get("floors") or [])
                    if not had:
                        note = "F 상태 파일이 없어요 — 다음 주문일 시작 때 현재 보유분으로 만들어요"
                    elif fq == lq:
                        note = f"잔고 {d['hold']}주 = 장부 {lq}주 = F 합계 {fq}주 · 맞아요 (바꾼 것 없음)"
                    elif pend:
                        note = f"F 합계 {fq}주 ≠ 장부 {lq}주지만 체결 반영 전 주문 기록이 있어 안 바꿨어요 (20:00 ET 동기화가 맞춰요)"
                    else:
                        tst2, tn = _TW.reconcile(tst, lq, float(pos["principal"]), _TW.params(s)[2], s)
                        cfg._save_json(o.TOWER_FILE, tst2)
                        note = f"F 합계 {fq}주 → 장부 {lq}주에 맞췄어요" + (" · " + "; ".join(tn[:2]) if tn else "")
                        d["tst"] = tst2
            lines.append(esc(note))
            lines.append("──────────────")
            px = float(d["price"]) if d.get("price") else 0.0
            fl = _SN.active_floors(d["tst"])
            tq, tc = _TW.totals(d["tst"])
            lines.append(f"🏛️ <b>[보유 F : {len(fl)}F · 총 {tq}주]</b> (원가 ${tc:,.0f})")
            rows, _fill = self.floor_lines(s, d["tst"], px)
            lines += rows or ["⚪ 보유 F 없음"]
        lines.append("──────────────")
        lines.append(f"🕒 {o.now_et().strftime('%m-%d %H:%M:%S ET')}")
        return "\n".join(lines)

    def ledger_text(self, s):
        o = self.o
        pos, halt, avg, _ = self._local(s)
        lines = ["[거래 내역 — 조회만]"]
        lines.append(f"· 장부: {pos['qty']}주 · 원금 ${float(pos['principal']):,.0f} · 평단 ${avg:.2f}" if pos else "· 장부: 시작 전")
        lines.append(f"· 정지 표시: {halt.get('reason') if halt else '없음'}")
        with o.in_dir(s["state_dir"]):
            cfg = o.ConfigManager(s)
            hist = cfg._load_json("data/add_shares_log.json", None)
            d = o.now_et().strftime("%Y-%m-%d")
            marks = [(n, cfg._load_json(f"data/{n}_{d}.json", None)) for n in ("orders", "dry_orders")]
        if isinstance(hist, list) and hist:
            h = hist[-1]
            lines.append(f"· 직접 산 주식 반영 기록: {len(hist)}건 · 최근 {str(h.get('at', ''))[:16]} {h.get('qty')}주 @ ${float(h.get('avg') or 0):.2f}"
                         f" ({(h.get('before') or {}).get('qty')}→{(h.get('after') or {}).get('qty')}주)")
        else:
            lines.append("· 직접 산 주식 반영 기록: 없음")
        shown = [(n, m) for n, m in marks if m is not None]
        if not shown:
            lines.append("· 오늘 주문 기록: 없음")
        for n, m in shown:
            label = "주문" if n == "orders" else "모의 주문"
            if m.get("skipped"):
                lines.append(f"· 오늘 {label}: 안 냄 — {str(m.get('skipped'))[:160]}")
                continue
            lines.append(f"· 오늘 {label}: {len(m.get('orders') or [])}건 · 오류 {len(m.get('errors') or [])}건 · 체결 반영 {'됨' if m.get('synced') else '전'}")
            lines += ["   " + x for x in self.o.fmt_orders(m.get("orders") or []).split("\n")]
            if m.get("sell_deferred"):
                lines.append("   오늘 산 주식이 체결되면 평단이 바뀌어서, 매도는 장중에 확인해서 내요")
            if m.get("sell_attempt"):
                lines.append("   당일 매도: " + str(m["sell_attempt"].get("status")))
        return "\n".join(lines)

    def funds_text(self, s):
        d = self.board(s)
        fu, _n, _g = _TW.params(s)
        lines = ["[자금 현황 — 조회만]", f"· 전략: {self.strategy_text(s)} · F 완성 기준 금액 ${fu:,.0f} (총 시드·F 수 한도 없음)"]
        if d["api_bad"]:
            return "\n".join(lines + ["· 메리츠 조회: 미확인 (" + "; ".join(d["api_bad"][:3]) + ")"])
        lq = d.get("live_qty")
        fxp = self.o.hybrid_fx_plan(s, d["cash"], 1)
        plan = d["plan"]
        if plan is not None:
            i = plan["info"]
            need = f"· 지금 신호가 나면 스나이퍼 매수 필요 ${i['need_usd']:,.0f}" + (f" · 부족 ${math.ceil(i['need_usd'] - i['usd_cash']):,}" if i["need_usd"] > i["usd_cash"] + 1e-9 else " · 부족 없음") if i.get("need_usd") else "· 지금은 매수 주문 계획 없음"
        else:
            need = f"· 오늘 계획: 미확인 ({d['plan_err']})"
        lines += [f"· 달러 예수금 ${d['cash']:,.0f}", need,
                  f"· 아침 환전 기준 {fxp['fx_basis']} · " + (f"부족 ${math.ceil(fxp['info']['shortfall_usd']):,}" if fxp["info"]["shortfall_usd"] else "부족 없음")
                  + f" · 자동환전 {'켜짐' if s.get('auto_fx_enabled') else '꺼짐'}",
                  f"· 보유 주수: 메리츠 {d['hold']}주 · 장부(오늘 체결 반영) {lq if lq is not None else '시작 전'}" + (" · 잔고 ≠ 장부" if lq is not None and d["hold"] != lq else "")]
        return "\n".join(lines)

    def power_text(self, s):
        idb, fp = self.o.check_identity(s)
        exp = str(s.get("expected_key_fp") or "").strip()
        _, halt, _, _ = self._local(s)
        fp_txt = ("없음" if not fp else "있음 · " + ("기대값과 일치" if exp and fp == exp else ("기대값 없음" if not exp else "기대값과 다름")))
        return "\n".join(["[봇 상태 — 표시만]",
                          f"· 봇 {'켜짐' if s.get('enabled') else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'}",
                          f"· 입고 확인 {'됨' if s.get('transfer_confirmed') else '전'} · 토스 스나이퍼 정지 확인 {'됨' if s.get('toss_sniper_stopped_confirmed') else '전'}",
                          f"· 키 지문: {fp_txt}",
                          f"· 정지 표시: {halt.get('reason') if halt else '없음'}",
                          "· 봇 켜기/끄기: 버튼은 없어요. 채팅에 '봇 끄기'라고 보내면 꺼져요 · 매매 정지: 채팅에 '매매 정지'라고 보내면 켜져요. 모의/실거래 전환은 메뉴에서 안 바꿔요 (서버 설정·기존 안전 절차 그대로)."])


    # ---------------------------------------------------------- v2.3.0 화면 (인라인 버튼 패널)
    def _set_rows(self, labels, s):
        def lab(label):
            k = SET_ITEMS[label]["key"]
            return (f"{KEY_ITEM[k]['name']}  {fmt_val(KEY_ITEM[k], cur_val(s, k))}  ▶ 변경", label)
        return [[lab(x)] for x in labels]

    def _assn_ko(self, s):
        """암살자 지금 모드 글자 (읽기 실패 = 모의)"""
        try:
            return self.o.BB.MODE_KO.get(self.o.BB.assassin_mode(s.get("state_dir") or ""), "모의")
        except Exception:
            return "모의"

    def radar_inline(self, s):
        """레이더 화면 = 원작 전술 제어반 (v2.12.0 판 39): [스나이퍼 켜기/끄기] [매수 비율 모드] [암살자]. 뒤로 없음 (레이더가 최상위)"""
        pm = _TW.portion_mode(s)
        return [[("🔴 스나이퍼 끄기 (지금 켜짐)", BOT_OFF) if s.get("enabled") else ("🟢 스나이퍼 켜기 (지금 꺼짐)", BOT_ON)],
                [(f"🔄 매수 비율 모드: {PM_KO[pm]} → {PM_KO[PM_NEXT[pm]]}", T_PMODE)],
                [(f"🗡 암살자: {self._assn_ko(s)} (승격/복귀)", T_ASSN)]]

    def sync_inline(self, s):
        """잔고 동기화 화면 (v2.12.0 판 39 할 일 3): 시드 설정 2개 — F 완성 기준 금액 · 버킷 시드"""
        return self._set_rows(SYNC_SET, s)

    def tower_inline(self, s):
        """탑쌓기 매매 화면 — 판 35 수정 12차: 시작·바벨 먼저, 설정은 비슷한 것끼리 2개씩 (봇 전원·도구 뺌)"""
        rows = [[("🏗 탑쌓기 매매 시작 (지금: 하이브리드 스나이퍼)", T_MODE_TOWER) if _TW.trade_mode(s) != "tower" else ("🔫 스나이퍼 매매로 돌아가기 (지금: 탑쌓기 매매)", T_MODE_SNIPER)]]
        cell = {r[0][1]: r[0] for r in self._set_rows(TOWER_SET, s)}      # _set_rows는 1개씩이라 여기서만 2개씩 묶음
        for a, b in (("탑쌓기 매도% 변경", "매도 비중 변경"),
                     ("하루 매수 F 수 변경", "하루 매도 F 수 변경")):
            rows.append([cell[a], cell[b]])
        rows.append([cell["매수 간격 변경"]])
        return rows


    def fx_inline(self, s):
        return [[("🔴 자동환전 끄기 (지금 켜짐)", FX_OFF) if s.get("auto_fx_enabled") else ("🟢 자동환전 켜기 (지금 꺼짐)", FX_ON)],
                [(f"환전 하루 상한  {fmt_val(KEY_ITEM['auto_fx_max_usd_per_day'], s.get('auto_fx_max_usd_per_day'), '입력 전')}  ▶ 변경", "환전 하루 상한 변경")],
                [(f"환전 여유%  {fmt_val(KEY_ITEM['auto_fx_buffer_pct'], s.get('auto_fx_buffer_pct'), '입력 전')}  ▶ 변경", "환전 여유% 변경")],
                [R_REFRESH]]

    def inline_for(self, s):
        """지금 화면(nav)의 인라인 버튼줄. 첫 화면(main)이면 None → 맨밑 4개 키보드"""
        return {"radar": self.radar_inline(s), "tower": self.tower_inline(s), "sync": self.sync_inline(s), "fx": self.fx_inline(s), "tools": TOOLS_INLINE}.get(self.nav)

    def tower_text(self, s):
        esc = _html.escape
        v = lambda k: esc(fmt_val(KEY_ITEM[k], cur_val(s, k)))
        on = bool(s.get("enabled"))
        return "\n".join(["🏛️ <b>[탑쌓기 매매]</b>", "──────────────",
                          f"1️⃣ 봇 전원: <b>{'🟢 켜짐' if on else '🔴 꺼짐'}</b> ({'모의' if s.get('dry_run', True) else '실거래'}) · 매매 모드 <b>{MODE_KO[_TW.trade_mode(s)]}</b>",
                          f"2️⃣ 매수 비율 모드: <b>{PM_KO[_TW.portion_mode(s)]}</b> · 시드 설정은 [잔고 동기화] 화면",
                          f"3️⃣ 탑쌓기 매도(완성 F): 평단 <b>+{v('sell_profit_pct')}</b> → 보유의 <b>{v('sell_fraction_pct')}</b>",
                          f"4️⃣ 하루 매수 <b>{v('tower_max_buy_layers_per_day')}</b>F · 하루 매도 <b>{v('tower_max_sell_layers_per_day')}</b>F",
                          "──────────────", "💡 버튼을 누르면 새 값을 입력해요 (현재값 → 바꿀 값 확인 뒤 바뀌고, 주문은 안 나가요)"])

    def seed_lines(self, s):
        """잔고 동기화 화면 아래에 붙는 시드 설정 표시 (v2.12.0 판 39 할 일 3)"""
        esc = _html.escape
        v = lambda k: esc(fmt_val(KEY_ITEM[k], cur_val(s, k)))
        return ["──────────────", "🌱 <b>[시드 설정]</b>",
                f"· F 완성 기준 금액: <b>{v('tower_floor_usd')}</b>",
                f"· 버킷 시드: <b>{v('tower_box_seed_usd')}</b> (모드 {PM_KO[_TW.portion_mode(s)]} → 매수 1번 ${_TW.portion_usd(s):,.0f})",
                "💡 버튼을 누르면 새 값을 입력해요 (현재값 → 바꿀 값 확인 뒤 바뀌고, 주문은 안 나가요)"]

    def fx_text(self, s):
        """환전 화면: 오늘 환전한 금액 · 남은 한도 · 자동환전 설정 (환전 기록 파일 fx_<날짜>.json 읽기만)"""
        esc = _html.escape
        o = self.o
        k = lambda key: esc(fmt_val(KEY_ITEM[key], s.get(key), "입력 전"))
        on = bool(s.get("auto_fx_enabled"))
        day = o.now_kst().strftime("%Y-%m-%d") if hasattr(o, "now_kst") else o.now_et().strftime("%Y-%m-%d")
        done, rec = 0.0, None
        try:
            with o.in_dir(s["state_dir"]):
                cfg = o.ConfigManager(s)
                for dd in {day, o.now_et().strftime("%Y-%m-%d")}:
                    r = cfg._load_json(f"data/{'' if not s.get('dry_run', True) else 'dry_'}fx_{dd}.json", None)
                    if isinstance(r, dict) and r.get("usd") and "신청 완료" in str(r.get("result") or ""):
                        done, rec = max(done, float(r["usd"])), r
        except Exception:
            pass
        cap = _num(s.get("auto_fx_max_usd_per_day"))
        left = (f"${max(0.0, cap - done):,.0f}" if cap else "미확인 (하루 상한 입력 전)")
        lines = ["💱 <b>[환전]</b>", "──────────────",
                 f"▫️ 오늘 환전한 금액: <b>${done:,.0f}</b>" + ("" if rec else " (기록 없음)"),
                 f"▫️ 오늘 남은 한도: <b>{left}</b> (하루 상한 {k('auto_fx_max_usd_per_day')})",
                 f"▫️ 자동환전: <b>{'🟢 켜짐' if on else '🔴 꺼짐'}</b> · 여유 {k('auto_fx_buffer_pct')}",
                 "──────────────"]
        try:
            api_bad = self._api_ok(s)
            if not api_bad:
                cash = self._api(s).usd_cash()
                fxp = o.hybrid_fx_plan(s, cash, 1)
                lines.append(f"▫️ 아침 환전 기준: {esc(fxp['fx_basis'])} · 예수금 ${cash:,.0f} · " + (f"부족 ${math.ceil(fxp['info']['shortfall_usd']):,}" if fxp['info']['shortfall_usd'] else "부족 없음"))
                if cap and fxp["info"]["shortfall_usd"] * (1 + float(s.get("auto_fx_buffer_pct") or 0) / 100.0) > cap:
                    lines.append("⚠️ 필요 환전액이 하루 상한을 넘어요 — 상한만큼만 아침에 환전돼요")
            else:
                lines.append("▫️ 예수금 조회 미확인: " + esc("; ".join(api_bad[:2])))
        except Exception as e:
            lines.append(f"▫️ 예수금 조회 실패 ({type(e).__name__})")
        lines.append("▫️ 켜면 실거래에서 한국시간 09:00부터 주문 시간 전까지(실시간 환전 시간 안) 아침에 F 완성 기준 금액 × 하루 매수 F 수를 미리 환전하고, 장중 매수 신호 때 달러가 모자라면 부족분만 환전해요")
        if not fx_values_ready(s):
            lines.append("▫️ 켜기 전에 하루 상한·여유%를 먼저 입력해 주세요")
        if s.get("dry_run", True):
            lines.append("▫️ 지금은 모의 모드라 환전 신청은 안 나가요")
        return "\n".join(lines)

    def power_bot_text(self, s):
        on = bool(s.get("enabled"))
        return (f"[봇 켜기/끄기]\n· 지금: {'켜짐' if on else '꺼짐'} · {'모의' if s.get('dry_run', True) else '실거래'}\n"
                "· 끄면 바로 적용, 켜면 확인 버튼이 한 번 더 나와요. 모의/실거래 전환은 여기서 안 바꿔요.")

    def show(self, name, s, say, text=None):
        """화면 보이기. name: main(첫 화면) | radar | tower | fx | tools"""
        self.nav, self.in_prompt = name, False
        if name == "main":
            return say(text or "아래 버튼을 눌러 주세요", None)
        if name == "tower":
            return self.send(self._c, text or self.tower_text(s), None, s.get("dry_run", True), html=True, inline=self.inline_for(s))
        if name == "fx":
            return self.send(self._c, text or self.fx_text(s), None, s.get("dry_run", True), html=True, inline=self.inline_for(s))
        if name == "tools":
            return say(text or "도구 · 가끔 쓰는 기능이에요", TOOLS_INLINE)
        return say(text or "스나이퍼 레이더", self.radar_inline(s))

    # ---------------------------------------------------------- 설정 변경 (설정 파일 값만 바꿈)
    def _desc(self, changes, res):
        out = []
        for k, (old, new) in res.items():
            if k == "trade_mode":
                out.append(f"매매 모드: {MODE_KO[_TW.trade_mode({k: old})]} → {MODE_KO[_TW.trade_mode({k: new})]}")
            elif k in BOOL_NAME:
                out.append(f"{BOOL_NAME[k]}: {'켜짐' if old else '꺼짐'} → {'켜짐' if new else '꺼짐'}")
            else:
                out.append(f"{KEY_ITEM[k]['name']}: {fmt_val(KEY_ITEM[k], cur_val({k: old}, k))} → {fmt_val(KEY_ITEM[k], new)}")
        return "\n".join("· " + x for x in out)

    def propose(self, s, say, changes, extra=""):
        """검사만 하고(쓰지 않음) 이전 → 새 값을 보여 준 뒤 [변경 확인] 을 기다림"""
        try:
            res = update_settings(changes, dry=True)
        except ValueError as e:
            self.in_prompt = False
            return say(f"바꿀 수 없어요: {e}")
        except OSError as e:
            self.in_prompt = False
            return say("설정 파일을 읽지 못했어요. 서버 파일 권한을 확인해 주세요.")
        self.pending = {"changes": changes}
        self.confirm[CHG_OK] = time.time() + CONFIRM_SEC
        self.in_prompt = True
        return say(self._desc(changes, res) + (("\n" + extra) if extra else "")
                   + f"\n{CONFIRM_SEC}초 안에 [{CHG_OK}] 를 눌러 주세요. 주문은 안 나가고 값만 바뀌어요.", [[CHG_OK, BACK]])

    def apply(self, s, say, changes):
        try:
            res = update_settings(changes)
        except ValueError as e:
            return say(f"바꾸지 못했어요: {e}")
        except OSError as e:
            return say("설정 파일을 쓰지 못했어요 — 바뀐 것 없음. 서버 파일 쓰기 권한을 확인해 주세요.")
        try:
            self._s = self.o.load_settings()
        except Exception:
            pass
        self.in_prompt = False
        hint = ""
        if any(k in ("auto_fx_buffer_pct", "auto_fx_max_usd_per_day") for k in changes) and not (self._s or {}).get("auto_fx_enabled"):
            hint = ("\n· 이제 환전 화면에서 [자동환전 켜기]를 눌러 주세요." if fx_values_ready(self._s)
                    else "\n· 아직 " + ("하루 상한" if _num(self._s.get("auto_fx_buffer_pct")) is not None else "여유%") + "을 입력하지 않았어요.")
        return say("변경됨 (다음 주문 시간부터 적용)\n" + self._desc(changes, res) + hint)

    # ---------------------------------------------------------- 글자 처리
    def _ok_confirm(self, label):
        until = self.confirm.pop(label, 0)
        return time.time() <= until

    def handle(self, s, c, text):
        if not text:
            return
        text = _EMOJI_RE.sub("", text or "").strip()   # 버튼 앞 이모티콘(맨밑 키보드)·예전 키보드 글자를 떼고 같은 버튼으로 읽음
        if not text:
            return
        self._s, self._c = s, c
        dry = s.get("dry_run", True)
        say = lambda t, rows=None: self.send(c, t, None, dry, inline=(rows if rows is not None else self.inline_for(self._s)))
        if self.wait and text not in ALL_LABELS:
            w, self.wait = self.wait, None
            self.in_prompt = False
            if time.time() - w["ts"] > WAIT_SEC:
                return say("입력 시간이 지났어요. 버튼을 다시 눌러 주세요.")
            if w["kind"] == "set":
                item = SET_ITEMS[w["label"]]
                v, err = parse_value(item, text)
                if err:
                    self.wait, self.in_prompt = {**w, "ts": time.time()}, True
                    return say(f"{err}", [[BACK]])
                return self.propose(s, say, {item["key"]: v})
            parts = text.replace(",", " ").split()
            qty = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else None
            try:
                avg = float(parts[1]) if len(parts) >= 2 else None
            except ValueError:
                avg = None
            if qty is None or qty < 1 or avg is None or not (avg > 0) or avg == float("inf"):
                self.wait, self.in_prompt = {"kind": "add", "ts": time.time()}, True
                return say("수량은 1 이상 정수, 평단은 0보다 큰 달러 숫자로 띄어 써 주세요. 예: 3 52.10", [[BACK]])
            self.add_args = (qty, avg)
            self.confirm[ADD_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            return say(f"장부에 넣을까요?\n지금 값 → 새 값\n· 장부 추가: 없음 → {qty}주 · 평단 ${avg:g}" +
                       f"\n{CONFIRM_SEC}초 안에 [{ADD_OK}] 를 눌러 주세요. 주문은 안 나가요 (장부만 바뀌고, 메리츠 잔고가 장부 + 수량과 같을 때만 반영돼요).", [[ADD_OK, BACK]])
        if text not in ALL_LABELS:                      # 모르는 글자·/start·예전 버튼(모드·자금·전술·현상태·기타 등) → 새 첫 화면
            self.nav = "main"
            return self.show("main", s, say, "메뉴가 바뀌었어요 (하이브리드). 아래 버튼으로 써 주세요.")
        active, self.in_prompt, self.wait = self.in_prompt, False, None
        if text not in (CHG_OK, MODE_OK, PM_OK, ASSN_OK):
            self.pending = None
        if text == BACK:
            return self.show(self.nav if active else PARENT.get(self.nav, self.nav), s, say)
        # ---- 첫 화면 4개
        if text == B_RADAR:
            self.nav = "radar"
            return self.send(c, self.board_text(s), None, dry, html=True, inline=self.radar_inline(s))
        if text == B_SYNC:
            self.nav = "sync"      # v2.12.0 판 39 할 일 3: 시드 설정 2개(F 완성 기준 금액·버킷 시드)를 이 화면 버튼으로 바꿈 — 바꾼 뒤에도 이 화면에 머무름
            return self.send(c, self.sync_text(s) + "\n" + "\n".join(self.seed_lines(s)), None, dry, html=True, inline=self.sync_inline(s))
        if text == B_TOWER:
            return self.show("tower", s, say)
        if text == B_FX:
            return self.show("fx", s, say)
        if text == R_REFRESH:
            if self.nav == "fx":
                return self.show("fx", s, say)
            if self.nav == "tower":
                return self.show(self.nav, s, say)
            self.nav = "radar"
            return self.send(c, self.board_text(s), None, dry, html=True, inline=self.radar_inline(s))
        if text == T_TOOLS:
            return self.show("tools", s, say)
        # ---- 레이더 안 (조회만)
        if text in (I_FUNDS, I_PLAN, I_LEDGER, I_POWER):
            self.nav = "radar"
            return say({I_FUNDS: self.funds_text, I_LEDGER: self.ledger_text, I_POWER: self.power_text}.get(text, lambda x: "\n".join(self.plan_lines(x, self.board(x))))(s), self.radar_inline(s))
        # ---- 환전 (설정 값만 바꿈)
        if text in (FX_ON, FX_OFF):
            self.nav = "fx"
        if text == FX_ON:
            if not fx_values_ready(s):
                return say(FX_NEED)
            return self.propose(s, say, {"auto_fx_enabled": True},
                                "켜면 실거래 모드에서만, 한국시간 09:00부터 주문 시간 전까지(실시간 환전 시간 안에서만) 아침에 F 완성 기준 금액 × 하루 매수 F 수를 미리 환전하고 (하루 상한 안에서), 장중 매수 신호 때 달러가 모자라면 부족분을 환전해요. 실제 환전은 아직 시험 전이라 처음엔 적은 상한으로 켜 보세요.")
        if text == FX_OFF:
            return self.apply(s, say, {"auto_fx_enabled": False})
        # ---- 탑쌓기 매매 화면 (봇 전원·매매 모드·바벨)
        if text == BOT_OFF:
            self.nav = "radar" if self.nav == "radar" else "tower"      # 판 39: 레이더 제어반에서 눌렀으면 레이더에 머무름
            return self.apply(s, say, {"enabled": False})
        if text == BOT_ON:
            self.nav = "radar" if self.nav == "radar" else "tower"
            bad = self.o.validate_settings(s)
            return self.propose(s, say, {"enabled": True},
                                f"켜면 다음 주문 시간부터 동작해요. 지금 {'모의' if dry else '실거래'}예요. 입고 확인·토스 정지 확인·키 지문 등 기존 안전 조건은 그대로 먼저 통과해야 해요."
                                + (f"\n설정 문제 {len(bad)}건 (켜도 주문은 막혀요): " + "; ".join(bad[:3]) if bad else ""))
        if text in SET_ITEMS:
            it = SET_ITEMS[text]
            self.nav = "fx" if it["key"].startswith("auto_fx") else ("sync" if text in SYNC_SET else "tower")      # v2.12.0 판 39: 시드 설정은 잔고 동기화 화면에 머무름 (snset 화면 삭제)
            self.wait, self.in_prompt = {"kind": "set", "label": text, "ts": time.time()}, True
            return say(f"{text}\n· 지금: {fmt_val(it, cur_val(s, it['key']))}\n· 넣을 수 있는 값: {self.range_text(it)}\n"
                       f"· 무슨 뜻: {MEANS.get(it['key'], ('', ''))[0]}\n· 바꾸면: {MEANS.get(it['key'], ('', ''))[1]} (주문은 바로 나가지 않아요)\n"
                       f"· 새 값을 숫자로 보내 주세요. {it['ex']}", [[BACK]])
        if text in (T_MODE_TOWER, T_MODE_SNIPER):      # 판 33: 모드 바꾸기 — 바로 안 바꾸고 확인 메시지부터 (스나이퍼로 돌아갈 때도 똑같이)
            self.nav = "tower"
            to = "tower" if text == T_MODE_TOWER else "sniper"
            cur = _TW.trade_mode(s)
            if cur == to:
                return say(f"이미 {MODE_KO[to]} 모드예요. 바꿀 것이 없어요.")
            try:
                update_settings({"trade_mode": to}, dry=True)
            except (ValueError, OSError) as e:
                return say(f"바꿀 수 없어요: {e}")
            self.pending = {"changes": {"trade_mode": to}, "mode": True}
            self.confirm[MODE_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            return say(f"매매 모드를 바꿀까요?\n· 지금 모드: {MODE_KO[cur]}\n· 바꿀 모드: {MODE_KO[to]}\n"
                       f"· 시드(F 완성 기준 금액): ${_TW.params(s)[0]:,.0f}\n· 매수 간격: ${cur_val(s, 'tower_buy_gap_usd')} (시초가 가까운 칸부터 $1씩 아래로 {cur_val(s, 'tower_buy_gap_usd')}칸)\n"
                       f"{MODE_KO[to]}로 바꿀까요? {CONFIRM_SEC}초 안에 [{MODE_OK}] 를 눌러 주세요. 이미 낸 주문은 안 건드리고 다음 판단부터 적용돼요.", [[MODE_OK, BACK]])
        if text == T_PMODE:      # v2.12.0 판 39: 매수 비율 모드 2순환 (복리↔단리) — 바로 안 바꾸고 확인부터
            self.nav = "radar"
            cur = _TW.portion_mode(s)
            to = PM_NEXT[cur]
            try:
                update_settings(PM_CHANGES[to], dry=True)
            except (ValueError, OSError) as e:
                return say(f"바꿀 수 없어요: {e}")
            self.pending = {"changes": PM_CHANGES[to], "mode": "pm"}
            self.confirm[PM_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            s2 = dict(s, **PM_CHANGES[to])
            return say(f"매수 비율 모드를 바꿀까요?\n· 지금: {PM_KO[cur]} → 바꿀 모드: {PM_KO[to]}\n"
                       f"· 바꾼 뒤 F 완성 기준 금액 ${_TW.params(s2)[0]:,.0f} · 매수 1번 ${_TW.portion_usd(s2):,.0f}\n"
                       f"· {CONFIRM_SEC}초 안에 [{PM_OK}] 를 눌러 주세요. 이미 낸 주문은 안 건드려요.", [[PM_OK, BACK]])
        if text == T_ASSN:      # v2.13.0 판 40 할 일 2: 암살자 승격·복귀 — 계획을 먼저 보여 주고 확인 뒤에만 저장. 주문은 안 나감
            self.nav = "radar"
            try:
                cur = self.o.BB.assassin_mode(s.get("state_dir") or "")
                want = cur == self.o.BB.MODE_SIM
                plan, _c = self.o.assassin_promote(s, self._api(s), want, apply=False)
            except Exception as e:
                return say(f"암살자 상태를 확인하지 못했어요 ({type(e).__name__}). 바뀐 건 없어요.")
            if plan["to"] is None:
                return say(f"암살자: {self.o.BB.MODE_KO.get(cur, cur)}\n· {plan['msg']}")
            self.pending = {"changes": {}, "mode": "assn", "want": want}
            self.confirm[ASSN_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            return say(f"암살자 모드를 바꿀까요?\n· 지금: {self.o.BB.MODE_KO.get(cur, cur)} → 바꾼 뒤: {self.o.BB.MODE_KO.get(plan['to'], plan['to'])}\n· {plan['msg']}\n"
                       f"· {CONFIRM_SEC}초 안에 [{ASSN_OK}] 를 눌러 주세요. 바꾸는 것 자체로는 주문이 안 나가요 (실전이 되면 이후 암살자가 직접 주문을 내요).", [[ASSN_OK, BACK]])
        if text == ASSN_OK:
            p, self.pending = self.pending, None
            if not p or p.get("mode") != "assn" or not self._ok_confirm(ASSN_OK):
                return say("확인 시간이 지났거나 바꿀 것이 없어요. 암살자 버튼을 다시 눌러 주세요.")
            self.nav = "radar"
            try:
                plan, cur = self.o.assassin_promote(s, self._api(s), p["want"], apply=True)
            except Exception as e:
                return say(f"저장하지 못했어요 ({type(e).__name__}). 바뀐 건 없어요.")
            return say(f"암살자: {self.o.BB.MODE_KO.get(cur, cur)} → {self.o.BB.MODE_KO.get(plan['to'] or cur, '')}\n· {plan['msg']}")
        if text == PM_OK:
            p, self.pending = self.pending, None
            if not p or p.get("mode") != "pm" or not self._ok_confirm(PM_OK):
                return say("확인 시간이 지났거나 바꿀 것이 없어요. 모드 버튼을 다시 눌러 주세요.")
            self.nav = "radar"
            return self.apply(s, say, p["changes"])
        if text == MODE_OK:
            p, self.pending = self.pending, None
            if not p or p.get("mode") is not True or not self._ok_confirm(MODE_OK):
                return say("확인 시간이 지났거나 바꿀 모드가 없어요. 모드 버튼을 다시 눌러 주세요.")
            return self.apply(s, say, p["changes"])
        if text == ADD_OK:
            a, self.add_args = getattr(self, "add_args", None), None
            if not a or not self._ok_confirm(ADD_OK):
                return say("확인 시간이 지났거나 넣을 주식이 없어요. 주식 넣기를 다시 눌러 주세요.")
            rc, out = self._out(self.o.cmd_add_shares, s, a[0], a[1])
            return say(("완료 · " if rc == 0 else "") + (out or "결과 없음"))
        if text == CHG_OK:
            p, self.pending = self.pending, None
            if not p or not self._ok_confirm(CHG_OK):
                return say("확인 시간이 지났거나 바꿀 값이 없어요. 다시 눌러 주세요.")
            return self.apply(s, say, p["changes"])
        # ---- 도구 (탑쌓기 매매 화면 → 도구)
        self.nav = "tools"
        if text == T_CHECK:
            _, out = self._out(self.o.cmd_check, s)
            return say(out or "점검 결과 없음")
        if text == T_ADD:
            self.wait, self.in_prompt = {"kind": "add", "ts": time.time()}, True
            return say("직접 산 주식 수량과 평단(달러)을 띄어 써서 보내 주세요. 예: 3 52.10\n"
                       "• 메리츠 잔고가 (장부 + 수량)과 같을 때만 반영돼요 · 봇이 켜져 있거나 미국장 주문 시간(미 동부 "
                       f"{s.get('order_time_et')}~{s.get('order_deadline_et')})이면 거부 · 주문은 안 나가요", [[BACK]])
        if text == T_STOP:
            with self.o.in_dir(s["state_dir"]):
                cfg = self.o.ConfigManager(s)
                with GlobalThrottle.get_file_lock(cfg.FILES["HALT"]):
                    cur = cfg.get_halt()
                    if not cur:
                        cfg.halt("텔레그램 수동 정지 (매매 정지)")
            if cur:
                return say(f"이미 정지 표시가 있어요: {cur.get('reason')}")
            return say("매매 정지 표시를 켰어요.\n· 실거래 모드에서는 정지 표시가 있는 동안 새 주문이 안 나가요 (이미 낸 주문의 취소는 안 하고, 체결 반영은 그대로).\n"
                       "· 오늘 이미 주문 시간이 지나 '주문 안 함'으로 기록됐다면 정지를 풀어도 오늘은 다시 안 내요.\n· 풀려면 정지 해제.")
        if text == T_HALT:
            halt = self._local(s)[1]
            if not halt:
                return say("정지 표시가 없어요. 해제할 것이 없습니다.")
            self.confirm[HALT_OK], self.in_prompt = time.time() + CONFIRM_SEC, True
            return say(f"정지 표시: {halt.get('reason')}\n원인을 확인한 뒤에 쓰는 기능이에요.\n"
                       f"확인했으면 {CONFIRM_SEC}초 안에 [{HALT_OK}] 를 눌러 주세요.", [[HALT_OK, BACK]])
        if text == HALT_OK:
            if not self._ok_confirm(HALT_OK):
                return say("확인 시간이 지났어요. 정지 해제를 다시 눌러 주세요.")
            with self.o.in_dir(s["state_dir"]):
                cfg = self.o.ConfigManager(s)
                with GlobalThrottle.get_file_lock(cfg.FILES["HALT"]):
                    cfg.clear_halt()
            return say("정지 표시 해제")
        if text == T_INJECT:
            pos = self._local(s)[0]
            label = INJECT_OVER if pos else INJECT_OK
            self.confirm[label], self.in_prompt = time.time() + CONFIRM_SEC, True
            if pos:
                return say(f"이미 장부가 있어요 ({pos['qty']}주). 덮어쓰려면 한 번 더 확인이 필요해요.\n"
                           f"{CONFIRM_SEC}초 안에 [{INJECT_OVER}] 를 누르면 같은 검사(설정·키·입고 확인·잔고가 시작 수량과 같은지) 뒤 덮어써요.",
                           [[INJECT_OVER, BACK]])
            return say("장부 시작: 설정·키 점검 · 입고 확인 · 메리츠 잔고가 시작 수량과 같을 때만 시작해요.\n"
                       f"{CONFIRM_SEC}초 안에 [{INJECT_OK}] 를 눌러 주세요.", [[INJECT_OK, BACK]])
        if text in (INJECT_OK, INJECT_OVER):
            if not self._ok_confirm(text):
                return say("확인 시간이 지났어요. 장부 시작을 다시 눌러 주세요.")
            rc, out = self._out(self.o.cmd_inject_start, s, text == INJECT_OVER)
            return say(out or ("완료" if rc == 0 else "실패"))
        if text == T_FP:
            try:
                fp = self.o.key_fingerprint(s["key_file"])
            except Exception as e:
                return say("키 지문: 읽지 못함 (키 파일을 확인해 주세요)")
            exp = str(s.get("expected_key_fp") or "").strip()
            return say(f"키 지문 (앞 12자리, 키 원문 아님): {fp}\n기대값: "
                       + ("일치" if exp and exp == fp else ("없음" if not exp else "다름")))
        return say("아래 버튼으로 써 주세요.")
