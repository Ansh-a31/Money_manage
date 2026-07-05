import MetaTrader5 as mt5
from Algo.logger import logger


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
