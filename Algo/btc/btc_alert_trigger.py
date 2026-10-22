import time
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import pytz

from Algo.common.common import _calculate_ema_mt5, prevent_sleep, allow_sleep
from Algo.credentials import login, password, server
from Algo.logger import logger
from communication.send_email import send_email_price_alert
from Algo.xauusd.services import has_open_position
from database import mongo_client


SYMBOL       = "BTCUSDz"
TIMEFRAME    = mt5.TIMEFRAME_M1
TOUCH_BUFFER = 50.0   
POLL_INTERVAL = 60     
NUM_CANDLES = 1000

def connect() -> bool:
    if not mt5.initialize():
        logger.error(f"[connect]: MT5 init failed: {mt5.last_error()}")
        return False
    if not mt5.login(login, password, server):
        logger.error(f"[connect]: MT5 login failed: {mt5.last_error()}")
        return False
    logger.info("[connect]: Connected to MT5 successfully")
    return True


def _get_ema_200() -> float:
    rates = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 0, NUM_CANDLES)
    if rates is None or len(rates) < 200:
        logger.error(f"[_get_ema_200]: Not enough candle data for EMA 200 | received: {len(rates) if rates is not None else 0}")
        raise ValueError("Not enough candle data for EMA 200")
    df = pd.DataFrame(rates)
    ema = _calculate_ema_mt5(df, 200, "close")
    logger.debug(f"[_get_ema_200]: EMA200 calculated: {ema:.2f}")
    return ema


def _send_touch_alert(current_price: float, ema: float, distance: float):
    msg = (
        f"btcusd Price Touch Alert!\n\n"
        f"Symbol: {SYMBOL}\n"
        f"Current Price: {current_price:.2f}\n"
        f"EMA 200 : {ema:.2f}\n"
        f"Distance: {distance:.2f} points"
    )
    logger.info(f"[send_touch_alert]: Sending touch alert email | price: {current_price:.2f} | EMA200: {ema:.2f} | distance: {distance:.2f}")
    send_email_price_alert(msg)
    logger.info(f"[send_touch_alert]: Email sent successfully. ")


def _check_tick():    
    tick = mt5.symbol_info_tick(SYMBOL)
    if tick is None:
        logger.warning(f"[_check_tick]: Failed to get tick for {SYMBOL}, retrying...")
        return

    current_price = tick.bid
    ema_200 = _get_ema_200()
    if ema_200 is None:
        logger.warning(f"[_check_tick]: EMA 200 calculation failed, skipping tick check.")
        return

    distance = abs(current_price - ema_200)
    if distance <= TOUCH_BUFFER:
        _send_touch_alert(current_price, ema_200, distance)



# ========================
# BACKTEST
# ========================
def _calculate_ema_series_mt5(close_prices: np.ndarray, period: int = 200) -> np.ndarray:
    """
    Vectorized calculation of EMA replicating MT5 formula:
    - Seeds with SMA of first `period` candles
    - Applies EMA alpha = 2.0 / (period + 1)
    Runs in O(N) linear time.
    """
    ema_values = np.full(len(close_prices), np.nan)
    if len(close_prices) < period:
        return ema_values

    # MT5 Seed: SMA of first `period` candles
    ema = float(close_prices[:period].mean())
    ema_values[period - 1] = ema
    alpha = 2.0 / (period + 1)

    for i in range(period, len(close_prices)):
        ema = alpha * close_prices[i] + (1.0 - alpha) * ema
        ema_values[i] = ema

    return ema_values


def backtest(start_date: str, end_date: str, only_new_touches: bool = True):
    """
    Backtests the EMA 200 touch alert strategy on historical M1 data.
    
    :param start_date: Start date string formatted as 'YYYY-MM-DD'
    :param end_date: End date string formatted as 'YYYY-MM-DD'
    :param only_new_touches: If True, logs only initial entry into the buffer zone (debounced alert).
    """
    import os

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt   = datetime.strptime(end_date,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

    rates = mt5.copy_rates_range(SYMBOL, TIMEFRAME, start_dt, end_dt)
    if rates is None or len(rates) < 200:
        logger.error(f"[backtest]: Not enough data for range {start_date} to {end_date} | received: {len(rates) if rates is not None else 0}")
        return

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["ema200"] = _calculate_ema_series_mt5(df["close"].astype(float).values, period=200)

    rows = []
    prev_in_buffer = False

    for i in range(200, len(df)):
        row = df.iloc[i]
        candle_time = row["time"]
        close_p = float(row["close"])
        high_p  = float(row["high"])
        low_p   = float(row["low"])
        ema200  = float(row["ema200"])

        # Check if candle range or close touches/is within TOUCH_BUFFER of EMA200
        in_buffer = (close_p <= ema200 + TOUCH_BUFFER) and (close_p >= ema200 - TOUCH_BUFFER)
        distance = abs(close_p - ema200)

        if in_buffer:
            if not only_new_touches or not prev_in_buffer:
                if low_p <= ema200 and high_p >= ema200:
                    signal = "EMA200_CROSS"
                elif low_p > ema200:
                    signal = "TOUCH_FROM_ABOVE"
                else:
                    signal = "TOUCH_FROM_BELOW"

                rows.append({
                    "Datetime": candle_time,
                    "Close": round(close_p, 2),
                    "High": round(high_p, 2),
                    "Low": round(low_p, 2),
                    "EMA200": round(ema200, 2),
                    "Distance": round(distance, 2),
                    "Signal": signal
                })

        prev_in_buffer = in_buffer

    result_df = pd.DataFrame(rows, columns=["Datetime", "Close", "High", "Low", "EMA200", "Distance", "Signal"])
    if not result_df.empty:
        result_df["Datetime"] = result_df["Datetime"].dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d %H:%M:%S")

    filename = f"btc_200_touch_backtest_{start_date}_{end_date}.csv"
    output_path = os.path.join(os.path.dirname(__file__), filename)
    result_df.to_csv(output_path, index=False)
    logger.info(f"[backtest]: Saved {output_path} | total touch events: {len(result_df)}")
    return output_path


# ========================
# MAIN LOOP
# ========================
def run():
    logger.info(
        f"[run]: EMA200 touch monitor started | symbol: {SYMBOL}.\n"
        f"[run]: timeframe: {TIMEFRAME} | buffer: {TOUCH_BUFFER} points | poll interval: {POLL_INTERVAL}s"
    )
    while True:
        try:
            _check_tick()
        except Exception as e:
            logger.exception(f"[run]: Error in monitor loop: {e}")
        time.sleep(POLL_INTERVAL)


# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    if not connect():
        exit(1)
    try:
        prevent_sleep()  # Enable sleep prevention
        logger.info("Starting btcusd monitor with sleep prevention enabled")
        # run()
        backtest("2026-10-21", "2026-10-22")
    finally:
        allow_sleep()  # Restore normal sleep behavior
        mt5.shutdown()
        logger.info("[btc_200_touch]: MT5 shutdown")
