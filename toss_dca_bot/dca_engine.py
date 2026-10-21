# =====================================================================
# FILE: dca_engine.py
# 목적: 스마트 적립식(평단 이하 1배 / 평단 초과 1/2배 매수) 및
#       목표 수익률(1%~1000%) 도달 시 매수 영구 잠금 + 비율(1%~100%) 익절 엔진
# =====================================================================

import os
import json
import math
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from toss_api import TossApiClient, GlobalThrottle

KST_TZ = ZoneInfo("Asia/Seoul")
EST_TZ = ZoneInfo("America/New_York")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dca_config.json")


class DcaConfigManager:
    """
    종목별 설정 및 당일 실행 이력, 목표 수익률 도달 후 매수 잠금(profit_lock) 상태를
    원자적(Atomic os.replace)으로 저장/관리합니다.
    """

    DEFAULT_CONFIG = {
        "is_master_active": True,
        "kr_exec_time": "10:00",  # 한국 주식 매일 실행 시각 (KST, 09:00~15:20 권장)
        "us_exec_time": "10:00",  # 미국 주식 매일 실행 시각 (EST, 소수점 주문 가능 시간 09:30~15:00 권장)
        "active_symbol": "",      # 현재 텔레그램 제어반에서 선택된 종목
        "stocks": {},             # symbol -> 종목 설정 dict
    }

    @classmethod
    def _default_stock_entry(cls, symbol: str, name: str, currency: str, market_country: str) -> dict:
        is_kr = (currency == "KRW")
        return {
            "symbol": symbol,
            "name": name,
            "currency": currency,
            "market_country": market_country,
            "enabled": True,
            "base_amount": 100000.0 if is_kr else 20.0,   # 1회 기준 매수 금액 (KRW 또는 USD)
            "target_profit_pct": 10.0,                    # 목표 수익률 % (1% ~ 1000%)
            "sell_ratio_pct": 10.0,                       # 익절 시 매도 비율 % (1% ~ 100%)
            "kr_min_one_share": True,                     # 한국주식 1/2 금액이 1주 미만일 때 최소 1주 매수 여부
            "profit_lock": False,                         # 목표 수익률 도달 후 매수 금지 락 (요구사항 2번)
            "last_exec_date": "",                         # 마지막 자동 실행 일자 (중복 실행 방지)
            "last_action_summary": "대기 중",
        }

    @classmethod
    async def load(cls) -> dict:
        async with GlobalThrottle.get_file_lock(CONFIG_FILE):
            def _read():
                if not os.path.exists(CONFIG_FILE):
                    return dict(cls.DEFAULT_CONFIG)
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if not isinstance(data, dict):
                            return dict(cls.DEFAULT_CONFIG)
                        merged = dict(cls.DEFAULT_CONFIG)
                        merged.update(data)
                        if not isinstance(merged.get("stocks"), dict):
                            merged["stocks"] = {}
                        return merged
                except Exception:
                    return dict(cls.DEFAULT_CONFIG)
            return await asyncio.to_thread(_read)

    @classmethod
    async def save(cls, config_data: dict):
        async with GlobalThrottle.get_file_lock(CONFIG_FILE):
            def _write():
                tmp_path = f"{CONFIG_FILE}.tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, CONFIG_FILE)
            await asyncio.to_thread(_write)

    @classmethod
    async def upsert_stock(cls, symbol: str, name: str, currency: str, market_country: str) -> dict:
        cfg = await cls.load()
        sym = symbol.strip().upper()
        if sym not in cfg["stocks"]:
            cfg["stocks"][sym] = cls._default_stock_entry(sym, name, currency, market_country)
        else:
            cfg["stocks"][sym]["name"] = name
            cfg["stocks"][sym]["currency"] = currency
            cfg["stocks"][sym]["market_country"] = market_country
        cfg["active_symbol"] = sym
        await cls.save(cfg)
        return cfg["stocks"][sym]


