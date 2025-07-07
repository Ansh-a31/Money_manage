from cry.service import check_trending, detect_doji, adjust_open_close
import time
import ccxt
import pandas as pd
from datetime import datetime
from logger import logger
from send_email import send_email_report


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
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nStopped live feed.")
        df = pd.DataFrame(data, columns=['timestamp', 'price', 'bid', 'ask'])

        print("Saved final data to 'final_live_btc_price.csv'")

# continuous_live_data()




def get_previous_closed_candle(symbol='BTC/USDT', timeframe='15m'):
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
        
        df = detect_doji(df)
        if df["is_doji"].items() == True:
            created_time = df["timestamp"][0]
            email_msg = f"Doji created in Symbol {symbol}, at: [{created_time}]."
            logger.info(f"Email Send: {email_msg}")
            send_email_report(email_msg)
        print(df)

    except Exception as e:
        logger.error(f"[{datetime.now()}][get_previous_closed_candle] error due to :{e}.")
        get_previous_closed_candle()
        time.sleep(30)


# get_previous_closed_candle()



def fetch_previous_data():
    exchange = ccxt.binance()
    # Load markets (needed to initialize market symbols properly)
    exchange.load_markets()

    symbol = 'BTC/USDT'

    # Fetch the current ticker (includes last price, bid, ask, etc.)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=30)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms',utc = True)
    df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
    df = adjust_open_close(df)
    # df.to_csv('btc_ohlcv_1m.csv', index=False)

    # Print relevant data
    print(f"Symbol: {symbol}")
    print(detect_doji(df))
    print(check_trending(df))
    

fetch_previous_data()