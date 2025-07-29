import pandas as pd
from logger import logger
from datetime import datetime

# Status: Working fine.
def adjust_open_close(df):
    """
    Adjusts the DataFrame by:
      - Adding 30 to the 'open' and 'close' column.

    Parameters:
        df (pd.DataFrame): The original DataFrame.

    Returns:
        pd.DataFrame: Modified DataFrame with adjusted 'open' and 'close'.
    """
    df = df.copy()  # To avoid modifying the original DataFrame

    df['open'] = df['open'] + 30
    df['close'] = df['close'] + 30

    return df



# Status:
def detect_doji(df, threshold=0.1):
    """
    Adds a column 'is_doji' to the DataFrame, marking True where a Doji is detected.
    Parameters:
    - df: Pandas DataFrame with OHLCV columns
    - threshold: The fraction of the high-low range that open-close difference must be below to be a Doji
    Returns:
    - Modified DataFrame with an additional 'is_doji' column
    """
    df = df.copy()
    body = (df['open'] - df['close']).abs()
    range_ = df['high'] - df['low']
    # Avoid division by zero
    df['is_doji'] = (range_ > 0) & (body / range_ < threshold)
    return df



# Status: Working properly.
def check_trending(symbol,df,candles = 10):
    """
    Calculate the number of pips covered and direction from a DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame containing at least 'open' and 'close' columns.

    Returns:
        tuple: (pips_covered: float, direction: str)
    """
    # Ensure the DataFrame is sorted by timestamp (just in case)
    logger.info(f"[{datetime.now()}]: Check trending for symbol: {symbol} on Candle:{candles} ")
    df = df.sort_values('timestamp')
    state = None    


    # Calculate pips
    if symbol == "BTC/USDT":
        df = df.tail(candles)
        # Get first open and last close
        first_open = float(df.iloc[0]['open'])
        last_close = float(df.iloc[-1]['close'])
        pips_covered = abs(last_close - first_open)  # 1 pip = 0.01
        if pips_covered >300:
            state = "Trending"
        elif pips_covered in range(100,200):
            state = "Consolidating."
    
    else:
        df = df.tail(5)
        # Get first open and last close
        first_open = float(df.iloc[0]['open'])
        last_close = float(df.iloc[-1]['close'])
        pips_covered = abs(last_close - first_open)  # 1 pip = 0.01
        if pips_covered >15:
            state = "Trending"
        elif pips_covered in range(5,10):
            state = "Consolidating."


    # Determine direction
    direction = "Buy" if pips_covered > 0 else "Sell"

    return {"pips_covered":pips_covered, "direction":direction, "state":state}



# Status: 
def identify_supply_demand_zones(df, lookback=3, threshold=0.003):
    """
    Identifies supply and demand zones based on recent price structure.

    Parameters:
    - df: DataFrame with OHLCV data and timestamp
    - lookback: Number of candles to look back/forward for reversals
    - threshold: Minimum price change (%) to consider a zone

    Returns:
    - A tuple of (demand_zones, supply_zones) lists
    """
    demand_zones = []
    supply_zones = []

    for i in range(lookback, len(df) - lookback):
        current_low = df.loc[i, 'low']
        current_high = df.loc[i, 'high']

        # Get previous and next lows/highs for comparison
        prev_lows = df.loc[i - lookback:i - 1, 'low']
        next_lows = df.loc[i + 1:i + lookback, 'low']
        prev_highs = df.loc[i - lookback:i - 1, 'high']
        next_highs = df.loc[i + 1:i + lookback, 'high']

        # Demand Zone: Swing Low + sharp move up
        if current_low < prev_lows.min() and current_low < next_lows.min():
            price_change = (df.loc[i + 1, 'close'] - current_low) / current_low
            if price_change >= threshold:
                demand_zones.append({
                    'timestamp': df.loc[i, 'timestamp'],
                    'price': round(current_low, 2)
                })

        # Supply Zone: Swing High + sharp move down
        if current_high > prev_highs.max() and current_high > next_highs.max():
            price_change = (current_high - df.loc[i + 1, 'close']) / current_high
            if price_change >= threshold:
                supply_zones.append({
                    'timestamp': df.loc[i, 'timestamp'],
                    'price': round(current_high, 2)
                })

    return demand_zones, supply_zones
