import time
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz

from Algo.common.common import _calculate_ema_mt5, prevent_sleep, allow_sleep
from Algo.credentials import login, password, server
from Algo.logger import logger
from communication.send_email import send_email_price_alert
from database import mongo_client


TIMEFRAME    = mt5.TIMEFRAME_M15
NUM_CANDLES = 100
LOT_SIZE = 0.01
TP_POINTS = 200.0
SL_POINTS = 25.0

prev_9_ma = None
prev_21_ma = None

def connect_mt5() -> bool:
    if not mt5.initialize():
        logger.error(f"[connect_mt5]: MT5 init failed: {mt5.last_error()}")
        return False
    if not mt5.login(login, password, server):
        logger.error(f"[connect_mt5]: MT5 login failed: {mt5.last_error()}")
        return False
    return True


def calculate_ma(symbol_data: pd.DataFrame, period: int, close_col: str = "close") -> float:
    """
    Calculates and returns the latest Moving Average (EMA) value for the specified period.
    """
    if symbol_data is None or len(symbol_data) < period:
        logger.error(f"[calculate_ma]: Not enough data to calculate MA {period} | received: {len(symbol_data) if symbol_data is not None else 0}")
        return None
        
    close_prices = symbol_data[close_col].astype(float).values
    ma = round(float(close_prices[-period:].mean()), 5)
    logger.info(f"[calculate_ma]: MA{period} calculated: {ma:.2f}")
    return ma


def _send_trade_execution_alert(direction: str):
        """Send email notification when trade is executed"""
        # Calculate SL and TP from execution price
        
        msg = (
            f"xauusd Trade Executed!\n\n"
            f"Direction: {direction}\n",
            f"Lot Size: {LOT_SIZE}\n",
            f"Time: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d %H:%M:%S')}\n",
            )
        # logger.info(f"[_send_trade_execution_alert]: Sending trade execution email | {direction} | ticket: {result.order} | price: {execution_price:.2f}")
        send_email_price_alert(msg)
        # logger.info(f"[_send_trade_execution_alert]: Trade execution email sent successfully | {direction} | ticket: {result.order}")


def get_symbol_data(symbol: str, timeframe: int, num_candles: int):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_candles)
    if rates is None or len(rates) == 0:
        logger.error(f"[get_symbol_data]: Failed to retrieve data for {symbol}: {mt5.last_error()}")
        return None
    return pd.DataFrame(rates)


def close_all_positions(symbol: str):
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        logger.info(f"[close_all_positions]: No open positions for {symbol}")
        return

    for pos in positions:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"[close_all_positions]: Failed to get tick for {symbol} | ticket: {pos.ticket}")
            continue

        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price      = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action":      mt5.TRADE_ACTION_DEAL,
            "symbol":      symbol,
            "volume":      pos.volume,
            "type":        order_type,
            "position":    pos.ticket,
            "price":       price,
            "deviation":   100,
            "magic":       pos.magic,
            "comment":     "close all positions",
            "type_time":   mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"[close_all_positions]: Failed to close ticket {pos.ticket} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
        else:
            logger.info(f"[close_all_positions]: Closed ticket {pos.ticket} | price: {price:.2f}")


def _place_order(SYMBOL,order_type):
        """Place market order at whatever price is available - executes immediately"""
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None:
            logger.error(f"[_place_order]: Failed to get tick for {SYMBOL}")
            return None
        
        # Get current market price - whatever is available
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        direction = "BUY" if order_type == mt5.ORDER_TYPE_BUY else "SELL"
        tp = round(price + TP_POINTS, 2) if order_type == mt5.ORDER_TYPE_BUY else round(price - TP_POINTS, 2)
        sl = round(price - SL_POINTS, 2) if order_type == mt5.ORDER_TYPE_BUY else round(price + SL_POINTS, 2)
        logger.info(f"[_place_order]: Placing {direction} order at market price | symbol: {SYMBOL} | lot: {LOT_SIZE} | price: {price:.2f} | TP: {tp:.2f} | SL: {sl:.2f}")
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": LOT_SIZE,
            "type": order_type,
            "price": price,
            "sl": 0.0,  # No SL - manual management
            "tp": tp,   # 50 dollars Take Profit
            "deviation": 100,  # Larger deviation to ensure execution at any available price
            "magic": 10003,
            "comment": "Script trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"[_place_order]: Order failed | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
            return None
        _send_trade_execution_alert("BUY")
        reason = f"Crossover at 1 Min trade executed. Direction: {direction}"
        mongo_client.push(doc={"symbol": SYMBOL, "reason": reason, "created_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")}, collection_name="instant_trade")
        time.sleep(5)  # Sleep for 5 seconds to ensure order execution is processed
        logger.info(f"[_place_order]: Order executed successfully | {direction} | ticket: {result.order} | executed_price: {result.price:.2f}")
        return result


