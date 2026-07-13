# TODO: test spread strategy 
# MOTO: tyr to find a praticular value of spread to execute the trade for BTC.
# Spread formula: ((​EMA9​​/EMA15)−1)×100
# try to check if you take entry only based on the value of 

import MetaTrader5 as mt5
import pandas as pd
import pytz
from Algo.common.common import _calculate_ema_mt5, prevent_sleep, allow_sleep

from datetime import datetime, timezone

from Algo.credentials import login, password, server
from Algo.logger import logger,BOLD,RESET

class BTC_spread_strategy_backtesting():
    SYMBOL       = "BTCUSDz"
    TIMEFRAME    = mt5.TIMEFRAME_H4
    TOUCH_BUFFER = 2.0   
    POLL_INTERVAL = 60     
    NUM_CANDLES  = 500
    ALERT_COOLDOWN_MINUTES = 4  
    LOT_SIZE = 0.1  
    SL_POINTS = 50.0  
    TP_POINTS = 150.0  
    SENTIMENT = "SELL"  #To be managed manually on basis of 1D chart. If 9 crosses 15 downward at 1D so sentiment will be SELL.                 


    def __init__(self):
        pass

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
        logger.info("[connect]: Connected to MT5 successfully")
        return True
    
    
    # ========================
    # BACKTEST
    # ========================
    def backtest(self, start_date: str, end_date: str):
        from datetime import datetime, timezone
        import os

        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

        rates = mt5.copy_rates_range(self.SYMBOL, self.TIMEFRAME, start_dt, end_dt)
        if rates is None or len(rates) < 15:
            logger.error(f"[backtest]: Not enough data for range {start_date} to {end_date}")
            return

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

        rows = []


        for i in range(15, len(df)):
            slice_df = df.iloc[:i + 1]
            ema9  = _calculate_ema_mt5(slice_df, 9,  "close")
            ema15 = _calculate_ema_mt5(slice_df, 15, "close")


            spread = round(((ema9 / ema15) - 1) * 100, 4)
            
            rows.append({"Datetime": df.iloc[i]["time"], "EMA9": round(ema9, 2), "EMA15": round(ema15, 2), "Spread": spread})

        result_df = pd.DataFrame(rows, columns=["Datetime", "EMA9", "EMA15", "Spread"])

        filename = f"btc_spread_backtest_{start_date}_{end_date}.csv"
        output_path = os.path.join(os.path.dirname(__file__), filename)
        result_df.to_csv(output_path, index=False)
        logger.info(f"[backtest]: Saved {output_path} | crossover signals: {len(result_df)}")
        return output_path

# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    monitor = BTC_spread_strategy_backtesting()
    if not monitor.connect():
        exit(1)
    try:
        prevent_sleep()  # Enable sleep prevention
        logger.info("Starting btcusd monitor with sleep prevention enabled")
        # monitor.run()
        monitor.backtest("2026-07-01", "2026-07-12")
    finally:
        allow_sleep()  # Restore normal sleep behavior
        mt5.shutdown()
        logger.info("[btc_200_touch]: MT5 shutdown")
