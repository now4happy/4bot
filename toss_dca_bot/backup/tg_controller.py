from addon import extra_buttons, check_market_holiday, addon_state
# =====================================================================
# FILE: tg_controller.py
# 목적: 텔레그램 제어반 UI 및 퍼센트(목표수익률 1~1000%, 매도비율 1~100%) 버튼 컨트롤러
# =====================================================================

import math
import html
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from dca_engine import DcaConfigManager, execute_stock_dca_step

router = Router()
api_client = None
ADMIN_CHAT_ID = None


def inject_dependencies(client, admin_id: int):
    global api_client, ADMIN_CHAT_ID
    api_client = client
    ADMIN_CHAT_ID = admin_id


class DcaInputState(StatesGroup):
    waiting_for_new_symbol = State()
    waiting_for_base_amount = State()
    waiting_for_target_profit = State()
    waiting_for_sell_ratio = State()
    waiting_for_exec_time = State()


def _is_admin(user) -> bool:
    return bool(user and getattr(user, "id", None) == ADMIN_CHAT_ID)


async def build_main_panel_message() -> tuple[str, InlineKeyboardMarkup]:
    cfg = await DcaConfigManager.load()
    is_master = cfg.get("is_master_active", True)
    kr_time = cfg.get("kr_exec_time", "10:00")
    us_time = cfg.get("us_exec_time", "10:00")
    stocks = cfg.get("stocks", {})
    active_sym = cfg.get("active_symbol", "")

    if active_sym not in stocks and stocks:
        active_sym = next(iter(stocks.keys()))
        cfg["active_symbol"] = active_sym
        await DcaConfigManager.save(cfg)

    master_str = "🟢 가동 중 (ON)" if is_master else "🔴 정지됨 (OFF)"

    lines = [
        "📊 <b>[토스 스마트 적립(1배/1/2배) & 분할익절 관제탑]</b>",
        f"▫️ 시장 상태: {"🛑 휴장일 시스템 대기" if check_market_holiday()[0] else "🟢 정상 개장일"}\n▫️ 시스템 전원: <b>{master_str}</b>",
        f"▫️ 자동 실행 시각: 🇰🇷 국내 <code>{kr_time} KST</code> | 🇺🇸 미국 <code>{us_time} EST(정규장)</code>",
        "➖➖➖➖➖➖➖➖➖➖➖➖➖➖",
    ]

    if not stocks:
        lines.append(
            "📭 <b>현재 등록된 종목이 없습니다.</b>\n"
            "아래 <b>[➕ 종목 추가 (한국/미국)]</b> 버튼을 눌러 모아갈 종목(예: <code>005930</code>, <code>AAPL</code>, <code>TSLA</code>, <code>SOXL</code>)을 등록해 주세요!"
        )
    else:
        st = stocks[active_sym]
        sym = st["symbol"]
        name = html.escape(st.get("name", sym))
        cur = st.get("currency", "USD")
        mc = st.get("market_country", "US")
        base_amt = float(st.get("base_amount", 20.0))
        half_amt = round(base_amt * 0.5, 2)
        target_pct = float(st.get("target_profit_pct", 10.0))
        sell_pct = float(st.get("sell_ratio_pct", 10.0))
        p_lock = bool(st.get("profit_lock", False))
        enabled = bool(st.get("enabled", True))

        amt_str = f"₩{base_amt:,.0f} (평단 상회 시 1/2: ₩{half_amt:,.0f})" if cur == "KRW" else f"${base_amt:,.2f} (평단 상회 시 1/2: ${half_amt:,.2f})"
        order_mode_str = "🇺🇸 소수점 금액/수량 시장가" if mc == "US" else "🇰🇷 1주 단위(정수) 시장가"
        lock_str = "🔒 <b>익절 도달 매수잠금 ON (신규매수 중단)</b>" if p_lock else "🔓 정상 적립 진행 중 (매수 허용)"
        en_str = "🟢 활성" if enabled else "⚪ 일시중지"

        hold_line = "▫️ 계좌 연동: <code>/sync</code> 또는 새로고침 시 실시간 조회"
        if api_client:
            try:
                hold = await api_client.get_symbol_holdings(sym)
                cur_p = float(hold.get("last_price") or 0.0)
                if cur_p <= 0:
                    cur_p = await api_client.get_current_price(sym)
                avg_p = float(hold.get("avg_price") or 0.0)
                qty = float(hold.get("qty") or 0.0)
                prof = float(hold.get("profit_pct") or 0.0)
                if cur == "KRW":
                    hold_line = f"▫️ 현재가: <code>₩{cur_p:,.0f}</code> | 평단가: <code>₩{avg_p:,.0f}</code> (<code>{prof:+.2f}%</code> / <code>{qty:g}주</code>)"
                else:
                    hold_line = f"▫️ 현재가: <code>${cur_p:,.2f}</code> | 평단가: <code>${avg_p:,.2f}</code> (<code>{prof:+.2f}%</code> / <code>{qty:.4f}주</code>)"
            except Exception:
                pass

        lines.extend([
            f"🎯 <b>현재 선택 종목: {name} (<code>{sym}</code>) [{en_str}]</b>",
            f"▫️ 주문 방식: <b>{order_mode_str}</b>",
            hold_line,
            f"▫️ 1회 기준 매수금: <b>{amt_str}</b>",
            f"▫️ 익절 목표 수익률: <b>+{target_pct:g}% 이상 도달 시</b> (최대 1000%)",
            f"▫️ 익절 시 매도 비율: <b>보유 수량의 {sell_pct:g}% 매도</b> (최대 100%)",
            f"▫️ 목표 도달 후 상태: {lock_str}",
            f"▫️ 최근 실행 기록: <code>{html.escape(st.get('last_action_summary', '대기 중'))}</code>",
        ])

        if len(stocks) > 1:
            other_syms = ", ".join([f"{k}({'ON' if v.get('enabled') else 'OFF'})" for k, v in stocks.items()])
            lines.append(f"▫️ 등록된 전체 종목: <code>{other_syms}</code>")

    kb_rows = [
        [
            InlineKeyboardButton(
                text=("🔴 전체 전원 끄기 (OFF)" if is_master else "🟢 전체 전원 켜기 (ON)"),
                callback_data="toggle_master",
            ),
            InlineKeyboardButton(text="➕ 종목 추가 (한국/미국)", callback_data="add_symbol"),
        ]
    ]

    if stocks and active_sym in stocks:
        st = stocks[active_sym]
        p_lock = bool(st.get("profit_lock", False))
        kb_rows.extend([
            [
                InlineKeyboardButton(text="💰 1회 기준 매수금액 설정", callback_data="menu_base_amount"),
                InlineKeyboardButton(text="⚡ 지금 즉시 1회 실행", callback_data="run_now"),
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 목표 수익률 조절 (+{st.get('target_profit_pct', 10):g}% · 최대 1000%)",
                    callback_data="menu_target_profit",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"📤 매도 비율 조절 ({st.get('sell_ratio_pct', 10):g}% · 최대 100%)",
                    callback_data="menu_sell_ratio",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=("🔓 매수잠금 해제 (다시 모으기)" if p_lock else "🔒 수동으로 매수잠금 켜기"),
                    callback_data="toggle_profit_lock",
                ),
                InlineKeyboardButton(
                    text=("⚪ 이 종목 일시중지" if st.get("enabled", True) else "🟢 이 종목 다시 켜기"),
                    callback_data="toggle_stock_enabled",
                ),
            ],
            [
                InlineKeyboardButton(text="⏰ 실행 시각 변경", callback_data="menu_exec_time"),
                InlineKeyboardButton(text="🔄 화면 새로고침", callback_data="refresh_panel"),
                InlineKeyboardButton(text="🗑️ 종목 삭제", callback_data="delete_symbol"),
            ],
        ])

        if len(stocks) > 1:
            switch_row = []
            for s_code in list(stocks.keys())[:4]:
                mark = "✅" if s_code == active_sym else "📌"
                switch_row.append(
                    InlineKeyboardButton(text=f"{mark} {s_code}", callback_data=f"select_sym:{s_code}")
                )
            kb_rows.append(switch_row)

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=kb_rows)


