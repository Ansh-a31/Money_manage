'''
                                                            KEY PATTERN OBSERVATIONS                           

'''


"""
--------------------------------------------------------------------------------------------------------------
   Confirmed observation  and strategy
--------------------------------------------------------------------------------------------------------------

Strategy1: Volatility-Based Mean Reversion   ->  Can be considered as 9/19 testcases are correct.
Trigger:
   If garman_klass_vol > 0.002 (high volatility) AND today’s move is > ±10,000 pips.  
Action:
   Bet on opposite direction next day (e.g., if today was -20,000 pips, go long tomorrow).
Stop-Loss:
   1.5x today’s volatility (e.g., if vol=0.003, SL = ±4,500 pips).


Strategy2: Only for Friday          ->        Working fine as 7/9 testcases are correct.
Trigger:
   When thursday is +ve -ie greater than 5000 pips, then friday is also +ve.
   You can combine it with strategy 1 for better results.
   
   
Strategy3: Only For Wednesday       ->       Working fine as 9/11 testcases are correct.
Trigger:
   If Tuesday was negative (< -3,000 pips), then Wednesday tends to rebound (+ve).
   

--------------------------------------------------------------------------------------------------------------
"""



'''
-----------------------------------------------------------------------
Self analysed Key observations :
Crypto data Trend.
-> {Day: { $in: ["Thursday","Friday"]},Pips_Moved:{$gt:5000}}
    When thursday is +ve -ie greater than 5000 pips, then friday is also +ve.

df['garman_klass_vol'] = ((np.log(df['high'])-np.log(df['low']))**2)/2-(2*np.log(2)-1)*((np.log(df['adj close'])-np.log(df['open']))**2)

garman_klass_vol:
Low: < 0.001
Moderate: 0.0001–0.0030
High: > 0.003

Pips_Moved:
Low: < 5,000
Moderate: 5,000–15,000
High: > 15,000

-----------------------------------------------------------------------
'''

   

'''   
------------------------------------------------------------------------

### **🔥 Golden Rules**  
1. **Always check volatility (GK vol)**:  
   - High (>0.0020) = Be careful, big moves possible.  
   - Low (<0.0010) = Small, predictable moves.  
2. **Weekend = Danger Zone**:  
   - Avoid holding big positions over Sunday.  
3. **Wednesday = Best Day to Buy**  
4. **Sunday = Best Day to Short**  

This is a **simple, rule-based strategy** based on past trends. Always use stop-losses and adjust for news/events! 🚀  

Would you like a **quick summary table** for easy reference?
--------------------------------------------------------------------------------
'''
