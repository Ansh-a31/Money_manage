import MetaTrader5 as mt5
from Algo.logger import logger
from Algo.credentials import login, password, server



def connect() -> bool: 
        if not mt5.initialize():
            logger.error(f"[connect]: MT5 init failed: {mt5.last_error()}")
            return False
        if not mt5.login(login, password, server):
            logger.error(f"[connect]: MT5 login failed: {mt5.last_error()}")
            return False
        logger.info("[connect]: Connected to MT5 successfully")
        return True

def test_tick(symbol: str):
    if not connect():
        return
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
            logger.error(f"[_place_order: {symbol}]: Failed to get tick for {symbol}")
            return None
    
    else:
        logger.info(f"[test_tick]: Tick for {symbol}: Bid={tick.bid}, Ask={tick.ask}, Last={tick.last}")
        return tick
   

if __name__ == "__main__":
    # Example usage
    symbol = "XAGEURz"
    test_tick(symbol)

