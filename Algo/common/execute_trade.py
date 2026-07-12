'''
For instantly executing a trade.
'''
from Algo.logger import logger
import MetaTrader5 as mt5
from Algo.credentials import login, password, server
from database import mongo_client
from datetime import datetime
import pytz

def _execute_instant__order(order_type,symbol,LOT_SIZE=0.1,reason=""):
    """Place market order at whatever price is available - executes immediately"""
    if not mt5.initialize():
            logger.error(f"[connect]: MT5 init failed: {mt5.last_error()}")
            return False
    if not mt5.login(login, password, server):
        logger.error(f"[connect]: MT5 login failed: {mt5.last_error()}")
        return False
    logger.info("[connect]: Connected to MT5 successfully")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        logger.error(f"[_place_order: {symbol}]: Failed to get tick for {symbol}")
        return None
    
    # Get current market price - whatever is available
    price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
    direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
    
    # No SL/TP - execute at market price immediately
    logger.info(f"[_place_order: {symbol}]: Placing {direction} order at market price  | lot: {LOT_SIZE} | price: {price:.2f}")
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": 0.0,  # No SL - manual management
        "tp": 0.0,  # No TP - manual management
        "deviation": 100,  # Larger deviation to ensure execution at any available price
        "magic": 10002,
        "comment": "EMA crossover",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"[_place_order: {symbol}]: Order failed | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
        return None
    mongo_client.push(doc={"symbol": symbol, "reason":reason, "created_at": datetime.now(pytz.timezone("Asia/Kolkata"))}, collection_name="instant_trade")
    logger.info(f"[_place_order: {symbol}]: Order executed successfully | {direction} | ticket: {result.order} | executed_price: {result.price:.2f}")
    return result

if __name__ == "__main__":
    try:
        _execute_instant__order(
            order_type = mt5.ORDER_TYPE_BUY,
            symbol = "BTCUSDz",
            LOT_SIZE = 0.5,
            reason = "Experimenting: Crossover and retest at 1D on 06/07/2026."
            )
        # monitor.backtest_24h()
    finally:
        logger.info("[4h_crossover]: MT5 shutdown")
