

import ccxt
import pandas as pd

from cry.service import detect_doji


def fetch_previous_data():
    exchange = ccxt.binance()
    # Load markets (needed to initialize market symbols properly)
    exchange.load_markets()

    symbol = 'BTC/USDT'

    # Fetch the current ticker (includes last price, bid, ask, etc.)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=5)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms',utc = True)
    df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Kolkata')

    # df.to_csv('btc_ohlcv_1m.csv', index=False)

    # Print relevant data
    print(f"Symbol: {symbol}")
    print(df)
    print(detect_doji(df))


fetch_previous_data()