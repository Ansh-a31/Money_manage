import schedule
from datetime import datetime
from crypto_manage import get_previous_closed_candle, fetch_previous_data
import time
from logger import logger
# Status: Tested Working Fine.
def run_if_15_minute_multiple():

    logger.info(f" [{datetime.now()}][run_if_15_minute_multiple] ")
    now = datetime.now()
    
    if now.minute % 5 == 0:
        fetch_previous_data("15m")

# Run every minute
schedule.every(5).minutes.do(run_if_15_minute_multiple)
# print(f"After{schedule.get_jobs()}")
logger.info("Scheduler started. Waiting for 15-minute intervals...")
while True:
    schedule.run_pending()
    time.sleep(10)
