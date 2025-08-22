import pandas as pd
from logger import logger
from datetime import datetime
import numpy as np
from mongo.mongo_client import push_many

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
    try:
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
    except Exception as e:
        logger.error(f"[{datetime.now()}][check_trending] error due to :{e}.")
        return {"pips_covered":0, "direction":"Unknown", "state":"Error"}


# Status: Not working porperly.
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


# Status: Working properly.
def analyze_daily_movement(df):
    '''
    It analyze week days movements and saves the results to MongoDB and CSV.
    '''
    logger.info(f"[{datetime.now()}]: [analyze_daily_movement] Starting analysis.")
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create date and day columns
    df['Date'] = pd.to_datetime(df['timestamp'].dt.date)
    df['Day'] = df['timestamp'].dt.day_name()

    # Group by each date
    daily_summary = df.groupby('Date').agg(
        first_open=('open', 'first'),
        last_close=('close', 'last'),
        Day=('Day', 'first')
    ).reset_index()

    # Calculate movement and direction
    daily_summary['Pips_Moved'] = (daily_summary['last_close'] - daily_summary['first_open']) * 100  # convert to pips
    daily_summary['Price_Movement'] = daily_summary['Pips_Moved'].apply(lambda x: '+ve' if x >= 0 else '-ve')
    # Reorder and rename columns
    daily_summary['garman_klass_vol'] = ((np.log(df['high'])-np.log(df['low']))**2)/2-(2*np.log(2)-1)*((np.log(df['close'])-np.log(df['open']))**2)
    final_df = daily_summary[['Date', 'Day', 'Price_Movement', 'Pips_Moved',"garman_klass_vol"]]
    push_dataframe_to_mongo(final_df,"week_data")
    final_df.to_csv("data_analyze.csv", index=False)
    logger.info(f"[{datetime.now()}]: [analyze_daily_movement] Data analysis finished, CSV created.")
    return final_df



def processing_hourly_movement(df):
    '''
    It analyze week days movements and saves the results to MongoDB and CSV.
    '''
    logger.info(f"[{datetime.now()}]: [processing_hourly_movement] Starting analysis.")
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create date and day columns
    df['Hour'] = df['timestamp'].dt.floor('h')
    df['Hour'] = df['Hour'].dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    df['Day'] = df['timestamp'].dt.day_name()

    # Group by each date
    hourly_summary = df.groupby('Hour').agg(
        first_open=('open', 'first'),
        last_close=('close', 'last'),
        high_max=('high', 'max'),
        low_min=('low', 'min'),
        Day=('Day', 'first')
    ).reset_index()

    # Calculate movement and direction
    hourly_summary['Pips_Moved'] = (hourly_summary['last_close'] - hourly_summary['first_open']) * 100  # convert to pips
    hourly_summary['Price_Movement'] = hourly_summary['Pips_Moved'].apply(lambda x: '+ve' if x >= 0 else '-ve')
    # Reorder and rename columns
    hourly_summary['garman_klass_vol'] = np.sqrt(
    0.5 * (np.log(hourly_summary['high_max'] / hourly_summary['low_min']) ** 2)
    - (2 * np.log(2) - 1) * (np.log(hourly_summary['last_close'] / hourly_summary['first_open']) ** 2)
    )

    final_df = hourly_summary[['Hour', 'Day', 'Price_Movement', 'Pips_Moved', 'garman_klass_vol']]
    push_dataframe_to_mongo(final_df,"hourly_data")
    final_df.to_csv("1h_analyze.csv", index=False, date_format='%Y-%m-%dT%H:%M:%SZ')
    logger.info(f"[{datetime.now()}]: [processing_hourly_movement] Data analysis finished, CSV created.")
    return final_df




# Status: Working properly.
def push_dataframe_to_mongo(df,collection_name):
    '''
    Pushes a DataFrame to MongoDB collection 'week_data'.
    '''
    try:
        logger.info(f"[{datetime.now()}]: [push_dataframe_to_mongo] Pushing data to mongo.")
        df = df.copy()

        # Convert DataFrame to list of dictionaries
        records = df.to_dict(orient='records')

        # Insert records if available
        if records:
            result = push_many(records, collection_name)
            logger.info(f"[{datetime.now()}]: [push_dataframe_to_mongo] Inserted documents into MongoDB collection: week_data")
        else:
            logger.warning(f"[{datetime.now()}]: [push_dataframe_to_mongo] No records to insert into MongoDB.")
    except Exception as e:
        logger.error(f"[{datetime.now()}]: [push_dataframe_to_mongo]  Error inserting into MongoDB: {e}")
