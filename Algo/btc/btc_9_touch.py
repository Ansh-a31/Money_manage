# --------------------------------------------------------------
# Script status: Working fine for touch alerts. Crossover trade execution not tested yet.
# --------------------------------------------------------------

"""
1. EMA200 TOUCH MONITORING:
   - Monitors when BTC price touches EMA200 (within 40 points buffer)
   - Sends email alerts when touch is detected
   - Implements 4-minute cooldown between alerts to prevent spam
   - Only sends alerts, does not execute trades

2. EMA9/200 CROSSOVER AUTOMATED TRADING:
   - Detects bullish crossover (EMA9 crosses above EMA200) → Executes BUY order
   - Detects bearish crossover (EMA9 crosses below EMA200) → Executes SELL order
   - Price validation: Checks if current market price matches crossover price (10-point tolerance)
   - Always executes at current available market price
   - Stop Loss: 50 points from execution price
   - Take Profit: 100 points from execution price (2:1 risk-reward ratio)
   - Sends email notification on every trade execution with full trade details
   - Implements 4-minute cooldown between trades to prevent overtrading
   - Checks for existing positions before opening new trades (one position at a time)

TRADE EXECUTION LOGIC:
   - On crossover detection, system fetches current market price
   - Validates if current price is within 10 points of crossover price
   - Executes trade at current market price (ask for BUY, bid for SELL)
   - Uses execution price as reference for SL/TP calculation
   - SL: execution_price ± 50 points
   - TP: execution_price ± 100 points

EMAIL NOTIFICATIONS:
   - EMA200 Touch Alert: Sent when price touches EMA200
   - Trade Execution Alert: Sent after every trade with ticket, prices, SL, TP, and EMA values

KEY FEATURES:
   - Real-time monitoring with 2-second polling interval
   - Separate cooldown timers for touch alerts and crossover trades
   - Position management (prevents duplicate positions)
   - Price validation before trade execution
   - Comprehensive logging for debugging and monitoring
   - Backtest capability for historical analysis (touch detection only)
   - MT5 integration for live trading
   - EMA calculations match MT5/Exness methodology exactly

"""

import time
import MetaTrader5 as mt5
import pandas as pd

from Algo.common.common import _calculate_ema_mt5, prevent_sleep, allow_sleep
from Algo.credentials import login, password, server
from Algo.logger import logger
from communication.send_email import send_email_price_alert
from Algo.btc.btc_service import has_open_position


