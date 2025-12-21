import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime,timedelta,timezone
import time
import pytz
from scipy import signal


login  = 83073970
password = "Ansh@123"
server = "Exness-MT5Trial12"

SYMBOL    = "GBPUSDz"          
LOT       = 0.01
TIMEFRAME = mt5.TIMEFRAME_M5  # 5-minute chart
EMA_FAST  = 9
EMA_SLOW  = 200
MAGIC     = 10001
BARS_INIT = 500



# ========================
# ENSURE SYMBOL
# ========================
def ensure_symbol(symbol, timeout=10):
    # import ipdb;ipdb.set_trace()
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Symbol not found: {symbol}")

# ========================
# GET LAST CLOSED CANDLE
# ========================
def get_last_closed_candle():
    rate = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, 1)
    if rate is None or len(rate) == 0:
        return None
    return rate

# ========================
# POSITION CHECK
# ========================
def has_open_position():
    positions = mt5.positions_get(symbol=SYMBOL)
    return positions is not None and len(positions) > 0

