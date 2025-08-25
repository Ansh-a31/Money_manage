'''
Official documentation for python metatrader5: 
        "https://www.mql5.com/en/docs/python_metatrader5"

'''
import MetaTrader5 as mt5
import pandas as pd
import datetime 
import numpy as np
import pandas_ta as ta
from scipy.signal import argrelextrema
import os

pd.options.mode.chained_assignment = None  # default='warn'



login  = 79638356
password = "Ansh@123"
server = "Exness-MT5Trial8"



def initialize_mt5():
    """Connect to MetaTrader 5 terminal."""
    
    if not mt5.initialize():
        print("initialize() failed")
        mt5.shutdown()
        return False
    if mt5.login(login, password, server):
        print("Connected to MT5, successfully")
        return True
    

def get_symbol():
    session = int(os.path.basename(__file__)[-5:-3])
    symbol_dict = {
        1: "EURUSD.a",
        2: "GBPUSD.a",
        3: "XAUUSD.a",
        4: "AUDUSD.a",
        5: "USDCAD.a",
        6: "BTCUSD.a",
        7: "ETHUSD.a",
    }

    return symbol_dict.get(session)


def ohlcv(symbol, num_bars=250):
    """Get historical OHLCV data for a symbol."""

    # import ipdb;ipdb.set_trace()
    start_bar = 0
    # bars = mt5.copy_rates_from_pos("GBPUSD", mt5.TIMEFRAME_D1, 0, 10)
    bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, start_bar, num_bars)
    if bars is None:
        print(f"Failed to get rates for {symbol}")
    data_ohlc = pd.DataFrame(bars)
    data_ohlc['time'] = pd.to_datetime(data_ohlc['time'], unit='s')
    data_ohlc['time'] = data_ohlc['time'] + datetime.timedelta(hours = 7)
    data_ohlc = data_ohlc.drop(columns=['spread', 'real_volume'])
    
    high_low = data_ohlc['high'] - data_ohlc['low']
    high_close = np.abs(data_ohlc['high'] - data_ohlc['close'].shift())
    low_close = np.abs(data_ohlc['low'] - data_ohlc['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close],axis=1)
    true_range = np.max(ranges, axis=1)
    data_ohlc['atr'] = true_range.rolling(window=14).sum() / 14
    
    data_ohlc["p_LC"] = np.abs(data_ohlc['low']- data_ohlc['close'])
    data_ohlc["p_HC"] = np.abs(data_ohlc['high']- data_ohlc['close'])
    
    data_ohlc = data_ohlc.drop(columns=['open', 'high', 'low', 'close'])
    
    return data_ohlc


initialize_mt5()
data = ohlcv('BTCUSD', 250)   
print(data[-30:])