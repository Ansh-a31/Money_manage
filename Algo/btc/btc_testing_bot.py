#  For testing purposes only, not for production use
import time
import MetaTrader5 as mt5
from communication.send_email import send_email_price_alert
from Algo.btc.btc_service import place_market_order


# def check_place_market_order():
#     symbol = "BTCUSDz"
#     lot = 0.1
#     order_type = mt5.ORDER_TYPE_BUY
#     crossover_price = 76300  # You can set this to a specific price if you want to test SL/TP calculation
#     result = place_market_order(symbol, order_type, lot, crossover_price)
#     if result is not None:
#         print(f"Market order placed successfully: {result}")
#     else:
#         print("Failed to place market order") 



# send_email_price_alert("Test email from BTC bot")



if __name__ == "__main__":
    if mt5.initialize():
        print("MT5 initialized successfully")
        send_email_price_alert("Test email from BTC bot")
        mt5.shutdown()
    else:
        print(f"Failed to initialize MT5: {mt5.last_error()}")