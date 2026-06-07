'''
                                        BTC Observation Notes.
'''
'''
1.  1 Min TF doesnt work because of the way MT5 calculates EMA. 
    It seeds with SMA of first `period` candles, so for EMA 200 you need at least 200 candles to get a valid value. 
    On 1 min TF, that means you need 200 minutes (over 3 hours) of data before your EMA 200 is valid. 
    This is why we see weird values on 1 min TF.

2.  Trade values change too fast in time between the moment we detect crossover and the moment we place order, causing us to miss trades or get bad fills.

'''


'''
                                        BTC Strategy 4h.
1. SL When 9 EMA crosses 200EMA in against side of the trade.
2. TP: 500 dollars
3. Lot size: 0.2
4. Backtested on whole 2025 year to may 2026, and working very effectively.
'''