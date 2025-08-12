'''
                                                        KEY PATTERN OBSERVATIONS                           
'''




'''
-----------------------------------------------------------------------
Key observations Self analysed:
Crypto data Trend.
-> {Day: { $in: ["Thursday","Friday"]},Pips_Moved:{$gt:5000}}
    When thursday is +ve -ie greater than 5000 pips, then friday is also +ve.

df['garman_klass_vol'] = ((np.log(df['high'])-np.log(df['low']))**2)/2-(2*np.log(2)-1)*((np.log(df['adj close'])-np.log(df['open']))**2)

garman_klass_vol:
Low: < 0.0005
Moderate: 0.0005–0.0020
High: > 0.0020

Pips_Moved:
Low: < 5,000
Moderate: 5,000–15,000
High: > 15,000

-----------------------------------------------------------------------

Key Patterns
Pattern 1: Thursday Dip → Friday Rebound
Occurred 4 times in the dataset:

2025-01-09 (Thu): -10,809 pips → 2025-01-10 (Fri): +4,784 pips.

2025-02-06 (Thu): -10,161 pips → 2025-02-07 (Fri): -6,453 pips (partial rebound failed).

2025-05-29 (Thu): -5,022 pips → 2025-05-30 (Fri): -10,005 pips (continuation).

2025-06-05 (Thu): -19,367 pips → 2025-06-06 (Fri): +6,208 pips.

Takeaway: If Thursday closes sharply negative, Friday sometimes rebounds (but not always).

Pattern 2: High Volatility on Friday = Weekend Uncertainty
Fridays with volatility > 0.0020 often preceded volatile weekends:

2025-02-28 (Fri): 0.00553 vol → Next day (Sat): -2,020 pips.

2025-03-07 (Fri): 0.00229 vol → Next day (Sat): +6,198 pips.

Implication: Traders may hedge before weekends, amplifying Friday volatility.

Pattern 3: Thursday-Friday Continuation
Trends often continued from Thursday to Friday:

2025-01-16 (Thu): -14,346 → 2025-01-17 (Fri): +16,559 (reversal).

2025-05-15 (Thu): -6,106 → 2025-05-16 (Fri): -1,158 (continuation of downtrend).

-------------------------------------------------
'''





'''
Actionable Insights
Thursday Strategy:

Watch for afternoon reversals (if Thursday opens weak, a bounce may follow Friday).

High volatility Thursdays often lead to Friday follow-through.

Friday Strategy:

Bullish bias: Fridays close positively 55% of the time.

Close positions before weekends if volatility spikes (> 0.0020).

Weekend Risk:

High Friday volatility → expect gaps on Sunday open.


-----------------------------------------------------------------------
'''