def evaluate_dca_decision(
    avg_price: float,
    current_price: float,
    holding_qty: float,
    base_amount: float,
    target_profit_pct: float,
    sell_ratio_pct: float,
    profit_lock: bool,
    market_country: str,
    kr_min_one_share: bool = True,
) -> dict:
    """
    순수 매매 판단 함수 (단위 테스트 및 Dry-Run 겸용)
    반환값:
      action: "BUY_FULL" | "BUY_HALF" | "SELL_PROFIT" | "HOLD_LOCKED" | "SKIP"
      profit_lock_next: bool (목표 수익률 도달 시 True로 영구 잠금, 전량 매도로 잔고 0주 복귀 시 False 해제)
      order_amount_usd: float (미국주식 소수점 금액 매수용)
      order_qty: float (한국주식 정수 매수/매도 및 미국주식 소수점 매도용)
      reason: str
    """
    if current_price <= 0:
        return {
            "action": "SKIP",
            "profit_lock_next": profit_lock,
            "order_amount_usd": 0.0,
            "order_qty": 0.0,
            "reason": "현재가 조회 불가(0 이하)",
        }

    has_holdings = (holding_qty > 0.0 and avg_price > 0.0)
    current_profit_pct = ((current_price / avg_price - 1.0) * 100.0) if has_holdings else 0.0

    # 잔고가 완전히 비워진 경우(0주) 이전 익절 매수잠금(profit_lock) 자동 해제하여 새 사이클 시작
    if not has_holdings:
        profit_lock = False

    # 1) 목표 수익률(+target_profit_pct%, 기본 +10% ~ 최대 +1000%) 이상 이익 구간 도달 시:
    #    - 즉시 profit_lock = True 로 설정하여 이후 날짜에는 절대 매수하지 않음 (요구사항 2번)
    #    - 보유 주식의 sell_ratio_pct% (1% ~ 100%) 매도 실행
    if has_holdings and current_profit_pct >= target_profit_pct:
        new_lock = True
        if market_country == "US":
            if sell_ratio_pct >= 100.0:
                sell_qty = round(holding_qty, 6)
            else:
                sell_qty = round(holding_qty * (sell_ratio_pct / 100.0), 6)
            if sell_qty <= 0.0:
                sell_qty = round(holding_qty, 6)
        else:
            int_hold = int(math.floor(holding_qty))
            if int_hold <= 0:
                return {
                    "action": "HOLD_LOCKED",
                    "profit_lock_next": True,
                    "order_amount_usd": 0.0,
                    "order_qty": 0.0,
                    "reason": "보유 수량 1주 미만으로 매도 불가",
                }
            if sell_ratio_pct >= 100.0:
                sell_qty = float(int_hold)
            else:
                sell_qty = float(max(1, min(int_hold, int(round(int_hold * (sell_ratio_pct / 100.0))))))

        return {
            "action": "SELL_PROFIT",
            "profit_lock_next": new_lock,
            "order_amount_usd": 0.0,
            "order_qty": sell_qty,
            "current_profit_pct": current_profit_pct,
            "reason": (
                f"목표 수익률(+{target_profit_pct:.1f}%) 도달 (현재 +{current_profit_pct:.2f}%) "
                f"➔ 보유분의 {sell_ratio_pct:.1f}% 익절 매도 및 이후 신규 매수 자동 잠금"
            ),
        }

    # 2) 이미 과거에 목표 수익률(+10% 등)에 도달하여 매수 잠금(profit_lock == True)된 상태라면:
    #    "10% 이상 목표퍼센트에 도달 한 뒤의 날은 매수하지마" 규칙에 따라 매수 전면 중단
    if profit_lock:
        return {
            "action": "HOLD_LOCKED",
            "profit_lock_next": True,
            "order_amount_usd": 0.0,
            "order_qty": 0.0,
            "current_profit_pct": current_profit_pct,
            "reason": (
                f"목표 수익률(+{target_profit_pct:.1f}%) 도달 이력으로 신규 매수 잠금 중 "
                f"(현재 수익률 {current_profit_pct:+.2f}% · 목표 수익률 재도달 시 {sell_ratio_pct:.1f}% 추가 매도 대기)"
            ),
        }

    # 3) 매수 구간:
    #    - 내 평단가보다 현재가가 높으면 (current_price >= avg_price * 1.01): 기준 금액의 1/2 구매 (BUY_HALF)
    #    - 내 평단가보다 현재가가 같거나 낮으면 (또는 첫 매수): 기준 금액 100% 구매 (BUY_FULL)
    if has_holdings and current_price >= avg_price * 1.01:
        action_type = "BUY_HALF"
        effective_budget = round(base_amount * 0.5, 2)
        ratio_desc = "평단가 상회 ➔ 1/2 금액 축소 매수"
    else:
        action_type = "BUY_FULL"
        effective_budget = round(base_amount, 2)
        ratio_desc = "평단가 이하(또는 첫 진입) ➔ 100% 기준 금액 정상 매수"

    if market_country == "US":
        if effective_budget < 1.0:
            return {
                "action": "SKIP",
                "profit_lock_next": False,
                "order_amount_usd": 0.0,
                "order_qty": 0.0,
                "current_profit_pct": current_profit_pct,
                "reason": f"미국주식 최소 소수점 주문 금액($1.00) 미만 (${effective_budget:.2f})",
            }
        return {
            "action": action_type,
            "profit_lock_next": False,
            "order_amount_usd": effective_budget,
            "order_qty": 0.0,
            "current_profit_pct": current_profit_pct,
            "reason": f"{ratio_desc} (${effective_budget:,.2f} 소수점 시장가 주문)",
        }
    else:
        raw_qty = int(math.floor(effective_budget / current_price))
        if raw_qty < 1:
            if kr_min_one_share:
                raw_qty = 1
                ratio_desc += " (1주 미만 보정 ➔ 최소 1주 매수)"
            else:
                return {
                    "action": "SKIP",
                    "profit_lock_next": False,
                    "order_amount_usd": 0.0,
                    "order_qty": 0.0,
                    "current_profit_pct": current_profit_pct,
                    "reason": f"산출 매수 금액(₩{effective_budget:,.0f})이 현재 1주 가격(₩{current_price:,.0f}) 미만으로 스킵",
                }
        return {
            "action": action_type,
            "profit_lock_next": False,
            "order_amount_usd": 0.0,
            "order_qty": float(raw_qty),
            "current_profit_pct": current_profit_pct,
            "reason": f"{ratio_desc} ({raw_qty}주 시장가 주문)",
        }


