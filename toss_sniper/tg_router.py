# =====================================================================
# FILE: tg_router.py
# 목적: 프리장(04:00~09:29 EST) SOXS 단방향 RSI<=30 무한 출동 스나이퍼 텔레그램 라우팅 컨트롤러
# =====================================================================
# MODIFIED: 제3헌법 및 Case 43 의거 구버전 03:58 시계열 잔재를 프리장(04:00~09:29 EST) RSI<=30 스나이퍼로 100% 동기화
# MODIFIED: 예산 입력 시 음수/0/NaN/Inf 유입으로 인한 장부 오염 방어 로직 유지 (Case 37)
# MODIFIED: /reset 명령을 통한 SOXS 스나이퍼 원장 원자적 0점 소각 및 wakeup_event 즉각 동기화 (Case 02)
# MODIFIED: 모든 인라인 콜백 제자리 갱신(edit_text) 및 except Exception as e 문법 무결성 사수 (Case 17, 26)
# NEW: 전술 제어반(/settlement) 내 목표 익절률(+0.64% vs +1.00%) 원클릭 선택 라우터(set_rate_SOXS_) 및 복리/단리 토글 라우터(toggle_compound_SOXS) 결속

import os
import math
import html
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from quant_engine import AssassinLedger
from tg_ui_plugin import (
    get_main_menu_text,
    build_avwap_radar,
    build_sync_board,
    build_settlement_board,
)

router = Router()
api_client = None
ADMIN_CHAT_ID = None
wakeup_event = None
shared_rsi_state = None


def inject_dependencies(client, admin_id, event, rsi_state):
    global api_client, ADMIN_CHAT_ID, wakeup_event, shared_rsi_state
    api_client = client
    ADMIN_CHAT_ID = admin_id
    wakeup_event = event
    shared_rsi_state = rsi_state


class BudgetState(StatesGroup):
    waiting_for_budget = State()


# NEW: 최대 차수 매수 후 손절 라인 입력 상태
class StopLossState(StatesGroup):
    waiting_for_stop_loss = State()


# NEW: 추가 매수 가격 간격(0.3~1.0%) 입력 상태
class AddGapState(StatesGroup):
    waiting_for_gap = State()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        text = await get_main_menu_text()
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        pass


@router.message(Command("avwap"))
async def cmd_avwap(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        msg = await message.answer("📡 <b>프리장 스나이퍼 레이더 스캔 중...</b>", parse_mode="HTML")
        text, keyboard = await build_avwap_radar(api_client, shared_rsi_state)
        await msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"🚨 <b>관제탑 렌더링 실패:</b> {html.escape(str(e))}", parse_mode="HTML")


@router.callback_query(F.data == "open_avwap")
async def process_open_avwap(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        text, keyboard = await build_avwap_radar(api_client, shared_rsi_state)
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass
    finally:
        try:
            await callback_query.answer("레이더 갱신 완료")
        except Exception as e:
            pass


@router.message(Command("sync"))
async def cmd_sync(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        msg = await message.answer("📡 <b>SOXS 스나이퍼 지시서 스캔 중...</b>", parse_mode="HTML")
        text = await build_sync_board(api_client)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 새로고침", callback_data="open_sync")],
                [InlineKeyboardButton(text="🔙 메인 메뉴", callback_data="back_to_main")],
            ]
        )
        await msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"🚨 <b>지시서 동기화 실패:</b> {html.escape(str(e))}", parse_mode="HTML")


@router.callback_query(F.data == "open_sync")
async def process_open_sync(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        text = await build_sync_board(api_client)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 새로고침", callback_data="open_sync")],
                [InlineKeyboardButton(text="🔙 메인 메뉴", callback_data="back_to_main")],
            ]
        )
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass
    finally:
        try:
            await callback_query.answer("동기화 완료")
        except Exception as e:
            pass


