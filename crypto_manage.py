from cry.service import check_trending, detect_doji, adjust_open_close
import time
import ccxt
import pandas as pd
from datetime import datetime
from logger import logger
from send_email import send_email_report
from mongo.mongo_client import push_mongo,fetch_last

# Status: Not working properly.
def continuous_live_data(interval=5):
    """
    Fetches live BTC/USDT price every few seconds.
    
    Parameters:
    - interval: Polling interval in seconds (default: 5s)
    """
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'
    data = []

    print("Streaming live BTC/USDT price. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            ticker = exchange.fetch_ticker(symbol)
            
            timestamp = pd.to_datetime(ticker['timestamp'], unit='ms', utc=True).tz_convert('Asia/Kolkata')
            price = ticker['last']
            open = ticker["open"]
            
            # print(f"[{timestamp}] Price: {price} | Open: {open}")
            
            data.append([timestamp, price, open])
            
            # Optional: Save live data to CSV
            df = pd.DataFrame(data, columns=['timestamp', 'price', 'open'])
            # df.to_csv('live_btc_price.csv', index=False)
            print(df)
            # time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nStopped live feed.")
        df = pd.DataFrame(data, columns=['timestamp', 'price', 'bid', 'ask'])

        print("Saved final data to 'final_live_btc_price.csv'")

# continuous_live_data()




def get_previous_closed_candle_status(symbol='BTC/USDT', timeframe='15m'):
    """
    Fetches the just-closed (previous) candle for the given symbol and timeframe.

    Returns:
    - A dictionary with candle data: timestamp, open, high, low, close, volume
    """
    try:
        logger.info(f"[{datetime.now()}] [get_previous_closed_candle]")
        
        exchange = ccxt.binance()
        exchange.load_markets()
        # Fetch last 2 candles: current (still forming) + previous (fully closed)
        candles = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=2)

        # Get the previous fully-closed candle (2nd last one)
        prev_candle = candles[-2]
        # Convert to DataFrame row for clarity
        df = pd.DataFrame([prev_candle], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True).dt.tz_convert('Asia/Kolkata')
        df = adjust_open_close(df)
        df = detect_doji(df)
        if df["is_doji"].items() == True:
            created_time = df["timestamp"][0]
            email_msg = f"Doji created in Symbol {symbol}, at: [{created_time}]."
            logger.info(f"Email Send: {email_msg}")
            send_email_report(email_msg)
        print(df)

    except Exception as e:
        logger.error(f"[{datetime.now()}][get_previous_closed_candle] error due to :{e}.")
        get_previous_closed_candle_status()
        time.sleep(30)

# get_previous_closed_candle_status()



def fetch_previous_data(time_frame):
    '''
    Function first check check trending and for 15 min, if found not trending then check trending for 1h.
        
    '''
    try:
        logger.info(f"[{datetime.now()}] [fetch_previous_data]")
        exchange = ccxt.binance()
        # Load markets (needed to initialize market symbols properly)
        exchange.load_markets()

        symbol = 'ETH/USDT'
        # Fetch the current ticker (includes last price, bid, ask, etc.)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe= time_frame, limit=30)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms',utc = True)
        df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
        df = adjust_open_close(df)
        # df.to_csv('btc_ohlcv_1m.csv', index=False)

        # Print relevant data
        print(f"Symbol: {symbol}")
        print(f"timeframe:{time_frame}")
        # print(detect_doji(df))
        is_trending =check_trending(symbol,df)
        print(is_trending)

        if is_trending.get("state") == "Trending":
            created_time = datetime.time(datetime.now())
            trending_direction = is_trending.get("direction")
            email_msg = f"{symbol} currently trending in {trending_direction} on TF: {time_frame}, at: [{created_time}]."
            logger.info(f"Email Send: {email_msg}")
            # send_email_report(email_msg)
            msg = {
                "symbol":symbol,
                "trending_direction":trending_direction,
                "time_frame": time_frame,
                "email_message":email_msg
            }
            push_mongo(msg)
        # print(df)
        
        elif time_frame == "15m" and is_trending.get("state") != "Trending":
            fetch_previous_data("1h")
    except Exception as e:
        logger.error(f"[{datetime.now()}][fetch_previous_data] error due to :{e}.")
        fetch_previous_data("15m")
        time.sleep(30)

fetch_previous_data("15m")