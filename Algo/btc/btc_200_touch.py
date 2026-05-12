# For testing purposes only, not for production use

import time
import MetaTrader5 as mt5
import pandas as pd

from Algo.common.common import _calculate_ema_mt5
from Algo.credentials import login, password, server
from Algo.logger import logger
from communication.send_email import send_email_price_alert


class EMA200TouchMonitor:
    """
    Monitors BTC price against the 200 EMA on M5 timeframe.
    Sends an email alert when price touches the EMA.
    Prevents duplicate alerts until price moves away and returns.
    """

    SYMBOL       = "BTCUSDz"
    TIMEFRAME    = mt5.TIMEFRAME_M5
    TOUCH_BUFFER = 60.0   # points within EMA200 considered a "touch"
    POLL_INTERVAL = 2     # seconds between each price check
    NUM_CANDLES  = 500
    ALERT_COOLDOWN_MINUTES = 4  # minimum minutes between alerts

    def __init__(self):
        self._already_alerted = False
        # self._last_alert_time = {}  # Tracks last alert time per symbol/event
        self._last_real_alert_time = None  # Tracks last alert time for real-time monitoring

    # ========================
    # MT5 CONNECTION
    # ========================
    def connect(self) -> bool:
        if not mt5.initialize():
            logger.error(f"MT5 init failed: {mt5.last_error()}")
            return False
        if not mt5.login(login, password, server):
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            return False
        logger.info("Connected to MT5 successfully")
        return True

    # ========================
    # EMA 200 CALCULATION
    # ========================
    def _get_ema_200(self) -> float:
        rates = mt5.copy_rates_from_pos(self.SYMBOL, self.TIMEFRAME, 0, self.NUM_CANDLES)
        if rates is None or len(rates) < 200:
            logger.error(f"Not enough candle data for EMA 200 | received: {len(rates) if rates is not None else 0}")
            raise ValueError("Not enough candle data for EMA 200")
        df = pd.DataFrame(rates)
        ema = _calculate_ema_mt5(df, 200, "close") + 3        # adding 5 points to EMA200 to create a buffer zone for matching exact value
        logger.debug(f"EMA200 calculated: {ema:.2f}")
        return ema 

    # ========================
    # ALERT
    # ========================
    def _send_touch_alert(self, current_price: float, ema_200: float, distance: float):
        msg = (
            f"BTC Price Touch Alert!\n\n"
            f"Symbol: {self.SYMBOL}\n"
            f"Current Price: {current_price:.2f}\n"
            f"EMA 200 (M5): {ema_200:.2f}\n"
            f"Distance: {distance:.2f} points"
        )
        logger.info(f"Sending touch alert email | price: {current_price:.2f} | EMA200: {ema_200:.2f} | distance: {distance:.2f}")
        send_email_price_alert(msg)
        logger.info(f"Email sent successfully | price: {current_price:.2f} | EMA200: {ema_200:.2f}")

    # ========================
    # SINGLE TICK CHECK
    # ========================
    def _check_tick(self):
        from datetime import datetime, timezone
        
        tick = mt5.symbol_info_tick(self.SYMBOL)
        if tick is None:
            logger.warning(f"Failed to get tick for {self.SYMBOL}, retrying...")
            return

        current_price = tick.bid
        ema_200       = self._get_ema_200()
        distance      = abs(current_price - ema_200)
        current_time  = datetime.now(timezone.utc)

        logger.info(f"Price: {current_price:.2f} | EMA200: {ema_200:.2f} | Distance: {distance:.2f} | Buffer: {self.TOUCH_BUFFER}")

        if distance <= self.TOUCH_BUFFER:
            # Check if we should trigger alert (5+ minutes since last alert)
            should_alert = False
            if self._last_real_alert_time is None:
                should_alert = True
            else:
                time_diff_minutes = (current_time - self._last_real_alert_time).total_seconds() / 60
                if time_diff_minutes >= self.ALERT_COOLDOWN_MINUTES:
                    should_alert = True
                    logger.info(f"Alert cooldown expired | time since last alert: {time_diff_minutes:.2f} minutes")
                else:
                    logger.info(f"EMA200 touch ongoing | cooldown active | time since last alert: {time_diff_minutes:.2f} minutes | price: {current_price:.2f}")

            if should_alert:
                logger.info(f"*** ALERT TRIGGERED *** | EMA200 touch detected | price: {current_price:.2f} | EMA200: {ema_200:.2f}")
                self._send_touch_alert(current_price, ema_200, distance)
                self._last_real_alert_time = current_time
        else:
            logger.info(f"Price outside touch buffer | distance: {distance:.2f} points")

    # ========================
    # MAIN LOOP
    # ========================
    def run(self):
        logger.info(
            f"EMA200 touch monitor started | symbol: {self.SYMBOL} | "
            f"timeframe: M5 | buffer: {self.TOUCH_BUFFER} points | poll interval: {self.POLL_INTERVAL}s"
        )
        while True:
            try:
                self._check_tick()
            except Exception as e:
                logger.exception(f"Error in monitor loop: {e}")
            time.sleep(self.POLL_INTERVAL)


    # ========================
    # BACKTEST
    # ========================
    def backtest_24h(self):
        """
        Backtests EMA200 touch detection on M5 candles from 1 May 6PM IST to 6 May 2AM IST.
        Logs every touch event — no emails sent.
        Only triggers alert if 5+ minutes have passed since last alert.
        """
        from datetime import datetime, timedelta, timezone
        import pytz
        IST = pytz.timezone("Asia/Kolkata")

        utc_from = IST.localize(datetime(2026, 5, 6, 0, 0, 0)).astimezone(timezone.utc)
        utc_to   = IST.localize(datetime(2026, 5, 6,  9, 0, 0)).astimezone(timezone.utc)

        logger.info(f"Backtest started | symbol: {self.SYMBOL} | from: {utc_from.astimezone(IST)} | to: {utc_to.astimezone(IST)}")

        # Fetch extra candles before range for accurate EMA seed
        seed_from = utc_from - timedelta(hours=48)
        rates_all = mt5.copy_rates_range(self.SYMBOL, self.TIMEFRAME, seed_from, utc_to)
        if rates_all is None or len(rates_all) < self.NUM_CANDLES:
            logger.error(f"Not enough historical data | received: {len(rates_all) if rates_all is not None else 0}")
            return

        df_all = pd.DataFrame(rates_all)
        df_all["time"] = pd.to_datetime(df_all["time"], unit="s", utc=True)
        df_all.sort_values("time", inplace=True)
        df_all.reset_index(drop=True, inplace=True)

        # Only iterate over candles within last 24h
        df_window = df_all[df_all["time"] >= pd.Timestamp(utc_from)]
        logger.info(f"Candles in last 24h: {len(df_window)}") 

        touch_count   = 0
        alert_cooldown_minutes = 4
        last_alert_time = None

        for idx in df_window.index:
            # Use all candles up to and including current for EMA calculation
            df_slice = df_all.loc[:idx]
            if len(df_slice) < 200:
                continue

            ema_200       = self._get_ema_200()
            candle_close  = float(df_slice.iloc[-1]["close"])
            candle_time   = df_slice.iloc[-1]["time"].astimezone(IST)
            distance      = abs(candle_close - ema_200)

            logger.info(f"[Backtest] {candle_time} | Close: {candle_close:.2f} | EMA200: {ema_200:.2f} | Distance: {distance:.2f}")

            if distance <= self.TOUCH_BUFFER:
                # Check if we should trigger alert (5+ minutes since last alert)
                should_alert = False
                if last_alert_time is None:
                    should_alert = True
                else:
                    time_diff = (candle_time - last_alert_time).total_seconds() / 60
                    if time_diff >= alert_cooldown_minutes:
                        should_alert = True
                        logger.info(f"[Backtest] Alert cooldown expired | time since last alert: {time_diff:.2f} minutes")
                    else:
                        logger.info(f"[Backtest] Touch ongoing | cooldown active | time since last alert: {time_diff:.2f} minutes")

                if should_alert:
                    logger.info(f"[Backtest] *** ALERT TRIGGERED *** | time: {candle_time} | close: {candle_close:.2f} | EMA200: {ema_200:.2f} | distance: {distance:.2f}")
                    touch_count += 1
                    last_alert_time = candle_time

        logger.info(f"Backtest complete | total alerts triggered: {touch_count}")


# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    monitor = EMA200TouchMonitor()
    if not monitor.connect():
        exit(1)
    try:
        monitor.run()
        # monitor.backtest_24h()
    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown")