@router.message(Command("settlement"))
async def cmd_settlement(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    text, keyboard = await build_settlement_board()
    try:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass


@router.callback_query(F.data == "open_settlement")
async def process_open_settlement(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        text, keyboard = await build_settlement_board()
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass


@router.callback_query(F.data.startswith("toggle_set_act_SOXS"))
async def process_toggle_set_act(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    state_data = await AssassinLedger.get_state("SOXS")
    new_act = not state_data[5]
    await AssassinLedger.save_state("SOXS", is_active=new_act)
    if wakeup_event:
        wakeup_event.set()
    text, keyboard = await build_settlement_board()
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass
    finally:
        try:
            await callback_query.answer(f"SOXS 스나이퍼 {'ON' if new_act else 'OFF'}")
        except Exception as e:
            pass


# NEW: 전술 제어반(/settlement) 목표 익절률(+0.64% vs +1.00%) 원클릭 선택 핸들러
@router.callback_query(F.data.startswith("set_rate_SOXS_"))
async def process_set_target_rate(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    raw_str = callback_query.data.replace("set_rate_SOXS_", "").strip()
    new_rate = AssassinLedger.normalize_target_rate(raw_str)
    net_rate = AssassinLedger.get_net_compound_rate(new_rate)

    await AssassinLedger.save_state("SOXS", target_profit_rate=new_rate)
    if wakeup_event:
        wakeup_event.set()

    text, keyboard = await build_settlement_board()
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass
    finally:
        try:
            await callback_query.answer(
                f"🎯 목표 익절률 +{new_rate:.2f}% (순수익 +{net_rate:.2f}%) 락온 완료"
            )
        except Exception as e:
            pass


# 전술 제어반(/settlement) 복리 모드(is_compound) vs 단리 모드 원클릭 토글 핸들러
@router.callback_query(F.data.startswith("toggle_compound_SOXS"))
async def process_toggle_compound(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    state_data = await AssassinLedger.get_state("SOXS")
    active_rate = AssassinLedger.normalize_target_rate(state_data[2])
    net_rate = AssassinLedger.get_net_compound_rate(active_rate)

    cur_comp = await AssassinLedger.get_is_compound("SOXS")
    new_comp = not cur_comp
    await AssassinLedger.save_state("SOXS", is_compound=new_comp)
    if wakeup_event:
        wakeup_event.set()
    text, keyboard = await build_settlement_board()
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass
    finally:
        try:
            mode_label = (
                f"📈 복리 모드 ON (익절 시 +{net_rate:.2f}% 증액)"
                if new_comp
                else "💵 단리(시드 고정) 모드 ON"
            )
            await callback_query.answer(mode_label)
        except Exception as e:
            pass


# NEW: 전술 제어반 추가 매수 간격(직전 매수가보다 몇 % 더 싸야 추가 매수) 입력 · 0.3~1.0%
@router.callback_query(F.data == "set_gap_SOXS")
async def process_set_add_gap(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.set_state(AddGapState.waiting_for_gap)
    cur = await AssassinLedger.get_add_gap_pct("SOXS")
    text = (
        "⌨️ <b>SOXS 추가 매수 간격 설정</b>\n\n"
        "▫️ RSI 35 회복 뒤 다시 RSI≤30이 되었을 때, 현재가가 <b>직전 매수가보다 몇 % 이상 싸야</b> 추가 매수할지 숫자로 보내 주세요.\n"
        "▫️ <b>0.3 ~ 1.0</b> 사이, 소수점 첫째 자리까지 (예: <code>0.7</code>)\n"
        "▫️ 작게 할수록 자주 사고(평단이 덜 내려감), 크게 할수록 드물게 더 싸게 삽니다.\n"
        f"▫️ 현재 설정: <code>-{cur:.1f}%</code>"
    )
    try:
        await callback_query.message.edit_text(text, parse_mode="HTML")
    except Exception:
        pass


@router.message(AddGapState.waiting_for_gap)
async def process_add_gap_input(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    raw = (message.text or "").strip().replace("%", "").replace("-", "")
    try:
        val = float(raw)
        if round(val, 1) != val:
            raise ValueError()
        val = AssassinLedger.normalize_add_gap(val)
    except Exception:
        await message.answer("🚨 <b>0.3 ~ 1.0</b> 사이 숫자(소수점 첫째 자리까지)를 보내 주세요. 예: <code>0.7</code>", parse_mode="HTML")
        return
    await AssassinLedger.save_state("SOXS", add_gap_pct=val)
    if wakeup_event:
        wakeup_event.set()
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 제어반으로", callback_data="open_settlement")]]
    )
    await message.answer(
        f"✅ <b>추가 매수 간격 -{val:.1f}% 설정 완료.</b>\n▫️ RSI 조건에 더해 직전 매수가보다 {val:.1f}% 이상 싸야 추가 매수합니다.",
        reply_markup=keyboard, parse_mode="HTML",
    )


# NEW: 전술 제어반 데이장 자동매매 켜기/끄기 (보유 중에 꺼도 데이장 보유분은 03:30 EST 강제 청산은 그대로 진행)
@router.callback_query(F.data == "toggle_day_SOXS")
async def process_toggle_day_trading(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    new_on = not await AssassinLedger.get_day_trading("SOXS")
    await AssassinLedger.save_state("SOXS", day_trading=new_on)
    if wakeup_event:
        wakeup_event.set()
    text, keyboard = await build_settlement_board()
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass
    finally:
        try:
            await callback_query.answer("🌙 데이장 매매 켜짐 (19:00~03:29 EST 매수 · 03:30 강제 청산)" if new_on else "⏸ 데이장 매매 꺼짐 (프리장만 매매)")
        except Exception:
            pass


# NEW: 전술 제어반(/settlement) 프리장 최대 매수 횟수(추가 매수 한도) 원클릭 선택 핸들러
@router.callback_query(F.data.startswith("set_maxbuy_SOXS_"))
async def process_set_max_buys(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    raw_str = callback_query.data.replace("set_maxbuy_SOXS_", "").strip()
    new_max = AssassinLedger.normalize_max_buys(raw_str)
    await AssassinLedger.save_state("SOXS", max_buy_count=new_max)
    if wakeup_event:
        wakeup_event.set()
    text, keyboard = await build_settlement_board()
    try:
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass
    finally:
        try:
            await callback_query.answer(f"🔁 최대 매수 {new_max}회 설정 완료")
        except Exception as e:
            pass


# NEW: 전술 제어반(/settlement) 최대 차수 매수 후 손절 라인(-1.0~-5.0%, 0 = 끄기) 입력 핸들러
@router.callback_query(F.data.startswith("set_sl_SOXS"))
async def process_set_stop_loss(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.set_state(StopLossState.waiting_for_stop_loss)
    cur = await AssassinLedger.get_stop_loss_pct("SOXS")
    _, max_buys = await AssassinLedger.get_buy_plan("SOXS")
    text = (
        "⌨️ <b>SOXS 최대 차수 매수 후 손절 라인 설정</b>\n\n"
        f"▫️ 추가 매수가 끝난 뒤(최대 {max_buys}회 도달 또는 09:30 매수 마감), 현재가가 <b>전체 평단가 대비 몇 % 아래</b>로 떨어지면 전량 매도할지 숫자로 보내 주세요.\n"
        "▫️ <b>1.0 ~ 5.0</b> 사이, 소수점 첫째 자리까지 (예: <code>2.5</code>) · <code>0</code> = 손절 끄기\n"
        f"▫️ 현재 설정: <code>{'-' + format(cur, '.1f') + '%' if cur > 0 else '꺼짐'}</code>"
    )
    try:
        await callback_query.message.edit_text(text, parse_mode="HTML")
    except Exception as e:
        pass


@router.message(StopLossState.waiting_for_stop_loss)
async def process_stop_loss_input(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    raw = (message.text or "").strip().replace("%", "").replace("-", "")
    try:
        val = float(raw)
        if val != 0.0 and (round(val, 1) != val or not 1.0 <= val <= 5.0):
            raise ValueError()
        val = AssassinLedger.normalize_stop_loss(val)
    except Exception:
        await message.answer("🚨 <b>1.0 ~ 5.0</b> 사이 숫자(소수점 첫째 자리까지)나 <code>0</code>(끄기)을 보내 주세요. 예: <code>2.5</code>", parse_mode="HTML")
        return
    await AssassinLedger.save_state("SOXS", stop_loss_pct=val)
    if wakeup_event:
        wakeup_event.set()
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 제어반으로", callback_data="open_settlement")]]
    )
    await message.answer(
        (f"✅ <b>손절 라인 -{val:.1f}% 설정 완료.</b>\n▫️ 추가 매수가 끝난 뒤(최대 차수 또는 09:30 마감) 평단 대비 -{val:.1f}% 아래로 떨어지면 전량 매도합니다."
         if val > 0 else "✅ <b>손절 라인을 껐습니다.</b>"),
        reply_markup=keyboard, parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("set_budget_SOXS"))
async def process_set_budget(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.set_state(BudgetState.waiting_for_budget)
    state_data = await AssassinLedger.get_state("SOXS")
    active_rate = AssassinLedger.normalize_target_rate(state_data[2])
    net_rate = AssassinLedger.get_net_compound_rate(active_rate)
    is_comp = await AssassinLedger.get_is_compound("SOXS")

    mode_desc = (
        f"📈 현재 <b>[복리 모드 · 목표 +{active_rate:.2f}%]</b>가 활성화되어 있습니다. 입력하신 시드를 시작점으로 익절 시마다 순수익 <b>+{net_rate:.2f}%</b>(수수료 0.14% 차감)가 가산되고 손절 시 수수료 포함 실손실금이 차감됩니다."
        if is_comp
        else f"💵 현재 <b>[단리(고정) 모드 · 목표 +{active_rate:.2f}%]</b>가 활성화되어 있습니다. 매 출동 시 입력하신 고정 달러 예산만 투입됩니다."
    )
    text = (
        "⌨️ <b>SOXS 스나이퍼 투입 시드 설정 (USD)</b>\n\n"
        "▫️ 04:00~09:29 EST 프리장 SOXS RSI≤30 스나이퍼 출동 시 투입할 기준 달러 예산을 숫자로 전송하십시오.\n"
        f"▫️ {mode_desc}"
    )
    try:
        await callback_query.message.edit_text(text, parse_mode="HTML")
    except Exception as e:
        pass


@router.message(BudgetState.waiting_for_budget)
async def process_budget_input(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    try:
        budget = round(float(message.text.strip()), 2)
        # 0 이하 또는 비정상 부동소수점(NaN/Inf) 입력 원천 차단 (Case 37)
        if budget <= 0.0 or not math.isfinite(budget):
            raise ValueError("Budget must be a positive finite number.")
        await AssassinLedger.save_state("SOXS", budget=budget)
        is_comp = await AssassinLedger.get_is_compound("SOXS")
        mode_tag = "📈 복리 시작 시드" if is_comp else "💵 단리 고정 시드"
        if wakeup_event:
            wakeup_event.set()
        await state.clear()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 제어반으로", callback_data="open_settlement")]]
        )
        await message.answer(
            f"✅ <b>SOXS 스나이퍼 {mode_tag} <code>${budget:,.2f}</code> 락온 완료.</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer("🚨 0보다 큰 유효한 숫자를 입력하세요.", parse_mode="HTML")


@router.message(Command("reset"))
async def cmd_reset(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ SOXS 장부 초기화", callback_data="execute_single_reset")],
            [InlineKeyboardButton(text="🔙 취소", callback_data="back_to_main")],
        ]
    )
    text = (
        "⚠️ <b>[SOXS 스나이퍼 장부 초기화]</b>\n\n"
        "경고: SOXS 로컬 장부(평단가, 목표가, 주문 ID, 당일 진입 잠금)를 "
        "100% 영구 소각하고 0점으로 원자적 초기화를 수행합니다.\n"
        "(설정된 시드 금액, 목표 익절률 및 복리/단리 모드는 그대로 보존됩니다.)\n진행하시겠습니까?"
    )
    try:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass


@router.callback_query(F.data == "execute_single_reset")
async def process_execute_reset(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        await AssassinLedger.reset_all_ledgers()
        if wakeup_event:
            wakeup_event.set()
        await callback_query.answer("✅ SOXS 장부 0점 소각 완료", show_alert=True)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 메인 메뉴", callback_data="back_to_main")]]
        )
        await callback_query.message.edit_text(
            "✅ <b>[SOXS 장부 영구 소각 완료]</b>\n"
            "▫️ 로컬 장부가 0점으로 원자적 초기화되었습니다 (프리장 내 RSI≤30 감시 즉시 복귀).",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            try:
                await callback_query.message.answer(
                    f"🚨 <b>초기화 실패:</b> {html.escape(str(e))}", parse_mode="HTML"
                )
            except Exception as ex:
                pass


@router.message(Command("update"))
async def cmd_update(message: types.Message, state: FSMContext):
    user = getattr(message, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 구글 클라우드 서버 탑재", callback_data="execute_update")],
            [InlineKeyboardButton(text="🔙 취소", callback_data="back_to_main")],
        ]
    )
    text = "⚠️ <b>[시스템 자가 업데이트]</b>\n\n최신 코드를 다운로드하고 재기동합니다. 진행하시겠습니까?"
    try:
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        pass


@router.callback_query(F.data == "execute_update")
async def process_execute_update(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        await callback_query.message.edit_text("🔄 <b>GitHub 최신 코드 다운로드 중...</b>", parse_mode="HTML")

        def _run_git_update():
            return (False, '자가 업데이트 해제: 직접 관리 모드입니다.')

        success, msg = await asyncio.to_thread(_run_git_update)
        if success:
            if "Already up to date." in msg:
                await callback_query.message.edit_text(
                    "✅ <b>서버 탑재 완료</b>\n▫️ 최신 버전입니다.", parse_mode="HTML"
                )
            else:
                await callback_query.message.edit_text(
                    f"🚀 <b>탑재 성공. 재기동 격발.</b>\n<pre>{html.escape(msg)}</pre>",
                    parse_mode="HTML",
                )
                await asyncio.sleep(1.0)
                os._exit(0)
        else:
            await callback_query.message.edit_text(
                f"🚨 <b>업데이트 실패 (롤백)</b>\n<pre>{html.escape(msg)}</pre>", parse_mode="HTML"
            )
    except Exception as e:
        await callback_query.message.edit_text(
            f"🚨 <b>서버 탑재 에러:</b> {html.escape(str(e))}", parse_mode="HTML"
        )


@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    user = getattr(callback_query, "from_user", None)
    if not user or getattr(user, "id", None) != ADMIN_CHAT_ID:
        return
    await state.clear()
    try:
        await callback_query.answer()
        text = await get_main_menu_text()
        await callback_query.message.edit_text(
            text, reply_markup=None, parse_mode="HTML"
        )
    except Exception as e:
        pass
