import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime,timedelta,timezone
import time
import pytz
from scipy import signal
from credentials import login, password, server


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
    # import ipdb;ipdb.set_trace()
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol not found: {symbol}")

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
# 9 EMA CALCULATION
# ========================
def calculate_ema_9_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    """
    Calculate EMA(9) for the last candle exactly like MT5.

    Args:
        df (pd.DataFrame): DataFrame containing at least 9+ candles
        close_col (str): Column name for close price

    Returns:
        float: EMA(9) value of the last candle
    """

    if len(df) < 9:
        raise ValueError("DataFrame must contain at least 9 candles")

    close_prices = df[close_col].astype(float)

    # MT5-compatible EMA
    ema = close_prices.ewm(
        span=9,
        adjust=False,   # CRITICAL: must be False
        min_periods=15
    ).mean()

    return float(ema.iloc[-1])



# ========================
# 60 EMA CALCULATION
# ========================
def calculate_ema_60_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    """
    Calculate EMA(60) for the last candle exactly like MT5.

    Requirements:
    - DataFrame must contain at least 60 candles (1000 is perfect)
    - Close prices must match MT5 chart closes exactly
    """

    if len(df) < 60:
        raise ValueError("DataFrame must contain at least 60 candles")

    close_prices = df[close_col].astype(float)

    ema_60 = close_prices.ewm(
        span=60, # smothning factor
        adjust=False,     # CRITICAL for MT5 match
        min_periods=100  # MT5 needs more data for accurate EMA
    ).mean()

    return float(ema_60.iloc[-1])



# ========================
# ORDER EXECUTION
# ========================
def place_market_order(symbol, order_type, lot = LOT, time = None):
    print(f"Sending order: {symbol}, type: {order_type}, time: {time}") # for testing
    return None  # Temporarily disable order sending for safety
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": MAGIC,
        "comment": "EMA 9/200 crossover",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    print("Order result:", result)
    return result

