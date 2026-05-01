import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import pytz
from scipy import signal
from Algo.logger import logger




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

