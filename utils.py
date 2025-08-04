from datetime import date
import csv
from collections import defaultdict
from io import StringIO


# Status: Working Properly
def days_since_start_of_year():
    today = date.today()
    start_of_year = date(today.year, 1, 1)
    return (today - start_of_year).days + 1  # +1 to include today

# Example usage:
# print(days_since_start_of_year())


def data(df):
    import ipdb;ipdb.set_trace()
    df['Day'] = df['Day'].str.lower()
    df['Price_Movement'] = df['Price_Movement'].str.strip()

    # Group and count
    summary = df.groupby(['Day', 'Price_Movement']).size().unstack(fill_value=0)

    # Ensure both +ve and -ve columns exist for all days
    for col in ['+ve', '-ve']:
        if col not in summary.columns:
            summary[col] = 0

    # Convert to dictionary
    result = summary[['+ve', '-ve']].astype(int).to_dict(orient='index')

    # Output the result
    import pprint
    pprint.pprint(result)    

# a= data()
# print(a)