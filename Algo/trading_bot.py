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
from services import ensure_symbol, has_open_position

login  = 83073970
password = "Ansh@123"
server = "Exness-MT5Trial12"

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