class EMA200TouchMonitor:
    """
    Monitors BTC price against the 200 EMA on M5 timeframe.
    Sends an email alert when:
    1. Price touches the EMA200
    2. EMA9 crosses EMA200 (bullish or bearish)
    Prevents duplicate alerts with 5-minute cooldown.
    """

    SYMBOL       = "BTCUSDz"
    TIMEFRAME    = mt5.TIMEFRAME_M5
    TOUCH_BUFFER = 40.0   # points within EMA200 considered a "touch"
    POLL_INTERVAL = 10     # seconds between each price check
    NUM_CANDLES  = 500
    ALERT_COOLDOWN_MINUTES = 4  # minimum minutes between alerts
    LOT_SIZE = 1  # trading lot size
    SL_POINTS = 50.0  # stop loss points from execution price
    TP_POINTS = 150.0  # take profit points from execution price

    def __init__(self):
        self._already_alerted = False
        # self._last_alert_time = {}  # Tracks last alert time per symbol/event
        self._last_real_alert_time = None  # Tracks last alert time for real-time monitoring
        self._last_crossover_alert_time = None  # Tracks last EMA9/200 crossover alert
        self._prev_ema9 = None  # Previous EMA9 value for crossover detection
        self._prev_ema200 = None  # Previous EMA200 value for crossover detection

    # ========================
    # MT5 CONNECTION
    # ========================
    def connect(self) -> bool:
        if not mt5.initialize():
            logger.error(f"[connect]: MT5 init failed: {mt5.last_error()}")
            return False
        if not mt5.login(login, password, server):
            logger.error(f"[connect]: MT5 login failed: {mt5.last_error()}")
            return False
        logger.info(f"[connect]: Connected to MT5 successfully")
        return True


    # ========================
    # EMA 200 CALCULATION
    # ========================
    def _get_ema_200(self) -> float:
        rates = mt5.copy_rates_from_pos(self.SYMBOL, self.TIMEFRAME, 0, self.NUM_CANDLES)
        if rates is None or len(rates) < 200:
            logger.error(f"[_get_ema_200]: Not enough candle data for EMA 200 | received: {len(rates) if rates is not None else 0}")
            raise ValueError("Not enough candle data for EMA 200")
        df = pd.DataFrame(rates)
        ema = _calculate_ema_mt5(df, 200, "close") + 3        # adding 5 points to EMA200 to create a buffer zone for matching exact value
        logger.debug(f"[_get_ema_200]: EMA200 calculated: {ema:.2f}")
        return ema

    def _get_ema_9(self) -> float:
        rates = mt5.copy_rates_from_pos(self.SYMBOL, self.TIMEFRAME, 0, self.NUM_CANDLES)
        if rates is None or len(rates) < 200:
            logger.error(f"[_get_ema_9]: Not enough candle data for EMA 9 | received: {len(rates) if rates is not None else 0}")
            raise ValueError("Not enough candle data for EMA 9")
        df = pd.DataFrame(rates)
        ema = _calculate_ema_mt5(df, 9, "close")
        logger.debug(f"[_get_ema_9]: EMA9 calculated: {ema:.2f}")
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
        logger.info(f"[_send_touch_alert]: Sending touch alert email | price: {current_price:.2f} | EMA200: {ema_200:.2f} | distance: {distance:.2f}")
        send_email_price_alert(msg)
        logger.info(f"[_send_touch_alert]: Email sent successfully | price: {current_price:.2f} | EMA200: {ema_200:.2f}")

    def _send_crossover_alert(self, ema_9: float, ema_200: float, crossover_type: str):
        msg = (
            f"BTC EMA Crossover Alert!\n\n"
            f"Symbol: {self.SYMBOL}\n"
            f"Crossover Type: {crossover_type}\n"
            f"EMA 9 (M5): {ema_9:.2f}\n"
            f"EMA 200 (M5): {ema_200:.2f}\n"
        )
        logger.info(f"[_send_crossover_alert]: Sending crossover alert email | type: {crossover_type} | EMA9: {ema_9:.2f} | EMA200: {ema_200:.2f}")
        send_email_price_alert(msg)
        logger.info(f"[_send_crossover_alert]: Crossover email sent successfully | type: {crossover_type}")

    def _send_trade_execution_alert(self, direction: str, execution_price: float, ema_9: float, ema_200: float, result):
        """Send email notification when trade is executed"""
        # Calculate SL and TP from execution price
        sl_price = execution_price - self.SL_POINTS if direction == "BUY" else execution_price + self.SL_POINTS
        tp_price = execution_price + self.TP_POINTS if direction == "BUY" else execution_price - self.TP_POINTS
        
        msg = (
            f"BTC Trade Executed!\n\n"
            f"Symbol: {self.SYMBOL}\n"
            f"Direction: {direction}\n"
            f"Ticket: {result.order}\n"
            f"Execution Price: {execution_price:.2f}\n"
            f"Lot Size: {self.LOT_SIZE}\n"
            f"Stop Loss: {sl_price:.2f} ({self.SL_POINTS} points)\n"
            f"Take Profit: {tp_price:.2f} ({self.TP_POINTS} points)\n\n"
            f"Crossover Details:\n"
            f"EMA 9: {ema_9:.2f}\n"
            f"EMA 200: {ema_200:.2f}\n"
        )
        logger.info(f"[_send_trade_execution_alert]: Sending trade execution email | {direction} | ticket: {result.order} | price: {execution_price:.2f}")
        send_email_price_alert(msg)
        logger.info(f"[_send_trade_execution_alert]: Trade execution email sent successfully | {direction} | ticket: {result.order}")

    def _place_order(self, order_type, execution_price):
        """Place market order with SL and TP set"""
        tick = mt5.symbol_info_tick(self.SYMBOL)
        if tick is None:
            logger.error(f"[_place_order]: Failed to get tick for {self.SYMBOL}")
            return None
        
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        
        # Calculate SL and TP from execution price
        if order_type == mt5.ORDER_TYPE_BUY:
            sl = execution_price - self.SL_POINTS
            tp = execution_price + self.TP_POINTS
        else:
            sl = execution_price + self.SL_POINTS
            tp = execution_price - self.TP_POINTS
        
        logger.info(f"[_place_order]: Placing {direction} order | symbol: {self.SYMBOL} | lot: {self.LOT_SIZE} | price: {price} | SL: {sl:.2f} | TP: {tp:.2f}")
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.SYMBOL,
            "volume": self.LOT_SIZE,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 50,
            "magic": 10002,
            "comment": "BTC EMA9/200 crossover - SL 50 TP 120",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"[_place_order]: Order failed | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
            return None
        
        logger.info(f"[_place_order]: Order placed successfully | {direction} | ticket: {result.order} | price: {price} | SL: {sl:.2f} | TP: {tp:.2f}")
        return result

    def _execute_crossover_trade(self, ema_9: float, ema_200: float, order_type):
        """Execute trade on EMA9/200 crossover with 50 pip SL and 120 pip TP"""
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        
        # Check if position already exists
        if has_open_position(self.SYMBOL):
            logger.info(f"[_execute_crossover_trade]: Crossover detected but skipping trade — open position already exists for {self.SYMBOL}")
            return None
        
        # Get current market price
        tick = mt5.symbol_info_tick(self.SYMBOL)
        if tick is None:
            logger.error(f"[_execute_crossover_trade]: Failed to get tick for {self.SYMBOL}")
            return None
        
        current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        crossover_price = ema_9
        
        # Check if current price matches crossover price (with small tolerance)
        price_tolerance = 10.0  # points tolerance
        price_diff = abs(current_price - crossover_price)
        
        if price_diff <= price_tolerance:
            logger.info(f"[_execute_crossover_trade]: Current price {current_price:.2f} matches crossover price {crossover_price:.2f} (diff: {price_diff:.2f} points)")
            execution_price = current_price
        else:
            logger.warning(f"[_execute_crossover_trade]: Current price {current_price:.2f} differs from crossover price {crossover_price:.2f} (diff: {price_diff:.2f} points) — executing at current price")
            execution_price = current_price
        
        logger.info(f"[_execute_crossover_trade]: Executing {direction} trade on crossover | EMA9: {ema_9:.2f} | EMA200: {ema_200:.2f} | execution_price: {execution_price:.2f} | SL: {self.SL_POINTS} points | TP: {self.TP_POINTS} points")
        
        # Place order with SL and TP
        result = self._place_order(order_type, execution_price)
        
        if result:
            logger.info(f"[_execute_crossover_trade]: Crossover trade executed successfully | {direction} | ticket: {result.order}")
            # Send email notification
            self._send_trade_execution_alert(direction, execution_price, ema_9, ema_200, result)
        else:
            logger.error(f"[_execute_crossover_trade]: Failed to execute crossover trade | {direction}")
        
        return result

    # ========================
    # SINGLE TICK CHECK
    # ========================
    def _check_tick(self):
        from datetime import datetime, timezone
        
        tick = mt5.symbol_info_tick(self.SYMBOL)
        if tick is None:
            logger.warning(f"[_check_tick]: Failed to get tick for {self.SYMBOL}, retrying...")
            return

        current_price = tick.bid
        ema_200       = self._get_ema_200()
        ema_9         = self._get_ema_9()
        distance      = abs(current_price - ema_200)
        current_time  = datetime.now(timezone.utc)

        logger.info(f"[_check_tick]: Price: {current_price:.2f} | EMA9: {ema_9:.2f} | EMA200: {ema_200:.2f} | Distance: {distance:.2f} | Buffer: {self.TOUCH_BUFFER}")

        # Check for EMA9/200 crossover
        if self._prev_ema9 is not None and self._prev_ema200 is not None:
            # Bullish crossover: EMA9 crosses above EMA200
            if ema_9 > ema_200 and self._prev_ema9 <= self._prev_ema200:
                should_trade = False
                if self._last_crossover_alert_time is None:
                    should_trade = True
                else:
                    time_diff_minutes = (current_time - self._last_crossover_alert_time).total_seconds() / 60
                    if time_diff_minutes >= self.ALERT_COOLDOWN_MINUTES:
                        should_trade = True
                        logger.info(f"[_check_tick]: Crossover cooldown expired | time since last trade: {time_diff_minutes:.2f} minutes")

                if should_trade:
                    logger.info(f"[_check_tick]: *** BULLISH CROSSOVER DETECTED *** | EMA9: {ema_9:.2f} crossed above EMA200: {ema_200:.2f}")
                    self._execute_crossover_trade(ema_9, ema_200, mt5.ORDER_TYPE_BUY)
                    self._last_crossover_alert_time = current_time

            # Bearish crossover: EMA9 crosses below EMA200
            elif ema_9 < ema_200 and self._prev_ema9 >= self._prev_ema200:
                should_trade = False
                if self._last_crossover_alert_time is None:
                    should_trade = True
                else:
                    time_diff_minutes = (current_time - self._last_crossover_alert_time).total_seconds() / 60
                    if time_diff_minutes >= self.ALERT_COOLDOWN_MINUTES:
                        should_trade = True
                        logger.info(f"[_check_tick]: Crossover cooldown expired | time since last trade: {time_diff_minutes:.2f} minutes")

                if should_trade:
                    logger.info(f"[_check_tick]: *** BEARISH CROSSOVER DETECTED *** | EMA9: {ema_9:.2f} crossed below EMA200: {ema_200:.2f}")
                    self._execute_crossover_trade(ema_9, ema_200, mt5.ORDER_TYPE_SELL)
                    self._last_crossover_alert_time = current_time

        # Update previous EMA values for next iteration
        self._prev_ema9 = ema_9
        self._prev_ema200 = ema_200

        # Check for price touching EMA200
        if distance <= self.TOUCH_BUFFER:
            # Check if we should trigger alert (5+ minutes since last alert)
            should_alert = False
            if self._last_real_alert_time is None:
                should_alert = True
            else:
                time_diff_minutes = (current_time - self._last_real_alert_time).total_seconds() / 60
                if time_diff_minutes >= self.ALERT_COOLDOWN_MINUTES:
                    should_alert = True
                    logger.info(f"[_check_tick]: Alert cooldown expired | time since last alert: {time_diff_minutes:.2f} minutes")
                else:
                    logger.info(f"[_check_tick]: EMA200 touch ongoing | cooldown active | time since last alert: {time_diff_minutes:.2f} minutes | price: {current_price:.2f}")

            if should_alert:
                logger.info(f"[_check_tick]: *** ALERT TRIGGERED *** | EMA200 touch detected | price: {current_price:.2f} | EMA200: {ema_200:.2f}")
                self._send_touch_alert(current_price, ema_200, distance)
                self._last_real_alert_time = current_time
        else:
            logger.info(f"[_check_tick]: Price outside touch buffer | distance: {distance:.2f} points")

    # ========================
    # MAIN LOOP
    # ========================
    def run(self):
        logger.info(
            f"[run]: EMA200 touch monitor started | symbol: {self.SYMBOL} | "
            f"[run]: timeframe: M5 | buffer: {self.TOUCH_BUFFER} points | poll interval: {self.POLL_INTERVAL}s"
        )
        while True:
            try:
                self._check_tick()
            except Exception as e:
                logger.exception(f"[run]: Error in monitor loop: {e}")
            time.sleep(self.POLL_INTERVAL)


    # ========================
    # BACKTEST
    # ========================
    def backtest_24h(self):
        """
        Backtests EMA9/200 crossover strategy on M5 candles.
        Tests both touch detection and crossover signals.
        No emails sent, no trades executed.
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

        # Only iterate over candles within test window
        df_window = df_all[df_all["time"] >= pd.Timestamp(utc_from)]
        logger.info(f"Candles in backtest window: {len(df_window)}") 

        touch_count = 0
        crossover_count = 0
        alert_cooldown_minutes = 4
        last_touch_alert_time = None
        last_crossover_time = None
        prev_ema9 = None
        prev_ema200 = None

        for idx in df_window.index:
            # Use all candles up to and including current for EMA calculation
            df_slice = df_all.loc[:idx]
            if len(df_slice) < 200:
                continue

            # Calculate EMAs using the slice
            ema_9 = _calculate_ema_mt5(df_slice, 9, "close")
            ema_200 = _calculate_ema_mt5(df_slice, 200, "close") + 3
            
            candle_close = float(df_slice.iloc[-1]["close"])
            candle_time = df_slice.iloc[-1]["time"].astimezone(IST)
            distance = abs(candle_close - ema_200)

            logger.info(f"[Backtest] {candle_time} | Close: {candle_close:.2f} | EMA9: {ema_9:.2f} | EMA200: {ema_200:.2f} | Distance: {distance:.2f}")

            # Check for EMA9/200 crossover
            if prev_ema9 is not None and prev_ema200 is not None:
                # Bullish crossover
                if ema_9 > ema_200 and prev_ema9 <= prev_ema200:
                    should_signal = False
                    if last_crossover_time is None:
                        should_signal = True
                    else:
                        time_diff = (candle_time - last_crossover_time).total_seconds() / 60
                        if time_diff >= alert_cooldown_minutes:
                            should_signal = True

                    if should_signal:
                        logger.info(f"[Backtest] *** BULLISH CROSSOVER *** | time: {candle_time} | EMA9: {ema_9:.2f} | EMA200: {ema_200:.2f}")
                        crossover_count += 1
                        last_crossover_time = candle_time

                # Bearish crossover
                elif ema_9 < ema_200 and prev_ema9 >= prev_ema200:
                    should_signal = False
                    if last_crossover_time is None:
                        should_signal = True
                    else:
                        time_diff = (candle_time - last_crossover_time).total_seconds() / 60
                        if time_diff >= alert_cooldown_minutes:
                            should_signal = True

                    if should_signal:
                        logger.info(f"[Backtest] *** BEARISH CROSSOVER *** | time: {candle_time} | EMA9: {ema_9:.2f} | EMA200: {ema_200:.2f}")
                        crossover_count += 1
                        last_crossover_time = candle_time

            # Update previous EMA values
            prev_ema9 = ema_9
            prev_ema200 = ema_200

            # Check for EMA200 touch
            if distance <= self.TOUCH_BUFFER:
                should_alert = False
                if last_touch_alert_time is None:
                    should_alert = True
                else:
                    time_diff = (candle_time - last_touch_alert_time).total_seconds() / 60
                    if time_diff >= alert_cooldown_minutes:
                        should_alert = True

                if should_alert:
                    logger.info(f"[Backtest] *** EMA200 TOUCH *** | time: {candle_time} | close: {candle_close:.2f} | EMA200: {ema_200:.2f} | distance: {distance:.2f}")
                    touch_count += 1
                    last_touch_alert_time = candle_time

        logger.info(f"Backtest complete | EMA200 touches: {touch_count} | EMA9/200 crossovers: {crossover_count}")


# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    monitor = EMA200TouchMonitor()
    if not monitor.connect():
        exit(1)
    try:
        prevent_sleep()  # Enable sleep prevention
        logger.info("[BTC_main]: Starting BTC monitor with sleep prevention enabled")
        monitor.run()
        # monitor.backtest_24h()
    finally:
        allow_sleep()  # Restore normal sleep behavior
        mt5.shutdown()
        logger.info("[BTC_main]: MT5 shutdown")
