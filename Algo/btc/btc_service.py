import MetaTrader5 as mt5
import pandas as pd
import math
from datetime import datetime, timezone
from Algo.logger import logger
from Algo.common.common import (
    ensure_symbol,
    get_symbols_containing_specific_word,
    calculate_ema_9_mt5,
    calculate_ema_15_mt5,
)

# SYMBOL    = "BTCUSD"
# LOT       = 0.01
# TIMEFRAME = mt5.TIMEFRAME_M5
MAGIC     = 10002
SL_BUFFER = 25.0  # points above/below crossover price for SL


# ========================
# POSITION CHECK
# ========================
def has_open_position(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        logger.warning(f"[has_open_position]:Failed to fetch positions for {symbol}")
        return False
    if len(positions) > 0:
        logger.info(f"[has_open_position]:Open position exists for {symbol} | total: {len(positions)}")
        return True
    return False


# ========================
# SL CALCULATION
# ========================
def _calc_sl(symbol: str, crossover_price: float, order_type, price: float) -> float:
    # import ipdb;ipdb.set_trace()
    info = mt5.symbol_info(symbol)
    min_distance = (info.trade_stops_level * info.point) if (info and info.trade_stops_level > 0) else SL_BUFFER
    effective_buffer = max(SL_BUFFER, min_distance * 1.1)
    
    if order_type == mt5.ORDER_TYPE_BUY:
        sl = crossover_price - effective_buffer
    else:
        sl = crossover_price + effective_buffer

    return sl


# ========================
# ORDER EXECUTION
# ========================
def place_market_order(symbol, order_type, lot=0.01, crossover_price=None):
    logger.info(f"[place_market_order]: symbol={symbol}, order_type={order_type}, lot={lot}, crossover_price={crossover_price}")
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Failed to get tick for {symbol}")
        return None

    price     = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"

    if crossover_price is not None:
        sl   = _calc_sl(symbol, crossover_price, order_type, price)
        risk = abs(price - sl)
        tp   = round(price + (risk * 2), 2) if order_type == mt5.ORDER_TYPE_BUY else round(price - (risk * 2), 2)
    else:
        sl = 0.0
        tp = 0.0

    logger.info(f"Placing {direction} | symbol: {symbol} | lot: {lot} | price: {price} | SL: {sl} | TP: {tp}")

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         order_type,
        "price":        price,
        "sl":           sl,
        "tp":           tp,
        "deviation":    50,
        "magic":        MAGIC,
        "comment":      "EMA 9/15 crossover",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order failed | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
        return None

    logger.info(f"Order placed | {direction} | symbol: {symbol} | lot: {lot} | price: {price} | SL: {sl} | TP: {tp} | ticket: {result.order}")
    return result

