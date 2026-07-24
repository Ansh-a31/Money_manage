from Algo.btc.btc_9_15 import BTCUSD_9_15_4H
from Algo.xauusd.xauusd_9_15_4h import XAUUSD_9_15_5M_sentiment_1H
from Algo.common.common import prevent_sleep, allow_sleep
from Algo.logger import logger
import MetaTrader5 as mt5

SCRIPTS = {
    "1": ("BTC 9/15 EMA 4H",    BTCUSD_9_15_4H,              ["run", "backtest"]),
    "2": ("XAUUSD 9/15 EMA 4H", XAUUSD_9_15_5M_sentiment_1H, ["run", "backtest"]),
}

def main():
    print("\n=== Algo Trading ===")
    for key, (name, _, _modes) in SCRIPTS.items():
        print(f"  {key}. {name}")

    choice = input("\nSelect script: ").strip()
    if choice not in SCRIPTS:
        print("Invalid choice.")
        return

    name, ScriptClass, modes = SCRIPTS[choice]

    print(f"\n=== {name} ===")
    for i, mode in enumerate(modes, 1):
        print(f"  {i}. {mode}")

    mode_choice = input("\nSelect mode: ").strip()
    if not mode_choice.isdigit() or not (1 <= int(mode_choice) <= len(modes)):
        print("Invalid choice.")
        return

    mode = modes[int(mode_choice) - 1]
    bot = ScriptClass()

    if not bot.connect():
        logger.error(f"[main]: Failed to connect to MT5 for {name}")
        return

    logger.info(f"[main]: Starting {name} | mode: {mode}")
    try:
        prevent_sleep()
        if mode == "run":
            bot.run()
        elif mode == "backtest":
            start_date = input("Start date (YYYY-MM-DD): ").strip()
            end_date   = input("End date   (YYYY-MM-DD): ").strip()
            bot.backtest(start_date, end_date)
    finally:
        allow_sleep()
        mt5.shutdown()
        logger.info(f"[main]: {name} stopped. MT5 shutdown.")

if __name__ == "__main__":
    main()
