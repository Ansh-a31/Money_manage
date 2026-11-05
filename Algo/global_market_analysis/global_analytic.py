import time
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
import pytz

from communication.send_email import send_email_price_alert
from Algo.common.common import _calculate_ema_mt5, prevent_sleep, allow_sleep
from Algo.credentials import login, password, server
from Algo.logger import logger
from Algo.xauusd.services import has_open_position
from database import mongo_client

TIMEFRAME    = mt5.TIMEFRAME_M5
NUM_CANDLES = 100
ALERT_COOLDOWN_SECONDS = 180  # 3 minutes cooldown between email alerts

def connect() -> bool:
    if not mt5.initialize():
        logger.error(f"[connect]: MT5 init failed: {mt5.last_error()}")
        return False
    if not mt5.login(login, password, server):
        logger.error(f"[connect]: MT5 login failed: {mt5.last_error()}")
        return False
    logger.info("[connect]: Connected to MT5 successfully")
    return True


def _send_touch_alert(symbol: str, current_price: float, ema: float, distance: float):
    now = time.time()
    # if (now - _last_alert_time) < ALERT_COOLDOWN_SECONDS:
    #     remaining = int(ALERT_COOLDOWN_SECONDS - (now - _last_alert_time))
    #     logger.info(f"[send_touch_alert]: Touch ongoing, alert in cooldown ({remaining}s remaining)")
    #     return

    msg = (
        f"XAUUSD Price Touch Alert!\n\n"
        f"Symbol: {symbol}\n"
        f"Current Price: {current_price:.2f}\n"
        f"EMA 200 : {ema:.2f}\n"
        f"Distance: {distance:.2f} points"
    )
    logger.info(f"[send_touch_alert]: Sending touch alert email | price: {current_price:.2f} | EMA200: {ema:.2f} | distance: {distance:.2f}")
    success = send_email_price_alert(msg)
    if success:
        # _last_alert_time = now
        logger.info(f"[send_touch_alert]: Email sent successfully.")
    else:
        logger.warning(f"[send_touch_alert]: Email sending failed.")

def calculate_ma(symbol_data: pd.DataFrame, period: int, close_col: str = "close") -> float:
    """
    Calculates and returns the latest Moving Average (EMA) value for the specified period.
    """
    if symbol_data is None or len(symbol_data) < period:
        logger.error(f"[calculate_ma]: Not enough data to calculate MA {period} | received: {len(symbol_data) if symbol_data is not None else 0}")
        
    close_prices = symbol_data[close_col].astype(float).values
    ma = close_prices[-period:].mean()
    logger.info(f"[calculate_ma]: MA{period} calculated: {ma:.2f}")
    return ma


def get_symbol_data(symbol: str, timeframe: int, num_candles: int):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    if rates is None or len(rates) == 0:
        logger.error(f"[get_symbol_data]: Failed to retrieve data for {symbol}: {mt5.last_error()}")
        return None
    return pd.DataFrame(rates)



def get_specific_symbols() -> list[str]:
    symbols = get_all_symbols()
    name = "ZTO"
    temp= [s for s in symbols if name in s.upper()]
    logger.info(f"[get_specific_symbols]: Retrieved {temp}")
    previous_data = mongo_client.fetch_last(query={"symbol": temp[0]}, collection_name="exness_symbols")
    if not previous_data:
        mongo_client.push(doc={"exness_name": name, "symbol": temp[0],}, collection_name="exness_symbols")
    else:
        pass

def get_all_symbols() -> list:
    symbols = mt5.symbols_get()
    if symbols is None:
        logger.error(f"[get_all_symbols]: Failed to retrieve symbols: {mt5.last_error()}")
        return []
    symbol_names = [symbol.name for symbol in symbols]
    logger.info(f"[get_all_symbols]: Retrieved {len(symbol_names)} symbols")
    return symbol_names


def global_stock_analyzer(symbols):
    # symbols = get_specific_symbols()
    # import ipdb;ipdb.set_trace()
    if symbols:
        logger.info(f"[main]: Retrieved symbols count: {len(symbols)}")
        exness_symbols = mongo_client.fetch_all(query={"is_active": True}, collection_name="exness_symbols")
        exness_symbols_list = [item['symbol'] for item in exness_symbols]
        for symbol in symbols:
            logger.info(f"[main]: Processing symbol: {symbol}")

            if symbol not in exness_symbols_list:                       # for checking any specific symbol
                continue

            symbol_data = get_symbol_data(symbol, TIMEFRAME, NUM_CANDLES)
            if symbol_data is not None:
                ma_5 = calculate_ma(symbol_data, 5)
                ma_15 = calculate_ma(symbol_data, 15)
                if abs(ma_15 - ma_5) < 0.5:
                    mongo_client.push(doc={"symbol": symbol,"created_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")}, collection_name="notification_logs")
                    # _send_touch_alert(symbol=symbol, current_price=symbol_data['close'].iloc[-1], ema=ma_15, distance=abs(ma_15 - ma_5))
    else:
        logger.warning("[main]: No symbols retrieved.")
        
 

if __name__ == "__main__":
    if not connect():
        logger.error("[main]: Failed to connect to MT5. Exiting.")
        exit(1)

    try:
        symbols = get_all_symbols()
        while True:
            global_stock_analyzer(symbols)
            logger.info("[main]: Sleeping for 60 seconds before next analysis.")
            time.sleep(60)  # Sleep for 60 seconds before next analysis
    except Exception as e:
        logger.exception(f"[main]: Exception occurred: {e}")
    finally:
        mt5.shutdown()
        logger.info("[main]: MT5 shutdown complete")