async def execute_stock_dca_step(
    client: TossApiClient,
    bot,
    chat_id: int,
    symbol: str,
    force_manual: bool = False,
) -> str:
    """단일 종목에 대해 실시간 잔고/평단가/현재가를 조회하고 매수(1배/1/2배) 또는 익절 매도를 수행합니다."""
    cfg = await DcaConfigManager.load()
    stock_cfg = cfg.get("stocks", {}).get(symbol)
    if not stock_cfg:
        return f"🚨 [{symbol}] 등록되지 않은 종목입니다."

    name = stock_cfg.get("name", symbol)
    currency = stock_cfg.get("currency", "USD")
    mc = stock_cfg.get("market_country", "US")
    base_amount = float(stock_cfg.get("base_amount", 20.0))
    target_profit_pct = float(stock_cfg.get("target_profit_pct", 10.0))
    sell_ratio_pct = float(stock_cfg.get("sell_ratio_pct", 10.0))
    profit_lock = bool(stock_cfg.get("profit_lock", False))
    kr_min_one_share = bool(stock_cfg.get("kr_min_one_share", True))

    # 정규장 개장 여부 확인
    is_open, market_msg = await client.is_regular_market_open(mc)
    if not is_open:
        msg = f"⏸️ <b>[{name}({symbol})] 장 운영 시간이 아닙니다.</b>\n▫️ 상태: <code>{market_msg}</code>"
        if force_manual:
            await bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
        return msg

    # 보유 잔고 및 현재가 조회
    hold = await client.get_symbol_holdings(symbol)
    avg_price = float(hold.get("avg_price", 0.0))
    holding_qty = float(hold.get("qty", 0.0))
    current_price = float(hold.get("last_price", 0.0))
    if current_price <= 0.0:
        current_price = await client.get_current_price(symbol)

    decision = evaluate_dca_decision(
        avg_price=avg_price,
        current_price=current_price,
        holding_qty=holding_qty,
        base_amount=base_amount,
        target_profit_pct=target_profit_pct,
        sell_ratio_pct=sell_ratio_pct,
        profit_lock=profit_lock,
        market_country=mc,
        kr_min_one_share=kr_min_one_share,
    )

    action = decision["action"]
    next_lock = decision["profit_lock_next"]
    reason = decision["reason"]
    cur_profit_pct = decision.get("current_profit_pct", 0.0)

    now_tz = datetime.now(KST_TZ if mc == "KR" else EST_TZ)
    today_str = now_tz.strftime("%Y-%m-%d")
    idem_key = f"DCA_{symbol}_{now_tz.strftime('%Y%m%d_%H%M%S')}"[:36]

    price_fmt = f"₩{current_price:,.0f}" if currency == "KRW" else f"${current_price:,.2f}"
    avg_fmt = f"₩{avg_price:,.0f}" if currency == "KRW" else f"${avg_price:,.2f}"

    try:
        if action in ("BUY_FULL", "BUY_HALF"):
            bp = await client.get_buying_power(currency)
            if mc == "US":
                order_amt = decision["order_amount_usd"]
                if bp < order_amt:
                    warn = (
                        f"⚠️ <b>[{name}({symbol}) 매수 보류 — 예수금 부족]</b>\n"
                        f"▫️ 필요 금액: <code>${order_amt:,.2f}</code> | 주문가능 USD: <code>${bp:,.2f}</code>"
                    )
                    await bot.send_message(chat_id=chat_id, text=warn, parse_mode="HTML")
                    return warn
                res = await client.place_us_fractional_buy(symbol, order_amt, idem_key)
                order_desc = f"소수점 시장가 매수 <code>${order_amt:,.2f}</code>"
            else:
                order_qty = int(decision["order_qty"])
                est_cost = order_qty * current_price
                if bp < est_cost:
                    warn = (
                        f"⚠️ <b>[{name}({symbol}) 매수 보류 — 원화 예수금 부족]</b>\n"
                        f"▫️ 필요 금액: <code>₩{est_cost:,.0f} ({order_qty}주)</code> | 가능 원화: <code>₩{bp:,.0f}</code>"
                    )
                    await bot.send_message(chat_id=chat_id, text=warn, parse_mode="HTML")
                    return warn
                res = await client.place_kr_integer_order(symbol, "BUY", order_qty, idem_key)
                order_desc = f"시장가 매수 <code>{order_qty}주</code> (약 ₩{est_cost:,.0f})"

            tag = "🟢 [100% 정상 적립 매수]" if action == "BUY_FULL" else "🟡 [평단 상회 ➔ 1/2 반액 매수]"
            report = (
                f"{tag} <b>{name} ({symbol})</b>\n"
                f"▫️ 현재가: <code>{price_fmt}</code> | 내 평단가: <code>{avg_fmt}</code> (<code>{cur_profit_pct:+.2f}%</code>)\n"
                f"▫️ 판별: {reason}\n"
                f"▫️ 주문 내역: {order_desc}"
            )

        elif action == "SELL_PROFIT":
            sellable_q = await client.get_sellable_quantity(symbol)
            if sellable_q <= 0.0:
                sellable_q = holding_qty
            if mc == "US":
                sell_q = min(round(sellable_q, 6), decision["order_qty"])
                res = await client.place_us_fractional_sell(symbol, sell_q, idem_key)
                qty_str = f"{sell_q:.6f}".rstrip("0").rstrip(".")
                order_desc = f"소수점 시장가 매도 <code>{qty_str}주</code> (보유분의 {sell_ratio_pct:.1f}%)"
            else:
                sell_q = min(int(math.floor(sellable_q)), int(decision["order_qty"]))
                res = await client.place_kr_integer_order(symbol, "SELL", sell_q, idem_key)
                order_desc = f"시장가 매도 <code>{sell_q}주</code> (보유분의 {sell_ratio_pct:.1f}%)"

            report = (
                f"🎉 <b>[목표 수익 +{target_profit_pct:.1f}% 달성 ➔ {sell_ratio_pct:.1f}% 분할 익절] {name} ({symbol})</b>\n"
                f"▫️ 현재가: <code>{price_fmt}</code> | 내 평단가: <code>{avg_fmt}</code> (수익률 <code>{cur_profit_pct:+.2f}%</code>)\n"
                f"▫️ 주문 내역: {order_desc}\n"
                f"▫️ 🔒 <b>매수 영구 잠금 활성화</b>: 목표 수익률 도달 이후 날부터는 신규 매수를 중단합니다."
            )

        elif action == "HOLD_LOCKED":
            report = (
                f"🔒 <b>[목표 수익 달성 후 매수 중지 상태] {name} ({symbol})</b>\n"
                f"▫️ 현재가: <code>{price_fmt}</code> | 내 평단가: <code>{avg_fmt}</code> (<code>{cur_profit_pct:+.2f}%</code>)\n"
                f"▫️ 사유: {reason}"
            )
        else:
            report = (
                f"⏭️ <b>[{name} ({symbol}) 매매 스킵]</b>\n"
                f"▫️ 사유: {reason}"
            )

        # 상태 저장
        cfg = await DcaConfigManager.load()
        if symbol in cfg.get("stocks", {}):
            cfg["stocks"][symbol]["profit_lock"] = next_lock
            cfg["stocks"][symbol]["last_exec_date"] = today_str
            cfg["stocks"][symbol]["last_action_summary"] = f"{today_str}: {action}"
            await DcaConfigManager.save(cfg)

        await bot.send_message(chat_id=chat_id, text=report, parse_mode="HTML")
        return report

    except Exception as e:
        err_msg = (
            f"🚨 <b>[{name}({symbol}) 주문 실행 오류]</b>\n"
            f"▫️ 사유: <code>{str(e)}</code>"
        )
        await bot.send_message(chat_id=chat_id, text=err_msg, parse_mode="HTML")
        return err_msg
