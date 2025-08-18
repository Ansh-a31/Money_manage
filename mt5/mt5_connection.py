import MetaTrader5 as mt5
import pandas as pd
import datetime 
import numpy as np
# import pandas_ta as ta
# from scipy.signals import argrelextrema
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


def ohlcv(symbol, num_bars=1000):
    """Get historical OHLCV data for a symbol."""

    # import ipdb;ipdb.set_trace()
    start_bar = 0
    bars = mt5.copy_rates_from(symbol, mt5.TIMEFRAME_M1, datetime.now(), num_bars)
    if bars is None:
        print(f"Failed to get rates for {symbol}")
    return bars


initialize_mt5()
ohlcv('BTCUSD.a', 250)  