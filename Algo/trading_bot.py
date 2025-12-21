'''
Official documentation for python metatrader5: 
        "https://www.mql5.com/en/docs/python_metatrader5"

'''

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime,timedelta,timezone
import time
import pytz
from scipy import signal
from services import *
from credentials import login, password, server



SYMBOL    = "XAUUSDz"          
LOT       = 0.01
TIMEFRAME = mt5.TIMEFRAME_M5  # 5-minute chart
EMA_FAST  = 9
EMA_SLOW  = 200
MAGIC     = 10001
BARS_INIT = 500



# ========================
# MT5 CONNECTION
# ========================
def connect_MT5():
    # import ipdb;ipdb.set_trace()
    if not mt5.initialize():
        print("MT5 connection failed:", mt5.last_error())
        mt5.shutdown()
        return False
    if mt5.login(login, password, server):
        print("Connected to MT5, successfully")
        return True
    return("MT5 connected successfully")




def backtest_strategy():
    import pytz
    # import ipdb;ipdb.set_trace()    
    # timezone = pytz.timezone("Etc/UTC")
    utc_from = datetime(2025, 12, 17,1)
    utc_to =  datetime(2025, 12, 18, 23)
    rate = mt5.copy_rates_range(SYMBOL, mt5.TIMEFRAME_M5, utc_from, utc_to)
    if rate is None or len(rate) == 0:
        return None
    return rate



# =======================
# FETCH PREVIOUS CANDLES DF
# =======================
def fetch_previous_candles_df(symbol, timeframe, candle, candle_time_ist,num_candles):
    ''' 
        Fetch previous minimum candles data for EMA calculation.
    '''
    # In copy_rates_from pass candle time in ist timezone. MT5 issue
    prev_candles_data = mt5.copy_rates_from(symbol, timeframe, candle_time_ist, num_candles)
    if prev_candles_data is None or len(prev_candles_data) < num_candles:
        raise ValueError("Not enough candle data available")
    
    df = pd.DataFrame(prev_candles_data)
    df["time"] = pd.to_datetime(df["time"], unit="s") 
    # Ensure chronological order (oldest → newest)
    df.sort_values("time", inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df



# ========================
# CALCULATE EMAS AT TIMESTAMP
# ========================
def calculate_emas_at_timestamp(symbol, timeframe, candle, candle_time_ist):
    ''' 
        Fetch previous candles and calculate EMAs

    '''
    # Fetch enough candles for slow EMA
    previous_candle_data = fetch_previous_candles_df(symbol, timeframe, candle, candle_time_ist,EMA_SLOW) 
    ema_fast = calculate_ema_9_mt5(previous_candle_data, "close")
    ema_slow =calculate_ema_60_mt5(previous_candle_data, "close")
    return ema_fast, ema_slow 

    

# ========================
# EMA CROSSOVER DETECTION
# =======================
def detect_ema_crossover_signal(symbol, timeframe, candle_time, candle_time_ist):
    # import ipdb;ipdb.set_trace()
    rates = mt5.copy_rates_from(symbol, timeframe, candle_time, 2) # only two candles needed one previous and current
    if rates is None or len(rates) < 2:
        return None
    
    prev_time  = datetime.fromtimestamp(rates[0]["time"], tz=timezone.utc)
    curr_time  = datetime.fromtimestamp(rates[1]["time"], tz=timezone.utc)
    # converting prev_time to IST
    prev_time_ist = prev_time.astimezone(pytz.timezone("Asia/Kolkata"))

    curr_ema_fast, curr_ema_slow = calculate_emas_at_timestamp(symbol, timeframe, curr_time,candle_time_ist)
    prev_ema_fast, prev_ema_slow = calculate_emas_at_timestamp(symbol, timeframe, prev_time, prev_time_ist)
    if curr_ema_fast > curr_ema_slow and prev_ema_fast <= prev_ema_slow:
        # import ipdb;ipdb.set_trace()
        print("----------------------------------------------------------")
        print(f"Buy signal at {candle_time_ist} Values below.")
        print("curr_ema_fast:", curr_ema_fast, "curr_ema_slow:", curr_ema_slow)
        print("prev_ema_fast:", prev_ema_fast, "prev_ema_slow:", prev_ema_slow)
        return "BUY"
    elif curr_ema_fast < curr_ema_slow and prev_ema_fast >= prev_ema_slow:
        # import ipdb;ipdb.set_trace()
        print("----------------------------------------------------------")
        print(f"Sell signal at {candle_time_ist} Values below.")
        print("curr_ema_fast:", curr_ema_fast, "curr_ema_slow:", curr_ema_slow)
        print("prev_ema_fast:", prev_ema_fast, "prev_ema_slow:", prev_ema_slow)
        return "SELL"

    return None



# ========================
# Live Bot Execution
# ======================
def run_bot_backtest():
    # import ipdb;ipdb.set_trace()
    last_candle_time = None
    while True:
        rate = backtest_strategy()
        if rate is None:
            time.sleep(10)
            continue
        
        tdf = pd.DataFrame(rate).copy()
        tdf["time_utc"] = pd.to_datetime(tdf["time"], unit="s", utc=True)
        tdf["time_ist"] = tdf["time_utc"].dt.tz_convert("Asia/Kolkata")
        tdf.drop(columns=["spread", "real_volume","tick_volume"], inplace=True, errors="ignore")

        for i,j in tdf.iterrows():
            # print(j)
            # if  j["time_ist"] == pd.Timestamp("2025-12-19 18:30:00").tz_localize("Asia/Kolkata") or j["time_ist"] == pd.Timestamp("2025-12-19 18:25:00").tz_localize("Asia/Kolkata"):
            #         # import ipdb;ipdb.set_trace()
                df = j
                candle_time =  df["time_utc"].to_pydatetime()
                candle_time_ist = df["time_ist"].to_pydatetime()
                if candle_time != last_candle_time:
                    last_candle_time = candle_time
                    # print(f"New candle: {candle_time}")
                    signal = detect_ema_crossover_signal(symbol=SYMBOL, timeframe=TIMEFRAME, candle_time=candle_time,candle_time_ist = candle_time_ist)
                    if signal is not None:
                        import ipdb;ipdb.set_trace()
                        place_market_order(SYMBOL, signal)
                    else:
                        # print("No trade")
                        pass
            
        print("Waiting for next cycle...")
        time.sleep(15)



# ========================
# MAIN EXECUTION
# ========================
def main():
    try:
        connect_MT5()
        ensure_symbol(SYMBOL)
        # print(f"get symbols containing specific word :{get_symbols_containing_specific_word("XAU")}")

        run_bot_backtest()

    finally:
        print("Shutting down MT5 connection")
        mt5.shutdown()

# ========================
# RUN
# ========================
if __name__ == "__main__":
    main()


