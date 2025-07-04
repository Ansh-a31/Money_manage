import pandas as pd
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