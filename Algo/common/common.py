import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import pytz
from scipy import signal
import ctypes
from Algo.logger import logger


# ========================
# PREVENT WINDOWS SLEEP
# ========================
ES_CONTINUOUS       = 0x80000000
ES_SYSTEM_REQUIRED  = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def prevent_sleep():
    """
    Prevents Windows from sleeping or turning off display while script runs.
    Call this function at the start of your script to keep it running even when screen sleeps.
    
    Usage:
        from Algo.common.common import prevent_sleep, allow_sleep
        
        prevent_sleep()  # Enable sleep prevention
        # Your script logic here
        allow_sleep()    # Restore normal sleep behavior (optional, on script exit)
    """
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )
    logger.info("Sleep prevention enabled - script will continue running even when screen sleeps")

def allow_sleep():
    """
    Restores normal Windows sleep behavior.
    Call this function when you want to allow the system to sleep again.
    """
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    logger.info("Sleep prevention disabled - normal sleep behavior restored")




# ========================
# ENSURE SYMBOL AVAILABLE
# ========================
def ensure_symbol(symbol, timeout=10):
    if not mt5.symbol_select(symbol, True):
        logger.error(f"Symbol not found: {symbol}")
        get_symbols_containing_specific_word(symbol)
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
# MT5/EXNESS EMA CALCULATION
# ========================
# NOTE: This function only works well with higher timeframe only.
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

def calculate_ema_15_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    return _calculate_ema_mt5(df, 15, close_col)

def calculate_ema_60_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    return _calculate_ema_mt5(df, 60, close_col)


def calculate_ema_200_mt5(df: pd.DataFrame, close_col: str = "close") -> float:
    return _calculate_ema_mt5(df, 200, close_col)


def has_open_position(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        logger.warning(f"[has_open_position]:Failed to fetch positions for {symbol}")
        return False
    if len(positions) > 0:
        logger.info(f"[has_open_position]:Open position exists for {symbol} | total: {len(positions)}")
        return True
    return False