def global_stock_analyzer(symbol):
    global prev_9_ma, prev_21_ma
    # symbols = get_specific_symbols()
    # import ipdb;ipdb.set_trace()
    order_placed = None
    if symbol:
        logger.info(f"[main]: Processing symbol: {symbol}")

        symbol_data = get_symbol_data(symbol, TIMEFRAME, NUM_CANDLES)
        if symbol_data is not None:
            ma_9 = calculate_ma(symbol_data, 9)
            ma_21 = calculate_ma(symbol_data, 21)
            if ma_9 is None or ma_21 is None:
                return

            if prev_9_ma is not None and prev_21_ma is not None:
                if ma_9 > ma_21 and prev_9_ma <= prev_21_ma:

                    # for refying the direction and order type
                    time.sleep(30)  # Sleep for 30 seconds to ensure the crossover is confirmed
                    ma_9 = calculate_ma(symbol_data, 9)
                    ma_21 = calculate_ma(symbol_data, 21)
                    if ma_9 > ma_21 and prev_9_ma <= prev_21_ma:
                        logger.info(f"[_execute_crossover_trade]: Re-Confirmed crossover for {symbol}. Current MA9: {ma_9:.2f}, MA21: {ma_21:.2f}")
                        direction = "BUY"
                        target_type = mt5.ORDER_TYPE_BUY
                        positions = mt5.positions_get(symbol=symbol)
                        if positions:
                            if any(pos.type == target_type for pos in positions):
                                logger.info(f"[_execute_crossover_trade]: Open {direction} position already exists, skipping.")
                                return None
                            else:
                                close_all_positions(symbol)
                                logger.info(f"[_execute_crossover_trade]: Opposite position closed, proceeding with {direction}.")
                                order_placed = _place_order(symbol, target_type)
                        else:
                            order_placed = _place_order(symbol, target_type)
                    else:
                        logger.info(f"[_execute_crossover_trade]: Crossover not confirmed for {symbol}. Current MA9: {ma_9:.2f}, MA21: {ma_21:.2f}")
                elif ma_9 < ma_21 and prev_9_ma >= prev_21_ma:

                    # for refying the direction and order type
                    time.sleep(30)  # Sleep for 30 seconds to ensure the crossover is confirmed
                    ma_9 = calculate_ma(symbol_data, 9)
                    ma_21 = calculate_ma(symbol_data, 21)
                    if ma_9 < ma_21 and prev_9_ma >= prev_21_ma:
                        logger.info(f"[_execute_crossover_trade]: Re-Confirmed crossover for {symbol}. Current MA9: {ma_9:.2f}, MA21: {ma_21:.2f}")
                        direction = "SELL"
                        target_type = mt5.ORDER_TYPE_SELL
                        positions = mt5.positions_get(symbol=symbol)
                        if positions:
                            if any(pos.type == target_type for pos in positions):
                                logger.info(f"[_execute_crossover_trade]: Open {direction} position already exists, skipping.")
                                return None
                            else:
                                close_all_positions(symbol)
                                logger.info(f"[_execute_crossover_trade]: Opposite position closed, proceeding with {direction}.")
                                order_placed = _place_order(symbol, target_type)
                        else:
                            order_placed = _place_order(symbol, target_type)
                    else:
                        logger.info(f"[_execute_crossover_trade]: Crossover not confirmed for {symbol}. Current MA9: {ma_9:.2f}, MA21: {ma_21:.2f}")
                else:
                    logger.info(f"[_execute_crossover_trade]: No crossover detected for {symbol}. Current MA9: {ma_9:.2f}, MA21: {ma_21:.2f}")
            else:
                logger.warning(f"[main]: No previous data available for symbol: {symbol}")
            if order_placed:
                mongo_client.push(doc={"symbol": symbol, "ema9": ma_9, "ema21": ma_21, "direction": direction, "created_at": datetime.now(pytz.timezone("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")}, collection_name="crossover_detected")
            prev_9_ma = ma_9
            prev_21_ma = ma_21
    else:
        logger.warning("[main]: No symbols retrieved.")


def handle_trailing_sl(position):
    symbol = position.symbol
    # volume = position.volume
    open_price = position.price_open
    is_buy = position.type == mt5.POSITION_TYPE_BUY

    current_profit = position.profit
    logger.info(f"[handle_trailing_sl]: Current profit for {symbol} | sl: {position.sl} | profit: {current_profit:.2f}")

    if current_profit > 90:
        if is_buy:
            new_sl = open_price + 80
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 80
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 80:
        if is_buy:
            new_sl = open_price + 70
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 70
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 70:
        if is_buy:
            new_sl = open_price + 60
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 60
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 60:
        if is_buy:
            new_sl = open_price + 50
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 50
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 50:
            if is_buy:
                new_sl = open_price + 40
                if position.sl < new_sl:
                    modify_request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": symbol,
                        "sl": new_sl,
                        "position": position.ticket,
                        "tp":       position.tp,
                    }
                    result = mt5.order_send(modify_request)
                    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                        logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                    else:
                        logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")
    
            else:
                new_sl = open_price - 40
                if position.sl > new_sl:
                    modify_request = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "symbol": symbol,
                        "sl": new_sl,
                        "position": position.ticket,
                        "tp":       position.tp,
                    }
                    result = mt5.order_send(modify_request)
                    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                        logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                    else:
                        logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 40:
        if is_buy:
            new_sl = open_price + 30
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 30
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 30:
        if is_buy:
            new_sl = open_price + 15
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 15
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

    elif current_profit > 20:
        if is_buy:
            new_sl = open_price + 5
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 5
            if position.sl > new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")
    
    elif current_profit > 10:
        if is_buy:
            new_sl = open_price + 1
            if position.sl < new_sl:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")

        else:
            new_sl = open_price - 1
            if position.sl > new_sl or position.sl == 0.0:
                modify_request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": symbol,
                    "sl": new_sl,
                    "position": position.ticket,
                    "tp":       position.tp,
                }
                result = mt5.order_send(modify_request)
                if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                    logger.error(f"[handle_trailing_sl]: Failed to modify SL for {symbol} | retcode: {result.retcode if result else 'None'} | error: {mt5.last_error()}")
                else:
                    logger.info(f"[handle_trailing_sl]: SL modified for {symbol} | new SL: {new_sl:.2f}")


if __name__ == "__main__":
    if not connect_mt5():
        logger.error("[main]: Failed to connect to MT5. Exiting.")
        exit(1)

    try:
        prevent_sleep()
        while True:
            
            global_stock_analyzer("XAUUSDz")
            positions = mt5.positions_get(symbol="XAUUSDz")
            if positions:
                for pos in positions: 
                    handle_trailing_sl(pos)  # Assuming only one position for simplicity
            # _place_order("BTCUSDz", mt5.ORDER_TYPE_BUY)
            logger.info("[main]: Sleeping for 300 seconds before next analysis.")
            logger.info("[main]:-------------------------------------------------------------------------------------------------")
            time.sleep(300)  # Sleep for 5 seconds before next analysis
    except Exception as e:
        logger.exception(f"[main]: Exception occurred: {e}")
    finally:
        allow_sleep()
        mt5.shutdown()
        logger.info("[main]: MT5 shutdown complete")
