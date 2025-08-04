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
