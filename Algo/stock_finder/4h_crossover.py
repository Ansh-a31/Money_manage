from typing import Optional
from datetime import datetime, timezone
import MetaTrader5 as mt5
from Algo.logger import logger
from Algo.credentials import login, password, server
from Algo.common.common import _calculate_ema_mt5, prevent_sleep, allow_sleep,has_open_position
import time
import ipdb
import pandas as pd
from database import mongo_client

class stock_tracker_4H():
    def __init__(self):
        self.TIMEFRAME = mt5.TIMEFRAME_H4
        self.NUM_CANDLES = 500
        self.LOT_SIZE = 0.1
        self._prev_ema9 = None  # Previous EMA9 value for crossover detection
        self._prev_ema15 = None  
        self.POLL_INTERVAL = 10 # seconds

    def connect(self) -> bool: 
        if not mt5.initialize():
            logger.error(f"[connect]: MT5 init failed: {mt5.last_error()}")
            return False
        if not mt5.login(login, password, server):
            logger.error(f"[connect]: MT5 login failed: {mt5.last_error()}")
            return False
        logger.info("[connect]: Connected to MT5 successfully")
        return True

    def get_stocks(self):
        # ipdb.set_trace()
        symbols = mt5.symbols_get()
        print(f"Total symbols: {len(symbols)}")

        sym =[]
        for symbol in symbols:
            # print(symbol.name)
            sym.append({
                "symbol_name":symbol.name,
                "category":symbol.category,
                "description": symbol.description
                })
            
        # for s in symbols:
        #     rows.append({
        #         "symbol": s.name,
        #         "description": s.description,
        #         "path": s.path,
        #     })

        # df = pd.DataFrame(rows)

        # print(df.head())
        # print(f"Total instruments: {len(df)}")

        # df.to_csv("Algo/stock_finder/exness_symbols.csv", index=False)
        return sym

        
    def movers_1D(self, data:list, timeframe: Optional[str] = None, ):
        '''
        Function to calculate the fast and slow movers in 24 hours.
        ''' 
        # ipdb.set_trace()
        movers = []
        count = 0
        for symbol in data:
            symbol_name = symbol['symbol_name']
            count+=1
            # if symbol != "USDHRKz":
            #     continue
            logger.info(f"[calculate_top_movers]:{count} Processing symbol: {symbol_name}")
            rates = mt5.copy_rates_from_pos(symbol_name, self.TIMEFRAME, 0, 2)

            if rates is None:
                logger.warning(f"[calculate_top_movers]: Failed to get rates for {symbol_name}")
                continue

            current_data = rates[-1]   # Latest daily candle
            current = current_data.item()[4]    #current closed price
            previous_data = rates[-2]  # Previous daily candle
            previous = previous_data.item()[4]  # previous close price 

            movers.append({
            "symbol": symbol_name,
            "category": symbol['category'],
            "current": current,
            "previous": previous,
            "change_pct": ((current - previous) / previous) * 100
            })

        ipdb.set_trace()
        top_movers = sorted(movers, key=lambda x: x["change_pct"], reverse=True)
        slow_movers = sorted(movers, key=lambda x: x["change_pct"], reverse=False)

        return {
            "top_movers": top_movers[:5],
            "slow_movers": slow_movers[:5]
        }
    
    # ========================
    # EMA 15 CALCULATION
    # ========================    
    def _get_ema_15(self,symbol) -> float:
        rates = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME, 0, 100)
        if rates is None or len(rates) < 50:
            logger.error(f"[_get_ema_15]: Not enough candle data for EMA 15 | received: {len(rates) if rates is not None else 0}")
            raise ValueError("Not enough candle data for EMA 15")
        df = pd.DataFrame(rates)
        ema = _calculate_ema_mt5(df, 15, "close") + 3        # adding 5 points to EMA15 to create a buffer zone for matching exact value
        logger.debug(f"[_get_ema_15]: EMA15 calculated: {ema:.2f}")
        return ema


    # ========================
    # EMA 9 CALCULATION
    # ========================
    def _get_ema_9(self,symbol) -> float:
        rates = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME, 0, 100)
        if rates is None or len(rates) < 50:
            logger.error(f"[_get_ema_9]: Not enough candle data for EMA 9 | received: {len(rates) if rates is not None else 0}")
            raise ValueError("Not enough candle data for EMA 9")
        df = pd.DataFrame(rates)
        ema = _calculate_ema_mt5(df, 9, "close")
        logger.debug(f"[_get_ema_9]: EMA9 calculated: {ema:.2f}")
        return ema 
    

    
    def _place_order(self, order_type,symbol):
        """Place market order at whatever price is available - executes immediately"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"[_place_order: {symbol}]: Failed to get tick for {symbol}")
            return None
        
        # Get current market price - whatever is available
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        
        # No SL/TP - execute at market price immediately
        logger.info(f"[_place_order: {symbol}]: Placing {direction} order at market price  | lot: {self.LOT_SIZE} | price: {price:.2f}")
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": self.LOT_SIZE,
            "type": order_type,
            "price": price,
            "sl": 0.0,  # No SL - manual management
            "tp": 0.0,  # No TP - manual management
            "deviation": 100,  # Larger deviation to ensure execution at any available price
            "magic": 10002,
            "comment": "BTCUSD EMA9/15 crossover - Market execution",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"[_place_order: {symbol}]: Order failed | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
            return None
        
        logger.info(f"[_place_order: {symbol}]: Order executed successfully | {direction} | ticket: {result.order} | executed_price: {result.price:.2f}")
        return result



    def _execute_crossover_trade(self, symbol: str, ema_9: float, ema_15: float, order_type):
        """Execute trade on EMA9/15 crossover at market price"""
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        
        # Check if position already exists
        if has_open_position(symbol):
            logger.info(f"[_execute_crossover_trade]: Crossover detected but skipping trade — open position already exists for {symbol}")
            return None
        
        # Get current market price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"[_execute_crossover_trade]: Failed to get tick for {symbol}")
            return None
        
        current_price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        logger.info(f"[_execute_crossover_trade]: Executing {direction} trade on crossover | EMA9: {ema_9:.2f} | EMA15: {ema_15:.2f} | current_price: {current_price:.2f}")
        

        # Place order at market price
        result = self._place_order(order_type,symbol)
        
        if result:
            execution_price = result.price
            logger.info(f"[_execute_crossover_trade]: Crossover trade executed successfully | {direction} | ticket: {result.order} | executed_price: {execution_price:.2f}")
            # Send email notification
            self._send_trade_execution_alert(direction, execution_price, ema_9, ema_15, result)
        else:
            logger.error(f"[_execute_crossover_trade]: Failed to execute crossover trade | {direction}")
        
        return result



    # ========================
    # PRICE TRACKER
    # ========================
    def _track_price(self,symbol):
        '''
        
        '''
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.warning(f"[_track_price]: Failed to get tick for {symbol}, retrying...")
            return

        current_price = tick.bid
        ema_15        = self._get_ema_15(symbol)
        ema_9         = self._get_ema_9(symbol)
        distance      = abs(ema_9 - ema_15)
        current_time  = datetime.now(timezone.utc)
        
        # ipdb.set_trace()
        logger.info(f"[_track_price]: Price: {current_price:.2f} | EMA9: {ema_9:.2f} | EMA15: {ema_15:.2f} | Distance: {distance:.2f}")
        previous_stock_data = mongo_client.fetch_last(query={"symbol": symbol}, collection_name="previous_ema_value")
        if previous_stock_data:
            self._prev_ema15 = previous_stock_data[0].get("ema15")
            self._prev_ema9  = previous_stock_data[0].get("ema9")

        if self._prev_ema9 is not None and self._prev_ema15 is not None:
            # Bullish crossover: EMA9 crosses above EMA15
            if ema_9 > ema_15 and self._prev_ema9 <= self._prev_ema15:
                ipdb.set_trace()
                logger.info(f"[_track_price]: *** BULLISH CROSSOVER DETECTED *** | EMA9: {ema_9:.2f} crossed above EMA15: {ema_15:.2f}")
                self._execute_crossover_trade(symbol, ema_9, ema_15, mt5.ORDER_TYPE_BUY)

            elif ema_9 < ema_15 and self._prev_ema9 >= self._prev_ema15:
                ipdb.set_trace()
                logger.info(f"[_track_price]: *** BEARISH CROSSOVER DETECTED *** | EMA9: {ema_9:.2f} crossed below EMA15: {ema_15:.2f}")
                self._execute_crossover_trade(symbol, ema_9, ema_15, mt5.ORDER_TYPE_SELL)

        else:
            logger.debug(f"[_track_price]: Previous EMA values not set for: {symbol}.")
            mongo_client.push(doc={"symbol": symbol, "ema9": ema_9, "ema15": ema_15, "timestamp": current_time}, collection_name="previous_ema_value")



    # ========================
    # MAIN LOOP
    # ========================
    def run(self):
        logger.info(
            f"[run]: stock_4H touch monitor started | for timeframe: {self.TIMEFRAME}. "
        )
        while True:
            try:
                current_time  = datetime.now(timezone.utc)
                stock_data = self.get_stocks()
                for symbol in stock_data:
                    logger.info(f"{symbol['symbol_name']}----------------------------Started----------------------------------")
                    logger.info(f"[run]: Processing symbol: {symbol['symbol_name']} datetime: {current_time}")
                    symbol_name = symbol['symbol_name']
                    self._track_price(symbol_name)
                    time.sleep(2)    
                    logger.info(f"{symbol['symbol_name']}-----------------------------Ended---------------------------------")
                time.sleep(self.POLL_INTERVAL)
            except Exception as e:
                logger.exception(f"[run]: Error in monitor loop: {e}")
            time.sleep(self.POLL_INTERVAL)



if __name__ == "__main__":
    stock = stock_tracker_4H()
    if not stock.connect():
        exit(1)
    try:
        prevent_sleep()  # Enable sleep prevention
        logger.info("[4h_crossover]: Starting Stock tracer monitor with sleep prevention enabled")
        stock.run()
        # monitor.backtest_24h()
    finally:
        allow_sleep()  # Restore normal sleep behavior
        mt5.shutdown()
        logger.info("[4h_crossover]: MT5 shutdown")
