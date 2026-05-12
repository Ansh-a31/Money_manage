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
    TOUCH_BUFFER = 10.0   # points within EMA200 considered a "touch"
    POLL_INTERVAL = 2     # seconds between each price check
    NUM_CANDLES  = 500

    def __init__(self):
        self._already_alerted = False

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
            raise ValueError("Not enough candle data for EMA 200")
        df = pd.DataFrame(rates)
        return _calculate_ema_mt5(df, 200, "close")

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
        send_email_price_alert(msg)
        logger.info(f"Email sent | price: {current_price:.2f} | EMA200: {ema_200:.2f} | distance: {distance:.2f}")

    # ========================
    # SINGLE TICK CHECK
    # ========================
    def _check_tick(self):
        tick = mt5.symbol_info_tick(self.SYMBOL)
        if tick is None:
            logger.warning("Failed to get tick, retrying...")
            return

        current_price = tick.bid
        ema_200       = self._get_ema_200()
        distance      = abs(current_price - ema_200)

        logger.info(f"Price: {current_price:.2f} | EMA200: {ema_200:.2f} | Distance: {distance:.2f}")

        if distance <= self.TOUCH_BUFFER:
            if not self._already_alerted:
                self._send_touch_alert(current_price, ema_200, distance)
                self._already_alerted = True
        else:
            if self._already_alerted:
                logger.info("Price moved away from EMA200 — alert reset")
                self._already_alerted = False

    # ========================
    # MAIN LOOP
    # ========================
    def run(self):
        logger.info(
            f"EMA200 touch monitor started | symbol: {self.SYMBOL} | "
            f"timeframe: M5 | buffer: {self.TOUCH_BUFFER} points"
        )
        while True:
            try:
                self._check_tick()
            except Exception as e:
                logger.exception(f"Error in monitor loop: {e}")
            time.sleep(self.POLL_INTERVAL)


# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    monitor = EMA200TouchMonitor()
    if not monitor.connect():
        exit(1)
    try:
        monitor.run()
    finally:
        mt5.shutdown()
        logger.info("MT5 shutdown")
