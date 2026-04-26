import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime,timedelta,timezone
import time
import pytz
from scipy import signal
from credentials import login, password, server
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import logger


SYMBOL    = "GBPUSDz"          
LOT       = 0.01
TIMEFRAME = mt5.TIMEFRAME_M5  # 5-minute chart
EMA_FAST  = 9
EMA_SLOW  = 200
MAGIC     = 10001
BARS_INIT = 500



# ========================
# ENSURE SYMBOL
# ========================
def ensure_symbol(symbol, timeout=10):
    if not mt5.symbol_select(symbol, True):
        logger.error(f"Symbol not found: {symbol}")
        raise RuntimeError(f"Symbol not found: {symbol}")
    logger.info(f"Symbol selected: {symbol}")


# ========================
# GET SYMBOLS BY KEYWORD
# ========================
def get_symbols_containing_specific_word(word: str) -> list:
    symbols = mt5.symbols_get()
    if symbols is None:
        logger.warning("No symbols returned from MT5")
        return []
    result = [s.name for s in symbols if word.lower() in s.name.lower()]
    logger.info(f"Symbols containing '{word}': {result}")
    return result


# ========================
# GET LAST CLOSED CANDLE
# ========================
def get_last_closed_candle():
    rate = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, 1)
    if rate is None or len(rate) == 0:
        return None
    return rate

# ========================
# POSITION CHECK
# ========================
def has_open_position():
    positions = mt5.positions_get(symbol=SYMBOL)
    return positions is not None and len(positions) > 0



# ========================
# MT5/EXNESS EMA CALCULATION
# ========================
def _calculate_ema_mt5(df: pd.DataFrame, period: int, close_col: str = "close") -> float:
    """
    Replicates MT5/Exness EMA exactly:
    - Seeds with SMA of first `period` candles
    - Then applies EMA multiplier: alpha = 2 / (period + 1)
    - adjust=False, min_periods=period
    """
    if len(df) < period:
        raise ValueError(f"DataFrame must contain at least {period} candles")

    close_prices = df[close_col].astype(float).values

    # Seed: SMA of first `period` values (exactly how MT5 initializes)
    ema = float(close_prices[:period].mean())
    alpha = 2.0 / (period + 1)

    for price in close_prices[period:]:
        ema = alpha * price + (1 - alpha) * ema

    return ema


def calculate_ema_9_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    return _calculate_ema_mt5(df, 9, close_col)


def calculate_ema_60_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    return _calculate_ema_mt5(df, 60, close_col)


def calculate_ema_200_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    return _calculate_ema_mt5(df, 200, close_col)



# ========================
# CALCULATE 60 & 200 EMA FOR CURRENT CANDLE
# ========================
def calculate_ema_60_200_current_candle(symbol, timeframe, candle_time_ist) -> tuple:
    """
    Fetches enough candles and returns (ema_60, ema_200) for the current candle.
    """
    NUM_CANDLES = 500  # enough for accurate 200 EMA
    prev_candles_data = mt5.copy_rates_from(symbol, timeframe, candle_time_ist, NUM_CANDLES)
    if prev_candles_data is None or len(prev_candles_data) < NUM_CANDLES:
        raise ValueError("Not enough candle data available")

    df = pd.DataFrame(prev_candles_data)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df.sort_values("time", inplace=True)
    df.reset_index(drop=True, inplace=True)

    ema_60  = calculate_ema_60_mt5(df, "close")
    ema_200 = calculate_ema_200_mt5(df, "close")

    return ema_60, ema_200




# ========================
# ORDER EXECUTION
# ========================
def place_market_order(symbol, order_type, lot=LOT):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"Failed to get tick for {symbol}")
        return None

    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
    logger.info(f"Placing {direction} order | symbol: {symbol} | lot: {lot} | price: {price}")

    request = {
        "action":       mt5.TRADE_ACTION_DEAL,
        "symbol":       symbol,
        "volume":       lot,
        "type":         order_type,
        "price":        price,
        "deviation":    20,
        "magic":        MAGIC,
        "comment":      "EMA 60/200 crossover",
        "type_time":    mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
 
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order failed | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
        return None

    logger.info(f"Order placed | {direction} | symbol: {symbol} | lot: {lot} | price: {price} | ticket: {result.order}")
    return result

