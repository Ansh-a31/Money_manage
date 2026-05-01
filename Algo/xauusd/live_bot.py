'''
Live trading bot — EMA 60/200 crossover strategy.
Runs on live MT5 data and executes trades on crossover signals.
'''

import MetaTrader5 as mt5
import pandas as pd
import pytz
import time
import sys
import os
import ctypes
from datetime import datetime, timezone
from Algo.xauusd.services import (
    ensure_symbol,
    place_market_order,
    calculate_ema_60_mt5,
    calculate_ema_200_mt5,
)
from credentials import login, password, server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import logger


SYMBOL     = "XAUUSDz"
LOT        = 0.1
TIMEFRAME  = mt5.TIMEFRAME_M5
MAGIC      = 10001
IST        = pytz.timezone("Asia/Kolkata")
NUM_CANDLES = 500

# Global candle cache
_candle_cache: pd.DataFrame = pd.DataFrame()


# ========================
# PREVENT WINDOWS SLEEP
# ========================
ES_CONTINUOUS        = 0x80000000
ES_SYSTEM_REQUIRED   = 0x00000001
ES_DISPLAY_REQUIRED  = 0x00000002

def prevent_sleep():
    """Prevent Windows from sleeping or turning off display while bot runs."""
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )
    logger.info("Sleep prevention enabled")

def allow_sleep():
    """Restore normal Windows sleep behaviour on shutdown."""
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    logger.info("Sleep prevention disabled")


# ========================
# MT5 CONNECTION
# ========================
def connect_mt5():
    if not mt5.initialize():
        logger.error(f"MT5 init failed: {mt5.last_error()}")
        return False
    if not mt5.login(login, password, server):
        logger.error(f"MT5 login failed: {mt5.last_error()}")
        return False
    logger.info("Connected to MT5 successfully")
    return True


# ========================
# CANDLE CACHE
# ========================
def init_candle_cache():
    """Fetch initial 500 candles once at startup."""
    global _candle_cache
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, NUM_CANDLES)
    if rates is None or len(rates) < NUM_CANDLES:
        raise ValueError("Failed to initialize candle cache")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df.sort_values("time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    _candle_cache = df
    logger.info(f"Candle cache initialized with {len(_candle_cache)} candles")


def update_cache_with_candle(rate):
    """Append a new closed candle to cache, drop the oldest to keep size fixed."""
    global _candle_cache
    new_row = pd.DataFrame([dict(zip(rate.dtype.names, rate))])
    new_row["time"] = pd.to_datetime(new_row["time"], unit="s", utc=True)
    _candle_cache = pd.concat([_candle_cache, new_row], ignore_index=True).iloc[-NUM_CANDLES:]
    _candle_cache.reset_index(drop=True, inplace=True)


# ========================
# CROSSOVER SIGNAL
# ========================
def detect_crossover(candle_time_utc: datetime, candle_time_ist: datetime):
    if len(_candle_cache) < NUM_CANDLES:
        logger.warning("Cache not ready yet")
        return None


    # Current candle EMAs — use full cache
    curr_ema_60  = calculate_ema_60_mt5(_candle_cache)
    curr_ema_200 = calculate_ema_200_mt5(_candle_cache)

    # Previous candle EMAs — use cache minus last row
    prev_df      = _candle_cache.iloc[:-1]
    prev_ema_60  = calculate_ema_60_mt5(prev_df)
    prev_ema_200 = calculate_ema_200_mt5(prev_df)

    logger.info(f"Candle: {candle_time_ist} | EMA60: {curr_ema_60:.4f} | EMA200: {curr_ema_200:.4f}")

    if curr_ema_60 > curr_ema_200 and prev_ema_60 <= prev_ema_200:
        logger.info(f"BUY crossover detected at {candle_time_ist} | crossover price: {curr_ema_60:.4f}")
        return mt5.ORDER_TYPE_BUY, curr_ema_60
    elif curr_ema_60 < curr_ema_200 and prev_ema_60 >= prev_ema_200:
        logger.info(f"SELL crossover detected at {candle_time_ist} | crossover price: {curr_ema_60:.4f}")
        return mt5.ORDER_TYPE_SELL, curr_ema_60

    return None, None


# ========================
# PROCESS A SINGLE CANDLE
# ========================
def process_candle(rate: dict):
    update_cache_with_candle(rate)
    candle_time_utc = datetime.fromtimestamp(rate["time"], tz=timezone.utc)
    candle_time_ist = candle_time_utc.astimezone(IST)
    logger.info(f"Processing candle: {candle_time_ist}")
    signal, crossover_price = detect_crossover(candle_time_utc, candle_time_ist)
    if signal is not None:
        place_market_order(SYMBOL, signal, LOT, crossover_price)
    else:
        logger.info("No crossover signal")


# ========================
# LIVE BOT LOOP
# ========================
def run_live_bot():
    last_candle_time = None
    logger.info("Live bot loop started")

    while True:
        try:
            # Fetch last 10 closed candles to catch any missed ones
            rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, 10)
            if rates is None or len(rates) == 0:
                logger.warning("No rates received, retrying...")
                time.sleep(5)
                continue

            # Filter only new candles since last processed
            new_rates = [
                r for r in rates
                if last_candle_time is None or
                datetime.fromtimestamp(r["time"], tz=timezone.utc) > last_candle_time
            ]

            if not new_rates:
                time.sleep(5)
                continue

            if len(new_rates) > 1:
                logger.warning(f"Missed {len(new_rates) - 1} candle(s), processing all now")

            for rate in new_rates:
                process_candle(rate)

            last_candle_time = datetime.fromtimestamp(new_rates[-1]["time"], tz=timezone.utc)

        except Exception as e:
            logger.exception(f"Unexpected error in bot loop: {e}")
            time.sleep(10)


# ========================
# MAIN
# ========================
def main():
    try:
        if not connect_mt5():
            return
        prevent_sleep()
        ensure_symbol(SYMBOL)
        init_candle_cache()
        logger.info(f"Live bot started | symbol: {SYMBOL} | EMA 60/200 | timeframe: {TIMEFRAME}")
        run_live_bot()
    finally:
        allow_sleep()
        logger.info("Shutting down MT5")
        mt5.shutdown()


if __name__ == "__main__":
    main()
