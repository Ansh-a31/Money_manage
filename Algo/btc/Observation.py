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