@router.message(Command("start", "panel", "settlement", "sync"))
async def cmd_main_panel(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user):
        return
    await state.clear()
    text, kb = await build_main_panel_message()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "refresh_panel")
async def cb_refresh_panel(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.clear()
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("🔄 최신 상태로 갱신되었습니다.")


@router.callback_query(F.data == "toggle_master")
async def cb_toggle_master(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    cfg = await DcaConfigManager.load()
    cfg["is_master_active"] = not cfg.get("is_master_active", True)
    await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("전원 상태가 변경되었습니다.")


@router.callback_query(F.data.startswith("select_sym:"))
async def cb_select_sym(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    sym = callback.data.split(":", 1)[1]
    cfg = await DcaConfigManager.load()
    if sym in cfg.get("stocks", {}):
        cfg["active_symbol"] = sym
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer(f"📌 {sym} 종목이 선택되었습니다.")


@router.callback_query(F.data == "add_symbol")
async def cb_add_symbol(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.set_state(DcaInputState.waiting_for_new_symbol)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 취소하고 돌아가기", callback_data="refresh_panel")]]
    )
    await callback.message.edit_text(
        "➕ <b>[새 종목 추가 — 한국주식 / 미국주식]</b>\n\n"
        "▫️ 모아갈 종목의 <b>종목코드(한국 6자리 숫자)</b> 또는 <b>미국 티커(영문)</b>를 입력해 주세요.\n"
        "▫️ 예시:\n"
        "  • 한국주식: <code>005930</code> (삼성전자), <code>000660</code> (SK하이닉스)\n"
        "  • 미국주식: <code>AAPL</code>, <code>TSLA</code>, <code>NVDA</code>, <code>QQQ</code>, <code>SOXL</code>",
        reply_markup=kb,
        parse_mode="HTML",
    )


@router.message(DcaInputState.waiting_for_new_symbol)
async def msg_add_symbol(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user):
        return
    raw_sym = (message.text or "").strip().upper()
    if not raw_sym:
        await message.answer("🚨 유효한 종목코드를 입력해 주세요.")
        return

    info = {}
    if api_client:
        try:
            info = await api_client.get_stock_info(raw_sym)
        except Exception as e:
            await message.answer(f"🚨 토스 API 종목 조회 실패: {html.escape(str(e))}")
            return

    if not info:
        await message.answer(
            f"🚨 <code>{html.escape(raw_sym)}</code> 종목을 토스증권에서 찾을 수 없습니다. "
            "한국주식은 6자리 숫자(예: 005930), 미국주식은 영문 티커(예: AAPL)로 입력해 주세요.",
            parse_mode="HTML",
        )
        return

    await DcaConfigManager.upsert_stock(
        symbol=info["symbol"],
        name=info["name"],
        currency=info["currency"],
        market_country=info["market_country"],
    )
    await state.clear()
    text, kb = await build_main_panel_message()
    await message.answer(
        f"✅ <b>{html.escape(info['name'])} (<code>{info['symbol']}</code>) 등록 완료!</b>\n"
        "아래 제어반에서 1회 기준 금액, 목표 수익률(최대 1000%), 매도 비율(최대 100%)을 설정하세요.",
        parse_mode="HTML",
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# =====================================================================
# 목표 수익률(%) 조절 메뉴 (1% ~ 1000% 버튼 + 직접 입력)
# =====================================================================
@router.callback_query(F.data == "menu_target_profit")
async def cb_menu_target_profit(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.clear()
    presets = [
        [5, 10, 15, 20],
        [30, 50, 75, 100],
        [150, 200, 300, 500],
        [700, 800, 900, 1000],
    ]
    rows = []
    for row_vals in presets:
        rows.append([
            InlineKeyboardButton(text=f"+{v}%", callback_data=f"set_tp:{v}") for v in row_vals
        ])
    rows.append([InlineKeyboardButton(text="⌨️ 원하는 퍼센트 직접 입력 (1~1000%)", callback_data="input_tp_custom")])
    rows.append([InlineKeyboardButton(text="🔙 제어반으로 돌아가기", callback_data="refresh_panel")])

    await callback.message.edit_text(
        "🎯 <b>[익절 목표 수익률(%) 선택 — 최대 1000%]</b>\n\n"
        "▫️ 내 평단가 대비 현재가가 아래 선택한 퍼센트(%) 이상 오르면:\n"
        "  1) 설정한 매도 비율만큼 <b>자동 익절 매도</b>하고,\n"
        "  2) 그다음 날부터는 <b>신규 매수를 자동으로 멈춥니다.</b>\n"
        "▫️ 원하시는 목표 수익률 버튼을 누르거나 직접 입력해 주세요.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_tp:"))
async def cb_set_tp(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    val = float(callback.data.split(":", 1)[1])
    val = max(1.0, min(1000.0, val))
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cfg["stocks"][sym]["target_profit_pct"] = val
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer(f"🎯 목표 수익률이 +{val:g}%로 설정되었습니다!")


@router.callback_query(F.data == "input_tp_custom")
async def cb_input_tp_custom(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.set_state(DcaInputState.waiting_for_target_profit)
    await callback.message.edit_text(
        "⌨️ <b>목표 수익률(%)을 1 ~ 1000 사이의 숫자로 입력해 주세요.</b> (예: <code>15</code>, <code>120</code>, <code>1000</code>)",
        parse_mode="HTML",
    )


@router.message(DcaInputState.waiting_for_target_profit)
async def msg_input_tp_custom(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user):
        return
    try:
        val = round(float(message.text.strip().replace("%", "")), 2)
        if not (1.0 <= val <= 1000.0) or not math.isfinite(val):
            raise ValueError()
    except Exception:
        await message.answer("🚨 1에서 1000 사이의 숫자를 입력해 주세요 (예: 10, 50, 1000).")
        return

    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cfg["stocks"][sym]["target_profit_pct"] = val
        await DcaConfigManager.save(cfg)
    await state.clear()
    text, kb = await build_main_panel_message()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# =====================================================================
# 익절 시 매도 비율(%) 조절 메뉴 (1% ~ 100% 버튼 + 직접 입력)
# =====================================================================
@router.callback_query(F.data == "menu_sell_ratio")
async def cb_menu_sell_ratio(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.clear()
    presets = [
        [10, 20, 25, 30],
        [40, 50, 75, 100],
    ]
    rows = []
    for row_vals in presets:
        rows.append([
            InlineKeyboardButton(
                text=("100% (전량매도)" if v == 100 else f"{v}% 매도"),
                callback_data=f"set_sr:{v}",
            )
            for v in row_vals
        ])
    rows.append([InlineKeyboardButton(text="⌨️ 원하는 매도 비율 직접 입력 (1~100%)", callback_data="input_sr_custom")])
    rows.append([InlineKeyboardButton(text="🔙 제어반으로 돌아가기", callback_data="refresh_panel")])

    await callback.message.edit_text(
        "📤 <b>[목표 수익 달성 시 매도 수량 비율(%) 선택 — 최대 100%]</b>\n\n"
        "▫️ 목표 수익률 구간에 도달했을 때 현재 보유 중인 주식의 몇 %를 팔지 선택합니다.\n"
        "▫️ 미국주식은 소수점 수량까지 정확히 계산해 팔고, 한국주식은 1주 단위(최소 1주)로 계산해 매도합니다.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_sr:"))
async def cb_set_sr(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    val = float(callback.data.split(":", 1)[1])
    val = max(1.0, min(100.0, val))
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cfg["stocks"][sym]["sell_ratio_pct"] = val
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer(f"📤 익절 매도 비율이 {val:g}%로 설정되었습니다!")


@router.callback_query(F.data == "input_sr_custom")
async def cb_input_sr_custom(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.set_state(DcaInputState.waiting_for_sell_ratio)
    await callback.message.edit_text(
        "⌨️ <b>익절 시 매도할 비율(%)을 1 ~ 100 사이의 숫자로 입력해 주세요.</b> (예: <code>10</code>, <code>50</code>, <code>100</code>)",
        parse_mode="HTML",
    )


@router.message(DcaInputState.waiting_for_sell_ratio)
async def msg_input_sr_custom(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user):
        return
    try:
        val = round(float(message.text.strip().replace("%", "")), 2)
        if not (1.0 <= val <= 100.0) or not math.isfinite(val):
            raise ValueError()
    except Exception:
        await message.answer("🚨 1에서 100 사이의 숫자를 입력해 주세요.")
        return

    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cfg["stocks"][sym]["sell_ratio_pct"] = val
        await DcaConfigManager.save(cfg)
    await state.clear()
    text, kb = await build_main_panel_message()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# =====================================================================
# 1회 기준 매수 금액 설정 (평단 상회 시 자동으로 1/2 금액 적용)
# =====================================================================
@router.callback_query(F.data == "menu_base_amount")
async def cb_menu_base_amount(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    st = cfg.get("stocks", {}).get(sym, {})
    cur = st.get("currency", "USD")

    if cur == "KRW":
        presets = [[10000, 30000, 50000], [100000, 200000, 500000]]
        rows = [
            [InlineKeyboardButton(text=f"₩{v:,}", callback_data=f"set_amt:{v}") for v in r]
            for r in presets
        ]
    else:
        presets = [[10, 20, 30, 50], [100, 200, 300, 500]]
        rows = [
            [InlineKeyboardButton(text=f"${v}", callback_data=f"set_amt:{v}") for v in r]
            for r in presets
        ]

    rows.append([InlineKeyboardButton(text="⌨️ 금액 직접 숫자로 입력", callback_data="input_amt_custom")])
    rows.append([InlineKeyboardButton(text="🔙 제어반으로 돌아가기", callback_data="refresh_panel")])

    await callback.message.edit_text(
        f"💰 <b>[{sym} 1회 기준 매수 금액 설정 ({cur})]</b>\n\n"
        "▫️ 현재가가 내 평단가 이하일 때는 <b>설정한 금액 100%</b>로 매수하고,\n"
        "▫️ 현재가가 내 평단가보다 높을 때는 자동으로 <b>절반(1/2) 금액</b>만 매수합니다.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_amt:"))
async def cb_set_amt(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    val = float(callback.data.split(":", 1)[1])
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cfg["stocks"][sym]["base_amount"] = val
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("💰 1회 기준 매수 금액이 변경되었습니다!")


@router.callback_query(F.data == "input_amt_custom")
async def cb_input_amt_custom(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.set_state(DcaInputState.waiting_for_base_amount)
    await callback.message.edit_text(
        "⌨️ <b>1회 기준 매수 금액을 숫자로만 입력해 주세요.</b> (예: 미국주식 <code>40</code> / 한국주식 <code>150000</code>)",
        parse_mode="HTML",
    )


@router.message(DcaInputState.waiting_for_base_amount)
async def msg_input_amt_custom(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user):
        return
    try:
        val = round(float(message.text.strip().replace(",", "").replace("$", "").replace("₩", "")), 2)
        if val <= 0 or not math.isfinite(val):
            raise ValueError()
    except Exception:
        await message.answer("🚨 0보다 큰 숫자를 입력해 주세요.")
        return

    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cfg["stocks"][sym]["base_amount"] = val
        await DcaConfigManager.save(cfg)
    await state.clear()
    text, kb = await build_main_panel_message()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "toggle_profit_lock")
async def cb_toggle_profit_lock(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cur_lock = bool(cfg["stocks"][sym].get("profit_lock", False))
        cfg["stocks"][sym]["profit_lock"] = not cur_lock
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("매수 잠금 상태가 전환되었습니다.")


@router.callback_query(F.data == "toggle_stock_enabled")
async def cb_toggle_stock_enabled(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        cur_en = bool(cfg["stocks"][sym].get("enabled", True))
        cfg["stocks"][sym]["enabled"] = not cur_en
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer("종목 활성 상태가 변경되었습니다.")


@router.callback_query(F.data == "delete_symbol")
async def cb_delete_symbol(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if sym in cfg.get("stocks", {}):
        del cfg["stocks"][sym]
        cfg["active_symbol"] = next(iter(cfg["stocks"].keys()), "")
        await DcaConfigManager.save(cfg)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
    await callback.answer(f"🗑️ {sym} 종목이 목록에서 삭제되었습니다.")


@router.callback_query(F.data == "menu_exec_time")
async def cb_menu_exec_time(callback: types.CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user):
        return
    await state.set_state(DcaInputState.waiting_for_exec_time)
    await callback.message.edit_text(
        "⏰ <b>[매일 자동 실행 시각 변경]</b>\n\n"
        "▫️ 변경할 시장과 시각을 <code>KR 10:00</code> 또는 <code>US 10:30</code> 형식으로 입력해 주세요.\n"
        "▫️ 🇰🇷 국내 주식 권장: <code>09:05 ~ 15:15</code> (한국 시간 KST)\n"
        "▫️ 🇺🇸 미국 주식 권장: <code>09:35 ~ 14:50</code> (미국 동부 시간 EST — 소수점 주문 허용 구간)",
        parse_mode="HTML",
    )


@router.message(DcaInputState.waiting_for_exec_time)
async def msg_menu_exec_time(message: types.Message, state: FSMContext):
    if not _is_admin(message.from_user):
        return
    parts = (message.text or "").strip().upper().split()
    if len(parts) != 2 or parts[0] not in ("KR", "US") or ":" not in parts[1]:
        await message.answer("🚨 예시처럼 입력해 주세요: <code>KR 10:00</code> 또는 <code>US 10:30</code>", parse_mode="HTML")
        return
    try:
        hh, mm = parts[1].split(":")
        h_i, m_i = int(hh), int(mm)
        if not (0 <= h_i <= 23 and 0 <= m_i <= 59):
            raise ValueError()
        fmt_t = f"{h_i:02d}:{m_i:02d}"
    except Exception:
        await message.answer("🚨 올바른 시간(HH:MM)을 입력해 주세요.")
        return

    cfg = await DcaConfigManager.load()
    if parts[0] == "KR":
        cfg["kr_exec_time"] = fmt_t
    else:
        cfg["us_exec_time"] = fmt_t
    await DcaConfigManager.save(cfg)
    await state.clear()
    text, kb = await build_main_panel_message()
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "run_now")
async def cb_run_now(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user):
        return
    cfg = await DcaConfigManager.load()
    sym = cfg.get("active_symbol", "")
    if not sym or sym not in cfg.get("stocks", {}):
        await callback.answer("선택된 종목이 없습니다.", show_alert=True)
        return
    await callback.answer(f"⚡ {sym} 즉시 판별 및 주문을 실행합니다...")
    await execute_stock_dca_step(api_client, callback.bot, ADMIN_CHAT_ID, sym, force_manual=True)
    text, kb = await build_main_panel_message()
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
