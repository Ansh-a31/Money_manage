"""
Stock Journey Dashboard - Standard Python HTTP Server
Exposes MetaTrader 5 API endpoints for the dashboard frontend.
Uses Python's standard library: http.server and socketserver.
"""

import os
import sys
import json
import mimetypes
import urllib.parse
from datetime import datetime, time, date
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.mt5_service import (
    get_overview_metrics,
    get_total_profit,
    get_symbol_wise_performance,
    get_symbol_wise_records,
    ensure_mt5_connected
)

HOST = "0.0.0.0"
PORT = 5000

CURRENT_MODE = {"force_sample": False}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests concurrently using threads."""
    daemon_threads = True
    allow_reuse_address = True


def parse_datetime_param(val: str, is_end: bool = False) -> datetime:
    """Parses date or datetime string into a datetime object."""
    if not val:
        return None
    val = val.strip()
    
    # Supported formats
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):
        try:
            dt = datetime.strptime(val, fmt)
            # If only date was provided and is_end is True, set to end of day
            if len(val) <= 10 and is_end:
                return dt.replace(hour=23, minute=59, second=59)
            return dt
        except ValueError:
            continue
    return None


class DashboardAPIHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Add CORS and JSON headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def send_json(self, data: dict, status: int = HTTPStatus.OK):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_file(self, filepath, content_type):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/toggle-mode":
            CURRENT_MODE["force_sample"] = not CURRENT_MODE["force_sample"]
            mode_name = "Sample data" if CURRENT_MODE["force_sample"] else "Live MT5"
            self.send_json({
                "status": "success",
                "force_sample": CURRENT_MODE["force_sample"],
                "mode": mode_name
            })
            return
        self.send_json({"status": "received"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # Serve Frontend HTML
        if path == "/" or path == "/index.html":
            index_path = os.path.join(BASE_DIR, "index.html")
            if not os.path.exists(index_path):
                index_path = os.path.join(BASE_DIR, "templates", "index.html")
            self.serve_file(index_path, "text/html; charset=utf-8")
            return

        # Serve Static CSS / JS
        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = os.path.join(BASE_DIR, "static", rel_path.replace("/", os.sep))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.serve_file(file_path, mime or "application/octet-stream")
                return
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
                return

        # Health check
        if path == "/api/health" or path == "/health":
            connected = ensure_mt5_connected()
            self.send_json({
                "status": "ok",
                "mt5_connected": connected,
                "mode": "Sample data" if CURRENT_MODE["force_sample"] else "Live MT5",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            return

        # 1. Single API: Top Overview Metrics
        # Returns: Net Profit, Win Rate, Profit Factor, Total Trades
        if path in ("/api/overview-metrics", "/api/overview", "/api/metrics"):
            from_str = params.get("from_date", [None])[0] or params.get("start_date", [None])[0]
            to_str = params.get("to_date", [None])[0] or params.get("end_date", [None])[0]
            symbol = params.get("symbol", [None])[0]
            magic_val = params.get("magic", [None])[0]
            magic = int(magic_val) if magic_val and magic_val.isdigit() else None

            from_dt = parse_datetime_param(from_str, is_end=False)
            to_dt = parse_datetime_param(to_str, is_end=True)

            # Default date range if not specified: Today (start of today to now)
            now = datetime.now()
            if not from_dt:
                from_dt = datetime(now.year, now.month, now.day, 0, 0, 0)
            if not to_dt:
                to_dt = now

            use_mock = params.get("mock", ["false"])[0].lower() in ("true", "1") or CURRENT_MODE["force_sample"]
            
            if use_mock:
                self.send_json({
                    "status": "success",
                    "source": "sample_data",
                    "from_date": str(from_dt),
                    "to_date": str(to_dt),
                    "symbol": symbol,
                    "magic": magic,
                    "net_profit": 8340.0,
                    "net_profit_formatted": "+$8,340",
                    "win_rate": 58.0,
                    "win_rate_formatted": "58%",
                    "profit_factor": 1.9,
                    "profit_factor_formatted": "1.9",
                    "total_trades": 312,
                    "total_trades_formatted": "312"
                })
                return

            result = get_overview_metrics(
                from_date=from_dt,
                to_date=to_dt,
                symbol=symbol,
                magic=magic
            )

            # Fallback if MT5 not connected or empty
            if result.get("status") == "error":
                self.send_json({
                    "status": "success",
                    "source": "sample_data",
                    "notice": "MT5 terminal not running; serving sample data",
                    "from_date": str(from_dt),
                    "to_date": str(to_dt),
                    "net_profit": 8340.0,
                    "net_profit_formatted": "+$8,340",
                    "win_rate": 58.0,
                    "win_rate_formatted": "58%",
                    "profit_factor": 1.9,
                    "profit_factor_formatted": "1.9",
                    "total_trades": 312,
                    "total_trades_formatted": "312"
                })
                return

            # Format formatted fields for easy UI binding
            pnl = result.get("net_profit", 0.0)
            result["net_profit_formatted"] = f"{'+' if pnl >= 0 else '-'}${abs(pnl):,.2f}"
            result["win_rate_formatted"] = f"{result.get('win_rate', 0)}%"
            result["profit_factor_formatted"] = f"{result.get('profit_factor', 0):.1f}"
            result["total_trades_formatted"] = str(result.get("total_trades", 0))
            self.send_json(result)
            return

        # 2. Pairs Traded Table API (from get_symbol_wise_performance)
        if path in ("/api/pairs", "/api/symbols", "/api/pairs-traded"):
            from_str = params.get("from_date", [None])[0] or params.get("start_date", [None])[0]
            to_str = params.get("to_date", [None])[0] or params.get("end_date", [None])[0]
            magic_val = params.get("magic", [None])[0]
            magic = int(magic_val) if magic_val and magic_val.isdigit() else None

            now = datetime.now()
            from_dt = parse_datetime_param(from_str, is_end=False) or datetime(now.year, now.month, now.day, 0, 0, 0)
            to_dt = parse_datetime_param(to_str, is_end=True) or now

            pairs = get_symbol_wise_records(
                from_date=from_dt,
                to_date=to_dt,
                magic=magic,
                force_sample=CURRENT_MODE["force_sample"]
            )
            self.send_json({
                "status": "success",
                "pairs": pairs,
                "count": len(pairs)
            })
            return

        # 3. Total Profit only API (Direct wrapper over get_total_profit)
        if path in ("/api/total-profit", "/api/profit"):
            from_str = params.get("from_date", [None])[0] or params.get("start_date", [None])[0]
            to_str = params.get("to_date", [None])[0] or params.get("end_date", [None])[0]
            symbol = params.get("symbol", [None])[0]
            magic_val = params.get("magic", [None])[0]
            magic = int(magic_val) if magic_val and magic_val.isdigit() else None

            now = datetime.now()
            from_dt = parse_datetime_param(from_str, is_end=False) or datetime(now.year, now.month, now.day, 0, 0, 0)
            to_dt = parse_datetime_param(to_str, is_end=True) or now

            net_profit = get_total_profit(
                from_date=from_dt,
                to_date=to_dt,
                symbol=symbol,
                magic=magic
            )
            self.send_json({
                "status": "success",
                "from_date": str(from_dt),
                "to_date": str(to_dt),
                "symbol": symbol,
                "magic": magic,
                "net_profit": net_profit
            })
            return

        # 404 for unknown endpoints
        self.send_json({
            "status": "error",
            "message": f"Endpoint '{path}' not found",
            "available_endpoints": [
                "/api/overview-metrics?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD",
                "/api/total-profit?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD",
                "/api/health"
            ]
        }, status=HTTPStatus.NOT_FOUND)


def run_server(host=HOST, port=PORT):
    server = ThreadedHTTPServer((host, port), DashboardAPIHandler)
    print("=" * 65)
    print(" Stock Journey Dashboard API Server (Standard Python HTTP)")
    print(f" -> Server URL:        http://127.0.0.1:{port}")
    print(f" -> Overview Metrics:  http://127.0.0.1:{port}/api/overview-metrics")
    print(f" -> Total Profit API:  http://127.0.0.1:{port}/api/total-profit")
    print(f" -> Health Check:      http://127.0.0.1:{port}/api/health")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    port = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)
