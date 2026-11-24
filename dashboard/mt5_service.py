from datetime import datetime, time
import MetaTrader5 as mt5
import pandas as pd


def ensure_mt5_connected() -> bool:
    """Ensures MT5 terminal is initialized and connected."""
    try:
        if mt5.terminal_info() is not None:
            return True
        if not mt5.initialize():
            try:
                from Algo.credentials import login, password, server
                return bool(mt5.initialize(login=login, password=password, server=server))
            except Exception:
                return False
        try:
            from Algo.credentials import login, password, server
            mt5.login(login, password, server)
        except Exception:
            pass
        return True
    except Exception:
        return False


def get_total_profit(from_date, to_date, symbol=None, magic=None):
    """
    Calculate total net profit between from_date and to_date.
    Derives directly from get_symbol_wise_performance for 100% consistency.
    """
    summary = get_symbol_wise_performance(from_date, to_date, magic=magic)
    if summary is None or summary.empty:
        return 0.0
    if symbol:
        summary = summary[summary['symbol'] == symbol]
        if summary.empty:
            return 0.0
    return round(float(summary['net_profit'].sum()), 2)


def get_overview_metrics(from_date, to_date, symbol=None, magic=None):
    """
    Calculates top overview metrics directly from get_symbol_wise_performance,
    guaranteeing 100% mathematical consistency with the pairs traded table.
    """
    summary = get_symbol_wise_performance(from_date, to_date, magic=magic)

    if summary is None or summary.empty:
        return {
            "status": "success",
            "from_date": str(from_date),
            "to_date": str(to_date),
            "symbol": symbol,
            "magic": magic,
            "net_profit": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "message": "No closed trades found in the given period"
        }

    if symbol:
        summary = summary[summary['symbol'] == symbol]
        if summary.empty:
            return {
                "status": "success",
                "from_date": str(from_date),
                "to_date": str(to_date),
                "symbol": symbol,
                "magic": magic,
                "net_profit": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "message": f"No trades found for symbol {symbol}"
            }

    # 1. Total Net Profit strictly equal to sum of symbol net_profits
    total_profit = round(float(summary['net_profit'].sum()), 2)

    # 2. Total Trades & Overall Win Rate
    total_trades = int(summary['total_trades'].sum())
    total_winning = int(summary['winning_trades'].sum())
    win_rate = round((total_winning / total_trades) * 100, 2) if total_trades > 0 else 0.0

    # 3. Overall Profit Factor from aggregate gross profit / gross loss
    gross_profit = float(summary['gross_profit'].sum()) if 'gross_profit' in summary.columns else 0.0
    gross_loss = float(summary['gross_loss'].sum()) if 'gross_loss' in summary.columns else 0.0
    if gross_loss > 0:
        profit_factor = round(gross_profit / gross_loss, 1)
    else:
        profit_factor = round(gross_profit, 1) if gross_profit > 0 else 0.0

    return {
        "status": "success",
        "from_date": str(from_date),
        "to_date": str(to_date),
        "symbol": symbol,
        "magic": magic,
        "net_profit": total_profit,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": total_trades
    }


def get_symbol_wise_performance(from_date, to_date, magic=None):
    """
    Returns symbol-wise performance:
    - Total Trades
    - Win Rate
    - Net P/L
    - Profit Factor
    """
    if not ensure_mt5_connected():
        print("Failed to connect to MT5")
        return None
    
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None or len(deals) == 0:
        print("No deals found")
        return None
    
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    
    # Filter by magic if needed
    if magic is not None:
        df = df[df['magic'] == magic]
    
    # Keep only real trades (remove balance/credit operations)
    df = df[df['symbol'] != '']
    
    # We only care about closing deals (entry = 1) for P/L
    closes = df[df['entry'] == 1].copy()
    
    if closes.empty:
        print("No closed trades found")
        return None
    
    # Net profit per deal
    closes['net_profit'] = closes['profit'] + closes['commission'] + closes['swap']
    
    # Group by symbol
    summary = closes.groupby('symbol').agg(
        total_trades=('net_profit', 'count'),
        net_profit=('net_profit', 'sum'),
        winning_trades=('net_profit', lambda x: (x > 0).sum()),
        losing_trades=('net_profit', lambda x: (x < 0).sum()),
        gross_profit=('net_profit', lambda x: float(x[x > 0].sum())),
        gross_loss=('net_profit', lambda x: float(abs(x[x < 0].sum())))
    ).reset_index()
    
    # Calculate Win Rate & Profit Factor per symbol
    summary['win_rate'] = (summary['winning_trades'] / summary['total_trades'] * 100).round(2)
    summary['net_profit'] = summary['net_profit'].round(2)
    summary['profit_factor'] = summary.apply(
        lambda r: round(r['gross_profit'] / r['gross_loss'], 1) if r['gross_loss'] > 0 else (round(r['gross_profit'], 1) if r['gross_profit'] > 0 else 0.0),
        axis=1
    )
    
    # Sort by highest profit
    summary = summary.sort_values('net_profit', ascending=False).reset_index(drop=True)
    
    return summary


SAMPLE_PAIRS_DATA = [
    {"pair": "EUR/USD", "trades": 96, "win_rate": 63.0, "profit_factor": 2.1, "net_pnl": 2840.0, "net_pnl_formatted": "+$2,840", "action_text": "Open calendar >", "action_primary": True},
    {"pair": "XAU/USD", "trades": 48, "win_rate": 60.0, "profit_factor": 2.4, "net_pnl": 4310.0, "net_pnl_formatted": "+$4,310", "action_text": "View >", "action_primary": False},
    {"pair": "NAS100",  "trades": 71, "win_rate": 57.0, "profit_factor": 1.6, "net_pnl": 1780.0, "net_pnl_formatted": "+$1,780", "action_text": "View >", "action_primary": False},
    {"pair": "BTC/USD", "trades": 37, "win_rate": 54.0, "profit_factor": 1.3, "net_pnl": 960.0,  "net_pnl_formatted": "+$960",   "action_text": "View >", "action_primary": False},
    {"pair": "USD/JPY", "trades": 33, "win_rate": 45.0, "profit_factor": 0.8, "net_pnl": -430.0, "net_pnl_formatted": "-$430",   "action_text": "View >", "action_primary": False},
    {"pair": "GBP/JPY", "trades": 27, "win_rate": 41.0, "profit_factor": 0.6, "net_pnl": -1120.0, "net_pnl_formatted": "-$1,120", "action_text": "View >", "action_primary": False},
]


def get_symbol_wise_records(from_date, to_date, magic=None, force_sample=False):
    """
    Returns symbol-wise performance as a list of dicts for frontend rendering.
    If MT5 is live and has deals, uses real MT5 summary; otherwise returns sample dataset.
    """
    if not force_sample:
        summary_df = get_symbol_wise_performance(from_date, to_date, magic=magic)
        if isinstance(summary_df, pd.DataFrame) and not summary_df.empty:
            records = []
            for idx, row in summary_df.iterrows():
                pnl = float(row['net_profit'])
                pnl_formatted = f"{'+' if pnl >= 0 else '-'}${abs(pnl):,.2f}"
                pf = float(row.get('profit_factor', 1.9))
                records.append({
                    "pair": str(row['symbol']),
                    "trades": int(row['total_trades']),
                    "win_rate": float(row['win_rate']),
                    "profit_factor": pf,
                    "net_pnl": pnl,
                    "net_pnl_formatted": pnl_formatted,
                    "action_text": "Open calendar >" if idx == 0 else "View >",
                    "action_primary": idx == 0
                })
            return records

    return SAMPLE_PAIRS_DATA
