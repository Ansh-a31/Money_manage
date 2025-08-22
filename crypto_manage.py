from cry.service import check_trending, detect_doji, adjust_open_close, analyze_daily_movement, processing_hourly_movement
import time
import ccxt
import pandas as pd
from datetime import datetime
from logger import logger
from send_email import send_email_report
from mongo.mongo_client import push_mongo,delete_data_mongo
from utils import days_since_start_of_year

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

# Status: Working properly.
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


# Status: Working properly.
def data_loader(symbol,time_frame,week_day_analysis=False):
    '''
    Loads historical OHLCV data for the given symbol and timeframe.
    Returns a DataFrame with timestamp, open, high, low, close, volume.
    If week_day_analysis is True, it will also analyze week days  movements.
    '''
    try:
        logger.info(f"[{datetime.now()}] [data_loader]. Loading basic data.")
        print(f"Symbol: {symbol}")
        print(f"timeframe:{time_frame}")
        exchange = ccxt.binance()
        # Load markets (needed to initialize market symbols properly)
        exchange.load_markets()
        
        candles = days_since_start_of_year() if time_frame == "1d" else 1000
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe= time_frame, limit=candles)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms',utc = True)
        df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')
        df = adjust_open_close(df)
        if week_day_analysis and time_frame == "1h":
            delete_data_mongo("","hourly_data")
            processing_hourly_movement(df)
        elif week_day_analysis and time_frame == "1d":
            delete_data_mongo()
            analyze_daily_movement(df)
        return df
    except Exception as e:
        logger.error(f"[{datetime.now()}]: [data_loader] error due to :{e}.")
        data_loader(time_frame,week_day_analysis)
        time.sleep(30)


# Status: Working properly.
def adaptive_trend_check(time_frame):
    '''
    Function first check check trending and for 15 min, if found not trending then check trending for 1h.
    '''
    try:
        logger.info(f"[{datetime.now()}] [adaptive_trend_check]")
        symbol = 'ETH/USDT'
        
        df = data_loader(symbol, time_frame,week_day_analysis=True)

        is_trending =check_trending(symbol,df)
        print(is_trending)

        if is_trending.get("state") == "Trending":
            created_time = datetime.time(datetime.now())
            trending_direction = is_trending.get("direction")
            email_msg = f"{symbol} currently trending in {trending_direction} on TF: {time_frame}, at: [{created_time}]."
            logger.info(f"Email Send: {email_msg}")
            # send_email_report(email_msg)
            db_data = {
                "symbol":symbol,
                "trending_direction":trending_direction,
                "time_frame": time_frame,
                "email_message":email_msg
            }
            push_mongo(db_data)
        # print(df)
        
        elif time_frame == "15m" and is_trending.get("state") != "Trending":
            adaptive_trend_check("1h")
        

    except Exception as e:
        logger.error(f"[{datetime.now()}][adaptive_trend_check] error due to :{e}.")
        adaptive_trend_check("15m")
        time.sleep(30)

adaptive_trend_check("1h")


