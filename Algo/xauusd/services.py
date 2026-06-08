import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime,timedelta,timezone
import time
import pytz
from scipy import signal
from Algo.credentials import login, password, server
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import logger


SYMBOL    = "GBPUSDz"          
LOT       = 0.01
TIMEFRAME = mt5.TIMEFRAME_M5  # 5-minute chart
EMA_FAST  = 9
EMA_SLOW  = 200
MAGIC     = 10001
BARS_INIT = 500



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
def has_open_position(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        logger.warning(f"[has_open_position]:Failed to fetch positions for {symbol}")
        return False
    if len(positions) > 0:
        logger.info(f"[has_open_position]:Open position exists for {symbol} | total: {len(positions)}")
        return True
    return False
