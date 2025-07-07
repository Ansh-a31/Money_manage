import pandas as pd



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



# Status: Not tested properly.
def check_trending(df,candles = 10):
    """
    Calculate the number of pips covered and direction from a BTC DataFrame.

    Parameters:
        df (pd.DataFrame): DataFrame containing at least 'open' and 'close' columns.

    Returns:
        tuple: (pips_covered: float, direction: str)
    """
    # Ensure the DataFrame is sorted by timestamp (just in case)
    df = df.sort_values('timestamp')
    df = df.tail(candles)
    state = None

    # Get first open and last close
    first_open = df.iloc[0]['open']
    last_close = df.iloc[-1]['close']

    # Calculate pips
    pips_covered = (last_close - first_open)  # 1 pip = 0.01
    if abs(pips_covered) >300:
        state = "Trending"
    elif abs(pips_covered) in [100,200]:
        state = "Trapped."
    
    # Determine direction
    direction = "Buy" if pips_covered > 0 else "Sell"

    return pips_covered, direction, state


