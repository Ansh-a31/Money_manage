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
    Uses real MT5 summary; only uses sample dataset if explicitly requested via force_sample=True.
    """
    if not force_sample:
        summary_df = get_symbol_wise_performance(from_date, to_date, magic=magic)
        if isinstance(summary_df, pd.DataFrame) and not summary_df.empty:
            records = []
            for idx, row in summary_df.iterrows():
                pnl = float(row['net_profit'])
                pnl_formatted = f"{'+' if pnl >= 0 else '-'}${abs(pnl):,.2f}"
                pf = float(row.get('profit_factor', 0.0))
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
        return []

    return SAMPLE_PAIRS_DATA


def get_pair_calendar_data(symbol: str = None, year: int = None, month: int = None, from_date=None, to_date=None, magic=None, force_sample=False) -> dict:
    """
    Returns calendar day-by-day P&L and monthly summary statistics for a given trading pair.
    Fetches real closed deals directly from MetaTrader 5.
    """
    import calendar

    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    # Determine date range for the query
    if from_date is None or to_date is None:
        last_day = calendar.monthrange(year, month)[1]
        query_start = datetime(year, month, 1, 0, 0, 0)
        query_end = datetime(year, month, last_day, 23, 59, 59)
    else:
        query_start = from_date
        query_end = to_date
        year = from_date.year
        month = from_date.month

    month_name = calendar.month_name[month]
    first_weekday = calendar.weekday(year, month, 1)
    grid_start_offset = (first_weekday + 1) % 7
    total_days_in_month = calendar.monthrange(year, month)[1]

    # Empty structure returned if MT5 is not connected or has no trades
    empty_result = {
        "status": "success",
        "source": "live_mt5",
        "symbol": symbol or "All",
        "year": year,
        "month": month,
        "month_name": month_name,
        "first_day_offset": grid_start_offset,
        "total_days_in_month": total_days_in_month,
        "month_net_pnl": 0.0,
        "month_net_pnl_formatted": "$0.00",
        "winning_days": 0,
        "losing_days": 0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "total_trades": 0,
        "best_day": None,
        "worst_day": None,
        "days": {},
        "message": "No trades found in MT5 for this period"
    }

    if not ensure_mt5_connected():
        return empty_result

    deals = mt5.history_deals_get(query_start, query_end)
    if deals is None or len(deals) == 0:
        return empty_result

    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    if df.empty or 'symbol' not in df.columns:
        return empty_result

    # Keep only real trades (exclude balance/deposit/withdrawal)
    df = df[df['symbol'] != '']
    if df.empty:
        return empty_result

    # If no symbol specified, take the most traded symbol in this period
    if not symbol or symbol == "All":
        symbol = str(df['symbol'].value_counts().index[0])

    # Match symbol flexibly (e.g. BTCUSDz, BTCUSD, BTC/USD)
    sym_clean = symbol.replace("/", "").replace(" ", "").upper()
    df['sym_clean'] = df['symbol'].astype(str).str.replace("/", "").str.replace(" ", "").str.upper()
    matched_df = df[df['sym_clean'] == sym_clean]
    if matched_df.empty:
        matched_df = df[df['sym_clean'].str.startswith(sym_clean.rstrip('Z'))]
    df = matched_df

    if df.empty:
        empty_result["symbol"] = symbol
        return empty_result

    if magic is not None and 'magic' in df.columns:
        df = df[df['magic'] == magic]
        if df.empty:
            empty_result["symbol"] = symbol
            return empty_result

    # Focus on closed trades (entry == 1)
    if 'entry' not in df.columns:
        empty_result["symbol"] = symbol
        return empty_result

    closes = df[df['entry'] == 1].copy()
    if closes.empty:
        empty_result["symbol"] = symbol
        return empty_result

    closes['net_profit'] = closes['profit'] + closes['commission'] + closes['swap']
    closes['deal_dt'] = pd.to_datetime(closes['time'], unit='s')
    closes['day'] = closes['deal_dt'].dt.day
    closes['date_str'] = closes['deal_dt'].dt.strftime('%Y-%m-%d')

    days_dict = {}
    for day, group in closes.groupby('day'):
        day_pnl = round(float(group['net_profit'].sum()), 2)
        trade_count = int(len(group))
        days_dict[int(day)] = {
            "day": int(day),
            "trades": trade_count,
            "net_pnl": day_pnl,
            "net_pnl_formatted": f"{'+' if day_pnl >= 0 else '-'}${abs(day_pnl):,.2f}",
            "is_profit": day_pnl >= 0
        }

    total_pnl = round(float(closes['net_profit'].sum()), 2)
    winning_days = sum(1 for d in days_dict.values() if d['net_pnl'] > 0)
    losing_days = sum(1 for d in days_dict.values() if d['net_pnl'] < 0)
    total_trades = int(len(closes))
    winning_trades = int((closes['net_profit'] > 0).sum())
    win_rate = round((winning_trades / total_trades * 100), 1) if total_trades > 0 else 0.0

    gp = float(closes[closes['net_profit'] > 0]['net_profit'].sum())
    gl = abs(float(closes[closes['net_profit'] < 0]['net_profit'].sum()))
    pf = round(gp / gl, 1) if gl > 0 else (round(gp, 1) if gp > 0 else 0.0)

    # Best and worst days
    sorted_days = sorted(days_dict.values(), key=lambda x: x['net_pnl'], reverse=True)
    best_day = None
    worst_day = None
    if sorted_days:
        b = sorted_days[0]
        best_day = {
            "day": b['day'],
            "date": f"{month_name[:3]} {b['day']}",
            "net_pnl": b['net_pnl'],
            "net_pnl_formatted": b['net_pnl_formatted']
        }
        w = sorted_days[-1]
        if w['net_pnl'] < 0:
            worst_day = {
                "day": w['day'],
                "date": f"{month_name[:3]} {w['day']}",
                "net_pnl": w['net_pnl'],
                "net_pnl_formatted": w['net_pnl_formatted']
            }

    return {
        "status": "success",
        "source": "live_mt5",
        "symbol": symbol,
        "year": year,
        "month": month,
        "month_name": month_name,
        "first_day_offset": grid_start_offset,
        "total_days_in_month": total_days_in_month,
        "month_net_pnl": total_pnl,
        "month_net_pnl_formatted": f"{'+' if total_pnl >= 0 else '-'}${abs(total_pnl):,.2f}",
        "winning_days": winning_days,
        "losing_days": losing_days,
        "win_rate": win_rate,
        "profit_factor": pf,
        "total_trades": total_trades,
        "best_day": best_day,
        "worst_day": worst_day,
        "days": days_dict
    }
